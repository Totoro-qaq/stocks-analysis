from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from paths import (
    ANALYSIS_UNIVERSE_50_CSV,
    BENCHMARK_METADATA_CSV,
    DAILY_PRICES_CSV,
    OUTPUT_DIR,
    ROOT,
    ensure_project_dirs,
)

TRADING_DAYS = 252

BENCHMARK_TICKERS = ["^GSPC", "^NDX", "QQQ", "XLK", "^VIX", "^IRX"]
RETURN_BENCHMARKS = ["^GSPC", "^NDX", "QQQ", "XLK"]


def ensure_outputs() -> None:
    ensure_project_dirs()


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    universe = pd.read_csv(ANALYSIS_UNIVERSE_50_CSV)
    prices = pd.read_csv(DAILY_PRICES_CSV, parse_dates=["date"])
    benchmarks = pd.read_csv(BENCHMARK_METADATA_CSV)
    return universe, prices, benchmarks


def price_matrix(prices: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    subset = prices[prices["ticker"].isin(tickers)].copy()
    subset["price"] = subset["adj_close"].fillna(subset["close"])
    matrix = subset.pivot(index="date", columns="ticker", values="price").sort_index()
    return matrix.ffill().dropna(how="all")


def return_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan).dropna(how="all")


def annualized_return(returns: pd.Series) -> float:
    clean = returns.dropna()
    if clean.empty:
        return np.nan
    cumulative = (1 + clean).prod()
    years = len(clean) / TRADING_DAYS
    if years <= 0 or cumulative <= 0:
        return np.nan
    return cumulative ** (1 / years) - 1


def annualized_volatility(returns: pd.Series) -> float:
    return returns.dropna().std(ddof=1) * np.sqrt(TRADING_DAYS)


def sharpe_ratio(returns: pd.Series, risk_free_daily: pd.Series | None = None) -> float:
    clean = returns.dropna()
    if clean.empty:
        return np.nan
    if risk_free_daily is not None:
        aligned_rf = risk_free_daily.reindex(clean.index).ffill().fillna(0)
        clean = clean - aligned_rf
    std = clean.std(ddof=1)
    if std == 0 or pd.isna(std):
        return np.nan
    return clean.mean() / std * np.sqrt(TRADING_DAYS)


def sortino_ratio(returns: pd.Series, risk_free_daily: pd.Series | None = None) -> float:
    clean = returns.dropna()
    if clean.empty:
        return np.nan
    if risk_free_daily is not None:
        aligned_rf = risk_free_daily.reindex(clean.index).ffill().fillna(0)
        clean = clean - aligned_rf
    downside = clean[clean < 0]
    downside_std = downside.std(ddof=1)
    if downside_std == 0 or pd.isna(downside_std):
        return np.nan
    return clean.mean() / downside_std * np.sqrt(TRADING_DAYS)


def drawdown_series(returns: pd.Series) -> pd.Series:
    wealth = (1 + returns.dropna()).cumprod()
    peak = wealth.cummax()
    return wealth / peak - 1


def max_drawdown(returns: pd.Series) -> float:
    dd = drawdown_series(returns)
    return dd.min() if not dd.empty else np.nan


def drawdown_coverage(returns: pd.Series) -> float:
    dd = drawdown_series(returns)
    if dd.empty:
        return np.nan
    return (dd < 0).mean()


def max_drawdown_duration(returns: pd.Series) -> int:
    dd = drawdown_series(returns)
    if dd.empty:
        return 0
    underwater = dd < 0
    max_duration = 0
    current = 0
    for value in underwater:
        if value:
            current += 1
            max_duration = max(max_duration, current)
        else:
            current = 0
    return max_duration


