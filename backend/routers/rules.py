"""人工规则 CRUD API。"""

from __future__ import annotations

from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException

from paths import HUMAN_OVERRIDES_CSV, OUTPUT_DIR
from schemas.common import RulesUpdateBody, DifyExtractParams
from services.report_service import extract_rules_dify

router = APIRouter(prefix="/api/rules", tags=["规则"])


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    import numpy as np
    return df.replace({np.nan: None}).to_dict(orient="records")


@router.get("")
async def get_rules():
    """当前人工规则列表。"""
    if not HUMAN_OVERRIDES_CSV.exists():
        return {"rules": [], "raw": ""}
    df = pd.read_csv(HUMAN_OVERRIDES_CSV)
    return {
        "rules": _df_to_records(df),
        "raw": HUMAN_OVERRIDES_CSV.read_text(encoding="utf-8"),
    }


@router.put("")
async def save_rules(body: RulesUpdateBody):
    """保存人工规则 CSV。"""
    HUMAN_OVERRIDES_CSV.parent.mkdir(parents=True, exist_ok=True)
    HUMAN_OVERRIDES_CSV.write_text(body.csv_content, encoding="utf-8")
    return {"status": "saved"}


@router.get("/active")
async def active_rules():
    """当前生效的规则。"""
    path = OUTPUT_DIR / "active_human_overrides.csv"
    if not path.exists():
        return []
    return _df_to_records(pd.read_csv(path))


@router.post("/dify-extract")
async def dify_extract(params: DifyExtractParams):
    """调用 Dify Workflow B 从自然语言抽取规则草稿。"""
    try:
        csv_text = extract_rules_dify(
            params.human_rule_text,
            params.effective_start_date,
            params.effective_end_date,
        )
        return {"csv": csv_text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
