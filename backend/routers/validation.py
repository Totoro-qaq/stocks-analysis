"""前向验证 + 统计检验 API。"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from schemas.common import WalkForwardParams, StatTestsParams
from services.portfolio_service import (
    get_bootstrap_intervals,
    get_significance_tests,
    get_wf_summary,
    get_wf_window_metrics,
    run_stat_tests,
    run_walk_forward,
)

router = APIRouter(prefix="/api/validation", tags=["验证"])


@router.post("/walk-forward")
async def walk_forward(params: WalkForwardParams, background_tasks: BackgroundTasks):
    """触发 Walk-forward 前向验证（异步）。"""
    background_tasks.add_task(
        run_walk_forward,
        train_days=params.train_days,
        test_days=params.test_days,
        step_days=params.step_days,
        max_weight=params.max_weight,
        covariance_method=params.covariance_method,
    )
    return {"status": "started", "params": params.model_dump()}


@router.get("/wf-summary")
async def wf_summary():
    """Walk-forward 样本外汇总。"""
    return get_wf_summary()


@router.get("/wf-window-metrics")
async def wf_window_metrics():
    """Walk-forward 各窗口详细指标。"""
    return get_wf_window_metrics()


@router.post("/stat-tests")
async def stat_tests(params: StatTestsParams, background_tasks: BackgroundTasks):
    """触发统计检验（异步）。"""
    background_tasks.add_task(
        run_stat_tests,
        samples=params.samples,
        block_size=params.block_size,
    )
    return {"status": "started", "params": params.model_dump()}


@router.get("/significance-tests")
async def significance_tests():
    """t 检验结果。"""
    return get_significance_tests()


@router.get("/bootstrap")
async def bootstrap():
    """Bootstrap 置信区间。"""
    return get_bootstrap_intervals()