def beta_to_benchmark(asset_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    aligned = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
    if aligned.shape[0] < 30:
        return np.nan
    asset = aligned.iloc[:, 0]
    benchmark = aligned.iloc[:, 1]
    variance = benchmark.var(ddof=1)
    if variance == 0 or pd.isna(variance):
        return np.nan
    return asset.cov(benchmark) / variance


def historical_var(returns: pd.Series, alpha: float = 0.05) -> float:
    clean = returns.dropna()
    if clean.empty:
        return np.nan
    return clean.quantile(alpha)


def historical_cvar(returns: pd.Series, alpha: float = 0.05) -> float:
    clean = returns.dropna()
    if clean.empty:
        return np.nan
    threshold = clean.quantile(alpha)
    tail = clean[clean <= threshold]
    return tail.mean() if not tail.empty else np.nan


def calmar_ratio(returns: pd.Series) -> float:
    ann_return = annualized_return(returns)
    mdd = abs(max_drawdown(returns))
    if mdd == 0 or pd.isna(mdd):
        return np.nan
    return ann_return / mdd


def tracking_error(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
    if aligned.empty:
        return np.nan
    diff = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    return diff.std(ddof=1) * np.sqrt(TRADING_DAYS)


def information_ratio(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
    if aligned.empty:
        return np.nan
    diff = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    std = diff.std(ddof=1)
    if std == 0 or pd.isna(std):
        return np.nan
    return diff.mean() / std * np.sqrt(TRADING_DAYS)


def t_test_mean(returns: pd.Series) -> dict[str, float]:
    clean = returns.dropna()
    if len(clean) < 3:
        return {"t_stat": np.nan, "p_value": np.nan}
    result = stats.ttest_1samp(clean, popmean=0.0, nan_policy="omit")
    return {"t_stat": float(result.statistic), "p_value": float(result.pvalue)}


def risk_free_daily_from_irx(irx_prices: pd.Series) -> pd.Series:
    clean = irx_prices.ffill()
    annual_decimal = clean / 100.0
    return annual_decimal / TRADING_DAYS


def build_single_stock_metrics(
    returns: pd.DataFrame,
    benchmark_returns: pd.DataFrame,
    risk_free_daily: pd.Series,
    universe: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for ticker in universe["ticker"].tolist():
        series = returns[ticker].dropna()
        row = {
            "ticker": ticker,
            "name": universe.set_index("ticker").loc[ticker, "name"],
            "annualized_return": annualized_return(series),
            "annualized_volatility": annualized_volatility(series),
            "sharpe_ratio": sharpe_ratio(series, risk_free_daily),
            "sortino_ratio": sortino_ratio(series, risk_free_daily),
            "max_drawdown": max_drawdown(series),
            "drawdown_coverage": drawdown_coverage(series),
            "max_drawdown_duration_days": max_drawdown_duration(series),
            "var_95_daily": historical_var(series, 0.05),
            "cvar_95_daily": historical_cvar(series, 0.05),
            "observations": int(series.count()),
        }
        for benchmark in RETURN_BENCHMARKS:
            row[f"beta_{clean_ticker_name(benchmark)}"] = beta_to_benchmark(series, benchmark_returns[benchmark])
            row[f"corr_{clean_ticker_name(benchmark)}"] = series.corr(benchmark_returns[benchmark])
        row["corr_vix"] = series.corr(benchmark_returns["^VIX"]) if "^VIX" in benchmark_returns else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values("sharpe_ratio", ascending=False)


def clean_ticker_name(ticker: str) -> str:
    return ticker.replace("^", "").replace("-", "_").lower()


def equal_weight_returns(returns: pd.DataFrame, universe_tickers: list[str]) -> pd.Series:
    stock_returns = returns[universe_tickers].dropna(how="all")
    return stock_returns.mean(axis=1, skipna=True).rename("equal_weight")


def portfolio_metrics(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.DataFrame,
    risk_free_daily: pd.Series,
) -> pd.DataFrame:
    rows = []
    portfolios = {"equal_weight": portfolio_returns}
    for name, series in portfolios.items():
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
            "var_95_daily": historical_var(series, 0.05),
            "cvar_95_daily": historical_cvar(series, 0.05),
            "cumulative_return": (1 + series.dropna()).prod() - 1,
            "observations": int(series.dropna().count()),
        }
        for benchmark in RETURN_BENCHMARKS:
            row[f"beta_{clean_ticker_name(benchmark)}"] = beta_to_benchmark(series, benchmark_returns[benchmark])
            row[f"tracking_error_{clean_ticker_name(benchmark)}"] = tracking_error(series, benchmark_returns[benchmark])
            row[f"information_ratio_{clean_ticker_name(benchmark)}"] = information_ratio(series, benchmark_returns[benchmark])
            excess_test = t_test_mean(series - benchmark_returns[benchmark])
            row[f"excess_t_stat_{clean_ticker_name(benchmark)}"] = excess_test["t_stat"]
            row[f"excess_p_value_{clean_ticker_name(benchmark)}"] = excess_test["p_value"]
        own_test = t_test_mean(series)
        row["mean_return_t_stat"] = own_test["t_stat"]
        row["mean_return_p_value"] = own_test["p_value"]
        rows.append(row)
    return pd.DataFrame(rows)


def cumulative_returns(returns: pd.DataFrame) -> pd.DataFrame:
    return (1 + returns.dropna(how="all")).cumprod() - 1


def bollinger_bands(price_matrix_df: pd.DataFrame, tickers: list[str], window: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    frames = []
    for ticker in tickers:
        price = price_matrix_df[ticker].dropna()
        mid = price.rolling(window).mean()
        std = price.rolling(window).std(ddof=1)
        frame = pd.DataFrame(
            {
                "date": price.index,
                "ticker": ticker,
                "price": price.values,
                "middle_band": mid.values,
                "upper_band": (mid + num_std * std).values,
                "lower_band": (mid - num_std * std).values,
                "bandwidth": ((mid + num_std * std) - (mid - num_std * std)).values / mid.values,
                "percent_b": (price.values - (mid - num_std * std).values)
                / ((mid + num_std * std).values - (mid - num_std * std).values),
            }
        )
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def write_summary_json(
    single_metrics: pd.DataFrame,
    portfolio_metrics_df: pd.DataFrame,
    universe: pd.DataFrame,
    returns: pd.DataFrame,
) -> None:
    equal_row = portfolio_metrics_df.iloc[0].to_dict()
    top_sharpe = single_metrics.head(10)[["ticker", "name", "sharpe_ratio", "annualized_return", "annualized_volatility", "max_drawdown"]]
    bottom_drawdown = single_metrics.sort_values("max_drawdown").head(10)[
        ["ticker", "name", "max_drawdown", "drawdown_coverage", "annualized_volatility"]
    ]
    payload = {
        "generated_from": "analysis_engine.py",
        "universe_size": int(universe["ticker"].nunique()),
        "date_min": str(returns.index.min().date()),
        "date_max": str(returns.index.max().date()),
        "equal_weight_portfolio": {key: safe_json_value(value) for key, value in equal_row.items()},
        "top_10_single_stock_sharpe": top_sharpe.replace({np.nan: None}).to_dict(orient="records"),
        "worst_10_single_stock_drawdown": bottom_drawdown.replace({np.nan: None}).to_dict(orient="records"),
        "method_notes": [
            "Returns use adjusted close when available.",
            "Risk-free proxy uses ^IRX divided by 252.",
            "Universe is current XLK membership filtered to 50 liquid stocks; not point-in-time survivor-bias-free membership.",
            "Metrics are descriptive and not investment advice.",
        ],
    }
    (OUTPUT_DIR / "analysis_summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def safe_json_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or summarize the 50-stock analysis engine.")
    parser.add_argument("--summary", action="store_true", help="Print summary of existing output files and exit.")
    return parser.parse_args()


def print_output_summary() -> None:
    files = sorted(OUTPUT_DIR.glob("*"))
    for path in files:
        if path.is_file():
            print(f"{path.name}: {path.stat().st_size} bytes", flush=True)

    single_path = OUTPUT_DIR / "single_stock_metrics.csv"
    portfolio_path = OUTPUT_DIR / "portfolio_metrics.csv"
    if single_path.exists():
        single = pd.read_csv(single_path)
        cols = ["ticker", "annualized_return", "annualized_volatility", "sharpe_ratio", "max_drawdown"]
        print("top_single_stock_sharpe:", flush=True)
        print(single[cols].head(10).to_string(index=False), flush=True)
    if portfolio_path.exists():
        portfolio = pd.read_csv(portfolio_path)
        cols = ["portfolio", "annualized_return", "annualized_volatility", "sharpe_ratio", "max_drawdown", "drawdown_coverage"]
        print("portfolio_metrics:", flush=True)
        print(portfolio[cols].to_string(index=False), flush=True)


def main() -> int:
    args = parse_args()
    if args.summary:
        print_output_summary()
        return 0

    ensure_outputs()
    universe, prices, benchmarks = load_inputs()
    stock_tickers = universe["ticker"].tolist()
    all_tickers = stock_tickers + BENCHMARK_TICKERS

    prices_wide = price_matrix(prices, all_tickers)
    returns = return_matrix(prices_wide)
    risk_free_daily = risk_free_daily_from_irx(prices_wide["^IRX"]).reindex(returns.index).ffill().fillna(0)
    benchmark_returns = returns[[ticker for ticker in BENCHMARK_TICKERS if ticker in returns.columns]]

    single_metrics = build_single_stock_metrics(returns, benchmark_returns, risk_free_daily, universe)
    ew_returns = equal_weight_returns(returns, stock_tickers)
    ew_cumulative = cumulative_returns(pd.DataFrame({"equal_weight": ew_returns, "QQQ": returns["QQQ"], "XLK": returns["XLK"], "SP500": returns["^GSPC"], "NASDAQ100": returns["^NDX"]}))
    portfolio_metrics_df = portfolio_metrics(ew_returns, benchmark_returns, risk_free_daily)
    corr = returns[stock_tickers].corr()
    benchmark_corr = returns[stock_tickers + ["QQQ", "XLK", "^GSPC", "^NDX", "^VIX"]].corr()
    bollinger = bollinger_bands(prices_wide, stock_tickers)

    universe.to_csv(OUTPUT_DIR / "analysis_universe_50.csv", index=False)
    single_metrics.to_csv(OUTPUT_DIR / "single_stock_metrics.csv", index=False)
    pd.DataFrame({"date": ew_returns.index, "equal_weight_return": ew_returns.values}).to_csv(
        OUTPUT_DIR / "equal_weight_returns.csv", index=False
    )
    ew_cumulative.reset_index().rename(columns={"date": "date"}).to_csv(OUTPUT_DIR / "cumulative_returns.csv", index=False)
    portfolio_metrics_df.to_csv(OUTPUT_DIR / "portfolio_metrics.csv", index=False)
    corr.to_csv(OUTPUT_DIR / "correlation_matrix.csv")
    benchmark_corr.to_csv(OUTPUT_DIR / "correlation_matrix_with_benchmarks.csv")
    bollinger.to_csv(OUTPUT_DIR / "bollinger_bands.csv", index=False)
    benchmarks.to_csv(OUTPUT_DIR / "benchmark_metadata.csv", index=False)
    write_summary_json(single_metrics, portfolio_metrics_df, universe, returns)

    print(f"wrote outputs to {OUTPUT_DIR}", flush=True)
    print(f"single_stock_metrics={len(single_metrics)}", flush=True)
    print(f"return_observations={len(ew_returns.dropna())}", flush=True)
    print(f"equal_weight_sharpe={portfolio_metrics_df.loc[0, 'sharpe_ratio']:.4f}", flush=True)
    print(f"equal_weight_max_drawdown={portfolio_metrics_df.loc[0, 'max_drawdown']:.4f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
