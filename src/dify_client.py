"""Dify Workflow API 客户端封装。

通过 ``config/.env`` 中的 DIFY_* 字段调用 Workflow A（投资报告生成）和
Workflow B（人工规则抽取）两个工作流。Workflow A 走流式输出，Workflow B
走 blocking 输出（CSV 一次返回更稳）。

设计要点：
- 不依赖第三方 SDK，只用 ``requests``。
- streaming 解析 Dify 标准 SSE，事件名以 ``text_chunk`` 为主，最终拼接成
  完整 markdown。
- 网络/解析异常统一抛 :class:`DifyClientError`，由调用方在 UI 中提示。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Iterator

import requests

from paths import ENV_FILE


class DifyClientError(RuntimeError):
    """Dify 调用失败统一异常。"""


@dataclass(frozen=True)
class DifyConfig:
    base_url: str
    report_api_key: str
    rules_api_key: str
    user: str
    response_mode: str
    timeout: int


def _load_dotenv(path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_dify_config() -> DifyConfig:
    """从 ``config/.env`` 读取 Dify 配置；缺失关键字段直接抛错。"""
    _load_dotenv(ENV_FILE)
    base_url = os.getenv("DIFY_BASE_URL", "").rstrip("/")
    if not base_url:
        raise DifyClientError("DIFY_BASE_URL 未配置")
    return DifyConfig(
        base_url=base_url,
        report_api_key=os.getenv("DIFY_REPORT_API_KEY", ""),
        rules_api_key=os.getenv("DIFY_RULES_API_KEY", ""),
        user=os.getenv("DIFY_USER", "stocks-analysis-local"),
        response_mode=os.getenv("DIFY_RESPONSE_MODE", "streaming"),
        timeout=int(os.getenv("DIFY_TIMEOUT", "120")),
    )


def _headers(api_key: str) -> dict[str, str]:
    if not api_key:
        raise DifyClientError("Dify API Key 未配置")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _post(url: str, api_key: str, payload: dict[str, Any], stream: bool, timeout: int) -> requests.Response:
    try:
        resp = requests.post(url, headers=_headers(api_key), json=payload, stream=stream, timeout=timeout)
    except requests.RequestException as exc:
        raise DifyClientError(f"调用 Dify 失败: {exc}") from exc
    if resp.status_code >= 400:
        raise DifyClientError(f"Dify 返回 {resp.status_code}: {resp.text[:500]}")
    return resp


def run_report_workflow(inputs: dict[str, str]) -> Iterator[str]:
    """调用 Workflow A，逐块 yield markdown 文本。

    Dify SSE 中每条形如 ``data: {...}\\n\\n``。其中 ``event=text_chunk`` 的
    ``data.text`` 是模型输出片段；``event=workflow_finished`` 时如果之前没接到
    任何片段（比如非流式应用），再从 ``outputs.investment_report_md`` 兜底。

    DeepSeek-R1 / Qwen QwQ 等思维链模型会把推理写在 ``<think>...</think>``
    之间，正文里不需要展示，本函数原地剥掉。
    """
    config = load_dify_config()
    url = f"{config.base_url}/workflows/run"
    payload = {"inputs": inputs, "response_mode": "streaming", "user": config.user}
    resp = _post(url, config.report_api_key, payload, stream=True, timeout=config.timeout)

    received_any = False
    final_text = ""
    in_think = False
    pending = ""
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        chunk = line[len("data:"):].strip()
        if not chunk:
            continue
        try:
            event = json.loads(chunk)
        except json.JSONDecodeError:
            continue

        event_type = event.get("event")
        data = event.get("data") or {}
        if event_type == "text_chunk":
            text = data.get("text", "")
            if not text:
                continue
            received_any = True
            cleaned, in_think, pending = _strip_thinking(pending + text, in_think)
            if cleaned:
                yield cleaned
        elif event_type == "workflow_finished":
            outputs = data.get("outputs") or {}
            final_text = (
                outputs.get("investment_report_md")
                or outputs.get("text")
                or ""
            )
        elif event_type == "error":
            raise DifyClientError(f"Dify 节点报错: {data}")

    if not received_any and final_text:
        cleaned, _, _ = _strip_thinking(final_text, False)
        if cleaned:
            yield cleaned


def _strip_thinking(buffer: str, in_think: bool) -> tuple[str, bool, str]:
    """剥离思维链标签 ``<think>...</think>``。

    增量调用：``buffer`` 是当前累计未输出的文本，``in_think`` 表示当前是否
    处于 think 段中。返回 (可输出文本, 新的 in_think, 残留 buffer)。
    残留 buffer 是疑似不完整标签的尾部，下次拼到新 chunk 前再继续匹配。
    """
    output = []
    while buffer:
        if in_think:
            close_idx = buffer.find("</think>")
            if close_idx == -1:
                if len(buffer) > 7:
                    return "".join(output), True, buffer[-7:]
                return "".join(output), True, buffer
            buffer = buffer[close_idx + len("</think>"):]
            in_think = False
        else:
            open_idx = buffer.find("<think>")
            if open_idx == -1:
                if len(buffer) > 6:
                    output.append(buffer[:-6])
                    return "".join(output), False, buffer[-6:]
                return "".join(output) + buffer, False, ""
            output.append(buffer[:open_idx])
            buffer = buffer[open_idx + len("<think>"):]
            in_think = True
    return "".join(output), in_think, ""


def run_rules_workflow(human_rule_text: str, effective_start_date: str, effective_end_date: str = "") -> str:
    """调用 Workflow B，blocking 模式返回 CSV 文本。"""
    config = load_dify_config()
    url = f"{config.base_url}/workflows/run"
    payload = {
        "inputs": {
            "human_rule_text": human_rule_text,
            "effective_start_date": effective_start_date,
            "effective_end_date": effective_end_date,
        },
        "response_mode": "blocking",
        "user": config.user,
    }
    resp = _post(url, config.rules_api_key, payload, stream=False, timeout=config.timeout)
    try:
        body = resp.json()
    except ValueError as exc:
        raise DifyClientError(f"Dify 返回非 JSON: {resp.text[:500]}") from exc

    data = body.get("data") or {}
    if data.get("status") == "failed":
        raise DifyClientError(f"Dify 工作流失败: {data.get('error')}")
    outputs = data.get("outputs") or {}
    csv_text = outputs.get("rules_csv") or outputs.get("text") or ""
    if not csv_text:
        raise DifyClientError(f"Dify 返回为空: {body}")
    return csv_text.strip()
