"""组合优化 API — 马科维茨 / CVaR / HRP / Black-Litterman。"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from schemas.common import OptimizationParams
from services.portfolio_service import (
    get_efficient_frontier,
    get_hrp_dendrogram,
    get_optimized_cumulative_returns,
    get_optimized_metrics,
    get_optimized_returns,
    get_portfolio_weights,
    run_portfolio_optimization,
)

router = APIRouter(prefix="/api/portfolio", tags=["组合"])

@router.get("/hrp-dendrogram")
async def hrp_dendrogram():
    """获取层次风险平价(HRP)的聚类树状图结构。"""
    return get_hrp_dendrogram()

@router.post("/optimize")
async def optimize(params: OptimizationParams, background_tasks: BackgroundTasks):
    """触发组合优化计算（异步）。支持 min_variance / max_sharpe / min_cvar。"""
    background_tasks.add_task(
        run_portfolio_optimization,
        objective=params.objective,
        covariance_method=params.covariance_method,
        max_weight=params.max_weight,
        use_black_litterman=params.use_black_litterman,
        cvar_alpha=params.cvar_alpha,
    )
    return {"status": "started", "params": params.model_dump()}


@router.get("/weights")
async def weights():
    """组合权重（所有策略）。"""
    return get_portfolio_weights()


@router.get("/metrics")
async def metrics():
    """优化组合指标表。"""
    return get_optimized_metrics()


@router.get("/efficient-frontier")
async def efficient_frontier():
    """有效前沿散点数据。"""
    return get_efficient_frontier()


@router.get("/returns")
async def returns():
    """优化组合日收益序列。"""
    return get_optimized_returns()


@router.get("/cumulative-returns")
async def cumulative_returns():
    """优化组合累计收益序列。"""
    return get_optimized_cumulative_returns()
