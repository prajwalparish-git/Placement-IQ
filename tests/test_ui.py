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


def _captions(at: AppTest) -> str:
    return "\n".join(c.value for c in at.caption)


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


def _components_page() -> None:
    import streamlit as st

    from piq import ui

    st.session_state["clicked"] = ui.page_header("Home", "One plain sentence.", "Do it", key="go")
    ui.empty_state("inbox", "Nothing here yet", "Make the first one.")
    ui.stat_row([ui.Stat("Readiness", "42/100", "+4"), ui.Stat("Quizzes taken", "24")])
    ui.topic_chip("<b>OS</b>")
    ui.status_badge("done", "Onboarded")


def test_design_system_components_render():
    at = AppTest.from_function(_components_page).run()
    assert not at.exception
    assert [t.value for t in at.title] == ["Home"]
    assert [s.value for s in at.subheader] == ["Nothing here yet"]
    assert [(m.label, m.value) for m in at.metric] == [
        ("Readiness", "42/100"),
        ("Quizzes taken", "24"),
    ]
    assert ":gray[One plain sentence.]" in _md(at)
    assert ":green-badge[:material/check_circle: Onboarded]" in _md(at)
    assert "&lt;b&gt;OS&lt;/b&gt;" in at.get("html")[0].proto.body  # chip text is escaped
    assert at.session_state["clicked"] is False
    _button(at, "Do it").click().run()
    assert at.session_state["clicked"] is True


def test_navigation_groups_pages_with_material_icons():
    import ast
    from pathlib import Path

    from streamlit.string_util import validate_material_icon

    tree = ast.parse(Path("app.py").read_text(encoding="utf-8"))
    nav = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "navigation"
    )
    sections = {
        k.value: [ast.literal_eval(p.args[0]) for p in v.elts]
        for k, v in zip(nav.args[0].keys, nav.args[0].values, strict=True)
    }
    assert list(sections) == ["Prepare", "Insights"]
    assert sections["Insights"] == ["views/dashboard.py", "views/results.py"]
    icons = [
        k.value.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "Page"
        for k in n.keywords
        if k.arg == "icon"
    ]
    assert icons and all(validate_material_icon(i) for i in icons)  # unknown names raise


def test_sidebar_shows_readiness_and_a_quiet_mock_badge(seeded):
    at = _app(seeded, "views/plan.py")
    [progress] = at.sidebar.get("progress")
    assert progress.proto.text == "Readiness 42/100"
    assert any("gray-badge[:material/science: Mock mode]" in m.value for m in at.sidebar.markdown)
    assert not at.sidebar.warning  # the loud MOCK_MODE box is gone


def test_onboard_with_sample_resume():
    at = _app(page="views/onboard.py")  # Home is the default page now
    at.text_input[0].input("ui0001")
    next(s for s in at.selectbox if s.label.startswith("…or use")).select(
        "java_backend_fresher.txt"
    )
    _button(at, "Analyse resume").click().run()
    assert not at.exception
    assert at.session_state["student_id"]
    [readiness] = [m for m in at.metric if m.label == "Readiness"]  # was "Readiness:" text
    assert readiness.value.endswith("/100")
    assert any(s.label.startswith("Profile agent — last run") for s in at.status)
    assert [s["usn"] for s in db.list_students()] == ["UI0001"]


def test_onboard_without_a_student_explains_what_happens_next():
    at = _app(page="views/onboard.py")
    assert [t.value for t in at.title] == ["Onboard"]
    assert [s.value for s in at.subheader] == ["New student", "What happens next"]
    assert all(f"**{n}.**" in _md(at) for n in (1, 2, 3))
    assert not at.metric  # no profile yet, so no score


def test_onboard_profile_shows_readiness_skills_and_fixes(seeded):
    at = _app(seeded, "views/onboard.py")
    assert [s.value for s in at.subheader] == ["Demo Student", "From the resume"]
    [readiness] = [m for m in at.metric if m.label == "Readiness"]
    assert readiness.value == "42/100"
    assert at.get("arrow_vega_lite_chart") or at.get("vega_lite_chart")  # the ring
    md = _md(at)
    # Matched and missing skills differ by icon and words, not by colour alone.
    assert ":green-badge[:material/check_circle: Java]" in md
    assert ":gray-badge[:material/radio_button_unchecked: Operating Systems]" in md
    assert "5 of the 12 skills Java Backend Developer needs are on the resume." in _captions(at)
    assert "**Internships**  \n:gray[None listed.]" in md
    assert "**Resume fixes**  \n:gray[:material/check_box_outline_blank:] Add measurable" in md
    assert at.expander[0].label == "Re-profile with a new resume"  # one click away


