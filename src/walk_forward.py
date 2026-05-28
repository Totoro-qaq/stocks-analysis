from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np
import pandas as pd

from analysis_engine import (
    OUTPUT_DIR,
    ROOT,
    TRADING_DAYS,
    annualized_return,
    annualized_volatility,
    calmar_ratio,
    drawdown_coverage,
    historical_cvar,
    historical_var,
    information_ratio,
    max_drawdown,
    return_matrix,
    sharpe_ratio,
    sortino_ratio,
)
from portfolio_optimization import optimize_portfolio
from portfolio_optimization import constrained_equal_weight
from paths import ANALYSIS_UNIVERSE_50_CSV, DAILY_PRICES_CSV
from rules_engine import build_rule_set, load_rules


@dataclass(frozen=True)
class WindowConfig:
    train_days: int = 756
    test_days: int = 126
    step_days: int = 126
    max_weight: float = 0.10
    covariance_method: str = "sample"


def load_returns() -> tuple[pd.DataFrame, list[str]]:
    universe = pd.read_csv(ANALYSIS_UNIVERSE_50_CSV)
    prices = pd.read_csv(DAILY_PRICES_CSV, parse_dates=["date"])
    tickers = universe["ticker"].tolist()
    wanted = tickers + ["^GSPC", "^NDX", "QQQ", "XLK"]
    subset = prices[prices["ticker"].isin(wanted)].copy()
    subset["price"] = subset["adj_close"].fillna(subset["close"])
    price_wide = subset.pivot(index="date", columns="ticker", values="price").sort_index().ffill()
    returns = return_matrix(price_wide)
    return returns, tickers


def make_windows(index: pd.Index, config: WindowConfig) -> list[dict[str, pd.Timestamp]]:
    windows = []
    start = 0
    while start + config.train_days + config.test_days <= len(index):
        train_start = index[start]
        train_end = index[start + config.train_days - 1]
        test_start = index[start + config.train_days]
        test_end = index[start + config.train_days + config.test_days - 1]
        windows.append(
            {
                "train_start": train_start,
                "train_end": train_end,
                "test_start": test_start,
                "test_end": test_end,
            }
        )
        start += config.step_days
    return windows


def apply_weights(returns: pd.DataFrame, weights: pd.Series, name: str) -> pd.Series:
    return returns[weights.index].dot(weights).rename(name)


def metric_row(
    window_id: int,
    portfolio: str,
    series: pd.Series,
    benchmark_returns: pd.DataFrame,
    window: dict[str, pd.Timestamp],
    train_metrics: dict[str, float],
) -> dict[str, float | str | int]:
    clean = series.dropna()
    row = {
        "window_id": window_id,
        "portfolio": portfolio,
        "train_start": window["train_start"].date().isoformat(),
        "train_end": window["train_end"].date().isoformat(),
        "test_start": window["test_start"].date().isoformat(),
        "test_end": window["test_end"].date().isoformat(),
        "test_observations": int(clean.count()),
        "test_cumulative_return": (1 + clean).prod() - 1,
        "test_annualized_return": annualized_return(clean),
        "test_annualized_volatility": annualized_volatility(clean),
        "test_sharpe_ratio": sharpe_ratio(clean),
        "test_sortino_ratio": sortino_ratio(clean),
        "test_max_drawdown": max_drawdown(clean),
        "test_drawdown_coverage": drawdown_coverage(clean),
        "test_calmar_ratio": calmar_ratio(clean),
        "test_var_95_daily": historical_var(clean),
        "test_cvar_95_daily": historical_cvar(clean),
        "train_annualized_return": train_metrics["annualized_return"],
        "train_annualized_volatility": train_metrics["annualized_volatility"],
        "train_sharpe_ratio": train_metrics["sharpe_ratio"],
        "train_max_drawdown": train_metrics["max_drawdown"],
        "sharpe_decay": train_metrics["sharpe_ratio"] - sharpe_ratio(clean),
    }
    for benchmark in ["^GSPC", "^NDX", "QQQ", "XLK"]:
        label = benchmark.replace("^", "").lower()
        benchmark_series = benchmark_returns[benchmark].reindex(clean.index)
        aligned = pd.concat([clean, benchmark_series], axis=1).dropna()
        if aligned.empty:
            excess = pd.Series(dtype=float)
        else:
            excess = aligned.iloc[:, 0] - aligned.iloc[:, 1]
        row[f"excess_return_{label}"] = (1 + aligned.iloc[:, 0]).prod() - (1 + aligned.iloc[:, 1]).prod() if not aligned.empty else np.nan
        row[f"beat_{label}"] = bool(row[f"excess_return_{label}"] > 0) if not pd.isna(row[f"excess_return_{label}"]) else False
        row[f"information_ratio_{label}"] = information_ratio(clean, benchmark_series)
        row[f"mean_daily_excess_{label}"] = excess.mean() if not excess.empty else np.nan
    return row


