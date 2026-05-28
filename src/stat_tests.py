from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from scipy import stats

from analysis_engine import OUTPUT_DIR, TRADING_DAYS, annualized_return, return_matrix, sharpe_ratio
from paths import ANALYSIS_UNIVERSE_50_CSV, DAILY_PRICES_CSV, ensure_project_dirs


RANDOM_SEED = 42


def load_returns() -> pd.DataFrame:
    prices = pd.read_csv(DAILY_PRICES_CSV, parse_dates=["date"])
    universe = pd.read_csv(ANALYSIS_UNIVERSE_50_CSV)
    tickers = universe["ticker"].tolist()
    wanted = tickers + ["^GSPC", "^NDX", "QQQ", "XLK"]
    subset = prices[prices["ticker"].isin(wanted)].copy()
    subset["price"] = subset["adj_close"].fillna(subset["close"])
    price_wide = subset.pivot(index="date", columns="ticker", values="price").sort_index().ffill()
    returns = return_matrix(price_wide)
    returns["equal_weight"] = returns[tickers].mean(axis=1)
    return returns


def load_optimized_returns() -> pd.DataFrame | None:
    path = OUTPUT_DIR / "optimized_portfolio_returns.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    return df


def load_walk_forward_returns() -> pd.DataFrame | None:
    path = OUTPUT_DIR / "walk_forward_returns.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["date"])
    pivot = df.pivot_table(index="date", columns="portfolio", values="return", aggfunc="first")
    pivot.columns = [f"wf_{col}" for col in pivot.columns]
    return pivot


def one_sample_tests(series: pd.Series, label: str) -> dict[str, float | str | int]:
    clean = series.dropna()
    if len(clean) < 3:
        return {
            "series": label,
            "test": "mean_return_gt_0",
            "observations": len(clean),
            "mean_daily_return": np.nan,
            "annualized_return": np.nan,
            "t_stat": np.nan,
            "p_value_two_sided": np.nan,
            "p_value_one_sided_gt_0": np.nan,
            "sharpe_ratio": np.nan,
        }
    result = stats.ttest_1samp(clean, popmean=0.0)
    p_one_sided = result.pvalue / 2 if result.statistic > 0 else 1 - result.pvalue / 2
    return {
        "series": label,
        "test": "mean_return_gt_0",
        "observations": int(len(clean)),
        "mean_daily_return": float(clean.mean()),
        "annualized_return": annualized_return(clean),
        "t_stat": float(result.statistic),
        "p_value_two_sided": float(result.pvalue),
        "p_value_one_sided_gt_0": float(p_one_sided),
        "sharpe_ratio": sharpe_ratio(clean),
    }


def excess_return_tests(series: pd.Series, benchmark: pd.Series, label: str, benchmark_label: str) -> dict[str, float | str | int]:
    aligned = pd.concat([series, benchmark], axis=1).dropna()
    if aligned.shape[0] < 3:
        return {
            "series": label,
            "benchmark": benchmark_label,
            "test": "mean_excess_return_gt_0",
            "observations": aligned.shape[0],
            "mean_daily_excess_return": np.nan,
            "annualized_excess_return": np.nan,
            "t_stat": np.nan,
            "p_value_two_sided": np.nan,
            "p_value_one_sided_gt_0": np.nan,
            "excess_sharpe_like": np.nan,
        }
    excess = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    result = stats.ttest_1samp(excess, popmean=0.0)
    p_one_sided = result.pvalue / 2 if result.statistic > 0 else 1 - result.pvalue / 2
    return {
        "series": label,
        "benchmark": benchmark_label,
        "test": "mean_excess_return_gt_0",
        "observations": int(len(excess)),
        "mean_daily_excess_return": float(excess.mean()),
        "annualized_excess_return": float(excess.mean() * TRADING_DAYS),
        "t_stat": float(result.statistic),
        "p_value_two_sided": float(result.pvalue),
        "p_value_one_sided_gt_0": float(p_one_sided),
        "excess_sharpe_like": sharpe_ratio(excess),
    }


