from __future__ import annotations

import contextlib
import datetime as _dt
import importlib
import io
import logging
import os
import sys
import traceback
import warnings
from pathlib import Path
from typing import Iterator

# === 静默策略：在 import 任何科学计算/AI 库之前，先关掉运行时警告 ===
# scipy.optimize 在 SLSQP 求解时会抛 RuntimeWarning（值越界、除零等），
# numpy/sklearn/pandas 偶尔也会刷 FutureWarning，UI 上看到这些会非常不专业。
warnings.filterwarnings("ignore")
os.environ.setdefault("PYTHONWARNINGS", "ignore")

# LangChain / httpx / openai 的 INFO 日志默认会打到 stderr，
# Streamlit 在某些部署模式下会把这些日志拉到前端，统一压到 ERROR 级别。
for _logger_name in ("langchain", "langchain_openai", "httpx", "httpcore", "openai"):
    logging.getLogger(_logger_name).setLevel(logging.ERROR)


ROOT = Path(__file__).resolve().parent
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# 所有后端任务的原生 stdout/stderr 都重定向到这个日志文件，UI 永远不直接渲染原始字符串。
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
RUN_LOG = LOG_DIR / "dashboard_run.log"

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dify_client import DifyClientError, run_report_workflow, run_rules_workflow
from paths import (
    ANALYSIS_UNIVERSE_50_CSV,
    CONFIG_DIR,
    DAILY_PRICES_CSV,
    DATA_FETCH_FAILURES_CSV,
    HUMAN_OVERRIDES_CSV,
    OUTPUT_DIR,
    ensure_project_dirs,
)


HUMAN_NOTES_MD = CONFIG_DIR / "human_notes.md"
HUMAN_OVERRIDES_ARG = str(HUMAN_OVERRIDES_CSV)


def report_inputs_for_dify(focus: str, notes: str, language: str = "zh-CN") -> dict[str, str]:
    """组装 Workflow A 的 inputs，文件缺失时给空串，避免 Dify 报错。"""

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
        "human_research_notes": notes,
        "pca_explained_variance_csv": _read("pc_explained_variance.csv"),
        "report_focus": focus,
        "report_language": language,
    }


st.set_page_config(
    page_title="美股 50 股策略分析 MVP",
    layout="wide",
    initial_sidebar_state="expanded",
)


def csv_path(name: str) -> Path:
    return OUTPUT_DIR / name


@st.cache_data(show_spinner=False)
def read_csv(path: str, parse_dates: tuple[str, ...] = ()) -> pd.DataFrame:
    file_path = Path(path)
    if not file_path.exists():
        return pd.DataFrame()
    return pd.read_csv(file_path, parse_dates=list(parse_dates))


