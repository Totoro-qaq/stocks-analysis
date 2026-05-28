"""组合优化服务 — 封装 src/portfolio_optimization.py + walk_forward.py + stat_tests.py。"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from paths import ANALYSIS_UNIVERSE_50_CSV, DAILY_PRICES_CSV, OUTPUT_DIR, HUMAN_OVERRIDES_CSV


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return df.replace({np.nan: None}).to_dict(orient="records")


def run_portfolio_optimization(
    objective: str = "max_sharpe",
    covariance_method: str = "sample",
    max_weight: float = 0.10,
    use_black_litterman: bool = False,
    cvar_alpha: float = 0.05,
) -> dict[str, Any]:
    """运行组合优化，返回权重 + 指标 + 有效前沿。"""
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    from portfolio_optimization import (
        load_data,
        optimize_portfolio,
        constrained_equal_weight,
        portfolio_return_series,
        metrics_for_portfolio,
        build_weights_frame,
        efficient_frontier,
        covariance_shrinkage_intensity,
    )
    from rules_engine import load_rules, build_rule_set

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    _, returns, tickers = load_data()
    stock_returns = returns[tickers].dropna(how="any")
    benchmark_returns = returns[["^GSPC", "^NDX", "QQQ", "XLK"]].reindex(returns.index)
    risk_free_daily = pd.Series(0.0, index=returns.index)

    rules = load_rules(HUMAN_OVERRIDES_CSV if HUMAN_OVERRIDES_CSV.exists() else None)
    as_of_date = stock_returns.index.max()
    rule_set = build_rule_set(tickers, rules, as_of_date, default_max_weight=max_weight)

    weight_map: dict[str, pd.Series] = {}

    # 等权
    weight_map["equal_weight"] = constrained_equal_weight(tickers, rule_set).rename("equal_weight")

    # 马科维茨
    for obj, name in [("min_variance", "min_variance"), ("max_sharpe", "max_sharpe")]:
        try:
            w = optimize_portfolio(
                stock_returns, obj, max_weight=max_weight,
                rules=rules, as_of_date=as_of_date, covariance_method=covariance_method,
            )
            weight_map[name] = w.rename(name)
        except Exception:
            weight_map[name] = pd.Series(0.0, index=pd.Index(tickers, name="ticker")).rename(name)

    # CVaR（如果请求）
    if objective == "min_cvar":
        try:
            from portfolio_optimization import optimize_portfolio_cvar  # type: ignore[attr-defined]  # noqa: F811
            w_cvar = optimize_portfolio_cvar(stock_returns, alpha=cvar_alpha, max_weight=max_weight)
            weight_map["min_cvar"] = w_cvar.rename("min_cvar")
        except Exception:
            weight_map["min_cvar"] = pd.Series(0.0, index=pd.Index(tickers, name="ticker")).rename("min_cvar")

    # HRP
    try:
        from portfolio_hrp import hrp_weights
        w_hrp = hrp_weights(stock_returns)
        weight_map["hrp"] = pd.Series(w_hrp, index=tickers, name="hrp")
    except Exception:
        weight_map["hrp"] = pd.Series(0.0, index=pd.Index(tickers, name="ticker")).rename("hrp")

    weight_frame = build_weights_frame(weight_map)
    portfolio_returns_df = pd.concat(
        [portfolio_return_series(stock_returns, weight_map[name], name) for name in weight_map],
        axis=1,
    )
    cumulative = (1 + portfolio_returns_df).cumprod() - 1
    frontier = efficient_frontier(stock_returns, max_weight=max_weight, covariance_method=covariance_method)
    metrics = pd.DataFrame([
        metrics_for_portfolio(name, portfolio_returns_df[name], benchmark_returns, risk_free_daily)
        for name in portfolio_returns_df.columns
    ])
    metrics["covariance_method"] = covariance_method
    if covariance_method == "ledoit_wolf":
        metrics["lw_shrinkage"] = covariance_shrinkage_intensity(stock_returns)

    # 写 CSV
    weight_frame.to_csv(OUTPUT_DIR / "portfolio_weights.csv", index=False)
    portfolio_returns_df.reset_index().to_csv(OUTPUT_DIR / "optimized_portfolio_returns.csv", index=False)
    cumulative.reset_index().to_csv(OUTPUT_DIR / "optimized_portfolio_cumulative_returns.csv", index=False)
    frontier.to_csv(OUTPUT_DIR / "efficient_frontier.csv", index=False)
    metrics.to_csv(OUTPUT_DIR / "optimized_portfolio_metrics.csv", index=False)

    from rules_engine import export_active_rules
    export_active_rules(rule_set, OUTPUT_DIR / "active_human_overrides.csv")

    return {
        "weights": _df_to_records(weight_frame),
        "portfolio_returns": _df_to_records(portfolio_returns_df.reset_index()),
        "cumulative_returns": _df_to_records(cumulative.reset_index()),
        "efficient_frontier": _df_to_records(frontier),
        "metrics": _df_to_records(metrics),
        "portfolio_names": list(weight_map.keys()),
    }


def run_walk_forward(
    train_days: int = 756,
    test_days: int = 126,
    step_days: int = 126,
    max_weight: float = 0.10,
    covariance_method: str = "sample",
) -> dict[str, Any]:
    """运行 Walk-forward 前向验证。"""
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)

    from walk_forward import WindowConfig, run_walk_forward, summary_from_metrics
    from rules_engine import load_rules

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    config = WindowConfig(
        train_days=train_days, test_days=test_days, step_days=step_days,
        max_weight=max_weight, covariance_method=covariance_method,
    )
    rules = load_rules(HUMAN_OVERRIDES_CSV if HUMAN_OVERRIDES_CSV.exists() else None)
    metrics, weights, returns_df = run_walk_forward(config, rules)
    summary = summary_from_metrics(metrics)

    # 写 CSV
    metrics.to_csv(OUTPUT_DIR / "walk_forward_window_metrics.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "walk_forward_summary.csv", index=False)
    weights.to_csv(OUTPUT_DIR / "walk_forward_weights.csv", index=False)
    returns_df.to_csv(OUTPUT_DIR / "walk_forward_returns.csv", index=False)

    return {
        "summary": _df_to_records(summary),
        "window_metrics": _df_to_records(metrics),
        "weights": _df_to_records(weights),
    }


def run_stat_tests(samples: int = 2000, block_size: int = 21) -> dict[str, Any]:
    """运行统计检验 + bootstrap。"""
    import warnings
    warnings.filterwarnings("ignore")

    from stat_tests import run_tests

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    tests, bootstrap = run_tests(samples, block_size)
    tests.to_csv(OUTPUT_DIR / "significance_tests.csv", index=False)
    bootstrap.to_csv(OUTPUT_DIR / "bootstrap_intervals.csv", index=False)

    return {
        "significance_tests": _df_to_records(tests),
        "bootstrap_intervals": _df_to_records(bootstrap),
    }


def get_optimized_metrics() -> list[dict[str, Any]]:
    path = OUTPUT_DIR / "optimized_portfolio_metrics.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))


def get_portfolio_weights() -> list[dict[str, Any]]:
    path = OUTPUT_DIR / "portfolio_weights.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))


def get_efficient_frontier() -> list[dict[str, Any]]:
    path = OUTPUT_DIR / "efficient_frontier.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))


def get_optimized_returns() -> list[dict[str, Any]]:
    path = OUTPUT_DIR / "optimized_portfolio_returns.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path, parse_dates=["date"]))


def get_optimized_cumulative_returns() -> list[dict[str, Any]]:
    path = OUTPUT_DIR / "optimized_portfolio_cumulative_returns.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path, parse_dates=["date"]))


def get_wf_summary() -> list[dict[str, Any]]:
    path = OUTPUT_DIR / "walk_forward_summary.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))


def get_wf_window_metrics() -> list[dict[str, Any]]:
    path = OUTPUT_DIR / "walk_forward_window_metrics.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))


def get_significance_tests() -> list[dict[str, Any]]:
    path = OUTPUT_DIR / "significance_tests.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))


def get_bootstrap_intervals() -> list[dict[str, Any]]:
    path = OUTPUT_DIR / "bootstrap_intervals.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))

def get_hrp_dendrogram() -> dict[str, Any]:
    from paths import SRC_DIR

    if not DAILY_PRICES_CSV.exists() or not ANALYSIS_UNIVERSE_50_CSV.exists():
        return {"name": "No Data", "children": []}

    prices = pd.read_csv(DAILY_PRICES_CSV, parse_dates=["date"])
    universe = pd.read_csv(ANALYSIS_UNIVERSE_50_CSV)
    tickers = universe["ticker"].tolist()

    subset = prices[prices["ticker"].isin(tickers)].copy()
    if subset.empty:
        return {"name": "No Data", "children": []}

    subset["price"] = subset["adj_close"].fillna(subset["close"])
    price_wide = subset.pivot(index="date", columns="ticker", values="price").sort_index().ffill()
    stock_returns = (
        price_wide.pct_change(fill_method=None)
        .replace([np.inf, -np.inf], np.nan)
        .dropna(how="any")
    )

    if stock_returns.empty or stock_returns.shape[1] < 2:
        return {"name": "No Data", "children": []}

    import sys
    from scipy.cluster.hierarchy import linkage
    from scipy.spatial.distance import squareform
    
    sys.path.insert(0, str(SRC_DIR))
    from portfolio_hrp import correl_dist
    
    valid_tickers = stock_returns.columns.tolist()
    corr = stock_returns.corr()
    dist = correl_dist(corr)
    condensed = squareform(dist)
    Z = linkage(condensed, method="ward")
    
    n = len(valid_tickers)
    nodes = {i: {"name": valid_tickers[i], "value": 1.0} for i in range(n)}
    
    for i, merge in enumerate(Z):
        left_idx = int(merge[0])
        right_idx = int(merge[1])
        dist_val = float(merge[2])
        
        new_node = {
            "name": f"Cluster_{i+1}",
            "value": dist_val,
            "children": [nodes[left_idx], nodes[right_idx]]
        }
        nodes[n + i] = new_node
        
    root = nodes[n + len(Z) - 1]
    root["name"] = "Universe"
    return root

