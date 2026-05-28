"""数据总览与行情 API。"""

from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter

from paths import (
    ANALYSIS_UNIVERSE_50_CSV,
    DAILY_PRICES_CSV,
    DATA_FETCH_FAILURES_CSV,
    OUTPUT_DIR,
)

router = APIRouter(prefix="/api/data", tags=["数据"])

INDUSTRY_FALLBACKS = {
    "AAPL": "Hardware & Devices",
    "ACN": "IT Services",
    "ADBE": "Application Software",
    "ADI": "Semiconductors",
    "ADSK": "Application Software",
    "AMAT": "Semiconductor Equipment",
    "AMD": "Semiconductors",
    "ANET": "Communications Equipment",
    "APH": "Electronic Components",
    "AVGO": "Semiconductors",
    "CDNS": "EDA Software",
    "CIEN": "Communications Equipment",
    "COHR": "Optical & Components",
    "CRM": "Application Software",
    "CRWD": "Cybersecurity",
    "CSCO": "Communications Equipment",
    "DDOG": "Cloud Software",
    "DELL": "Hardware & Infrastructure",
    "FSLR": "Solar Technology",
    "FTNT": "Cybersecurity",
    "GLW": "Electronic Components",
    "HPE": "Hardware & Infrastructure",
    "IBM": "IT Services",
    "INTC": "Semiconductors",
    "INTU": "Application Software",
    "KEYS": "Electronic Test Equipment",
    "KLAC": "Semiconductor Equipment",
    "LITE": "Optical & Components",
    "LRCX": "Semiconductor Equipment",
    "MCHP": "Semiconductors",
    "MPWR": "Semiconductors",
    "MSFT": "Application Software",
    "MSI": "Communications Equipment",
    "MU": "Semiconductors",
    "NOW": "Cloud Software",
    "NVDA": "Semiconductors",
    "NXPI": "Semiconductors",
    "ON": "Semiconductors",
    "ORCL": "Application Software",
    "PANW": "Cybersecurity",
    "QCOM": "Semiconductors",
    "ROP": "Application Software",
    "SMCI": "Hardware & Infrastructure",
    "SNPS": "EDA Software",
    "STX": "Storage Hardware",
    "TEL": "Electronic Components",
    "TER": "Semiconductor Equipment",
    "WDC": "Storage Hardware",
    "WDAY": "Cloud Software",
}

MIN_MEANINGFUL_PORTFOLIO_WEIGHT = 1e-6
MIN_TREEMAP_DISPLAY_WEIGHT = 0.001


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    import numpy as np
    return df.replace({np.nan: None}).to_dict(orient="records")


def _usable_industry(ticker: str, industry: Any) -> str:
    if isinstance(industry, str) and industry.strip() and industry.strip().lower() not in {"-", "unknown", "nan"}:
        return industry.strip()
    return INDUSTRY_FALLBACKS.get(ticker.upper(), "Other Technology")


def _stock_return_over_window(prices: pd.DataFrame, ticker: str, window_days: int) -> float | None:
    ticker_prices = prices[prices["ticker"].eq(ticker)].sort_values("date").copy()
    if ticker_prices.empty:
        return None

    ticker_prices["price"] = ticker_prices["adj_close"].fillna(ticker_prices["close"])
    clean = ticker_prices["price"].dropna()
    if clean.shape[0] < 2:
        return None

    start_position = max(0, clean.shape[0] - window_days - 1)
    start_price = float(clean.iloc[start_position])
    end_price = float(clean.iloc[-1])
    if start_price <= 0:
        return None
    return end_price / start_price - 1.0


def _treemap_weight(row: pd.Series, weights: pd.DataFrame, portfolio: str) -> float:
    ticker = str(row["ticker"])
    if not weights.empty and portfolio in weights.columns:
        match = weights[weights["ticker"].eq(ticker)]
        if not match.empty:
            value = pd.to_numeric(match.iloc[0][portfolio], errors="coerce")
            if pd.notna(value) and float(value) > MIN_MEANINGFUL_PORTFOLIO_WEIGHT:
                return float(value)

    fallback_weight = pd.to_numeric(row.get("weight"), errors="coerce")
    if pd.notna(fallback_weight) and float(fallback_weight) > 0:
        return float(fallback_weight) / 100.0
    return 0.001