@st.cache_data(show_spinner=False)
def read_text(path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8")


@contextlib.contextmanager
def _silent_stdio() -> Iterator[io.StringIO]:
    """把 stdout/stderr 同时重定向到字符串缓冲和 run.log，
    保证后端脚本里散落的 print/底层警告永远不会出现在 Streamlit 页面上。"""
    buffer = io.StringIO()
    with open(RUN_LOG, "a", encoding="utf-8") as log_file:

        class _Tee:
            def write(self, data: str) -> int:
                buffer.write(data)
                try:
                    log_file.write(data)
                    log_file.flush()
                except Exception:  # noqa: BLE001
                    pass
                return len(data)

            def flush(self) -> None:
                try:
                    log_file.flush()
                except Exception:  # noqa: BLE001
                    pass

        tee = _Tee()
        with contextlib.redirect_stdout(tee), contextlib.redirect_stderr(tee):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                yield buffer


def run_module_main(
    module_name: str,
    cli_args: list[str] | None = None,
    log_label: str = "",
) -> tuple[bool, str]:
    """直接 import 后端模块并调用其 main()，避免 subprocess 把原始 stdout 暴露到前端。

    - cli_args 通过临时替换 sys.argv 注入，保留模块原本的 argparse 入口。
    - 所有 print/警告被静默到日志文件；只有失败时返回最后几行用于折叠展示。
    - 模块缓存会被清除一次，确保每次点击按钮都能加载到最新代码（开发期常见诉求）。
    """
    cli_args = cli_args or []
    saved_argv = sys.argv
    sys.argv = [f"{module_name}.py", *cli_args]
    header = f"\n===== {_dt.datetime.now().isoformat(timespec='seconds')} | {log_label or module_name} =====\n"
    with open(RUN_LOG, "a", encoding="utf-8") as log_file:
        log_file.write(header)
        log_file.write(f"argv={sys.argv}\n")
    try:
        with _silent_stdio() as buffer:
            try:
                module = importlib.import_module(module_name)
                # 模块在前一次调用后已经把 OUTPUT_DIR 等模块级变量初始化好，这里直接调 main。
                rc = module.main()
            except SystemExit as exc:
                rc = int(exc.code) if exc.code is not None else 0
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                rc = 1
        ok = rc == 0
        return ok, buffer.getvalue()
    finally:
        sys.argv = saved_argv


def clear_cache() -> None:
    read_csv.clear()
    read_text.clear()


def metric_card(label: str, value: float | int | str, fmt: str = "{:.2%}") -> None:
    if isinstance(value, (float, int)) and pd.notna(value):
        st.metric(label, fmt.format(value))
    else:
        st.metric(label, str(value))


def plot_cumulative_returns(cumulative: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    date_col = "date" if "date" in cumulative.columns else cumulative.columns[0]
    for column in cumulative.columns:
        if column == date_col:
            continue
        fig.add_trace(go.Scatter(x=cumulative[date_col], y=cumulative[column], mode="lines", name=column))
    fig.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_tickformat=".0%",
        legend_orientation="h",
        legend_y=-0.2,
    )
    return fig


def drawdown_from_returns(returns: pd.Series) -> pd.Series:
    wealth = (1 + returns.dropna()).cumprod()
    return wealth / wealth.cummax() - 1


def plot_drawdown(returns: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    date_col = "date" if "date" in returns.columns else returns.columns[0]
    for column in returns.columns:
        if column == date_col:
            continue
        dd = drawdown_from_returns(pd.Series(returns[column].values, index=pd.to_datetime(returns[date_col])))
        fig.add_trace(go.Scatter(x=dd.index, y=dd.values, mode="lines", name=column))
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_tickformat=".0%",
        legend_orientation="h",
        legend_y=-0.2,
    )
    return fig


def page_overview() -> None:
    st.subheader("数据总览")
    universe = read_csv(str(ANALYSIS_UNIVERSE_50_CSV))
    prices = read_csv(str(DAILY_PRICES_CSV), parse_dates=("date",))
    failures = read_csv(str(DATA_FETCH_FAILURES_CSV))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("研究股票数", universe["ticker"].nunique() if not universe.empty else 0, "{}")
    with col2:
        metric_card("行情行数", len(prices), "{:,.0f}")
    with col3:
        st.metric("起始日期", prices["date"].min().date().isoformat() if not prices.empty else "-")
    with col4:
        st.metric("结束日期", prices["date"].max().date().isoformat() if not prices.empty else "-")

    st.caption("股票池来自当前 XLK 官方持仓筛选，不是 point-in-time 历史成分股，不能完全排除生存者偏差。")

    st.dataframe(universe, use_container_width=True, height=360)

    if failures.empty or len(failures.dropna(how="all")) == 0:
        st.success("当前数据抓取失败记录为空。")
    else:
        st.warning("存在抓取失败记录。")
        st.dataframe(failures, use_container_width=True)


def page_market() -> None:
    st.subheader("市场与基准")
    cumulative = read_csv(str(csv_path("cumulative_returns.csv")), parse_dates=("date",))
    if cumulative.empty:
        st.warning("缺少 cumulative_returns.csv，请先运行 analysis_engine.py。")
        return

    st.plotly_chart(plot_cumulative_returns(cumulative), use_container_width=True)

    prices = read_csv(str(DAILY_PRICES_CSV), parse_dates=("date",))
    vix = prices[prices["ticker"].eq("^VIX")].copy()
    if not vix.empty:
        fig = px.line(vix, x="date", y="close", title="VIX 恐慌指数")
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)


