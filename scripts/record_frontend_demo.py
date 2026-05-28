from __future__ import annotations

import argparse
import io
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright


ROOT_DIR = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT_DIR / "frontend" / "public" / "demo"
DEFAULT_OUTPUT = DEMO_DIR / "trading-workflow.gif"
EDGE_EXECUTABLE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


class GifRecorder:
    def __init__(self, page: Page, output_path: Path, frame_duration_ms: int = 100) -> None:
        self.page = page
        self.output_path = output_path
        self.frame_duration_ms = frame_duration_ms
        self.frames: list[Image.Image] = []

    def capture(self) -> None:
        png_bytes = self.page.screenshot(type="png", full_page=False)
        frame = Image.open(io.BytesIO(png_bytes)).convert("P", palette=Image.Palette.ADAPTIVE, colors=128)
        self.frames.append(frame)

    def hold(self, milliseconds: int) -> None:
        frame_count = max(1, round(milliseconds / self.frame_duration_ms))
        for _ in range(frame_count):
            self.capture()
            self.page.wait_for_timeout(self.frame_duration_ms)

    def save(self) -> None:
        if not self.frames:
            raise RuntimeError("No frames captured.")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        first, *rest = self.frames
        first.save(
            self.output_path,
            save_all=True,
            append_images=rest,
            duration=self.frame_duration_ms,
            loop=0,
            optimize=True,
            disposal=2,
        )


def wait_for_page(page: Page, recorder: GifRecorder) -> None:
    page.wait_for_load_state("domcontentloaded")
    recorder.hold(720)


def install_recording_overlays(page: Page) -> None:
    page.add_style_tag(
        content="""
        [data-recording-caption] {
          position: fixed;
          left: 244px;
          bottom: 22px;
          z-index: 9999;
          padding: 10px 14px;
          border-radius: 8px;
          color: #0f172a;
          background: rgba(255, 255, 255, 0.94);
          border: 1px solid rgba(203, 213, 225, 0.95);
          box-shadow: 0 14px 34px rgba(15, 23, 42, 0.16);
          font-family: Inter, Arial, sans-serif;
          font-size: 13px;
          font-weight: 800;
          pointer-events: none;
        }

        [data-recording-cursor] {
          position: fixed;
          left: 0;
          top: 0;
          z-index: 10000;
          width: 22px;
          height: 30px;
          transform: translate(-2px, -1px);
          background-image: url("data:image/svg+xml,%3Csvg width='24' height='32' viewBox='0 0 24 32' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M3 2L3 25L9.4 18.7L13.7 29L18.1 27.1L13.9 17.1H22L3 2Z' fill='white' stroke='%23111827' stroke-width='1.5' stroke-linejoin='round'/%3E%3C/svg%3E");
          background-repeat: no-repeat;
          background-size: contain;
          pointer-events: none;
          filter: drop-shadow(0 2px 3px rgba(15, 23, 42, 0.35));
        }

        [data-recording-click-ring] {
          position: fixed;
          z-index: 9999;
          width: 18px;
          height: 18px;
          margin-left: -9px;
          margin-top: -9px;
          border-radius: 999px;
          border: 2px solid rgba(37, 99, 235, 0.9);
          background: rgba(37, 99, 235, 0.2);
          box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1);
          pointer-events: none;
          animation: recordingClickRipple 680ms ease-out forwards;
        }

        @keyframes recordingClickRipple {
          from {
            opacity: 0.85;
            transform: scale(0.45);
          }
          70% {
            opacity: 0.42;
          }
          to {
            opacity: 0;
            transform: scale(6);
          }
        }
        """
    )
    page.evaluate(
        """
        () => {
          if (!document.querySelector('[data-recording-cursor]')) {
            const cursor = document.createElement('div');
            cursor.setAttribute('data-recording-cursor', 'true');
            document.body.appendChild(cursor);
          }
        }
        """
    )


def set_caption(page: Page, text: str) -> None:
    page.evaluate(
        """
        (text) => {
          let caption = document.querySelector('[data-recording-caption]');
          if (!caption) {
            caption = document.createElement('div');
            caption.setAttribute('data-recording-caption', 'true');
            document.body.appendChild(caption);
          }
          caption.textContent = text;
        }
        """,
        text,
    )


def ease_in_out(progress: float) -> float:
    return progress * progress * (3 - 2 * progress)


def get_cursor_position(page: Page) -> tuple[float, float]:
    x, y = page.evaluate(
        """
        () => {
          const cursor = document.querySelector('[data-recording-cursor]');
          if (!cursor) return [96, 96];
          const x = Number.parseFloat(cursor.style.left);
          const y = Number.parseFloat(cursor.style.top);
          return [Number.isFinite(x) ? x : 96, Number.isFinite(y) ? y : 96];
        }
        """
    )
    return float(x), float(y)


