from __future__ import annotations

import argparse
import warnings
from pathlib import Path

# SLSQP 在 efficient_frontier 求解时偶尔会越界，scipy 会自动 clip 并发 RuntimeWarning。
# 不影响最终解，但会污染控制台和 Streamlit 输出，统一屏蔽。
warnings.filterwarnings(
    "ignore",
    message="Values in x were outside bounds",
    category=RuntimeWarning,
)

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

from analysis_engine import (
    OUTPUT_DIR,
    ROOT,
    TRADING_DAYS,
    annualized_return,
    annualized_volatility,
    beta_to_benchmark,
    calmar_ratio,
    drawdown_coverage,
    historical_cvar,
    historical_var,
    information_ratio,
    max_drawdown,
    max_drawdown_duration,
    return_matrix,
    sharpe_ratio,
    sortino_ratio,
    tracking_error,
)
from paths import ANALYSIS_UNIVERSE_50_CSV, DAILY_PRICES_CSV
from rules_engine import (
    adjusted_covariance,
    adjusted_mean_returns,
    bounds_from_rules,
    build_rule_set,
    export_active_rules,
    load_rules,
)


MAX_WEIGHT = 0.10
COVARIANCE_METHODS = ("sample", "ledoit_wolf", "factor_shrinkage")


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    universe = pd.read_csv(ANALYSIS_UNIVERSE_50_CSV)
    prices = pd.read_csv(DAILY_PRICES_CSV, parse_dates=["date"])
    tickers = universe["ticker"].tolist()
    wanted = tickers + ["^GSPC", "^NDX", "QQQ", "XLK", "^IRX"]
    subset = prices[prices["ticker"].isin(wanted)].copy()
    subset["price"] = subset["adj_close"].fillna(subset["close"])
    price_wide = subset.pivot(index="date", columns="ticker", values="price").sort_index().ffill()
    returns = return_matrix(price_wide)
    return universe, returns, tickers


def annualized_mean_returns(returns: pd.DataFrame) -> pd.Series:
    return returns.mean() * TRADING_DAYS


def annualized_covariance(returns: pd.DataFrame, method: str = "sample") -> pd.DataFrame:
    """计算年化协方差矩阵。

    method:
        - sample: 样本协方差（无偏估计），易受估计噪声影响。
        - ledoit_wolf: Ledoit-Wolf 收缩估计。把样本协方差向常数对角阵收缩，
          缩小估计噪声，提升样本外稳定性。对小样本 / 高维场景尤其有用。
    """
    clean = returns.dropna(how="any")
    if method == "sample":
        return clean.cov() * TRADING_DAYS
    if method == "ledoit_wolf":
        # LedoitWolf 期望日频收益的原始矩阵，输出日频协方差，再乘 TRADING_DAYS 年化。
        estimator = LedoitWolf().fit(clean.values)
        cov = pd.DataFrame(estimator.covariance_, index=clean.columns, columns=clean.columns)
        return cov * TRADING_DAYS
    if method == "factor_shrinkage":
        return _annualized_covariance_factor_shrinkage(clean)
    raise ValueError(f"Unknown covariance method: {method}")


def covariance_shrinkage_intensity(returns: pd.DataFrame) -> float:
    """返回 Ledoit-Wolf 估计的收缩强度（0 到 1，越大说明样本协方差越不稳）。"""
    clean = returns.dropna(how="any")
    return float(LedoitWolf().fit(clean.values).shrinkage_)


def _annualized_covariance_factor_shrinkage(returns: pd.DataFrame) -> pd.DataFrame:
    """向单因子（板块等权收益）收缩的协方差估计。

    适用于单板块高相关资产（如纯科技股池）。
    比 Ledoit-Wolf 向单位矩阵收缩更贴合数据结构。
    """
    clean = returns.dropna(how="any")
    # 板块因子：等权组合收益
    factor = clean.mean(axis=1)
    factor_var = factor.var()

    # 估计每只股票的 β
    betas: dict[str, float] = {}
    residuals_var: dict[str, float] = {}
    for ticker in clean.columns:
        stock = clean[ticker]
        beta = stock.cov(factor) / factor_var if factor_var > 0 else 1.0
        betas[ticker] = beta
        residuals_var[ticker] = (stock - beta * factor).var()

    beta_vec = pd.Series(betas)
    sigma_residual = pd.Series(residuals_var)

    # 因子模型隐含协方差
    beta_matrix = np.outer(beta_vec.values, beta_vec.values)
    factor_cov = beta_matrix * factor_var
    np.fill_diagonal(factor_cov, factor_cov.diagonal() + sigma_residual.values)
    cov_factor = pd.DataFrame(factor_cov, index=clean.columns, columns=clean.columns)

    # 简化版 OAS 收缩强度
    shrinkage = _oas_shrinkage_intensity(clean)

    sample_cov = clean.cov().values
    shrunk = (1 - shrinkage) * sample_cov + shrinkage * cov_factor.values
    return pd.DataFrame(shrunk, index=clean.columns, columns=clean.columns) * TRADING_DAYS