def page_single_stock() -> None:
    st.subheader("单股分析")
    metrics = read_csv(str(csv_path("single_stock_metrics.csv")))
    bollinger = read_csv(str(csv_path("bollinger_bands.csv")), parse_dates=("date",))

    if metrics.empty:
        st.warning("缺少 single_stock_metrics.csv，请先运行 analysis_engine.py。")
        return

    left, right = st.columns([1, 2])
    with left:
        ticker = st.selectbox("选择股票", metrics["ticker"].tolist())
        selected = metrics[metrics["ticker"].eq(ticker)].iloc[0]
        metric_card("年化收益率", selected["annualized_return"])
        metric_card("年化波动率", selected["annualized_volatility"])
        metric_card("夏普比率", selected["sharpe_ratio"], "{:.2f}")
        metric_card("最大回撤", selected["max_drawdown"])

    with right:
        stock_band = bollinger[bollinger["ticker"].eq(ticker)].dropna(subset=["middle_band"])
        if not stock_band.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=stock_band["date"], y=stock_band["price"], mode="lines", name="价格"))
            fig.add_trace(go.Scatter(x=stock_band["date"], y=stock_band["upper_band"], mode="lines", name="上轨"))
            fig.add_trace(go.Scatter(x=stock_band["date"], y=stock_band["middle_band"], mode="lines", name="中轨"))
            fig.add_trace(go.Scatter(x=stock_band["date"], y=stock_band["lower_band"], mode="lines", name="下轨"))
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10), legend_orientation="h", legend_y=-0.2)
            st.plotly_chart(fig, use_container_width=True)

    st.dataframe(metrics, use_container_width=True, height=420)


def page_portfolio() -> None:
    st.subheader("组合优化")
    opt_metrics = read_csv(str(csv_path("optimized_portfolio_metrics.csv")))
    weights = read_csv(str(csv_path("portfolio_weights.csv")))
    cumulative = read_csv(str(csv_path("optimized_portfolio_cumulative_returns.csv")), parse_dates=("date",))
    frontier = read_csv(str(csv_path("efficient_frontier.csv")))

    if opt_metrics.empty:
        st.warning("缺少优化结果，请先运行 portfolio_optimization.py。")
        return

    st.dataframe(opt_metrics, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(plot_cumulative_returns(cumulative), use_container_width=True)
    with col2:
        returns = read_csv(str(csv_path("optimized_portfolio_returns.csv")), parse_dates=("date",))
        st.plotly_chart(plot_drawdown(returns), use_container_width=True)

    if not weights.empty:
        portfolio = st.selectbox("选择权重组合", [col for col in weights.columns if col != "ticker"])
        top_weights = weights[["ticker", portfolio]].sort_values(portfolio, ascending=False).head(20)
        fig = px.bar(top_weights, x="ticker", y=portfolio, title=f"{portfolio} 前 20 权重")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10), yaxis_tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

    if not frontier.empty:
        fig = px.scatter(frontier, x="annualized_volatility", y="annualized_return", title="有效前沿")
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10), xaxis_tickformat=".0%", yaxis_tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)


def page_validation() -> None:
    st.subheader("Walk-forward 与统计检验")
    wf_summary = read_csv(str(csv_path("walk_forward_summary.csv")))
    wf_metrics = read_csv(str(csv_path("walk_forward_window_metrics.csv")))
    tests = read_csv(str(csv_path("significance_tests.csv")))
    bootstrap = read_csv(str(csv_path("bootstrap_intervals.csv")))

    if wf_summary.empty:
        st.warning("缺少 walk-forward 输出，请先运行 walk_forward.py。")
        return

    st.markdown("#### 样本外汇总")
    st.dataframe(wf_summary, use_container_width=True)

    fig = px.bar(
        wf_summary,
        x="portfolio",
        y=["avg_test_sharpe", "avg_train_sharpe"],
        barmode="group",
        title="训练期与测试期平均夏普比率",
    )
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)

    if not wf_metrics.empty:
        fig = px.line(
            wf_metrics,
            x="test_start",
            y="test_sharpe_ratio",
            color="portfolio",
            markers=True,
            title="各测试窗口夏普比率",
        )
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 统计显著性")
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(tests, use_container_width=True, height=360)
    with col2:
        st.dataframe(bootstrap, use_container_width=True, height=360)


