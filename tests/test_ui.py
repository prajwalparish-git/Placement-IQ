"""Headless UI smoke tests (Streamlit AppTest) in MOCK_MODE: every page renders and its
primary action works end to end."""

import pytest
from streamlit.testing.v1 import AppTest

from piq import db
from piq.config import INTERVIEW_MAX_TURNS
from scripts import seed


def _app(student_id: str | None = None, page: str | None = None) -> AppTest:
    at = AppTest.from_file("../app.py", default_timeout=60)
    if student_id:
        at.session_state["student_id"] = student_id
    if page:
        at.switch_page(page)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _button(at: AppTest, label: str):
    return next(b for b in at.button if b.label == label)


def _md(at: AppTest) -> str:
    return "\n".join(m.value for m in at.markdown)


@pytest.fixture
def seeded() -> str:
    seed.main()
    return next(s["id"] for s in db.list_students() if s["usn"] == seed.USN)


class _Recorder:
    """A sqlite3 connection that records every statement it runs, with its parameters."""

    def __init__(self, conn, seen: list):
        self._conn, self._seen = conn, seen

    def execute(self, sql: str, params=()):
        self._seen.append((" ".join(sql.split()), tuple(params)))
        return self._conn.execute(sql, params)

    def __getattr__(self, name: str):
        return getattr(self._conn, name)


PAGES = [
    "views/onboard.py",
    "views/plan.py",
    "views/quiz.py",
    "views/interview.py",
    "views/dashboard.py",
    "views/results.py",
]


@pytest.mark.parametrize("page", PAGES)
def test_a_page_render_never_repeats_a_query(seeded, monkeypatch, page):
    from collections import Counter
    from contextlib import contextmanager

    real, seen = db.tx, []

    @contextmanager
    def recording_tx():
        with real() as conn:
            yield _Recorder(conn, seen)

    monkeypatch.setattr(db, "tx", recording_tx)
    _app(seeded, page)
    assert seen
    assert [q for q, n in Counter(seen).items() if n > 1] == []


def test_onboard_prefills_the_selected_students_usn(seeded):
    at = _app(seeded, "views/onboard.py")
    assert at.text_input[0].value == seed.USN


def test_onboard_with_sample_resume():
    at = _app()
    at.text_input[0].input("ui0001")
    next(s for s in at.selectbox if s.label.startswith("…or use")).select(
        "java_backend_fresher.txt"
    )
    _button(at, "Analyse resume").click().run()
    assert not at.exception
    assert at.session_state["student_id"]
    assert "Readiness:" in _md(at)
    assert [s["usn"] for s in db.list_students()] == ["UI0001"]


def test_onboard_rejects_missing_usn():
    at = _app()
    _button(at, "Analyse resume").click().run()
    assert any("USN is required" in e.value for e in at.error)


def test_pages_require_a_student():
    for page in ("views/plan.py", "views/quiz.py", "views/interview.py", "views/dashboard.py"):
        at = _app(page=page)
        assert any("Select a student" in i.value for i in at.info)


def test_plan_generates_next_week_and_compares(seeded):
    at = _app(seeded, "views/plan.py")
    _button(at, "Generate week 5 plan").click().run()
    assert not at.exception
    assert [p.week_no for p in db.list_plans(seeded)] == [1, 2, 3, 4, 5]
    assert at.get("arrow_vega_lite_chart") or at.get("vega_lite_chart")


def test_quiz_generate_answer_and_review(seeded):
    at = _app(seeded, "views/quiz.py")
    _button(at, "Generate quiz").click().run()
    assert not at.exception and at.session_state["quiz"]
    assert "critic rejected quiz" in _md(at)  # the loop is visible to the user
    assert db.recent_rejections()[0]["agent_name"] == "quiz"
    for r in at.radio:
        r.set_value(0)
    _button(at, "Submit").click().run()
    assert not at.exception
    assert "next suggested difficulty" in _md(at)
    assert len(db.quiz_history(seeded)) == 25


def test_quiz_text_and_options_are_shown_literally(seeded, monkeypatch):
    from piq import services
    from tests import factories as f

    options = ("__init__", "![x](http://example.com/a.png)", "<script>alert(1)</script>", "d")
    quiz = f.quiz(n=1).model_copy(
        update={"questions": [f.question(text="What does *p hold?", options=options)]}
    )
    monkeypatch.setattr(services, "start_quiz", lambda *args, **kwargs: quiz)
    at = _app(seeded, "views/quiz.py")
    _button(at, "Generate quiz").click().run()
    assert at.radio[0].label == r"**Q1.** What does \*p hold?"
    assert at.radio[0].options[:3] == [
        r"\_\_init\_\_",
        r"\!\[x\]\(http://example\.com/a\.png\)",
        r"\<script\>alert\(1\)\</script\>",
    ]


