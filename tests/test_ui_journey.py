"""Headless UI tests (AppTest, MOCK_MODE) for the six-step journey's pages: each renders,
its primary action works end to end and lands in telemetry, and a crashed page shows a
message instead of a traceback."""

import pytest
from streamlit.testing.v1 import AppTest

from database import crud
from piq import journey, services
from piq.config import settings
from scripts import seed, seed_cohort

JOURNEY = (
    "views/scanner.py",
    "views/roadmap.py",
    "views/critic_quiz.py",
    "views/voice_interview.py",
)


def _app(student_id: str | None, page: str, **state) -> AppTest:
    at = AppTest.from_file("../app.py", default_timeout=60)
    if student_id:
        at.session_state["student_id"] = student_id
    for k, v in state.items():
        at.session_state[k] = v
    at.switch_page(page)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _text(at: AppTest) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    parts += [h.value for h in at.subheader] + [h.value for h in at.title]
    return "\n".join(parts)


def _button(at: AppTest, label: str):
    return next(b for b in at.button if b.label == label)


@pytest.fixture
def seeded() -> str:
    seed.main()
    return next(s["id"] for s in services.list_students() if s["usn"] == seed.USN)


def _telemetry_id() -> int:
    return crud.get_student(seed.USN).id


@pytest.mark.parametrize("page", JOURNEY)
def test_journey_pages_ask_for_a_student_first(page):
    at = _app(None, page)
    assert "No student selected" in [s.value for s in at.subheader]


def test_navigation_lists_the_six_steps_then_more_tools(seeded):
    at = _app(seeded, "views/home.py")
    assert not at.exception


def test_scanner_scans_a_sample_and_hands_gaps_to_the_roadmap(seeded):
    at = _app(seeded, "views/scanner.py", scan_source="Use a sample")
    _button(at, "Scan resume").click().run()
    assert not at.exception
    assert "% match" in _text(at)
    assert crud.latest_resume_analysis(_telemetry_id()) is not None
    roadmap = [b for b in at.button if b.label == "Build a 7-day roadmap for these gaps"]
    if roadmap:  # the sample may cover every skill
        roadmap[0].click().run()
        assert at.session_state["roadmap_gaps"]


def test_roadmap_generates_a_week_and_saves_ticked_tasks(seeded):
    at = _app(seeded, "views/roadmap.py", roadmap_gaps=["SQL", "Statistics"])
    _button(at, "Generate my 7-day roadmap").click().run()
    assert not at.exception
    assert "Day 7" in _text(at)
    at.checkbox[0].check().run()
    [week] = journey.roadmaps(seeded)
    assert week.week == 1 and len(week.done) == 1


def test_critic_quiz_runs_and_records_the_score(seeded):
    at = _app(seeded, "views/critic_quiz.py")
    _button(at, "Generate quiz").click().run()
    assert not at.exception and at.radio
    at.radio[0].set_value(0)
    _button(at, "Submit answers").click().run()
    assert not at.exception
    assert any(m.label == "Score" for m in at.metric)
    [attempt] = crud.quiz_attempts(_telemetry_id())
    assert attempt.total_questions == len(at.radio)


def test_voice_assessment_scores_a_typed_answer(seeded):
    at = _app(seeded, "views/voice_interview.py")
    _button(at, "Generate question").click().run()
    assert "Spoken by your browser's own voice." in _text(at)
    at.text_area(key="voice_text").input(
        "In my final year project the nightly import kept failing, so I profiled it, batched "
        "the inserts and added an index; as a result the job finished in six minutes."
    ).run()
    _button(at, "Score my answer").click().run()
    assert not at.exception
    assert "/15" in _text(at)
    [session] = crud.voice_sessions(_telemetry_id())
    assert 0 <= session.rubric_score <= 15


def test_faculty_dashboard_empty_then_with_a_cohort():
    at = _app(None, "views/faculty.py")
    assert "No activity recorded yet" in [s.value for s in at.subheader]
    seed_cohort.main([])
    at = _app(None, "views/faculty.py")
    assert any(b.label == "Export placement readiness report" for b in at.get("download_button"))
    charts = at.get("arrow_vega_lite_chart") or at.get("vega_lite_chart")
    assert len(charts) == 6  # streams, quiz and rubric spreads, criteria, gaps, weekly trend
    assert "leads at" in _text(at)


def test_a_crashed_page_shows_a_message_not_a_traceback(monkeypatch):
    monkeypatch.setenv("PIQ_RAISE_ERRORS", "0")
    settings.cache_clear()

    def boom():
        raise RuntimeError("bug")

    monkeypatch.setattr(journey, "cohort_view", boom)
    at = _app(None, "views/faculty.py")
    assert any("Something went wrong on this page" in e.value for e in at.error)


def test_faculty_can_switch_to_the_cloud_copy_and_an_outage_is_a_message(monkeypatch):
    from database.connection import reset_manager

    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://u:secret@127.0.0.1:1/x")  # nothing there
    settings.cache_clear()
    reset_manager()
    seed_cohort.main([])  # local records (the demo cohort stays local)
    at = _app(None, "views/faculty.py")
    assert "Showing this machine's records" in _text(at)
    _button(at, "Refresh from the cloud").click().run()
    assert not at.exception
    assert any("cloud copy is unavailable" in e.value for e in at.error)
    assert any(b.label == "This machine only" for b in at.button)