def test_onboard_reprofile_without_a_resume_shows_the_error(seeded):
    at = _app(seeded, "views/onboard.py")
    _button(at, "Analyse resume").click().run()
    assert any("Upload a resume or pick a sample" in e.value for e in at.error)
    assert [s["usn"] for s in db.list_students()] == [seed.USN]  # nothing saved


def _onboard(at: AppTest, usn: str) -> None:
    at.text_input[0].input(usn)
    next(s for s in at.selectbox if s.label.startswith("…or use")).select(
        "java_backend_fresher.txt"
    )
    _button(at, "Analyse resume").click().run()
    assert not at.exception


def test_onboarding_a_usn_that_is_taken_asks_before_replacing_that_student(seeded):
    before = db.latest_profile(seeded)
    at = _app(page="views/onboard.py")  # no student selected: this is a new student
    _onboard(at, seed.USN.lower())
    [warning] = at.warning
    assert f"{seed.USN} already belongs to Demo Student" in warning.value
    assert db.latest_profile(seeded) == before  # nothing saved yet
    _button(at, "Cancel").click().run()
    assert not at.warning and db.latest_profile(seeded) == before

    _onboard(at, seed.USN)
    _button(at, "Replace their profile").click().run()
    assert not at.exception and not at.warning
    assert db.latest_profile(seeded).name != before.name  # the resume's student now
    assert [s["usn"] for s in db.list_students()] == [seed.USN]
    assert at.session_state["student_id"] == seeded


def test_reprofiling_the_selected_student_closes_their_open_quiz_and_interview(seeded):
    at = _app(seeded, "views/quiz.py")
    _button(at, "Generate quiz").click().run()
    at.switch_page("views/interview.py").run()
    _button(at, "Start session").click().run()
    assert at.session_state["quiz"] and at.session_state["interview"]
    at.switch_page("views/onboard.py").run()
    next(s for s in at.selectbox if s.label.startswith("…or use")).select(
        "java_backend_fresher.txt"
    )
    _button(at, "Analyse resume").click().run()
    assert not at.exception
    assert at.session_state["student_id"] == seeded  # the same student, a new profile
    # Both were built from the old profile, so they close.
    assert "quiz" not in at.session_state and "interview" not in at.session_state
    assert any(s.label.startswith("Profile agent — last run") for s in at.status)


def test_reprofiling_the_selected_student_needs_no_confirmation(seeded):
    at = _app(seeded, "views/onboard.py")
    next(s for s in at.selectbox if s.label.startswith("…or use")).select(
        "java_backend_fresher.txt"
    )
    _button(at, "Analyse resume").click().run()
    assert not at.exception and not at.warning
    assert any(s.label.startswith("Profile agent — last run") for s in at.status)


def test_deleting_a_student_needs_their_usn_then_returns_home(seeded):
    at = _app(seeded, "views/onboard.py")
    _button(at, "Delete this student").click().run()
    assert "with every profile, plan, quiz and interview" in _md(at)
    confirm = next(t for t in at.text_input if t.label == "Type the USN to confirm")
    confirm.input("WRONG001")
    _button(at, "Delete for good").click().run()
    assert any("nothing was deleted" in e.value for e in at.error)
    assert [s["usn"] for s in db.list_students()] == [seed.USN]  # still there

    next(t for t in at.text_input if t.label == "Type the USN to confirm").input(seed.USN.lower())
    _button(at, "Delete for good").click().run()
    assert not at.exception
    assert db.list_students() == []
    assert at.session_state["student_id"] is None
    assert [t.value for t in at.title] == ["Placement prep that adapts to you"]  # Home