def _oas_shrinkage_intensity(returns: pd.DataFrame) -> float:
    """Oracle Approximating Shrinkage 收缩强度估计（简化版）。"""
    clean = returns.dropna(how="any")
    sample_cov = clean.cov().values
    n = clean.shape[1]
    t = clean.shape[0]

    tr_s = np.trace(sample_cov)
    tr_s2 = np.trace(sample_cov @ sample_cov)

    d_sq = (1.0 / n) * (tr_s2 - (tr_s ** 2) / n)
    b_sq = 0.0
    for i in range(t):
        xi = clean.values[i : i + 1, :].T
        diff = xi @ xi.T - sample_cov
        b_sq += np.trace(diff @ diff)
    b_sq /= (t * t)

    rho = min(1.0, b_sq / (d_sq + b_sq) if (d_sq + b_sq) > 0 else 0.0)
    return float(rho)


def optimize_portfolio_cvar(
    returns: pd.DataFrame,
    alpha: float = 0.05,
    max_weight: float = 0.10,
    risk_free_rate: float = 0.0,
    rules: pd.DataFrame | None = None,
    as_of_date: pd.Timestamp | None = None,
) -> pd.Series:
    """最小 CVaR (Conditional Value-at-Risk) 组合优化。

    Rockafellar & Uryasev (2000) 方法：
    min  γ + 1/(α·T) · Σ max(0, -w·r_t + risk_free - γ)

    参数:
        returns: (T, N) 日收益 DataFrame
        alpha: CVaR 置信水平（默认 0.05 = 95% CVaR）
        max_weight: 单股最大权重
        risk_free_rate: 年化无风险利率
    """
    clean = returns.dropna(how="any")
    tickers = clean.columns.tolist()
    T, N = clean.shape

    if as_of_date is None:
        as_of_date = clean.index.max()

    from rules_engine import load_rules, build_rule_set, bounds_from_rules
    if rules is None:
        rules = load_rules(None)
    rule_set = build_rule_set(tickers, rules, as_of_date, default_max_weight=max_weight)
    bounds = bounds_from_rules(tickers, rule_set)

    ret_matrix = clean.values
    initial = np.array([1.0 / N] * N + [0.0])  # [weights..., γ]

    def objective(x: np.ndarray) -> float:
        w = x[:N]
        gamma = x[N]
        portfolio_returns = ret_matrix @ w
        shortfall = -portfolio_returns + risk_free_rate / TRADING_DAYS - gamma
        return gamma + (1.0 / (alpha * T)) * np.sum(np.maximum(shortfall, 0.0))

    constraints = ({"type": "eq", "fun": lambda w: np.sum(w[:N]) - 1.0},)
    cvar_bounds = list(bounds) + [(None, None)]

    result = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=cvar_bounds,
        constraints=constraints,
        options={"maxiter": 2000, "ftol": 1e-10},
    )

    if not result.success:
        raise RuntimeError(f"CVaR optimization failed: {result.message}")
    return pd.Series(result.x[:N], index=tickers, name="min_cvar")


def portfolio_return(weights: np.ndarray, mean_returns: pd.Series) -> float:
    return float(np.dot(weights, mean_returns.values))


def portfolio_volatility(weights: np.ndarray, covariance: pd.DataFrame) -> float:
    variance = float(weights.T @ covariance.values @ weights)
    return float(np.sqrt(max(variance, 0)))


def feasible_initial_weights(min_weights: pd.Series, max_weights: pd.Series) -> np.ndarray:
    min_values = min_weights.values.astype(float)
    max_values = max_weights.values.astype(float)
    remaining = 1.0 - min_values.sum()
    capacity = max_values - min_values
    if remaining < -1e-9:
        raise ValueError("Minimum weights exceed 100%.")
    if capacity.sum() + min_values.sum() < 1 - 1e-9:
        raise ValueError("Maximum weights cannot sum to 100%.")
    if remaining <= 1e-12:
        return min_values
    return min_values + remaining * capacity / capacity.sum()


def neg_sharpe(weights: np.ndarray, mean_returns: pd.Series, covariance: pd.DataFrame, risk_free_rate: float) -> float:
    vol = portfolio_volatility(weights, covariance)
    if vol <= 0:
        return 1e9
    return -((portfolio_return(weights, mean_returns) - risk_free_rate) / vol)


def min_variance_objective(weights: np.ndarray, covariance: pd.DataFrame) -> float:
    return float(weights.T @ covariance.values @ weights)


