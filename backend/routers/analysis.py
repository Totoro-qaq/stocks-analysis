"""基础分析 API — 单股指标、等权组合、相关性、布林带。"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from schemas.common import OptimizationParams
from services.analysis_service import (
    get_bollinger,
    get_correlation_matrix,
    get_cumulative_returns,
    get_portfolio_metrics,
    get_single_stock_metrics,
    run_analysis_engine,
)

router = APIRouter(prefix="/api/analysis", tags=["分析"])


@router.post("/run")
async def trigger_analysis(background_tasks: BackgroundTasks):
    """触发基础分析计算（异步）。"""
    background_tasks.add_task(run_analysis_engine)
    return {"status": "started", "message": "基础分析已在后台启动"}


@router.get("/single-stock-metrics")
async def single_stock_metrics():
    """单股风险收益指标（年化收益/波动率/夏普/回撤等）。"""
    return get_single_stock_metrics()


@router.get("/portfolio-metrics")
async def portfolio_metrics():
    """等权组合指标。"""
    return get_portfolio_metrics()


@router.get("/correlation")
async def correlation(with_benchmarks: bool = False):
    """相关性矩阵。with_benchmarks=true 时包含 QQQ/XLK/SP500/NDX/VIX。"""
    return get_correlation_matrix(with_benchmarks)


@router.get("/cumulative-returns")
async def cumulative_returns():
    """等权组合 + 基准累计收益序列。"""
    return get_cumulative_returns()


@router.get("/bollinger")
async def bollinger(ticker: str | None = None):
    """布林带数据。可选 ticker 筛选。"""
    return get_bollinger(ticker)