def test_onboard_rejects_missing_usn():
    at = _app(page="views/onboard.py")  # Home is the default page now
    _button(at, "Analyse resume").click().run()
    assert any("USN is required" in e.value for e in at.error)


NEEDS_A_STUDENT = ("views/plan.py", "views/quiz.py", "views/interview.py", "views/dashboard.py")


@pytest.mark.parametrize("page", NEEDS_A_STUDENT)
def test_pages_require_a_student(page):
    # Was an st.info("Select a student ..."); now a designed empty state with a way forward.
    at = _app(page=page)
    assert "No student selected" in [s.value for s in at.subheader]
    assert "Nobody has onboarded yet." in _md(at)  # the empty database has no one to pick
    _button(at, "Open Onboard").click().run()
    assert not at.exception
    assert [b for b in at.button if b.label == "Analyse resume"]  # Onboard opened


def test_the_empty_state_points_to_the_sidebar_when_students_exist(seeded):
    at = _app(page="views/plan.py")  # students exist, none selected
    assert "No student selected" in [s.value for s in at.subheader]
    assert "Choose your name under **Student** in the sidebar" in _md(at)


def test_plan_generates_next_week_and_compares(seeded):
    at = _app(seeded, "views/plan.py")
    _button(at, "Generate week 5 plan").click().run()
    assert not at.exception
    assert [p.week_no for p in db.list_plans(seeded)] == [1, 2, 3, 4, 5]
    assert at.get("arrow_vega_lite_chart") or at.get("vega_lite_chart")


def test_plan_shows_the_latest_week_day_by_day_with_why_and_the_shift(seeded):
    at = _app(seeded, "views/plan.py")
    [week] = at.get("button_group")  # the week selector (pills)
    assert week.value == 4 and week.options[0] == "Week 1"
    assert "Week 4" in [s.value for s in at.subheader]
    [why] = at.info
    assert why.value.startswith("**Why this plan.** Seeded plan for week 4")
    [days] = [h for h in at.get("html") if '<ol class="piq-days"' in h.proto.body]
    assert days.proto.body.count('<li class="piq-day">') == 7
    shift = "OS gets 240 more minutes and DBMS 360 fewer than in week 3"
    assert shift in [s.value for s in at.subheader]
    assert "Hollow grey dot: week 3" in _captions(at)
    assert "last three quizzes" in _captions(at)  # where weakness comes from
    assert not at.dataframe  # the table is one toggle away


def test_plan_week_one_has_no_shift_and_table_view_shows_the_table(seeded):
    at = _app(seeded, "views/plan.py")
    at.get("button_group")[0].set_value(1).run()
    assert "Week 1" in [s.value for s in at.subheader]
    assert not any("than in week" in s.value for s in at.subheader)  # nothing to compare
    at.toggle[0].set_value(True).run()
    assert list(at.dataframe[0].value.columns) == ["Topic", "Subtopics", "Minutes", "Goal"]
    assert not [h for h in at.get("html") if '<ol class="piq-days"' in h.proto.body]


def test_plan_week_exports_as_calendar_and_table(seeded):
    from piq import formatter

    at = _app(seeded, "views/plan.py")
    assert at.expander[0].label == "Export this week"
    [first] = at.date_input
    assert first.value == formatter.next_monday(formatter.local_today())
    [at_time] = at.time_input
    assert at_time.value.strftime("%H:%M") == "19:00"
    downloads = at.get("download_button")
    assert [d.proto.label for d in downloads] == ["Calendar (.ics)", "Table (.csv)"]


def test_plan_without_a_plan_yet_invites_week_one():
    from piq import services

    sid, _ = services.onboard(
        "UI0005", "Java Backend Developer", services.load_sample("java_backend_fresher.txt")
    )
    at = _app(sid, "views/plan.py")
    assert "No plan yet" in [s.value for s in at.subheader]
    assert _button(at, "Generate week 1 plan")
    assert at.get("arrow_vega_lite_chart") or at.get("vega_lite_chart")  # weakness still shown