def set_cursor_position(page: Page, x: float, y: float) -> None:
    page.mouse.move(x, y)
    page.evaluate(
        """
        ([x, y]) => {
          const cursor = document.querySelector('[data-recording-cursor]');
          if (cursor) {
            cursor.style.left = `${x}px`;
            cursor.style.top = `${y}px`;
          }
        }
        """,
        [x, y],
    )


def move_cursor_to_point(page: Page, recorder: GifRecorder, x: float, y: float, duration_ms: int = 900) -> None:
    start_x, start_y = get_cursor_position(page)
    frame_count = max(3, round(duration_ms / recorder.frame_duration_ms))
    for frame_index in range(1, frame_count + 1):
        progress = ease_in_out(frame_index / frame_count)
        current_x = start_x + (x - start_x) * progress
        current_y = start_y + (y - start_y) * progress
        set_cursor_position(page, current_x, current_y)
        recorder.capture()
        page.wait_for_timeout(recorder.frame_duration_ms)


def locator_point(locator: Locator, x_ratio: float = 0.5, y_ratio: float = 0.5) -> tuple[float, float] | None:
    locator.scroll_into_view_if_needed()
    locator.wait_for(state="visible", timeout=20_000)
    box = locator.bounding_box()
    if box is None:
        return None
    x = box["x"] + box["width"] * x_ratio
    y = box["y"] + box["height"] * y_ratio
    return x, y


def move_cursor_to_locator(
    locator: Locator,
    recorder: GifRecorder,
    x_ratio: float = 0.5,
    y_ratio: float = 0.5,
    duration_ms: int = 900,
) -> None:
    point = locator_point(locator, x_ratio, y_ratio)
    if point is None:
        return
    move_cursor_to_point(locator.page, recorder, point[0], point[1], duration_ms)


def hover_locator(
    locator: Locator,
    recorder: GifRecorder,
    x_ratio: float = 0.5,
    y_ratio: float = 0.5,
    hold_ms: int = 1_260,
) -> None:
    move_cursor_to_locator(locator, recorder, x_ratio, y_ratio)
    recorder.hold(hold_ms)


def show_click_ring(page: Page, x: float, y: float) -> None:
    page.evaluate(
        """
        ([x, y]) => {
          const ring = document.createElement('div');
          ring.setAttribute('data-recording-click-ring', 'true');
          ring.style.left = `${x}px`;
          ring.style.top = `${y}px`;
          document.body.appendChild(ring);
          setTimeout(() => ring.remove(), 720);
        }
        """,
        [x, y],
    )


def click_locator(locator: Locator, recorder: GifRecorder) -> None:
    move_cursor_to_locator(locator, recorder)
    point = locator_point(locator)
    if point is not None:
        show_click_ring(locator.page, point[0], point[1])
    locator.click(timeout=20_000)
    recorder.hold(540)


def scroll_locator(locator: Locator, recorder: GifRecorder, top: int, duration_ms: int = 1_080) -> None:
    start_top = locator.evaluate("(el) => el.scrollTop")
    frame_count = max(2, round(duration_ms / recorder.frame_duration_ms))
    for frame_index in range(1, frame_count + 1):
        progress = ease_in_out(frame_index / frame_count)
        current_top = round(start_top + (top - start_top) * progress)
        locator.evaluate("(el, top) => { el.scrollTop = top }", current_top)
        recorder.capture()
        locator.page.wait_for_timeout(recorder.frame_duration_ms)


def scroll_main(page: Page, recorder: GifRecorder, top: int, duration_ms: int = 1_080) -> None:
    scroll_locator(page.locator("#app > div > div > main"), recorder, top, duration_ms)


def wait_for_optional_selector(page: Page, selector: str, timeout_ms: int = 10_000) -> None:
    try:
        page.wait_for_selector(selector, timeout=timeout_ms)
    except PlaywrightTimeoutError:
        return


def wait_for_report_content(page: Page, timeout_ms: int = 90_000) -> None:
    try:
        page.wait_for_function(
            """
            () => {
              const report = document.querySelector('[data-testid="report-content"]');
              return (report?.innerText || '').trim().length > 180;
            }
            """,
            timeout=timeout_ms,
        )
    except PlaywrightTimeoutError:
        return


