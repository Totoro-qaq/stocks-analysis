"""AI 报告生成 API — DeepSeek 流式 / Dify Workflow A。"""

from __future__ import annotations

import asyncio
import queue
import threading
from typing import AsyncIterator

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from services.report_service import (
    generate_deepseek_report,
    generate_dify_report,
    get_current_report,
)

router = APIRouter(prefix="/api/report", tags=["报告"])


def _stream_generator(generator) -> AsyncIterator[str]:
    """将同步生成器包装为异步流，逐 chunk 输出纯文本。"""
    q: queue.Queue[str | None] = queue.Queue()

    def _run() -> None:
        try:
            for chunk in generator:
                q.put(chunk)
            q.put(None)
        except Exception as exc:
            q.put(f"\n\n--- ERROR: {exc} ---\n\n")
            q.put(None)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    async def _stream() -> AsyncIterator[str]:
        loop = asyncio.get_event_loop()
        while True:
            try:
                item = await loop.run_in_executor(None, q.get, True, 0.2)
            except queue.Empty:
                continue
            if item is None:
                break
            yield item

    return _stream()


@router.get("/generate")
async def generate_report(
    focus: str = Query("balanced"),
    engine: str = Query("deepseek"),
    notes: str = Query(""),
):
    """触发报告生成（纯文本流式输出）。前端用 fetch + reader 接收。"""
    if engine == "dify":
        generator = generate_dify_report(focus, notes)
    else:
        generator = generate_deepseek_report(focus, notes)

    return StreamingResponse(
        _stream_generator(generator),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/current")
async def current_report():
    """获取当前已保存的报告内容。"""
    report = get_current_report()
    return {"content": report, "has_report": bool(report.strip())}
