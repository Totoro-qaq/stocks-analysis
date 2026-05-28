"""因子分析 API — PCA + Fama-French 因子归因。"""

from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, BackgroundTasks

from paths import OUTPUT_DIR
from schemas.common import FactorPCAParams

router = APIRouter(prefix="/api/factor", tags=["因子"])


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    import numpy as np
    return df.replace({np.nan: None}).to_dict(orient="records")


@router.post("/pca")
async def run_pca(params: FactorPCAParams, background_tasks: BackgroundTasks):
    """触发 PCA 主成分分析（异步）。"""
    background_tasks.add_task(_run_pca_task, params.components)
    return {"status": "started", "params": params.model_dump()}


def _run_pca_task(components: int):
    from factor_analysis import load_stock_returns, run_pca
    returns = load_stock_returns()
    if returns.empty:
        return
    loadings, pc_returns, explained = run_pca(returns, components)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    loadings.reset_index().to_csv(OUTPUT_DIR / "pc_loadings.csv", index=False)
    pc_returns.reset_index().to_csv(OUTPUT_DIR / "pc_returns.csv", index=False)
    explained.to_csv(OUTPUT_DIR / "pc_explained_variance.csv", index=False)


@router.get("/explained-variance")
async def explained_variance():
    """PCA 解释方差比。"""
    path = OUTPUT_DIR / "pc_explained_variance.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))


@router.get("/loadings")
async def loadings():
    """PCA 载荷矩阵。"""
    path = OUTPUT_DIR / "pc_loadings.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))


@router.get("/pc-returns")
async def pc_returns():
    """PC 收益序列。"""
    path = OUTPUT_DIR / "pc_returns.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))


@router.get("/ff-regression")
async def ff_regression():
    """Fama-French 因子回归结果（单股）。"""
    path = OUTPUT_DIR / "factor_regression_single_stock.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))


@router.get("/ff-attribution")
async def ff_attribution():
    """Fama-French 组合因子归因。"""
    path = OUTPUT_DIR / "factor_regression_portfolio.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))
