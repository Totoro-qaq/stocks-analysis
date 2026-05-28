"""美股 50 股量化分析系统 — FastAPI 入口。

把 src/ 下所有 CLI 脚本的计算能力暴露为 REST API。
重计算走 Celery 异步任务，结果缓存在 Redis。
"""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 将项目根、src/ 和 backend/ 加入 sys.path
ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
BACKEND_DIR = ROOT / "backend"
for _p in (str(ROOT), str(SRC_DIR), str(BACKEND_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from paths import ensure_project_dirs  # noqa: E402
from observability import configure_fastapi_observability  # noqa: E402
from schemas.common import PipelineParams  # noqa: E402
from services.pipeline_timeline import read_pipeline_timeline  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时确保数据目录存在。"""
    ensure_project_dirs()
    yield


app = FastAPI(
    title="美股 50 股量化分析系统",
    description="FastAPI 后端，提供数据总览、基础分析、组合优化、前向验证、统计检验、因子分析、人工规则和 AI 报告 API。",
    version="2.0.0",
    lifespan=lifespan,
)

configure_fastapi_observability(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册路由 ──
from routers.data import router as data_router           # noqa: E402
from routers.analysis import router as analysis_router   # noqa: E402
from routers.portfolio import router as portfolio_router # noqa: E402
from routers.validation import router as validation_router  # noqa: E402
from routers.factor import router as factor_router       # noqa: E402
from routers.rules import router as rules_router         # noqa: E402
from routers.report import router as report_router       # noqa: E402

app.include_router(data_router)
app.include_router(analysis_router)
app.include_router(portfolio_router)
app.include_router(validation_router)
app.include_router(factor_router)
app.include_router(rules_router)
app.include_router(report_router)


# ── 全流程异步 ──
from backend.celery_app import celery_app  # noqa: E402
from celery.result import AsyncResult  # noqa: E402


@app.post("/api/pipeline/run")
async def pipeline_run(params: PipelineParams):
    """触发一键全流程异步执行。"""
    task = celery_app.send_task(
        "run_full_pipeline",
        args=[params.model_dump()],
    )
    return {"task_id": task.id, "status": "PENDING"}


@app.get("/api/pipeline/status/{task_id}")
async def pipeline_status(task_id: str):
    """查询异步任务进度。"""
    result = AsyncResult(task_id, app=celery_app)
    response = {
        "task_id": task_id,
        "status": result.state,
    }
    result_info = result.info if isinstance(result.info, dict) else {}
    if result.state == "SUCCESS":
        response["progress"] = 1.0
        response["result"] = result_info
    elif result_info:
        for key, value in result_info.items():
            if key != "status":
                response[key] = value
    if result.state == "FAILURE":
        response["error"] = str(result.info) if result.info else "Unknown error"
    return response


@app.get("/api/pipeline/timeline")
async def pipeline_timeline():
    return read_pipeline_timeline()


import asyncio
from sse_starlette.sse import EventSourceResponse

@app.get("/api/pipeline/stream/{task_id}")
async def pipeline_stream(task_id: str):
    """SSE endpoint for streaming task status to the frontend."""
    async def event_generator():
        result = AsyncResult(task_id, app=celery_app)
        last_state = None
        last_info = None

        while True:
            # Refresh state
            result = AsyncResult(task_id, app=celery_app)
            current_state = result.state
            current_info = result.info if isinstance(result.info, dict) else {}

            if current_state != last_state or current_info != last_info:
                progress = current_info.get("progress", 0.0)
                if current_state == "SUCCESS":
                    progress = 1.0

                yield {
                    "event": "message",
                    "data": json.dumps({
                        "task_id": task_id,
                        "status": current_state,
                        "step": current_info.get("step", ""),
                        "progress": progress,
                        "error": str(result.info) if current_state == "FAILURE" else None
                    }, ensure_ascii=False)
                }
                last_state = current_state
                last_info = current_info

            if current_state in ["SUCCESS", "FAILURE", "REVOKED"]:
                break
            
            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
