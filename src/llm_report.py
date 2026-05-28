from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Windows 控制台默认 cp936，DeepSeek 流式中文输出会触发 GBK 编码异常。
# 强制 stdout/stderr 走 UTF-8，并忽略不可编码字符。
for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from paths import ENV_FILE, HUMAN_OVERRIDES_CSV, OUTPUT_DIR, ROOT, ensure_project_dirs


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8")


def model_config() -> dict[str, object]:
    load_dotenv(ENV_FILE)
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is missing in .env")

    model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    extra_body: dict[str, object] = {}
    # DeepSeek 思维链模型（reasoner 系列、v3.x reasoning 系列）会先输出
    # reasoning 字段。我们这里只要最终回答，关闭思考过程更干净。
    if "reason" in model_name.lower() or os.getenv("DEEPSEEK_THINKING", "disabled").lower() == "enabled":
        extra_body["reasoning_effort"] = os.getenv("DEEPSEEK_REASONING_EFFORT", "low")
    else:
        extra_body["thinking"] = {"type": "disabled"}

    return {
        "api_key": api_key,
        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        "model": model_name,
        "temperature": float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2")),
        "streaming": os.getenv("DEEPSEEK_STREAMING", "true").lower() in {"1", "true", "yes", "on"},
        "extra_body": extra_body,
    }


def load_report_inputs(notes_path: Path | None) -> dict[str, str]:
    notes = read_text(notes_path) if notes_path else ""
    return {
        "analysis_summary_json": read_text(OUTPUT_DIR / "analysis_summary.json"),
        "portfolio_metrics_csv": read_text(OUTPUT_DIR / "portfolio_metrics.csv"),
        "opt_portfolio_metrics_csv": read_text(OUTPUT_DIR / "optimized_portfolio_metrics.csv"),
        "walk_forward_summary_csv": read_text(OUTPUT_DIR / "walk_forward_summary.csv"),
        "significance_tests_csv": read_text(OUTPUT_DIR / "significance_tests.csv"),
        "bootstrap_intervals_csv": read_text(OUTPUT_DIR / "bootstrap_intervals.csv"),
        "human_overrides_csv": read_text(HUMAN_OVERRIDES_CSV),
        "human_research_notes": notes,
    }


def build_messages(inputs: dict[str, str], report_focus: str) -> list[SystemMessage | HumanMessage]:
    system = """你是一个严谨的中文投资研究报告助手。你负责把已经计算好的量化结果和人工研究备注整理成课程作业级别的投资策略分析报告。

重要规则：
1. 只能使用输入中出现的数据、指标、规则和人工备注。
2. 不得编造公司新闻、财报数据、监管事件或宏观数据。
3. 不得直接给出投资建议，不得说“应该买入/卖出”。
4. 必须区分机器计算结果、人工规则干预、解释性判断和模型局限。
5. 对马科维茨最大夏普组合必须提示过拟合风险。
6. 对 walk-forward 结果必须强调样本外表现。
7. 对统计显著性必须同时说明 p 值和 bootstrap 区间的不确定性。
8. 必须说明当前股票池无法完全排除生存者偏差。
9. 输出 Markdown，语言为中文。
"""
    human = f"""请基于以下输入生成一份结构化投资策略分析报告。

报告重点：{report_focus}

【分析摘要 JSON】
{inputs["analysis_summary_json"]}

【等权组合指标 CSV】
{inputs["portfolio_metrics_csv"]}

【优化组合指标 CSV】
{inputs["opt_portfolio_metrics_csv"]}

【Walk-forward 样本外验证 CSV】
{inputs["walk_forward_summary_csv"]}

【统计显著性检验 CSV】
{inputs["significance_tests_csv"]}

【Bootstrap 区间 CSV】
{inputs["bootstrap_intervals_csv"]}

【人工规则 CSV】
{inputs["human_overrides_csv"]}

【人工研究备注】
{inputs["human_research_notes"]}

请生成以下章节：

# 美股科技股 50 股投资组合策略分析报告

## 1. 研究目标与数据范围
## 2. 方法论
## 3. 单股风险收益特征
## 4. 组合表现比较
## 5. 样本外验证与过拟合风险
## 6. 人工规则干预
## 7. 统计显著性与稳健性
## 8. 主要风险与模型局限
## 9. 结论
"""
    return [SystemMessage(content=system), HumanMessage(content=human)]


def generate_report(report_focus: str, notes_path: Path | None, output_path: Path) -> None:
    config = model_config()
    llm = ChatOpenAI(
        model=str(config["model"]),
        api_key=str(config["api_key"]),
        base_url=str(config["base_url"]),
        temperature=float(config["temperature"]),
        streaming=bool(config["streaming"]),
        extra_body=config.get("extra_body") or None,
    )
    messages = build_messages(load_report_inputs(notes_path), report_focus)

    if bool(config["streaming"]):
        chunks: list[str] = []
        for chunk in llm.stream(messages):
            text = chunk.content or ""
            if text:
                print(text, end="", flush=True)
                chunks.append(text)
        print("", flush=True)
        output_path.write_text("".join(chunks), encoding="utf-8")
    else:
        response = llm.invoke(messages)
        text = str(response.content)
        print(text, flush=True)
        output_path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a streaming DeepSeek/LangChain investment report.")
    parser.add_argument("--focus", default="balanced", help="Report focus: balanced, risk_control, benchmark_outperformance, robustness.")
    parser.add_argument("--notes", default=None, help="Optional human research notes markdown/txt file.")
    parser.add_argument("--output", default=str(OUTPUT_DIR / "investment_report.md"), help="Output markdown path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_project_dirs()
    notes_path = Path(args.notes) if args.notes else None
    generate_report(args.focus, notes_path, Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