def portfolio_train_metrics(series: pd.Series) -> dict[str, float]:
    clean = series.dropna()
    return {
        "annualized_return": annualized_return(clean),
        "annualized_volatility": annualized_volatility(clean),
        "sharpe_ratio": sharpe_ratio(clean),
        "max_drawdown": max_drawdown(clean),
    }


def build_window_weights(
    train_returns: pd.DataFrame,
    tickers: list[str],
    max_weight: float,
    rules: pd.DataFrame,
    covariance_method: str = "sample",
) -> dict[str, pd.Series]:
    as_of_date = train_returns.index.max()
    rule_set = build_rule_set(tickers, rules, as_of_date, default_max_weight=max_weight)
    equal_weight = constrained_equal_weight(tickers, rule_set)
    min_variance = optimize_portfolio(
        train_returns[tickers],
        "min_variance",
        max_weight=max_weight,
        rules=rules,
        as_of_date=as_of_date,
        covariance_method=covariance_method,
    )
    max_sharpe = optimize_portfolio(
        train_returns[tickers],
        "max_sharpe",
        max_weight=max_weight,
        risk_free_rate=0.0,
        rules=rules,
        as_of_date=as_of_date,
        covariance_method=covariance_method,
    )
    return {
        "equal_weight": equal_weight,
        "min_variance": min_variance,
        "max_sharpe": max_sharpe,
    }