def test_interview_answer_is_shown_literally(seeded):
    at = _app(seeded, "views/interview.py")
    _button(at, "Start session").click().run()
    at.chat_input[0].set_value("I called __init__ on *p.").run()
    assert not at.exception
    assert r"I called \_\_init\_\_ on \*p\." in _md(at)


def test_interview_session_runs_to_completion(seeded):
    at = _app(seeded, "views/interview.py")
    _button(at, "Start session").click().run()
    assert not at.exception
    at.chat_input[0].set_value("I like coding.").run()  # vague -> mock probes it
    assert "You said 'I like coding" in _md(at)
    for _ in range(INTERVIEW_MAX_TURNS - 1):
        at.chat_input[0].set_value("Situation task action result " * 8).run()
        assert not at.exception
    assert any("Session complete" in s.value for s in at.success)


def test_dashboard_renders(seeded):
    at = _app(seeded, "views/dashboard.py")
    assert at.metric[1].value == "24"  # seeded quizzes


def test_onboard_requires_a_resume_or_sample():
    at = _app()
    at.text_input[0].input("UI0002")
    _button(at, "Analyse resume").click().run()
    assert any("Upload a resume or pick a sample" in e.value for e in at.error)
    assert db.list_students() == []


def test_onboarding_another_student_drops_the_previous_students_session(seeded):
    at = _app(seeded, "views/interview.py")
    _button(at, "Start session").click().run()
    at.chat_input[0].set_value("I like coding.").run()
    assert at.session_state["interview"].history

    at.switch_page("views/onboard.py").run()
    at.text_input[0].input("UI0003")
    next(s for s in at.selectbox if s.label.startswith("…or use")).select(
        "java_backend_fresher.txt"
    )
    _button(at, "Analyse resume").click().run()
    assert not at.exception
    assert at.session_state["student_id"] != seeded
    assert "interview" not in at.session_state
    assert any(s.label.startswith("Profile agent — last run") for s in at.status)

    at.switch_page("views/interview.py").run()
    assert not at.exception
    assert "I like coding." not in _md(at)  # no other student's transcript
    assert [b for b in at.button if b.label == "Start session"]


def test_failed_follow_up_offers_retry_without_reanswering(seeded, monkeypatch):
    from piq import agents, llm

    real, calls = agents.next_question, []

    def fails_second_time(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise llm.LLMError("Groq API error: temporarily unavailable")
        return real(*args, **kwargs)

    monkeypatch.setattr(agents, "next_question", fails_second_time)
    at = _app(seeded, "views/interview.py")
    _button(at, "Start session").click().run()
    turns_before = len(db.past_turns(seeded))
    at.chat_input[0].set_value("A complete answer with a concrete example " * 3).run()
    assert not at.exception
    retry = _button(at, "Retry next question")  # answer saved, follow-up failed
    assert any("last run failed" in s.label for s in at.status)
    assert len(db.past_turns(seeded)) == turns_before + 1
    retry.click().run()
    assert not at.exception and not [b for b in at.button if b.label == "Retry next question"]
    assert at.session_state["interview"].current is not None
    assert len(db.past_turns(seeded)) == turns_before + 1  # not saved twice


def test_failed_quiz_generation_stays_visible(seeded, monkeypatch):
    from piq import graph, services

    def rejected(*args, **kwargs):
        raise graph.CriticRejected("quiz", ["question 0: two answers correct"])

    monkeypatch.setattr(services, "start_quiz", rejected)
    at = _app(seeded, "views/quiz.py")
    _button(at, "Generate quiz").click().run()
    assert any("two answers correct" in e.value for e in at.error)
    at.run()  # any rerun keeps the failure visible
    assert any(s.label == "Quiz agent — last run failed" for s in at.status)
    assert "quiz" not in at.session_state


def test_results_page_without_and_with_results(tmp_path, monkeypatch):
    import json

    from piq import services
    from tests import factories as f

    monkeypatch.setattr(services, "RESULTS_DIR", tmp_path)
    at = _app(page="views/results.py")
    assert any("No results yet" in i.value for i in at.info)

    (tmp_path / "summary.json").write_text(json.dumps(f.eval_summary(mode="mock")))
    at = _app(page="views/results.py")
    assert any("MOCK_MODE" in w.value for w in at.warning)
    assert len(at.dataframe) == 2  # metrics table + agent cost


def test_seed_demo_fills_an_empty_database_on_start(monkeypatch):
    import streamlit as st

    from piq.config import settings
    from scripts import seed

    monkeypatch.setenv("SEED_DEMO", "true")
    settings.cache_clear()
    st.cache_resource.clear()  # _startup runs once per process
    try:
        _app()
        assert [s["usn"] for s in db.list_students()] == [seed.USN]
    finally:
        st.cache_resource.clear()