def page_correlation() -> None:
    st.subheader("相关性矩阵")
    corr = read_csv(str(csv_path("correlation_matrix.csv")))
    if corr.empty:
        st.warning("缺少 correlation_matrix.csv，请先运行 analysis_engine.py。")
        return
    corr = corr.rename(columns={corr.columns[0]: "ticker"}).set_index("ticker")
    fig = px.imshow(corr, color_continuous_scale="RdBu_r", zmin=-1, zmax=1, title="50 股收益率相关性")
    fig.update_layout(height=760, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig, use_container_width=True)


def page_rules() -> None:
    st.subheader("人工规则干预")
    rules_path = HUMAN_OVERRIDES_CSV

    if "rules_text" not in st.session_state:
        st.session_state["rules_text"] = read_text(str(rules_path))

    with st.expander("Dify Workflow B：自然语言 → 规则草稿", expanded=False):
        st.caption("把基本面、新闻、监管或风险判断写成自然语言，由 Dify 生成 human_overrides.csv 兼容草稿。审核后再合并。")
        rule_text = st.text_area(
            "人工判断（自然语言）",
            height=140,
            placeholder="例如：英伟达近期监管不确定性升高，未来 6 个月最大权重限制到 5%。",
            key="rule_nl_input",
        )
        date_col1, date_col2 = st.columns(2)
        today = _dt.date.today().isoformat()
        with date_col1:
            start_date = st.text_input("默认开始日期", value=today, key="rule_start_date")
        with date_col2:
            end_date = st.text_input("默认结束日期（可空）", value="", key="rule_end_date")

        if "rules_draft" not in st.session_state:
            st.session_state["rules_draft"] = ""

        if st.button("调用 Dify 抽取草稿", use_container_width=True):
            if not rule_text.strip():
                st.warning("请先填写人工判断文本。")
            else:
                try:
                    with st.spinner("Dify 正在抽取规则..."):
                        csv_text = run_rules_workflow(rule_text, start_date, end_date)
                    st.session_state["rules_draft"] = csv_text
                    st.success("草稿已生成，请在下方审核。")
                except DifyClientError as exc:
                    st.error(f"Dify 调用失败：{exc}")

        draft = st.session_state["rules_draft"]
        if draft:
            st.code(draft, language="csv")
            merge_col, replace_col = st.columns(2)
            with merge_col:
                if st.button("追加到当前规则（保留表头一份）", use_container_width=True):
                    st.session_state["rules_text"] = _merge_overrides_csv(
                        st.session_state["rules_text"], draft
                    )
                    st.success("已追加到下方编辑区，记得点保存。")
            with replace_col:
                if st.button("用草稿替换当前规则", use_container_width=True):
                    st.session_state["rules_text"] = draft
                    st.success("已替换到下方编辑区，记得点保存。")

    edited = st.text_area(
        "编辑 human_overrides.csv",
        value=st.session_state["rules_text"],
        height=260,
        key="rules_text_area",
    )
    st.session_state["rules_text"] = edited

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("保存规则", use_container_width=True):
            rules_path.parent.mkdir(parents=True, exist_ok=True)
            rules_path.write_text(edited, encoding="utf-8")
            clear_cache()
            st.success("已保存 human_overrides.csv")
    with col2:
        if st.button("重新计算组合", use_container_width=True):
            rules_path.parent.mkdir(parents=True, exist_ok=True)
            rules_path.write_text(edited, encoding="utf-8")
            steps: list[tuple[str, str, list[str]]] = [
                ("组合优化", "portfolio_optimization", ["--rules", HUMAN_OVERRIDES_ARG]),
                ("前向验证", "walk_forward", ["--rules", HUMAN_OVERRIDES_ARG]),
                ("统计检验", "stat_tests", []),
            ]
            ok_all = True
            with st.status("正在重新计算组合、前向验证和统计检验...", expanded=False) as status:
                for label, module_name, cli_args in steps:
                    status.update(label=f"正在执行：{label} ...")
                    ok, _ = run_module_main(module_name, cli_args, log_label=label)
                    ok_all = ok_all and ok
                status.update(
                    label="重算完成" if ok_all else "重算存在失败，详见 logs/dashboard_run.log",
                    state="complete" if ok_all else "error",
                )
            clear_cache()
            if ok_all:
                st.success("重算完成")
            else:
                st.error("部分任务失败，详见 logs/dashboard_run.log")
    with col3:
        active = read_csv(str(csv_path("active_human_overrides.csv")))
        st.metric("当前生效规则数", len(active) if not active.empty else 0)

    active = read_csv(str(csv_path("active_human_overrides.csv")))
    if not active.empty:
        st.dataframe(active, use_container_width=True)