def test_quiz_generate_answer_and_review(seeded):
    at = _app(seeded, "views/quiz.py")
    _button(at, "Generate quiz").click().run()
    assert not at.exception and at.session_state["quiz"]
    # The loop is visible to the user, step by step, with the critic's reason.
    assert [s.label for s in at.status][1:] == [
        "**Generated the quiz**",
        "**Critic rejected the quiz**",
        "**Regenerated the quiz**",
        "**Critic approved the quiz**",
    ]
    assert ":small[Q1: options are not distinct]" in _md(at)
    assert db.recent_rejections()[0]["agent_name"] == "quiz"
    for r in at.radio:
        r.set_value(0)
    _button(at, "Submit").click().run()
    assert not at.exception
    assert "next suggested difficulty" in _md(at)
    assert len(db.quiz_history(seeded)) == 25


def test_quiz_setup_hints_weakness_and_explains_the_suggestion(seeded):
    at = _app(seeded, "views/quiz.py")
    topic, difficulty = at.get("button_group")
    assert topic.key == "quiz_topic" and topic.value == "OS"  # the weakest topic leads
    assert topic.options[0] == "OS · 43% weak" and len(topic.options) == 6
    assert difficulty.value == "medium"
    assert ":primary-badge[:material/recommend: Suggested: medium] Your last OS quiz: 70%" in _md(
        at
    )
    assert not at.radio  # the setup has no radios: every radio on the next screen is an answer
    topic.set_value("OOP").run()  # 90% on medium last time: the suggestion moves up
    assert at.get("button_group")[1].value == "hard"
    assert "Suggested: hard] Your last OOP quiz: 90% on medium" in _md(at)


def test_quiz_review_shows_a_score_card_marks_and_next_steps(seeded):
    at = _app(seeded, "views/quiz.py")
    _button(at, "Generate quiz").click().run()
    quiz = at.session_state["quiz"]
    for r, q in zip(at.radio, quiz.questions, strict=True):
        r.set_value(q.correct_index)
    at.radio[0].set_value((quiz.questions[0].correct_index + 1) % 4)  # one wrong answer
    _button(at, "Submit").click().run()
    assert not at.exception
    assert {m.label: m.value for m in at.metric} == {"Score": "80%", "Correct": "4/5"}
    md = _md(at)
    assert md.count(":green-badge[:material/check_circle: Correct]") == 4
    assert md.count(":red-badge[:material/error: Wrong]") == 1
    assert "4 of 5 correct, so the next suggested difficulty is **hard**" in md
    links = [(p.proto.page, p.proto.label) for p in at.get("page_link")]
    assert links == [("plan", "Open Weekly plan")]
    _button(at, "New quiz").click().run()
    assert _button(at, "Generate quiz")


def test_critic_log_numbers_questions_like_the_quiz(seeded):
    at = _app(seeded, "views/quiz.py")
    _button(at, "Generate quiz").click().run()
    assert any(s.label == "**Critic rejected the quiz**" for s in at.status)
    assert ":small[Q1: options are not distinct]" in _md(at)
    assert "question 0" not in _md(at)


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
    [progress] = at.main.get("progress")
    assert progress.proto.text == f"All {INTERVIEW_MAX_TURNS} questions answered"
    assert _button(at, "New session")


def test_interview_setup_describes_each_type(seeded):
    at = _app(seeded, "views/interview.py")
    [kind] = at.radio
    assert kind.options == ["HR", "Technical", "Project"]
    hints = ("Motivation, teamwork", "Core concepts", "The projects on your resume")
    assert all(c.startswith(h) for c, h in zip(kind.proto.captions, hints, strict=True))
    assert "What happens next" in [s.value for s in at.subheader]


def test_interview_shows_progress_scored_feedback_and_the_critic_trail(seeded):
    at = _app(seeded, "views/interview.py")
    _button(at, "Start session").click().run()
    [progress] = at.main.get("progress")
    assert progress.proto.text == f"Question 1 of {INTERVIEW_MAX_TURNS}"
    assert any(s.label.startswith("Interview agent — last run") for s in at.status)
    assert ":gray-badge[:material/add_comment: New question]" in _md(at)
    at.chat_input[0].set_value("I like coding.").run()
    [progress] = at.main.get("progress")
    assert progress.proto.text == f"Question 2 of {INTERVIEW_MAX_TURNS}"
    titles = [m.value for m in at.markdown if m.value.startswith("**Feedback** · ")]
    assert len(titles) == 1 and titles[0].endswith("/5 overall")
    [bars] = [h for h in at.get("html") if '<div class="piq-criteria">' in h.proto.body]
    assert bars.proto.body.count('<div class="piq-criterion">') == 4
    assert at.expander[0].label == "Strengths, what to improve and a model answer"
    assert ":gray-badge[:material/subdirectory_arrow_right: Follow-up]" in _md(at)


