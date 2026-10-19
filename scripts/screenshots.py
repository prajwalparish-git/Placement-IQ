"""Capture every page and key flow for visual review (dev tool; Playwright + Chromium).

    python -m scripts.screenshots docs/design/before
    python -m scripts.screenshots docs/design/after --widths 1440,390 --schemes light

For each colour scheme it starts the app on a fresh, isolated database (MOCK_MODE and
SEED_DEMO on, the developer's .env ignored, Groq never contacted) and captures:
  * every page with no student selected and with the demo student selected
  * key in-flow states: a new plan week, the critic loop, quiz taking and review,
    an interview mid-session and complete
at each viewport width, as <page>-<state>-<width>-<scheme>.png, compressed to about
250 KB or less. Browser console errors are printed and make the run exit with status 1.

Never imported by the app; the test suite exercises only the pure helpers.
"""

import argparse
import contextlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = 8599
VIEWPORTS = {1440: 900, 1366: 768, 390: 844}  # width -> height
SCHEMES = ("light", "dark")
MAX_BYTES = 250_000
MAX_SHOT_HEIGHT = 9000  # px; longer pages are cut here
DEMO_OPTION = "DEMO0001 — Demo Student"  # sidebar option text, see piq.ui.student_selector


@dataclass(frozen=True)
class AppPage:
    slug: str
    title: str  # navigation label, as passed to st.Page in app.py
    path: str  # page file, as passed to st.Page / AppTest.switch_page


PAGES = (
    AppPage("onboard", "Onboard", "views/onboard.py"),
    AppPage("plan", "Weekly plan", "views/plan.py"),
    AppPage("quiz", "Quiz", "views/quiz.py"),
    AppPage("interview", "Mock interview", "views/interview.py"),
    AppPage("dashboard", "Dashboard", "views/dashboard.py"),
    AppPage("results", "Results", "views/results.py"),
)
STATES = ("nostudent", "demo")
FLOWS = (
    ("plan", "newweek"),
    ("quiz", "critic"),
    ("quiz", "taking"),
    ("quiz", "review"),
    ("interview", "mid"),
    ("interview", "complete"),
)


# --- pure helpers (unit-tested) ------------------------------------------------


def shot_name(page: str, state: str, width: int, scheme: str) -> str:
    return f"{page}-{state}-{width}-{scheme}.png"


def parse_widths(raw: str) -> list[int]:
    widths = [int(w) for w in raw.split(",") if w.strip()]
    unknown = [w for w in widths if w not in VIEWPORTS]
    if unknown or not widths:
        raise ValueError(f"widths must be from {sorted(VIEWPORTS)}, got {raw!r}")
    return widths


def parse_schemes(raw: str) -> list[str]:
    schemes = [s.strip() for s in raw.split(",") if s.strip()]
    if not schemes or any(s not in SCHEMES for s in schemes):
        raise ValueError(f"schemes must be from {SCHEMES}, got {raw!r}")
    return schemes


def planned_shots(widths: list[int], schemes: list[str]) -> list[str]:
    """Every file one run writes, in capture order."""
    names = []
    for scheme in schemes:
        names += [
            shot_name(p.slug, state, w, scheme) for state in STATES for p in PAGES for w in widths
        ]
        names += [shot_name(page, state, w, scheme) for page, state in FLOWS for w in widths]
    return names


def isolated_env(tmp: Path, base: dict[str, str] | None = None) -> dict[str, str]:
    """Environment for the app server: mock LLM, throwaway database, no .env, no Groq keys."""
    env = {k: v for k, v in (base if base is not None else os.environ).items()}
    for key in [k for k in env if k.startswith(("GROQ_", "STREAMLIT_"))]:
        del env[key]
    env.update(
        PIQ_DOTENV=str(tmp / "no-such.env"),
        MOCK_MODE="true",
        SEED_DEMO="true",
        DB_PATH=str(tmp / "screenshots.db"),
        PYTHONIOENCODING="utf-8",
    )
    return env