def optimize_portfolio(
    returns: pd.DataFrame,
    objective: str,
    max_weight: float = MAX_WEIGHT,
    risk_free_rate: float = 0.0,
    rules: pd.DataFrame | None = None,
    as_of_date: pd.Timestamp | None = None,
    covariance_method: str = "sample",
) -> pd.Series:
    clean = returns.dropna(how="any")
    tickers = clean.columns.tolist()
    if rules is None:
        rules = load_rules(None)
    if as_of_date is None:
        as_of_date = clean.index.max()
    rule_set = build_rule_set(tickers, rules, as_of_date, default_max_weight=max_weight)
    bounds = bounds_from_rules(tickers, rule_set)
    initial = feasible_initial_weights(rule_set.min_weights, rule_set.max_weights)
    constraints = ({"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0},)
    mean_returns = annualized_mean_returns(clean)
    covariance = annualized_covariance(clean, method=covariance_method)
    mean_returns = adjusted_mean_returns(mean_returns, rule_set)
    covariance = adjusted_covariance(covariance, rule_set)

    if objective == "min_variance":
        result = minimize(
            min_variance_objective,
            initial,
            args=(covariance,),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-12},
        )
    elif objective == "max_sharpe":
        result = minimize(
            neg_sharpe,
            initial,
            args=(mean_returns, covariance, risk_free_rate),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-12},
        )
    else:
        raise ValueError(f"Unknown objective: {objective}")

    if not result.success:
        raise RuntimeError(f"Optimization failed for {objective}: {result.message}")
    return pd.Series(result.x, index=tickers, name=objective)


def portfolio_return_series(returns: pd.DataFrame, weights: pd.Series, name: str) -> pd.Series:
    aligned = returns[weights.index].dropna(how="any")
    return aligned.dot(weights).rename(name)


def risk_free_rate_from_irx(returns: pd.DataFrame) -> float:
    if "^IRX" not in returns.columns:
        return 0.0
    # Approximate annual risk-free level from daily ^IRX observations.
    # ^IRX returns are not used; this function is only a fallback when price levels are unavailable.
    return 0.0


def metrics_for_portfolio(name: str, series: pd.Series, benchmark_returns: pd.DataFrame, risk_free_daily: pd.Series) -> dict[str, float | str]:
    row = {
        "portfolio": name,
        "annualized_return": annualized_return(series),
        "annualized_volatility": annualized_volatility(series),
        "sharpe_ratio": sharpe_ratio(series, risk_free_daily),
        "sortino_ratio": sortino_ratio(series, risk_free_daily),
        "max_drawdown": max_drawdown(series),
        "drawdown_coverage": drawdown_coverage(series),
        "max_drawdown_duration_days": max_drawdown_duration(series),
        "calmar_ratio": calmar_ratio(series),
        "var_95_daily": historical_var(series),
        "cvar_95_daily": historical_cvar(series),
        "cumulative_return": (1 + series.dropna()).prod() - 1,
        "observations": int(series.dropna().count()),
    }
    for ticker in ["^GSPC", "^NDX", "QQQ", "XLK"]:
        clean_name = ticker.replace("^", "").lower()
        row[f"beta_{clean_name}"] = beta_to_benchmark(series, benchmark_returns[ticker])
        row[f"tracking_error_{clean_name}"] = tracking_error(series, benchmark_returns[ticker])
        row[f"information_ratio_{clean_name}"] = information_ratio(series, benchmark_returns[ticker])
    return row


def efficient_frontier(returns: pd.DataFrame, points: int = 40, max_weight: float = MAX_WEIGHT, covariance_method: str = "sample") -> pd.DataFrame:
    clean = returns.dropna(how="any")
    mean_returns = annualized_mean_returns(clean)
    covariance = annualized_covariance(clean, method=covariance_method)
    n_assets = len(clean.columns)
    initial = np.repeat(1 / n_assets, n_assets)
    bounds = tuple((0.0, max_weight) for _ in range(n_assets))
    min_ret = float(mean_returns.min())
    max_ret = float(mean_returns.max() * max_weight + mean_returns.nlargest(int(1 / max_weight)).mean() * (1 - max_weight))
    target_returns = np.linspace(min_ret, max(mean_returns.mean(), max_ret), points)
    rows = []

    for target in target_returns:
        constraints = (
            {"type": "eq", "fun": lambda weights: np.sum(weights) - 1.0},
            {"type": "eq", "fun": lambda weights, target_return=target: np.dot(weights, mean_returns.values) - target_return},
        )
        result = minimize(
            min_variance_objective,
            initial,
            args=(covariance,),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
            options={"maxiter": 1000, "ftol": 1e-10},
        )
        if result.success:
            vol = portfolio_volatility(result.x, covariance)
            ret = portfolio_return(result.x, mean_returns)
            rows.append({"target_return": target, "annualized_return": ret, "annualized_volatility": vol})
    return pd.DataFrame(rows)