def run_walk_forward(config: WindowConfig, rules: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    returns, tickers = load_returns()
    stock_returns = returns[tickers].dropna(how="any")
    benchmark_returns = returns[["^GSPC", "^NDX", "QQQ", "XLK"]]
    windows = make_windows(stock_returns.index, config)

    metrics_rows = []
    weight_rows = []
    return_frames = []

    for window_id, window in enumerate(windows, start=1):
        train = stock_returns.loc[window["train_start"] : window["train_end"]]
        test = stock_returns.loc[window["test_start"] : window["test_end"]]
        weights = build_window_weights(train, tickers, config.max_weight, rules, config.covariance_method)

        for portfolio, weight_series in weights.items():
            train_series = apply_weights(train, weight_series, portfolio)
            test_series = apply_weights(test, weight_series, portfolio)
            train_metrics = portfolio_train_metrics(train_series)
            metrics_rows.append(metric_row(window_id, portfolio, test_series, benchmark_returns, window, train_metrics))

            weight_row = {
                "window_id": window_id,
                "portfolio": portfolio,
                "train_start": window["train_start"].date().isoformat(),
                "train_end": window["train_end"].date().isoformat(),
            }
            weight_row.update(weight_series.to_dict())
            weight_rows.append(weight_row)

            frame = pd.DataFrame(
                {
                    "date": test_series.index,
                    "window_id": window_id,
                    "portfolio": portfolio,
                    "return": test_series.values,
                }
            )
            return_frames.append(frame)

    return pd.DataFrame(metrics_rows), pd.DataFrame(weight_rows), pd.concat(return_frames, ignore_index=True)


def summary_from_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for portfolio, group in metrics.groupby("portfolio"):
        row = {
            "portfolio": portfolio,
            "windows": int(group["window_id"].nunique()),
            "avg_test_annualized_return": group["test_annualized_return"].mean(),
            "median_test_annualized_return": group["test_annualized_return"].median(),
            "avg_test_annualized_volatility": group["test_annualized_volatility"].mean(),
            "avg_test_sharpe": group["test_sharpe_ratio"].mean(),
            "median_test_sharpe": group["test_sharpe_ratio"].median(),
            "avg_train_sharpe": group["train_sharpe_ratio"].mean(),
            "avg_sharpe_decay": group["sharpe_decay"].mean(),
            "worst_test_max_drawdown": group["test_max_drawdown"].min(),
            "avg_test_drawdown_coverage": group["test_drawdown_coverage"].mean(),
        }
        for benchmark in ["gspc", "ndx", "qqq", "xlk"]:
            row[f"win_rate_vs_{benchmark}"] = group[f"beat_{benchmark}"].mean()
            row[f"avg_excess_return_vs_{benchmark}"] = group[f"excess_return_{benchmark}"].mean()
            row[f"avg_information_ratio_vs_{benchmark}"] = group[f"information_ratio_{benchmark}"].mean()
        rows.append(row)
    return pd.DataFrame(rows).sort_values("avg_test_sharpe", ascending=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run walk-forward validation for portfolio strategies.")
    parser.add_argument("--train-days", type=int, default=756, help="Training window length in trading days.")
    parser.add_argument("--test-days", type=int, default=126, help="Test window length in trading days.")
    parser.add_argument("--step-days", type=int, default=126, help="Step size in trading days.")
    parser.add_argument("--max-weight", type=float, default=0.10, help="Maximum single-stock weight.")
    parser.add_argument("--rules", default=None, help="Optional human override CSV.")
    parser.add_argument(
        "--covariance",
        choices=("sample", "ledoit_wolf"),
        default="sample",
        help="协方差估计方法。sample 样本协方差；ledoit_wolf 收缩估计。",
    )
    parser.add_argument("--summary", action="store_true", help="Print existing walk-forward summary and exit.")
    return parser.parse_args()


def print_existing_summary() -> None:
    path = OUTPUT_DIR / "walk_forward_summary.csv"
    if not path.exists():
        print("walk_forward_summary.csv not found", flush=True)
        return
    summary = pd.read_csv(path)
    cols = [
        "portfolio",
        "windows",
        "avg_test_annualized_return",
        "avg_test_sharpe",
        "avg_train_sharpe",
        "avg_sharpe_decay",
        "worst_test_max_drawdown",
        "win_rate_vs_xlk",
        "win_rate_vs_qqq",
    ]
    print(summary[cols].to_string(index=False), flush=True)


def main() -> int:
    args = parse_args()
    if args.summary:
        print_existing_summary()
        return 0

    OUTPUT_DIR.mkdir(exist_ok=True)
    config = WindowConfig(
        train_days=args.train_days,
        test_days=args.test_days,
        step_days=args.step_days,
        max_weight=args.max_weight,
        covariance_method=args.covariance,
    )
    rules = load_rules(args.rules)
    metrics, weights, returns = run_walk_forward(config, rules)
    summary = summary_from_metrics(metrics)

    metrics.to_csv(OUTPUT_DIR / "walk_forward_window_metrics.csv", index=False)
    summary.to_csv(OUTPUT_DIR / "walk_forward_summary.csv", index=False)
    weights.to_csv(OUTPUT_DIR / "walk_forward_weights.csv", index=False)
    returns.to_csv(OUTPUT_DIR / "walk_forward_returns.csv", index=False)

    print(f"wrote walk-forward outputs to {OUTPUT_DIR}", flush=True)
    print_existing_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