@router.get("/overview")
async def overview():
    """数据总览：股票数量、行情行数、日期范围、失败数。"""
    universe = pd.read_csv(ANALYSIS_UNIVERSE_50_CSV) if ANALYSIS_UNIVERSE_50_CSV.exists() else pd.DataFrame()
    prices = pd.read_csv(DAILY_PRICES_CSV, parse_dates=["date"]) if DAILY_PRICES_CSV.exists() else pd.DataFrame()
    failures = pd.read_csv(DATA_FETCH_FAILURES_CSV) if DATA_FETCH_FAILURES_CSV.exists() else pd.DataFrame()

    return {
        "ticker_count": int(universe["ticker"].nunique()) if not universe.empty else 0,
        "price_rows": len(prices),
        "date_min": str(prices["date"].min().date()) if not prices.empty else "",
        "date_max": str(prices["date"].max().date()) if not prices.empty else "",
        "failure_count": len(failures.dropna(how="all")) if not failures.empty else 0,
    }


@router.get("/universe")
async def universe():
    """50 股研究池列表。"""
    if not ANALYSIS_UNIVERSE_50_CSV.exists():
        return []
    df = pd.read_csv(ANALYSIS_UNIVERSE_50_CSV)
    return _df_to_records(df)


@router.get("/tickers")
async def tickers_list():
    """股票下拉列表（ticker + name）。"""
    if not ANALYSIS_UNIVERSE_50_CSV.exists():
        return []
    df = pd.read_csv(ANALYSIS_UNIVERSE_50_CSV)
    return _df_to_records(df[["ticker", "name"]])


@router.get("/market")
async def market(ticker: str):
    """单股或基准行情序列（OHLCV）。"""
    if not DAILY_PRICES_CSV.exists():
        return []
    df = pd.read_csv(DAILY_PRICES_CSV, parse_dates=["date"])
    subset = df[df["ticker"].eq(ticker.upper())].copy()
    return _df_to_records(subset)


@router.get("/treemap")
async def research_treemap(portfolio: str = "max_sharpe", window_days: int = 60):
    """研究池热力图：SIZE=组合权重，COLOR=近 window_days 个交易日收益。"""
    if not ANALYSIS_UNIVERSE_50_CSV.exists() or not DAILY_PRICES_CSV.exists():
        return {"groups": [], "meta": {"portfolio": portfolio, "window_days": window_days}}

    universe = pd.read_csv(ANALYSIS_UNIVERSE_50_CSV)
    prices = pd.read_csv(DAILY_PRICES_CSV, parse_dates=["date"])
    weights_path = OUTPUT_DIR / "portfolio_weights.csv"
    weights = pd.read_csv(weights_path) if weights_path.exists() else pd.DataFrame()

    rows: list[dict[str, Any]] = []
    for _, row in universe.iterrows():
        ticker = str(row["ticker"])
        weight = _treemap_weight(row, weights, portfolio)
        period_return = _stock_return_over_window(prices, ticker, window_days)
        rows.append(
            {
                "ticker": ticker,
                "name": row.get("name", ticker),
                "industry": _usable_industry(ticker, row.get("industry")),
                "weight": weight,
                "period_return": period_return,
                "value": [max(weight, MIN_TREEMAP_DISPLAY_WEIGHT), period_return if period_return is not None else 0.0],
            }
        )

    df = pd.DataFrame(rows)
    groups = []
    for industry, group in df.groupby("industry", dropna=False):
        children = group.sort_values("weight", ascending=False).to_dict(orient="records")
        total_weight = float(group["weight"].sum())
        groups.append({"name": industry, "value": total_weight, "children": children})

    return {
        "groups": sorted(groups, key=lambda item: item["value"], reverse=True),
        "meta": {
            "portfolio": portfolio,
            "window_days": window_days,
            "date_min": str(prices["date"].min().date()) if not prices.empty else "",
            "date_max": str(prices["date"].max().date()) if not prices.empty else "",
        },
    }


@router.get("/failures")
async def failures():
    """抓取失败记录。"""
    if not DATA_FETCH_FAILURES_CSV.exists():
        return []
    df = pd.read_csv(DATA_FETCH_FAILURES_CSV)
    return _df_to_records(df)