def constrained_equal_weight(tickers: list[str], rule_set) -> pd.Series:
    weights = feasible_initial_weights(rule_set.min_weights, rule_set.max_weights)
    return pd.Series(weights, index=tickers, name="equal_weight")


def build_weights_frame(weights: dict[str, pd.Series]) -> pd.DataFrame:
    frame = pd.concat(weights.values(), axis=1)
    frame.columns = list(weights.keys())
    frame = frame.fillna(0)
    frame.index.name = "ticker"
    return frame.reset_index()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Markowitz portfolio optimization.")
    parser.add_argument("--max-weight", type=float, default=MAX_WEIGHT, help="Maximum single-stock weight.")
    parser.add_argument("--rules", default=None, help="Optional human override CSV.")
    parser.add_argument(
        "--covariance",
        choices=COVARIANCE_METHODS,
        default="sample",
        help="协方差估计方法。sample 样本协方差；ledoit_wolf 收缩估计。",
    )
    parser.add_argument("--summary", action="store_true", help="Print existing optimization output summary.")
    return parser.parse_args()


def print_summary() -> None:
    metrics_path = OUTPUT_DIR / "optimized_portfolio_metrics.csv"
    weights_path = OUTPUT_DIR / "portfolio_weights.csv"
    if metrics_path.exists():
        metrics = pd.read_csv(metrics_path)
        cols = ["portfolio", "annualized_return", "annualized_volatility", "sharpe_ratio", "max_drawdown", "drawdown_coverage"]
        print(metrics[cols].to_string(index=False), flush=True)
    if weights_path.exists():
        weights = pd.read_csv(weights_path)
        for column in [col for col in weights.columns if col != "ticker"]:
            top = weights[["ticker", column]].sort_values(column, ascending=False).head(10)
            print(f"top_weights_{column}:", flush=True)
            print(top.to_string(index=False), flush=True)


def main() -> int:
    args = parse_args()
    if args.summary:
        print_summary()
        return 0

    OUTPUT_DIR.mkdir(exist_ok=True)
    _, returns, tickers = load_data()
    stock_returns = returns[tickers].dropna(how="any")
    benchmark_returns = returns[["^GSPC", "^NDX", "QQQ", "XLK"]]
    risk_free_daily = pd.Series(0.0, index=returns.index)
    rules = load_rules(args.rules)
    as_of_date = stock_returns.index.max()
    rule_set = build_rule_set(tickers, rules, as_of_date, default_max_weight=args.max_weight)

    equal_weight = constrained_equal_weight(tickers, rule_set)
    min_var = optimize_portfolio(
        stock_returns,
        "min_variance",
        max_weight=args.max_weight,
        rules=rules,
        as_of_date=as_of_date,
        covariance_method=args.covariance,
    )
    max_sharpe = optimize_portfolio(
        stock_returns,
        "max_sharpe",
        max_weight=args.max_weight,
        risk_free_rate=0.0,
        rules=rules,
        as_of_date=as_of_date,
        covariance_method=args.covariance,
    )

    weights = {
        "equal_weight": equal_weight,
        "min_variance": min_var,
        "max_sharpe": max_sharpe,
    }
    weight_frame = build_weights_frame(weights)

    portfolio_returns = pd.concat(
        [portfolio_return_series(stock_returns, weights[name], name) for name in weights],
        axis=1,
    )
    cumulative = (1 + portfolio_returns).cumprod() - 1
    frontier = efficient_frontier(stock_returns, max_weight=args.max_weight, covariance_method=args.covariance)
    metrics = pd.DataFrame(
        [metrics_for_portfolio(name, portfolio_returns[name], benchmark_returns, risk_free_daily) for name in portfolio_returns.columns]
    )
    metrics["covariance_method"] = args.covariance
    if args.covariance == "ledoit_wolf":
        metrics["lw_shrinkage"] = covariance_shrinkage_intensity(stock_returns)

    weight_frame.to_csv(OUTPUT_DIR / "portfolio_weights.csv", index=False)
    portfolio_returns.reset_index().to_csv(OUTPUT_DIR / "optimized_portfolio_returns.csv", index=False)
    cumulative.reset_index().to_csv(OUTPUT_DIR / "optimized_portfolio_cumulative_returns.csv", index=False)
    frontier.to_csv(OUTPUT_DIR / "efficient_frontier.csv", index=False)
    metrics.to_csv(OUTPUT_DIR / "optimized_portfolio_metrics.csv", index=False)
    export_active_rules(rule_set, OUTPUT_DIR / "active_human_overrides.csv")

    print(f"wrote optimization outputs to {OUTPUT_DIR}", flush=True)
    print(f"active_rules={len(rule_set.active_rules)}", flush=True)
    print(metrics[["portfolio", "annualized_return", "annualized_volatility", "sharpe_ratio", "max_drawdown"]].to_string(index=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
