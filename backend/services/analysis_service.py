"""分析引擎服务 — 封装 src/analysis_engine.py。

把 CSV 写入逻辑替换为返回结构化数据，供 API 路由直接序列化为 JSON。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from analysis_engine import (
    TRADING_DAYS,
    BENCHMARK_TICKERS,
    RETURN_BENCHMARKS,
    annualized_return,
    annualized_volatility,
    beta_to_benchmark,
    bollinger_bands,
    build_single_stock_metrics,
    calmar_ratio,
    clean_ticker_name,
    cumulative_returns,
    drawdown_coverage,
    drawdown_series,
    equal_weight_returns,
    historical_cvar,
    historical_var,
    information_ratio,
    load_inputs,
    max_drawdown,
    max_drawdown_duration,
    portfolio_metrics,
    price_matrix,
    return_matrix,
    risk_free_daily_from_irx,
    sharpe_ratio,
    sortino_ratio,
    tracking_error,
)
from paths import (
    ANALYSIS_UNIVERSE_50_CSV,
    BENCHMARK_METADATA_CSV,
    DAILY_PRICES_CSV,
    OUTPUT_DIR,
)


def _nan_to_none(value: Any) -> Any:
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame → 列表字典，NaN → None（JSON 兼容）。"""
    return df.replace({np.nan: None}).to_dict(orient="records")


def _series_to_list(series: pd.Series) -> list[Any]:
    return [_nan_to_none(v) for v in series.tolist()]


def run_analysis_engine() -> dict[str, Any]:
    """运行基础分析引擎，返回结构化结果（不写 CSV）。"""
    universe, prices, benchmarks = load_inputs()
    stock_tickers = universe["ticker"].tolist()
    all_tickers = stock_tickers + BENCHMARK_TICKERS

    prices_wide = price_matrix(prices, all_tickers)
    returns = return_matrix(prices_wide)
    risk_free_daily = risk_free_daily_from_irx(prices_wide["^IRX"]).reindex(returns.index).ffill().fillna(0)
    available_benchmarks = [t for t in BENCHMARK_TICKERS if t in returns.columns]
    benchmark_returns = returns[available_benchmarks]

    single_metrics = build_single_stock_metrics(returns, benchmark_returns, risk_free_daily, universe)
    ew_returns = equal_weight_returns(returns, stock_tickers)
    ew_cumulative = cumulative_returns(
        pd.DataFrame({
            "equal_weight": ew_returns,
            **{t: returns[t] for t in ["QQQ", "XLK", "^GSPC", "^NDX"] if t in returns.columns},
        })
    )
    portfolio_metrics_df = portfolio_metrics(ew_returns, benchmark_returns, risk_free_daily)
    corr = returns[stock_tickers].corr()
    benchmark_corr = returns[[t for t in stock_tickers + ["QQQ", "XLK", "^GSPC", "^NDX", "^VIX"] if t in returns.columns]].corr()
    bollinger = bollinger_bands(prices_wide, stock_tickers)

    # 写入 CSV（保留兼容）
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
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

    return {
        "single_stock_metrics": _df_to_records(single_metrics),
        "portfolio_metrics": _df_to_records(portfolio_metrics_df),
        "correlation_matrix": {
            "tickers": corr.columns.tolist(),
            "values": corr.values.tolist(),
        },
        "correlation_matrix_with_benchmarks": {
            "tickers": benchmark_corr.columns.tolist(),
            "values": benchmark_corr.values.tolist(),
        },
        "cumulative_returns": _df_to_records(ew_cumulative.reset_index()),
        "bollinger_bands": _df_to_records(bollinger),
        "date_min": str(returns.index.min().date()),
        "date_max": str(returns.index.max().date()),
    }


def get_single_stock_metrics() -> list[dict[str, Any]]:
    path = OUTPUT_DIR / "single_stock_metrics.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))


def get_portfolio_metrics() -> list[dict[str, Any]]:
    path = OUTPUT_DIR / "portfolio_metrics.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))


def get_correlation_matrix(with_benchmarks: bool = False) -> dict[str, Any]:
    name = "correlation_matrix_with_benchmarks.csv" if with_benchmarks else "correlation_matrix.csv"
    path = OUTPUT_DIR / name
    if not path.exists():
        return {"tickers": [], "values": []}
    df = pd.read_csv(path, index_col=0)
    return {"tickers": df.columns.tolist(), "values": df.values.tolist()}


def get_cumulative_returns() -> list[dict[str, Any]]:
    path = OUTPUT_DIR / "cumulative_returns.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path, parse_dates=["date"]))


def get_bollinger(ticker: str | None = None) -> list[dict[str, Any]]:
    path = OUTPUT_DIR / "bollinger_bands.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path, parse_dates=["date"])
    if ticker:
        df = df[df["ticker"].eq(ticker)]
    return _df_to_records(df)
