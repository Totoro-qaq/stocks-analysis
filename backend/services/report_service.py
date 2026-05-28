"""报告生成服务 — 封装 src/llm_report.py + dify_client.py。"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from paths import OUTPUT_DIR, CONFIG_DIR, HUMAN_OVERRIDES_CSV


HUMAN_NOTES_MD = CONFIG_DIR / "human_notes.md"


def load_report_data() -> dict[str, str]:
    """加载所有报告输入数据。"""

    def _read(name: str) -> str:
        path = OUTPUT_DIR / name
        return path.read_text(encoding="utf-8") if path.exists() else ""

    overrides_text = (
        HUMAN_OVERRIDES_CSV.read_text(encoding="utf-8") if HUMAN_OVERRIDES_CSV.exists() else ""
    )

    return {
        "analysis_summary_json": _read("analysis_summary.json"),
        "portfolio_metrics_csv": _read("portfolio_metrics.csv"),
        "opt_portfolio_metrics_csv": _read("optimized_portfolio_metrics.csv"),
        "walk_forward_summary_csv": _read("walk_forward_summary.csv"),
        "significance_tests_csv": _read("significance_tests.csv"),
        "bootstrap_intervals_csv": _read("bootstrap_intervals.csv"),
        "human_overrides_csv": overrides_text,
        "human_research_notes": "",
        "pca_explained_variance_csv": _read("pc_explained_variance.csv"),
    }


def generate_deepseek_report(focus: str, notes: str) -> Iterator[str]:
    """使用本地 DeepSeek (LangChain) 流式生成报告。"""
    import warnings
    warnings.filterwarnings("ignore")

    # 保存备注
    HUMAN_NOTES_MD.parent.mkdir(parents=True, exist_ok=True)
    HUMAN_NOTES_MD.write_text(notes, encoding="utf-8")

    data = load_report_data()
    data["human_research_notes"] = notes

    from llm_report import model_config, build_messages
    from langchain_openai import ChatOpenAI

    config = model_config()
    llm = ChatOpenAI(
        model=str(config["model"]),
        api_key=str(config["api_key"]),
        base_url=str(config["base_url"]),
        temperature=float(config["temperature"]),
        streaming=True,
        extra_body=config.get("extra_body") or None,
    )
    messages = build_messages(data, focus)

    full_text_parts: list[str] = []
    for chunk in llm.stream(messages):
        text = chunk.content or ""
        if text:
            full_text_parts.append(text)
            yield text

    # 保存到文件
    full_text = "".join(full_text_parts)
    if full_text.strip():
        report_path = OUTPUT_DIR / "investment_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(full_text, encoding="utf-8")


def generate_dify_report(focus: str, notes: str) -> Iterator[str]:
    """使用 Dify Workflow A 流式生成报告。"""
    data = load_report_data()
    data["human_research_notes"] = notes
    data["report_focus"] = focus
    data["report_language"] = "zh-CN"

    from dify_client import run_report_workflow

    full_text_parts: list[str] = []
    for chunk in run_report_workflow(data):
        full_text_parts.append(chunk)
        yield chunk

    full_text = "".join(full_text_parts)
    if full_text.strip():
        report_path = OUTPUT_DIR / "investment_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(full_text, encoding="utf-8")


def get_current_report() -> str:
    path = OUTPUT_DIR / "investment_report.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def extract_rules_dify(human_rule_text: str, start_date: str, end_date: str) -> str:
    """调用 Dify Workflow B 抽取规则。"""
    from dify_client import run_rules_workflow
    return run_rules_workflow(human_rule_text, start_date, end_date)