def record_workflow(page: Page, recorder: GifRecorder, base_url: str, generate_report: bool) -> None:
    page.goto(f"{base_url}/?recording=1", wait_until="domcontentloaded")
    install_recording_overlays(page)
    set_cursor_position(page, 92, 88)
    wait_for_page(page, recorder)

    set_caption(page, "研究池热力图：查看股票池表现和权重分布")
    scroll_main(page, recorder, 0)
    wait_for_optional_selector(page, "[data-testid='research-heatmap'] canvas")
    heatmap = page.get_by_test_id("research-heatmap")
    hover_locator(heatmap, recorder, 0.42, 0.52, 1_440)
    hover_locator(heatmap, recorder, 0.68, 0.64, 1_440)

    set_caption(page, "时间瀑布图：查看全流程各步骤耗时")
    scroll_main(page, recorder, 410)
    wait_for_optional_selector(page, "[data-testid='pipeline-waterfall'] canvas")
    waterfall = page.get_by_test_id("pipeline-waterfall")
    hover_locator(waterfall, recorder, 0.72, 0.58, 1_440)
    hover_locator(waterfall, recorder, 0.54, 0.76, 1_260)

    set_caption(page, "单股分析：从多只股票中选择一只分析")
    click_locator(page.get_by_test_id("nav-singleStock"), recorder)
    wait_for_page(page, recorder)
    scroll_main(page, recorder, 0, 720)
    page.wait_for_function(
        "() => document.querySelector('[data-testid=\"stock-selector\"]')?.options.length > 2",
        timeout=20_000,
    )
    selector = page.get_by_test_id("stock-selector")
    click_locator(selector, recorder)
    selector.select_option(index=1)
    recorder.hold(720)
    selector.select_option(index=2)
    recorder.hold(900)
    hover_locator(page.get_by_test_id("single-stock-chart"), recorder, 0.62, 0.48, 1_260)
    scroll_main(page, recorder, 360, 1_440)
    hover_locator(page.get_by_test_id("single-stock-metrics-table"), recorder, 0.62, 0.46, 1_440)

    set_caption(page, "一键全流程：触发分析、优化、验证、检验")
    run_button = page.get_by_test_id("run-full-pipeline")
    run_button.scroll_into_view_if_needed()
    if run_button.is_enabled(timeout=5_000):
        click_locator(run_button, recorder)
    else:
        move_cursor_to_locator(run_button, recorder)
    recorder.hold(1_800)

    set_caption(page, "人工规则：写入研究判断和权重约束")
    click_locator(page.get_by_test_id("nav-rules"), recorder)
    wait_for_page(page, recorder)
    natural_language = page.get_by_test_id("rule-natural-language")
    click_locator(natural_language, recorder)
    natural_language.fill("NVDA 未来 6 个月监管不确定性升高，最大权重限制到 5%，降低组合集中度。")
    recorder.hold(720)
    csv_editor = page.get_by_test_id("rules-csv-editor")
    click_locator(csv_editor, recorder)
    csv_editor.fill(
        "ticker,start_date,end_date,action,min_weight,max_weight,return_multiplier,risk_multiplier,reason\n"
        "NVDA,2026-05-28,2026-11-28,cap,,0.05,,1.20,监管不确定性升高，降低集中度\n"
        "MSFT,2026-05-28,,floor,0.04,,,0.95,现金流质量稳定，保留底仓"
    )
    recorder.hold(900)
    move_cursor_to_locator(page.get_by_test_id("save-rules"), recorder)
    recorder.hold(720)

    set_caption(page, "LangChain / DeepSeek：生成或查看投研报告")
    click_locator(page.get_by_test_id("nav-report"), recorder)
    wait_for_page(page, recorder)
    click_locator(page.get_by_test_id("report-focus-risk_control"), recorder)
    report_notes = page.get_by_test_id("report-notes")
    click_locator(report_notes, recorder)
    report_notes.fill("重点解释人工规则对 NVDA、MSFT 权重和回撤风险的影响。")
    recorder.hold(720)
    if generate_report:
        set_caption(page, "LangChain / DeepSeek：风险控制侧重，流式生成报告")
        click_locator(page.get_by_test_id("generate-report"), recorder)
        wait_for_report_content(page)
        recorder.hold(1_800)
    else:
        move_cursor_to_locator(page.get_by_test_id("generate-report"), recorder)
        recorder.hold(900)
    set_caption(page, "生成报告：慢速查看结论、规则影响和风险解释")
    report_content = page.get_by_test_id("report-content")
    move_cursor_to_locator(report_content, recorder, 0.58, 0.52)
    scroll_locator(report_content, recorder, 260, 1_800)
    recorder.hold(1_080)
    scroll_locator(report_content, recorder, 620, 2_160)
    recorder.hold(1_440)


def main() -> None:
    parser = argparse.ArgumentParser(description="Record the real frontend workflow demo as a GIF.")
    parser.add_argument("--url", default="http://localhost:18080", help="Frontend base URL.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output GIF path.")
    parser.add_argument("--generate-report", action="store_true", help="Compatibility flag; report generation is enabled by default.")
    parser.add_argument("--skip-generate-report", action="store_true", help="Do not click report generation.")
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        launch_kwargs = {"headless": True}
        if EDGE_EXECUTABLE.exists():
            launch_kwargs["executable_path"] = str(EDGE_EXECUTABLE)
        browser = playwright.chromium.launch(**launch_kwargs)
        page = browser.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
        recorder = GifRecorder(page, output_path)
        record_workflow(page, recorder, args.url.rstrip("/"), not args.skip_generate_report)
        recorder.save()
        browser.close()

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"{output_path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    started_at = time.perf_counter()
    main()
    print(f"done in {time.perf_counter() - started_at:.1f}s")