def _merge_overrides_csv(existing: str, draft: str) -> str:
    """把草稿 CSV 追加到现有规则末尾；如果现有为空，整段返回草稿。"""
    existing = (existing or "").strip()
    draft = (draft or "").strip()
    if not draft:
        return existing
    if not existing:
        return draft
    draft_lines = draft.splitlines()
    if not draft_lines:
        return existing
    body = draft_lines[1:] if "ticker" in draft_lines[0].lower() else draft_lines
    appended = "\n".join(line for line in body if line.strip())
    if not appended:
        return existing
    return existing.rstrip("\n") + "\n" + appended + "\n"


def page_report() -> None:
    st.subheader("智能报告")
    report_path = OUTPUT_DIR / "investment_report.md"

    col1, col2 = st.columns([1, 2])
    with col1:
        engine = st.radio(
            "生成方式",
            ["Dify Workflow A", "本地 DeepSeek (LangChain)"],
            help="Dify 走云端工作流；本地 LangChain 直连 DeepSeek。",
        )
        focus = st.selectbox("报告重点", ["balanced", "risk_control", "benchmark_outperformance", "robustness"])
        notes = st.text_area("人工研究备注，可选", height=200)

        if st.button("生成/刷新报告", use_container_width=True):
            HUMAN_NOTES_MD.parent.mkdir(parents=True, exist_ok=True)
            HUMAN_NOTES_MD.write_text(notes, encoding="utf-8")
            if engine.startswith("Dify"):
                inputs = report_inputs_for_dify(focus, notes)
                placeholder = col2.empty()
                buffer = io.StringIO()
                try:
                    with st.spinner("Dify Workflow A 正在生成报告..."):
                        for chunk in run_report_workflow(inputs):
                            buffer.write(chunk)
                            placeholder.markdown(buffer.getvalue())
                    text = buffer.getvalue().strip()
                    if not text:
                        st.warning("Dify 没有返回内容。检查工作流输出变量名是否为 investment_report_md。")
                    else:
                        report_path.parent.mkdir(parents=True, exist_ok=True)
                        report_path.write_text(text, encoding="utf-8")
                        clear_cache()
                        st.success("报告已生成并保存")
                except DifyClientError as exc:
                    st.error(f"Dify 调用失败：{exc}")
            else:
                # 直接调用 llm_report 的函数，用 placeholder 流式渲染 markdown，
                # 原始 stdout/stderr 全部静默到 run.log，避免 LangChain/httpx 日志糊到前端。
                placeholder = col2.empty()
                buffer = io.StringIO()
                try:
                    import llm_report  # noqa: WPS433  动态 import 是为了能感知 src 目录变化

                    with st.spinner("本地 DeepSeek 正在生成报告..."):
                        with _silent_stdio():
                            config = llm_report.model_config()
                            from langchain_openai import ChatOpenAI

                            llm = ChatOpenAI(
                                model=str(config["model"]),
                                api_key=str(config["api_key"]),
                                base_url=str(config["base_url"]),
                                temperature=float(config["temperature"]),
                                streaming=True,
                                extra_body=config.get("extra_body") or None,
                            )
                            messages = llm_report.build_messages(
                                llm_report.load_report_inputs(HUMAN_NOTES_MD),
                                focus,
                            )
                            for chunk in llm.stream(messages):
                                text = chunk.content or ""
                                if text:
                                    buffer.write(text)
                                    placeholder.markdown(buffer.getvalue())
                    text = buffer.getvalue().strip()
                    if not text:
                        st.warning("DeepSeek 没有返回内容，请检查 .env 中的 API Key 或网络。")
                    else:
                        report_path.parent.mkdir(parents=True, exist_ok=True)
                        report_path.write_text(text, encoding="utf-8")
                        clear_cache()
                        st.success("报告已生成")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"本地 DeepSeek 调用失败：{exc}（详见 logs/dashboard_run.log）")

    with col2:
        report = read_text(str(report_path))
        if report:
            st.markdown(report)
        else:
            st.info("还没有报告。点击左侧按钮生成。")


