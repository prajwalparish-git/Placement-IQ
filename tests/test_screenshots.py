"""Pure helpers of the screenshot tool; tests never launch a browser."""

import ast
import random
from pathlib import Path

import pytest

from piq.config import ROOT
from scripts import screenshots as ss


def _app_navigation() -> set[tuple[str, str]]:
    """(path, title) of every st.Page in app.py."""
    pages = set()
    for node in ast.walk(ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "Page":
            title = next(k.value.value for k in node.keywords if k.arg == "title")
            pages.add((node.args[0].value, title))
    return pages


def test_page_list_matches_the_app_navigation():
    assert {(p.path, p.title) for p in ss.PAGES} == _app_navigation()


def test_every_capture_is_checked_by_a_marker():
    planned = {(p.slug, s) for p in ss.PAGES for s in ss.STATES} | set(ss.FLOWS)
    assert set(ss.MARKERS) == planned
    assert all(text.strip() for text in ss.MARKERS.values())


def test_interview_answers_are_detailed_and_distinct():
    from piq.config import INTERVIEW_MAX_TURNS

    answers = ss.INTERVIEW_ANSWERS
    assert len(set(answers)) == len(answers) >= INTERVIEW_MAX_TURNS - 1
    assert all(len(a.split()) >= 25 for a in answers)  # the mock probes shorter answers


def test_shot_names_follow_the_convention():
    assert ss.shot_name("quiz", "review", 390, "dark") == "quiz-review-390-dark.png"


def test_planned_shots_cover_pages_states_flows_widths_and_schemes():
    names = ss.planned_shots([1440, 390], ["light", "dark"])
    per_scheme_width = len(ss.STATES) * len(ss.PAGES) + len(ss.FLOWS)
    assert len(names) == len(set(names)) == 2 * 2 * per_scheme_width
    assert "results-nostudent-390-dark.png" in names
    assert "interview-complete-1440-light.png" in names


@pytest.mark.parametrize("raw", ["", "1440,800", "1024"])
def test_unknown_widths_are_rejected(raw):
    with pytest.raises(ValueError):
        ss.parse_widths(raw)


def test_widths_and_schemes_parse():
    assert ss.parse_widths("1440, 390") == [1440, 390]
    assert ss.parse_schemes("dark") == ["dark"]
    with pytest.raises(ValueError):
        ss.parse_schemes("sepia")


def test_isolated_env_never_reaches_groq_or_the_real_env(tmp_path):
    base = {
        "GROQ_API_KEY": "secret",
        "GROQ_MODEL_LARGE": "model",
        "STREAMLIT_THEME_BASE": "dark",
        "MOCK_MODE": "false",
        "PATH": "kept",
    }
    env = ss.isolated_env(tmp_path, base)
    assert not [k for k in env if k.startswith(("GROQ_", "STREAMLIT_"))]
    assert (env["MOCK_MODE"], env["SEED_DEMO"], env["PATH"]) == ("true", "true", "kept")
    assert Path(env["DB_PATH"]).parent == tmp_path
    assert not Path(env["PIQ_DOTENV"]).exists()
    assert base["GROQ_API_KEY"] == "secret"  # the caller's mapping is not modified


def test_compress_png_shrinks_and_keeps_the_size(tmp_path):
    from PIL import Image

    rng = random.Random(1)
    img = Image.new("RGB", (300, 300))
    img.putdata(
        [(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(90_000)]
    )
    path = tmp_path / "noise.png"
    img.save(path)
    before = path.stat().st_size
    assert ss.compress_png(path, max_bytes=50_000) < before
    with Image.open(path) as out:
        assert out.size == (300, 300)
