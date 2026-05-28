"""共享的 Pydantic schemas。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(BaseModel):
    task_id: str
    status: str  # PENDING / STARTED / PROGRESS / SUCCESS / FAILURE
    step: str | None = None
    progress: float | None = None  # 0.0 ~ 1.0
    result: dict[str, Any] | None = None
    error: str | None = None


class OverviewResponse(BaseModel):
    ticker_count: int
    price_rows: int
    date_min: str
    date_max: str
    failure_count: int


class TickerInfo(BaseModel):
    selection_rank: int
    ticker: str
    name: str
    sector: str
    industry: str
    weight: float | None = None
    data_coverage: float | None = None
    avg_dollar_volume_252: float | None = None
    selection_score: float | None = None


class TickerListItem(BaseModel):
    ticker: str
    name: str


class PipelineParams(BaseModel):
    start_date: str | None = None
    max_weight: float = Field(default=0.10, ge=0.01, le=0.50)
    covariance_method: str = "sample"
    train_days: int = Field(default=756, ge=126)
    test_days: int = Field(default=126, ge=21)
    step_days: int = Field(default=126, ge=21)
    bootstrap_samples: int = Field(default=2000, ge=100)
    bootstrap_block_size: int = Field(default=21, ge=1)


class OptimizationParams(BaseModel):
    objective: str = Field(default="max_sharpe", pattern="^(min_variance|max_sharpe|min_cvar)$")
    covariance_method: str = Field(default="sample", pattern="^(sample|ledoit_wolf|factor_shrinkage)$")
    max_weight: float = Field(default=0.10, ge=0.01, le=0.50)
    use_black_litterman: bool = False
    cvar_alpha: float = Field(default=0.05, ge=0.01, le=0.20)


class WalkForwardParams(BaseModel):
    train_days: int = Field(default=756, ge=126)
    test_days: int = Field(default=126, ge=21)
    step_days: int = Field(default=126, ge=21)
    max_weight: float = Field(default=0.10, ge=0.01, le=0.50)
    covariance_method: str = Field(default="sample", pattern="^(sample|ledoit_wolf|factor_shrinkage)$")


class StatTestsParams(BaseModel):
    samples: int = Field(default=2000, ge=100)
    block_size: int = Field(default=21, ge=1)


class FactorPCAParams(BaseModel):
    components: int = Field(default=5, ge=1, le=20)


class ReportParams(BaseModel):
    focus: str = Field(default="balanced", pattern="^(balanced|risk_control|benchmark_outperformance|robustness)$")
    engine: str = Field(default="deepseek", pattern="^(deepseek|dify)$")
    notes: str = ""


class RulesUpdateBody(BaseModel):
    csv_content: str


class DifyExtractParams(BaseModel):
    human_rule_text: str
    effective_start_date: str = Field(default="")
    effective_end_date: str = Field(default="")