def _run_with_log(label: str, module_name: str, cli_args: list[str] | None = None, host=None) -> bool:
    """执行模块的 main()，UI 只展示成功/失败状态，原始日志写入 logs/dashboard_run.log。"""
    host = host or st.sidebar
    with st.spinner(f"正在执行：{label} ..."):
        ok, _ = run_module_main(module_name, cli_args, log_label=label)
    clear_cache()
    if ok:
        host.success(f"{label} 完成")
    else:
        host.error(f"{label} 失败，详见 logs/dashboard_run.log")
    return ok


def sidebar_actions() -> None:
    st.sidebar.header("操作")
    if st.sidebar.button("刷新缓存", use_container_width=True):
        clear_cache()
        st.rerun()

    st.sidebar.caption("推荐顺序：基础分析 -> 组合优化 -> 前向验证 -> 统计检验 -> 报告。")
    if st.sidebar.button("一键全流程", use_container_width=True):
        steps: list[tuple[str, str, list[str]]] = [
            ("基础分析", "analysis_engine", []),
            ("组合优化", "portfolio_optimization", ["--rules", HUMAN_OVERRIDES_ARG]),
            ("前向验证", "walk_forward", ["--rules", HUMAN_OVERRIDES_ARG]),
            ("统计检验", "stat_tests", []),
        ]
        ok_all = True
        with st.status("正在执行全流程，请稍候...", expanded=False) as status:
            for label, module_name, cli_args in steps:
                status.update(label=f"正在执行：{label} ...")
                ok, _ = run_module_main(module_name, cli_args, log_label=label)
                clear_cache()
                ok_all = ok_all and ok
            status.update(
                label="全流程完成" if ok_all else "全流程存在失败，详见 logs/dashboard_run.log",
                state="complete" if ok_all else "error",
            )
        if ok_all:
            st.sidebar.success("全流程完成")
        else:
            st.sidebar.error("有任务失败，详见 logs/dashboard_run.log")
    if st.sidebar.button("运行基础分析", use_container_width=True):
        _run_with_log("基础分析", "analysis_engine")
    if st.sidebar.button("运行优化", use_container_width=True):
        _run_with_log("组合优化", "portfolio_optimization", ["--rules", HUMAN_OVERRIDES_ARG])
    if st.sidebar.button("运行前向验证", use_container_width=True):
        _run_with_log("前向验证", "walk_forward", ["--rules", HUMAN_OVERRIDES_ARG])
    if st.sidebar.button("运行统计检验", use_container_width=True):
        _run_with_log("统计检验", "stat_tests")


def main() -> None:
    ensure_project_dirs()
    st.title("美股 50 股投资策略分析 MVP")
    st.caption("量化计算由 Python 完成，人工规则可重算组合，DeepSeek 只用于报告解释。")

    sidebar_actions()
    page = st.sidebar.radio(
        "页面",
        ["数据总览", "市场基准", "单股分析", "组合优化", "相关性", "前向验证", "人工规则", "智能报告"],
    )

    if page == "数据总览":
        page_overview()
    elif page == "市场基准":
        page_market()
    elif page == "单股分析":
        page_single_stock()
    elif page == "组合优化":
        page_portfolio()
    elif page == "相关性":
        page_correlation()
    elif page == "前向验证":
        page_validation()
    elif page == "人工规则":
        page_rules()
    elif page == "智能报告":
        page_report()


if __name__ == "__main__":
    main()
