"""Celery 应用配置。

Broker + Result Backend 都用 Redis。
重计算任务（全流程、优化、walk-forward）异步执行。
"""

from __future__ import annotations

import sys

from celery import Celery

from paths import ENV_FILE


def _load_redis_url() -> str:
    """从 config/.env 读取 Redis URL，默认 localhost:6379。"""
    import os

    if ENV_FILE.exists():
        for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("REDIS_URL") or line.startswith("REDIS_BROKER_URL"):
                _, value = line.split("=", 1)
                return value.strip().strip('"').strip("'")
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


celery_app = Celery(
    "us_stock_mvp",
    broker=_load_redis_url(),
    backend=_load_redis_url(),
    include=["backend.tasks.pipeline"],
)

sys.modules.setdefault("celery_app", sys.modules[__name__])
sys.modules.setdefault("backend.celery_app", sys.modules[__name__])

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

try:
    from observability import configure_celery_observability

    configure_celery_observability(celery_app)
except ImportError:
    pass
