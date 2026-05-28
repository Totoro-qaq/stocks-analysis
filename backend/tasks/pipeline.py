"""Celery async tasks."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from backend.celery_app import celery_app
from observability import get_tracer, record_pipeline_step, set_span_error
from services.pipeline_timeline import utc_now_iso, write_pipeline_timeline

PipelineStep = tuple[str, Callable[[], Any]]


def _duration_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 2)


def _build_timeline(task_id: str, steps: list[PipelineStep]) -> dict[str, Any]:
    started_at = utc_now_iso()
    return {
        "task_id": task_id,
        "status": "RUNNING",
        "started_at": started_at,
        "finished_at": None,
        "duration_ms": 0.0,
        "steps": [
            {
                "name": step_name,
                "status": "PENDING",
                "started_at": None,
                "finished_at": None,
                "offset_ms": 0.0,
                "duration_ms": 0.0,
            }
            for step_name, _ in steps
        ],
    }


@celery_app.task(bind=True, name="run_full_pipeline")
def run_full_pipeline(self: Any, params: dict[str, Any]) -> dict[str, Any]:
    """Run the full analysis pipeline asynchronously."""
    from services.analysis_service import run_analysis_engine
    from services.portfolio_service import (
        run_portfolio_optimization,
        run_stat_tests,
        run_walk_forward,
    )

    max_weight = params.get("max_weight", 0.10)
    covariance_method = params.get("covariance_method", "sample")
    train_days = params.get("train_days", 756)
    test_days = params.get("test_days", 126)
    step_days = params.get("step_days", 126)
    bootstrap_samples = params.get("bootstrap_samples", 2000)
    bootstrap_block_size = params.get("bootstrap_block_size", 21)

    steps: list[PipelineStep] = [
        ("基础分析", lambda: run_analysis_engine()),
        (
            "组合优化",
            lambda: run_portfolio_optimization(
                objective="max_sharpe",
                covariance_method=covariance_method,
                max_weight=max_weight,
            ),
        ),
        (
            "前向验证",
            lambda: run_walk_forward(
                train_days=train_days,
                test_days=test_days,
                step_days=step_days,
                max_weight=max_weight,
                covariance_method=covariance_method,
            ),
        ),
        (
            "统计检验",
            lambda: run_stat_tests(
                samples=bootstrap_samples,
                block_size=bootstrap_block_size,
            ),
        ),
    ]

    task_id = getattr(getattr(self, "request", None), "id", "") or "unknown"
    timeline = _build_timeline(task_id, steps)
    pipeline_started_at = time.perf_counter()
    tracer = get_tracer(__name__)
    write_pipeline_timeline(timeline)

    total = len(steps)
    for step_index, (step_name, step_fn) in enumerate(steps):
        step_started_at = time.perf_counter()
        step_record = timeline["steps"][step_index]
        step_record.update(
            {
                "status": "RUNNING",
                "started_at": utc_now_iso(),
                "offset_ms": _duration_ms(pipeline_started_at),
            }
        )
        timeline["duration_ms"] = _duration_ms(pipeline_started_at)
        write_pipeline_timeline(timeline)

        self.update_state(
            state="PROGRESS",
            meta={
                "step": step_name,
                "progress": step_index / total,
                "step_index": step_index,
                "total_steps": total,
            },
        )

        with tracer.start_as_current_span(
            "pipeline.step",
            attributes={
                "pipeline.task_id": task_id,
                "pipeline.step": step_name,
                "pipeline.step_index": step_index,
            },
        ) as span:
            try:
                step_fn()
            except Exception as exc:
                step_duration_seconds = (time.perf_counter() - step_started_at)
                step_record.update(
                    {
                        "status": "FAILURE",
                        "finished_at": utc_now_iso(),
                        "duration_ms": round(step_duration_seconds * 1000, 2),
                        "error": str(exc),
                    }
                )
                timeline.update(
                    {
                        "status": "FAILURE",
                        "finished_at": utc_now_iso(),
                        "duration_ms": _duration_ms(pipeline_started_at),
                    }
                )
                set_span_error(span, exc)
                record_pipeline_step(step_name, step_duration_seconds, "failure")
                write_pipeline_timeline(timeline)
                self.update_state(
                    state="FAILURE",
                    meta={"step": step_name, "error": str(exc)},
                )
                raise

        step_duration_seconds = time.perf_counter() - step_started_at
        step_record.update(
            {
                "status": "SUCCESS",
                "finished_at": utc_now_iso(),
                "duration_ms": round(step_duration_seconds * 1000, 2),
            }
        )
        timeline["duration_ms"] = _duration_ms(pipeline_started_at)
        record_pipeline_step(step_name, step_duration_seconds, "success")
        write_pipeline_timeline(timeline)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": step_name,
                "progress": (step_index + 1) / total,
                "step_index": step_index + 1,
                "total_steps": total,
            },
        )

    timeline.update(
        {
            "status": "SUCCESS",
            "finished_at": utc_now_iso(),
            "duration_ms": _duration_ms(pipeline_started_at),
        }
    )
    write_pipeline_timeline(timeline)
    return {"status": "complete", "steps_completed": total}