def test_dashboard_renders(seeded):
    at = _app(seeded, "views/dashboard.py")
    # Was at.metric[1]; found by label now, so adding or reordering metrics cannot break it.
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Quizzes taken"] == "24"  # seeded quizzes
    assert metrics["Readiness"] == "42/100" and metrics["Interview sessions"] == "2"
    charts = at.get("arrow_vega_lite_chart") or at.get("vega_lite_chart")
    assert len(charts) == 6 + 2  # a sparkline per topic, plan minutes, interview averages
    subheaders = [s.value for s in at.subheader]
    assert "OS is up from 30% to 70%" in subheaders
    assert "Week 4 puts 100% of its minutes on OS" in subheaders
    assert any(s.startswith("Your latest interview averaged") for s in subheaders)


def test_dashboard_readiness_shows_a_delta_and_trend_only_after_a_second_profile(seeded):
    from piq import services

    at = _app(seeded, "views/dashboard.py")
    [readiness] = [m for m in at.metric if m.label == "Readiness"]
    assert readiness.proto.delta == ""  # one profile: no invented delta
    assert "Readiness is 42/100 from your first profile" in [s.value for s in at.subheader]
    assert "re-profile with an updated resume" in _captions(at)

    resume = services.load_sample("python_developer.txt")
    services.onboard(seed.USN, "Python Developer", resume)  # a second profile, 73/100
    at = _app(seeded, "views/dashboard.py")
    [readiness] = [m for m in at.metric if m.label == "Readiness"]
    assert readiness.value == "73/100"
    assert readiness.proto.delta == "+31 since the last profile"
    assert any(
        s.value.startswith("Readiness ") and "over 2 profiles" in s.value for s in at.subheader
    )
    charts = at.get("arrow_vega_lite_chart") or at.get("vega_lite_chart")
    assert len(charts) == 6 + 3  # sparklines, readiness, interviews, plan minutes


def test_dashboard_keeps_system_telemetry_in_its_own_section(seeded):
    from piq import agents

    agents.make_quiz("OS", "medium", [], student_id=seeded)  # mock: one critic rejection
    at = _app(seeded, "views/dashboard.py")
    assert [h.value for h in at.header] == ["Under the hood: agents and critic"]
    stats, rejections = at.dataframe
    assert "Rejection rate" in stats.value.columns
    assert rejections.value.loc[0, "Critic's reason"].startswith("Q1: ")


def test_dashboard_for_a_new_student_explains_each_empty_section():
    from piq import services

    sid, _ = services.onboard(
        "UI0006", "Java Backend Developer", services.load_sample("java_backend_fresher.txt")
    )
    at = _app(sid, "views/dashboard.py")
    assert not at.exception
    assert {m.label: m.value for m in at.metric}["Quizzes taken"] == "0"
    subheaders = [s.value for s in at.subheader]
    assert {"No plan yet", "No interview yet"} <= set(subheaders)
    assert "No quizzes yet." in _captions(at)


def test_dashboard_error_state_offers_a_retry(seeded, monkeypatch):
    from piq import services

    def unreadable(*args, **kwargs):
        raise services.ServiceError("Your progress could not be read.")

    monkeypatch.setattr(services, "dashboard", unreadable)
    at = _app(seeded, "views/dashboard.py")
    assert "Your dashboard did not load" in [s.value for s in at.subheader]
    assert _button(at, "Try again")