def compress_png(path: Path, max_bytes: int = MAX_BYTES) -> int:
    """Rewrite `path` smaller: lossless first, then fewer palette colours until it fits."""
    from PIL import Image

    with Image.open(path) as img:
        rgb = img.convert("RGB")
    rgb.save(path, optimize=True)
    for colours in (256, 128, 64):
        if path.stat().st_size <= max_bytes:
            break
        rgb.quantize(
            colors=colours, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
        ).save(path, optimize=True)
    return path.stat().st_size


# --- server --------------------------------------------------------------------


def _port_in_use(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


@contextlib.contextmanager
def running_app(env: dict[str, str], port: int) -> Iterator[str]:
    if _port_in_use(port):
        raise SystemExit(f"port {port} is busy; stop that server or pass --port")
    cmd = [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true"]
    cmd += ["--server.port", str(port), "--browser.gatherUsageStats", "false"]
    proc = subprocess.Popen(
        cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    url = f"http://localhost:{port}/"
    try:
        for _ in range(120):
            with contextlib.suppress(OSError):
                urllib.request.urlopen(url + "_stcore/health", timeout=2)
                break
            time.sleep(0.5)
        else:
            raise SystemExit("the app did not become healthy within 60 s")
        yield url
    finally:
        proc.terminate()
        proc.communicate(timeout=30)


@contextlib.contextmanager
def results_summary_present() -> Iterator[None]:
    """Render a populated Results page without ever overwriting a real summary.json."""
    from piq.config import RESULTS_DIR

    summary = RESULTS_DIR / "summary.json"
    if summary.exists():
        yield
        return
    from tests.factories import eval_summary

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps(eval_summary(mode="mock")), encoding="utf-8")
    try:
        yield
    finally:
        summary.unlink(missing_ok=True)


# --- browser -------------------------------------------------------------------

_STATE = "document.querySelector('[data-testid=stApp]')?.getAttribute('data-test-script-state')"
# Streamlit scrolls inside its own containers, so measure them, not just the document.
_CONTENT_HEIGHT = (
    "() => Math.max(document.documentElement.scrollHeight, ...[...document.querySelectorAll("
    "'[data-testid=stMain], [data-testid=stAppViewContainer]')].map(e => e.scrollHeight))"
)


def _wait_idle(page, expect_run: bool = True) -> None:
    """Wait until the script has rerun (if expected) and finished, then let charts settle."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    if expect_run:
        with contextlib.suppress(PlaywrightTimeout):
            page.wait_for_function(f"{_STATE} === 'running'", timeout=2500)
    page.wait_for_function(f"{_STATE} === 'notRunning'", timeout=120_000)
    page.evaluate("document.fonts.ready.then(() => true)")
    page.wait_for_timeout(800)


def _open_sidebar(page) -> None:
    expand = page.get_by_test_id("stExpandSidebarButton")
    if expand.is_visible():
        expand.click()
        page.wait_for_timeout(400)


def _select_student(page, option: str) -> None:
    _open_sidebar(page)
    page.get_by_test_id("stSidebar").get_by_role("combobox", name="Student").click()
    page.get_by_role("option", name=option).click()
    _wait_idle(page)


def _goto(page, title: str) -> None:
    _open_sidebar(page)
    page.get_by_test_id("stSidebarNavLink").filter(has_text=title).first.click()
    _wait_idle(page)


def _click(page, label: str, exact: bool = True) -> None:
    page.get_by_role("button", name=label, exact=exact).first.click()
    _wait_idle(page)


def _answer_chat(page, text: str) -> None:
    box = page.get_by_test_id("stChatInputTextArea")
    box.fill(text)
    box.press("Enter")
    _wait_idle(page)


def _capture(page, out: Path, name: str, width: int) -> Path:
    page.set_viewport_size({"width": width, "height": VIEWPORTS[width]})
    page.wait_for_timeout(600)  # relayout; the sidebar collapses by itself at mobile width
    full = page.evaluate(_CONTENT_HEIGHT)
    height = min(max(VIEWPORTS[width], int(full)), MAX_SHOT_HEIGHT)
    page.set_viewport_size({"width": width, "height": height})
    page.wait_for_timeout(400)
    path = out / name
    page.screenshot(path=str(path), full_page=True)
    page.set_viewport_size({"width": width, "height": VIEWPORTS[width]})
    compress_png(path)
    return path


def _capture_widths(page, out, page_slug, state, widths, scheme, written) -> None:
    for w in widths:
        written.append(_capture(page, out, shot_name(page_slug, state, w, scheme), w))
    page.set_viewport_size({"width": 1440, "height": VIEWPORTS[1440]})
    page.wait_for_timeout(300)


def capture_scheme(url: str, out: Path, scheme: str, widths: list[int], errors: list[str]) -> list:
    from playwright.sync_api import sync_playwright

    written: list[Path] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1440, "height": VIEWPORTS[1440]}, color_scheme=scheme
        )
        page = context.new_page()
        where = {"step": "load"}
        page.on(
            "console",
            lambda m: (
                errors.append(f"[{scheme} {where['step']}] console: {m.text}")
                if m.type == "error"
                else None
            ),
        )
        page.on("pageerror", lambda e: errors.append(f"[{scheme} {where['step']}] pageerror: {e}"))
        page.goto(url)
        _wait_idle(page, expect_run=False)

        for state in STATES:
            if state == "demo":
                where["step"] = "select demo student"
                _select_student(page, DEMO_OPTION)
            for p in PAGES:
                where["step"] = f"{p.slug} ({state})"
                _goto(page, p.title)
                _capture_widths(page, out, p.slug, state, widths, scheme, written)

        where["step"] = "plan: generate a new week"
        _goto(page, "Weekly plan")
        _click(page, "Generate week", exact=False)
        _capture_widths(page, out, "plan", "newweek", widths, scheme, written)

        where["step"] = "quiz: generate (critic loop)"
        _goto(page, "Quiz")
        _click(page, "Generate quiz")
        _capture_widths(page, out, "quiz", "critic", widths, scheme, written)
        where["step"] = "quiz: answer"
        for radio in page.get_by_test_id("stRadio").all():
            radio.get_by_role("radio").first.check(force=True)  # inputs are visually hidden
        page.wait_for_timeout(300)
        _capture_widths(page, out, "quiz", "taking", widths, scheme, written)
        where["step"] = "quiz: review"
        _click(page, "Submit")
        _capture_widths(page, out, "quiz", "review", widths, scheme, written)

        where["step"] = "interview: start and answer vaguely"
        _goto(page, "Mock interview")
        _click(page, "Start session")
        _answer_chat(page, "I like coding.")
        _capture_widths(page, out, "interview", "mid", widths, scheme, written)
        where["step"] = "interview: finish"
        for _ in range(10):  # bounded: the chat input disappears once the session completes
            if not page.get_by_test_id("stChatInputTextArea").count():
                break
            _answer_chat(page, "Situation: a team project. Task, action and result: " * 3)
        _capture_widths(page, out, "interview", "complete", widths, scheme, written)
        browser.close()
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path, help="folder for the PNGs, e.g. docs/design/before")
    ap.add_argument("--widths", default="1440,1366,390")
    ap.add_argument("--schemes", default="light,dark")
    ap.add_argument("--port", type=int, default=PORT)
    args = ap.parse_args(argv)
    widths, schemes = parse_widths(args.widths), parse_schemes(args.schemes)
    args.out.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    written: list[Path] = []
    started = time.perf_counter()
    with results_summary_present():
        for scheme in schemes:
            with (
                tempfile.TemporaryDirectory() as tmp,
                running_app(isolated_env(Path(tmp)), args.port) as url,
            ):
                print(f"{scheme}: capturing ...", flush=True)
                written += capture_scheme(url, args.out, scheme, widths, errors)

    sizes = [p.stat().st_size for p in written]
    print(
        f"{len(written)} screenshots in {args.out} in {time.perf_counter() - started:.0f} s; "
        f"largest {max(sizes) // 1024} KB, total {sum(sizes) // 1024} KB"
    )
    over = [p.name for p, s in zip(written, sizes, strict=True) if s > MAX_BYTES]
    if over:
        print(f"over {MAX_BYTES // 1000} KB: {', '.join(over)}")
    for e in errors:
        print(e)
    print(f"browser console errors: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