def bootstrap_metric_ci(
    series: pd.Series,
    metric: str,
    samples: int = 2000,
    confidence: float = 0.95,
    block_size: int = 21,
) -> dict[str, float | str | int]:
    clean = series.dropna().to_numpy()
    rng = np.random.default_rng(RANDOM_SEED)
    if len(clean) < block_size * 2:
        return {
            "metric": metric,
            "bootstrap_samples": samples,
            "block_size": block_size,
            "ci_lower": np.nan,
            "ci_upper": np.nan,
            "bootstrap_mean": np.nan,
        }

    values = []
    n = len(clean)
    n_blocks = int(np.ceil(n / block_size))
    starts = np.arange(0, n - block_size + 1)
    for _ in range(samples):
        chosen_starts = rng.choice(starts, size=n_blocks, replace=True)
        boot = np.concatenate([clean[start : start + block_size] for start in chosen_starts])[:n]
        boot_series = pd.Series(boot)
        if metric == "annualized_return":
            values.append(annualized_return(boot_series))
        elif metric == "sharpe_ratio":
            values.append(sharpe_ratio(boot_series))
        elif metric == "mean_daily_return":
            values.append(float(boot_series.mean()))
        else:
            raise ValueError(f"Unsupported metric: {metric}")

    alpha = 1 - confidence
    return {
        "metric": metric,
        "bootstrap_samples": samples,
        "block_size": block_size,
        "ci_lower": float(np.nanquantile(values, alpha / 2)),
        "ci_upper": float(np.nanquantile(values, 1 - alpha / 2)),
        "bootstrap_mean": float(np.nanmean(values)),
    }


def collect_strategy_returns(base_returns: pd.DataFrame) -> dict[str, pd.Series]:
    strategies: dict[str, pd.Series] = {
        "equal_weight": base_returns["equal_weight"],
        "XLK": base_returns["XLK"],
        "QQQ": base_returns["QQQ"],
        "SP500": base_returns["^GSPC"],
        "NASDAQ100": base_returns["^NDX"],
    }

    optimized = load_optimized_returns()
    if optimized is not None:
        for column in optimized.columns:
            strategies[f"full_sample_{column}"] = optimized[column]

    walk_forward = load_walk_forward_returns()
    if walk_forward is not None:
        for column in walk_forward.columns:
            strategies[column] = walk_forward[column]

    return strategies


def run_tests(samples: int, block_size: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    base_returns = load_returns()
    strategies = collect_strategy_returns(base_returns)

    test_rows = []
    for label, series in strategies.items():
        test_rows.append(one_sample_tests(series, label))
        for benchmark_label, benchmark_col in [("XLK", "XLK"), ("QQQ", "QQQ"), ("SP500", "^GSPC"), ("NASDAQ100", "^NDX")]:
            if label == benchmark_label:
                continue
            test_rows.append(excess_return_tests(series, base_returns[benchmark_col], label, benchmark_label))

    bootstrap_rows = []
    for label, series in strategies.items():
        for metric in ["mean_daily_return", "annualized_return", "sharpe_ratio"]:
            row = {"series": label}
            row.update(bootstrap_metric_ci(series, metric, samples=samples, block_size=block_size))
            bootstrap_rows.append(row)

    return pd.DataFrame(test_rows), pd.DataFrame(bootstrap_rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run statistical tests and bootstrap intervals.")
    parser.add_argument("--samples", type=int, default=2000, help="Bootstrap sample count.")
    parser.add_argument("--block-size", type=int, default=21, help="Block bootstrap size in trading days.")
    parser.add_argument("--summary", action="store_true", help="Print existing test summary.")
    return parser.parse_args()


def print_summary() -> None:
    tests_path = OUTPUT_DIR / "significance_tests.csv"
    boot_path = OUTPUT_DIR / "bootstrap_intervals.csv"
    if tests_path.exists():
        tests = pd.read_csv(tests_path)
        subset = tests[
            tests["series"].isin(["equal_weight", "wf_equal_weight", "wf_min_variance", "wf_max_sharpe"])
            & tests["test"].eq("mean_return_gt_0")
        ]
        print("mean_return_tests:", flush=True)
        print(subset[["series", "observations", "annualized_return", "t_stat", "p_value_one_sided_gt_0", "sharpe_ratio"]].to_string(index=False), flush=True)
    if boot_path.exists():
        boot = pd.read_csv(boot_path)
        subset = boot[
            boot["series"].isin(["equal_weight", "wf_equal_weight", "wf_min_variance", "wf_max_sharpe"])
            & boot["metric"].eq("sharpe_ratio")
        ]
        print("bootstrap_sharpe_ci:", flush=True)
        print(subset[["series", "ci_lower", "ci_upper", "bootstrap_mean"]].to_string(index=False), flush=True)


def main() -> int:
    args = parse_args()
    if args.summary:
        print_summary()
        return 0

    ensure_project_dirs()
    tests, bootstrap = run_tests(args.samples, args.block_size)
    tests.to_csv(OUTPUT_DIR / "significance_tests.csv", index=False)
    bootstrap.to_csv(OUTPUT_DIR / "bootstrap_intervals.csv", index=False)
    print(f"wrote statistical outputs to {OUTPUT_DIR}", flush=True)
    print_summary()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