def test_onboard_requires_a_resume_or_sample():
    at = _app(page="views/onboard.py")  # Home is the default page now
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
    assert at.code[0].value == "python -m evaluation.run_eval --consecutive 5 --interviews"

    (tmp_path / "summary.json").write_text(json.dumps(f.eval_summary(mode="mock")))
    at = _app(page="views/results.py")
    assert any("MOCK_MODE" in w.value for w in at.warning)
    assert len(at.dataframe) == 2  # metrics table + agent cost
    md = _md(at)
    assert "**Plan valid rate** :gray-badge[:material/arrow_upward: Higher is better]" in md
    assert "**Repeated questions over 5 quizzes** :gray-badge[:material/arrow_downward:" in md
    bars = [h for h in at.get("html") if '<div class="piq-criteria">' in h.proto.body]
    assert len(bars) == 5 and "Not measured" in bars[-1].proto.body
    assert {m.label: m.value for m in at.metric} == {"Baseline": "1.00", "PlacementIQ": "1.80"}
    assert at.expander[0].label == "All numbers as a table"


def test_results_note_mentions_the_duplicate_rate_only_when_it_is_shown(tmp_path, monkeypatch):
    import json

    from piq import services
    from tests import factories as f

    monkeypatch.setattr(services, "RESULTS_DIR", tmp_path)
    for consecutive, shown in ((None, False), (f.eval_summary()["consecutive"], True)):
        summary = f.eval_summary(consecutive=consecutive)
        (tmp_path / "summary.json").write_text(json.dumps(summary))
        at = _app(page="views/results.py")
        rows = " ".join(at.dataframe[0].value.index)
        captions = " ".join(c.value for c in at.caption)
        assert ("Duplicate rate" in rows) == shown
        assert ("duplicate rate" in captions) == shown


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


# --- Home (the default page) ---------------------------------------------------------


def test_home_without_a_student_explains_the_loop():
    at = _app()  # Home is the default page
    assert [t.value for t in at.title] == ["Placement prep that adapts to you"]
    labels = {b.label for b in at.button}
    assert {"Start with your resume", "Try it with a sample resume"} <= labels
    for n, step in enumerate(("Profile", "Plan", "Quiz", "Adapt"), 1):
        assert f"**{n}. {step}**" in _md(at)


def test_home_quick_start_opens_onboard_with_a_sample():
    from piq import services

    at = _app()
    _button(at, "Try it with a sample resume").click().run()
    assert not at.exception
    sample = next(s for s in at.selectbox if s.label.startswith("…or use"))
    assert sample.value == services.sample_resumes()[0]


def test_home_shows_todays_focus_for_the_demo_student(seeded):
    at = _app(seeded)
    assert not at.exception
    assert [t.value for t in at.title] == ["Hello, Demo Student"]
    assert "Generate your week 5 plan" in [s.value for s in at.subheader]
    assert "**Today's focus**" in _md(at)
    assert _md(at).count(":green-badge[:material/check_circle: Done]") == 4  # icon and words
    assert at.get("arrow_vega_lite_chart") or at.get("vega_lite_chart")
    assert "Scored 90% on a medium OOP quiz" in _md(at)
    assert [m.value for m in at.metric] == ["42/100"]


def test_todays_focus_opens_the_page_it_names(seeded):
    at = _app(seeded)
    _button(at, "Open Weekly plan").click().run()
    assert not at.exception
    assert [b for b in at.button if b.label == "Generate week 5 plan"]


def test_todays_focus_preselects_the_quiz_topic():
    from piq import services

    sid, _ = services.onboard(
        "UI0004", "Java Backend Developer", services.load_sample("java_backend_fresher.txt")
    )
    services.generate_next_plan(sid)
    focus = services.next_action(sid)
    assert focus.page == "views/quiz.py" and focus.topic  # a weak topic with no quiz yet
    at = _app(sid)
    _button(at, "Set up this quiz").click().run()
    assert not at.exception
    # The topic picker is now pills (was a selectbox) under the same session key.
    [topic] = [b for b in at.get("button_group") if b.key == "quiz_topic"]
    assert topic.value == focus.topic
    assert f"Suggested: {focus.difficulty}" in _md(at)


def test_home_error_state_offers_a_retry(seeded, monkeypatch):
    from piq import services

    def unreadable(*args, **kwargs):
        raise services.ServiceError("Your progress could not be read.")

    monkeypatch.setattr(services, "home", unreadable)
    at = _app(seeded)
    assert [s.value for s in at.subheader] == ["Your overview did not load"]
    assert _button(at, "Try again")
