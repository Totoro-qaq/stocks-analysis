from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from paths import OUTPUT_DIR

PIPELINE_TIMELINE_PATH = OUTPUT_DIR / "pipeline_timeline.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def write_pipeline_timeline(timeline: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timeline["updated_at"] = utc_now_iso()
    temp_path = PIPELINE_TIMELINE_PATH.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(PIPELINE_TIMELINE_PATH)


def read_pipeline_timeline() -> dict[str, Any]:
    if not PIPELINE_TIMELINE_PATH.exists():
        return {"task_id": None, "status": "EMPTY", "steps": []}

    try:
        data = json.loads(PIPELINE_TIMELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "task_id": None,
            "status": "UNAVAILABLE",
            "steps": [],
            "error": f"pipeline timeline is unreadable: {exc}",
        }

    if not isinstance(data, dict):
        return {"task_id": None, "status": "UNAVAILABLE", "steps": []}
    if not isinstance(data.get("steps"), list):
        data["steps"] = []
    return data
