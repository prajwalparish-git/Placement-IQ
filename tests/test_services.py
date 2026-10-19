"""Integration tests: each user flow through services -> agents -> graph -> llm(mock) -> db."""

import pytest

from piq import agents, db, llm, services
from piq.config import INTERVIEW_MAX_TURNS, TOPICS
from piq.resume import ResumeError
from piq.services import ServiceError
from tests import factories as f

ROLE = "Java Backend Developer"


@pytest.fixture
def student() -> str:
    sid, _ = services.onboard("TEST01", ROLE, services.load_sample("java_backend_fresher.txt"))
    return sid


# --- onboarding ----------------------------------------------------------------


def test_onboard_creates_student_and_profile(student):
    [row] = services.list_students()
    assert (row["id"], row["usn"]) == (student, "TEST01")
    profile = services.current_profile(student)
    assert profile.target_role == ROLE and 0 <= profile.readiness_score <= 100


@pytest.mark.parametrize("usn", ["", "   ", "AB1", "AB 123", "AB-123", "x" * 21, None])
def test_invalid_usn_is_rejected(usn):
    with pytest.raises(ServiceError, match="USN is required"):
        services.normalise_usn(usn)


def test_usn_is_normalised():
    assert services.normalise_usn("  1ab22is001 ") == "1AB22IS001"


def test_onboard_rejects_unknown_role_and_empty_resume():
    with pytest.raises(ServiceError, match="Unknown target role"):
        services.onboard("TEST02", "Astronaut", "some resume text")
    with pytest.raises(ServiceError, match="empty"):
        services.onboard("TEST02", ROLE, "   ")
    assert services.list_students() == []


def test_sample_list_is_read_once(monkeypatch):
    from pathlib import PurePath

    globs = []

    class Folder:
        def glob(self, pattern: str) -> list[PurePath]:
            globs.append(pattern)
            return [PurePath("b.txt"), PurePath("a.txt")]

    monkeypatch.setattr(services, "SAMPLES_DIR", Folder())
    assert services.sample_resumes() == services.sample_resumes() == ("a.txt", "b.txt")
    assert globs == ["*.txt"]


def test_samples_load_only_from_the_listed_files():
    assert "java_backend_fresher.txt" in services.sample_resumes()
    assert "Spring Boot" in services.load_sample("java_backend_fresher.txt")
    for bad in ("../../.env", "../role_skills.json", "missing.txt"):
        with pytest.raises(ServiceError, match="Unknown sample"):
            services.load_sample(bad)


def test_read_resume_surfaces_parser_errors():
    with pytest.raises(ResumeError):
        services.read_resume("cv.exe", b"x" * 100)


def test_operations_require_an_onboarded_student():
    for call in (
        lambda: services.plan_overview("nobody"),
        lambda: services.generate_next_plan("nobody"),
        lambda: services.start_quiz("nobody", "OS", "easy"),
        lambda: services.start_interview("nobody", "HR"),
        lambda: services.dashboard("nobody"),
    ):
        with pytest.raises(ServiceError, match="Onboard this student first"):
            call()
    assert services.current_profile(None) is None


# --- planning ------------------------------------------------------------------


def test_plans_are_numbered_and_adapt_to_quiz_scores(student):
    assert services.plan_overview(student).next_week == 1
    w1 = services.generate_next_plan(student)
    quiz = services.start_quiz(student, "OS", "easy")
    services.submit_quiz(student, quiz, [None] * len(quiz.questions))  # 0% on OS
    w2 = services.generate_next_plan(student)
    assert (w1.week_no, w2.week_no) == (1, 2)
    assert w2.minutes_by_topic()["OS"] > w1.minutes_by_topic()["OS"]
    ov = services.plan_overview(student)
    assert ov.next_week == 3 and ov.scores == {"OS": 0.0} and ov.weakness["OS"] == 1.0


# --- quizzes -------------------------------------------------------------------


def test_quiz_round_trip_and_adaptive_difficulty(student):
    assert services.suggested_difficulty(student, "DBMS") == "medium"
    quiz = services.start_quiz(student, "DBMS", "medium")
    result = services.submit_quiz(student, quiz, [q.correct_index for q in quiz.questions])
    assert (result.score_pct, result.next_difficulty) == (100.0, "hard")
    assert services.suggested_difficulty(student, "DBMS") == "hard"
    again = services.start_quiz(student, "DBMS", "hard")
    assert not {q.text for q in again.questions} & {q.text for q in quiz.questions}


def test_quiz_setup_ranks_topics_and_suggests_from_the_latest_attempt(student):
    profile = services.current_profile(student)
    before = services.quiz_setup(student, profile)
    assert before.last == {} and before.suggested("DBMS") == "medium"
    assert sorted(before.weakness) == sorted(TOPICS)
    assert before.weakness[before.topics[0]] == max(before.weakness.values())  # weakest first
    quiz = services.start_quiz(student, "DBMS", "medium")
    result = services.submit_quiz(student, quiz, [q.correct_index for q in quiz.questions])
    assert result.correct == len(quiz.questions)
    after = services.quiz_setup(student)
    assert after.last == {"DBMS": (100.0, "medium")}
    assert after.suggested("DBMS") == services.suggested_difficulty(student, "DBMS") == "hard"
    assert after.weakness["DBMS"] == 0.0
    assert after.topics[-1] == "DBMS"  # now the strongest, so last


def test_quiz_result_counts_correct_answers_and_quiz_key_is_stable():
    quiz = f.quiz(n=3)
    result = services.QuizResult(quiz, [quiz.questions[0].correct_index, None, 3], 33.3, "easy")
    assert result.correct == 1
    assert services.quiz_key(quiz) == services.quiz_key(quiz.model_copy())
    assert services.quiz_key(quiz) != services.quiz_key(f.quiz(n=3, prefix="other"))


@pytest.mark.parametrize(("topic", "difficulty"), [("Maths", "easy"), ("OS", "extreme")])
def test_start_quiz_validates_parameters(student, topic, difficulty):
    with pytest.raises(ServiceError, match="Unknown"):
        services.start_quiz(student, topic, difficulty)


def test_submit_quiz_validates_answers(student):
    quiz = services.start_quiz(student, "OS", "easy")
    with pytest.raises(ServiceError, match="do not match"):
        services.submit_quiz(student, quiz, [0])
    with pytest.raises(ServiceError, match="Invalid answer"):
        services.submit_quiz(student, quiz, [4] + [0] * (len(quiz.questions) - 1))
    assert db.quiz_history(student) == []  # nothing saved for rejected submissions


# --- interviews ----------------------------------------------------------------


def test_interview_runs_to_completion_and_persists_turns(student):
    s = services.start_interview(student, "HR")
    assert s.current and not s.current.is_followup and s.history == [] and s.average is None
    s = services.answer_question(student, s, "I like coding.")
    assert s.current is None and len(s.history) == 1
    s = services.continue_interview(student, s)
    assert s.current.is_followup and "I like coding" in s.current.question
    while not s.done:
        s = services.answer_question(student, s, "Situation task action result " * 8)
        if not s.done:
            s = services.continue_interview(student, s)
    assert len(s.history) == INTERVIEW_MAX_TURNS
    assert s.average == round(sum(t.evaluation.overall for t in s.history) / len(s.history), 2)
    assert len(db.past_turns(student)) == INTERVIEW_MAX_TURNS


def test_interview_answer_validation(student):
    s = services.start_interview(student, "Technical")
    for bad, message in (("   ", "Type an answer"), ("x" * 4001, "limited to 4000")):
        with pytest.raises(ServiceError, match=message):
            services.answer_question(student, s, bad)
    answered = services.answer_question(student, s, "A process owns its memory.")
    with pytest.raises(ServiceError, match="no open question"):
        services.answer_question(student, answered, "again")  # no double save
    with pytest.raises(ServiceError, match="not waiting"):
        services.continue_interview(student, s)  # s still has an open question
    assert len(db.past_turns(student)) == 1


def test_failed_follow_up_can_be_retried_without_reanswering(student, monkeypatch):
    s = services.answer_question(student, services.start_interview(student, "HR"), "An answer.")
    real = agents.next_question

    def down(*args, **kwargs):
        raise llm.LLMError("Groq API error: unavailable")

    monkeypatch.setattr(agents, "next_question", down)
    with pytest.raises(llm.LLMError):
        services.continue_interview(student, s)
    monkeypatch.setattr(agents, "next_question", real)
    s = services.continue_interview(student, s)
    assert s.current is not None and len(db.past_turns(student)) == 1


def test_new_session_remembers_earlier_questions(student):
    first = services.start_interview(student, "HR")
    services.answer_question(student, first, "A long and detailed answer " * 5)
    second = services.start_interview(student, "HR")
    assert second.past and second.current.question != first.current.question


def test_unknown_interview_type(student):
    with pytest.raises(ServiceError, match="Unknown interview type"):
        services.start_interview(student, "Stress")


# --- dashboard -----------------------------------------------------------------


def test_dashboard_aggregates_everything(student):
    services.generate_next_plan(student)
    quiz = services.start_quiz(student, "CN", "easy")
    services.submit_quiz(student, quiz, [0] * len(quiz.questions))
    d = services.dashboard(student)
    assert d.profile.target_role == ROLE
    assert len(d.plans) == 1 and len(d.quiz_history) == 1 and d.sessions == []
    assert {r["agent_name"] for r in d.agent_stats} >= {"profile", "planner", "quiz", "critic"}
    assert d.rejections and d.rejections[0]["agent_name"] == "quiz"  # mock's deliberate flaw


def test_evaluation_summary(tmp_path, monkeypatch):
    import json

    from tests import factories as f

    monkeypatch.setattr(services, "RESULTS_DIR", tmp_path)
    assert services.evaluation_summary() is None
    (tmp_path / "summary.json").write_text("{not json", encoding="utf-8")
    assert services.evaluation_summary() is None
    (tmp_path / "summary.json").write_text(json.dumps(f.eval_summary()), encoding="utf-8")
    assert services.evaluation_summary()["placementiq"]["cases"] == 20


# --- home: today's focus ---------------------------------------------------------

NOW = __import__("datetime").datetime(2026, 10, 19, 12, 0, tzinfo=__import__("datetime").UTC)
PLAN_OLD = {"week_no": 4, "created_at": "2026-10-10 09:00:00"}  # 9 days before NOW
PLAN_NEW = {"week_no": 5, "created_at": "2026-10-18 09:00:00"}
WEAK = {"Aptitude": 0.2, "DBMS": 0.7, "OS": 0.8, "CN": 0.3, "DSA": 0.2, "OOP": 0.1}
CALM = {"Aptitude": 0.2, "DBMS": 0.4, "OS": 0.45, "CN": 0.3, "DSA": 0.2, "OOP": 0.1}


def _attempt(topic: str, at: str, pct: float = 40.0, difficulty: str = "medium") -> dict:
    return {"topic": topic, "attempted_at": at, "score_pct": pct, "difficulty": difficulty}


def _decide(profile=..., plan=PLAN_OLD, weakness=CALM, attempts=(), sessions=1):
    from tests import factories as f

    profile = f.profile() if profile is ... else profile
    return services.decide_next_action(profile, plan, weakness, list(attempts), sessions, NOW)


def test_next_action_without_a_profile_is_onboarding():
    a = _decide(profile=None)
    assert (a.page, a.label, a.cta) == (
        "views/onboard.py",
        "Onboard with your resume",
        "Open Onboard",
    )


def test_next_action_without_a_plan_is_week_1():
    a = _decide(plan=None, weakness=WEAK)
    assert (a.page, a.label) == ("views/plan.py", "Generate your week 1 plan")


def test_next_action_quizzes_the_weakest_unpractised_topic_first():
    a = _decide(weakness=WEAK)  # OS 0.8 and DBMS 0.7 are weak; neither has a quiz
    assert (a.page, a.topic, a.difficulty) == ("views/quiz.py", "OS", "medium")
    assert a.label == "Take a medium OS quiz" and "not taken a quiz on it yet" in a.reason
    recent_os = [_attempt("OS", "2026-10-17 10:00:00")]
    assert _decide(weakness=WEAK, attempts=recent_os).topic == "DBMS"  # OS was practised


def test_next_action_returns_to_a_weak_topic_after_a_week_at_the_suggested_level():
    stale = [_attempt("OS", "2026-10-01 10:00:00", pct=90.0, difficulty="medium")]
    a = _decide(weakness={**CALM, "OS": 0.8}, attempts=stale)
    assert (a.topic, a.difficulty) == ("OS", agents.suggest_difficulty(90.0, "medium"))
    assert "no quiz in the last 7 days" in a.reason


def test_next_action_suggests_an_interview_once_weak_topics_are_practised():
    recent = [_attempt("OS", "2026-10-17 10:00:00")]
    a = _decide(weakness={**CALM, "OS": 0.8}, attempts=recent, sessions=0)
    assert (a.page, a.label) == ("views/interview.py", "Try a mock interview")


def test_next_action_adapts_the_plan_when_it_is_a_week_old_with_new_scores():
    since = [_attempt("OS", "2026-10-12 10:00:00"), _attempt("CN", "2026-10-13 10:00:00")]
    a = _decide(plan=PLAN_OLD, attempts=since)
    assert (a.page, a.label) == ("views/plan.py", "Generate your week 5 plan")
    assert "9 days old and 2 quiz scores came in since" in a.reason


def test_next_action_otherwise_practises_the_weakest_topic():
    since = [_attempt("OS", "2026-10-18 10:00:00", pct=40.0)]  # low score: the level drops
    a = _decide(plan=PLAN_NEW, attempts=since)  # fresh plan: nothing to adapt yet
    assert (a.page, a.topic, a.difficulty) == ("views/quiz.py", "OS", "easy")
    assert a.label == "Practise OS with an easy quiz"  # "an" before a vowel
    old_plan_no_scores = _decide(plan=PLAN_OLD, attempts=[_attempt("OS", "2026-10-09 10:00:00")])
    assert old_plan_no_scores.page == "views/quiz.py"


def test_home_gathers_focus_checklist_and_recent_activity():
    from scripts import seed

    seed.main()
    sid = next(s["id"] for s in db.list_students() if s["usn"] == seed.USN)
    h = services.home(sid)
    assert (
        h.next_action.label == "Generate your week 5 plan"
    )  # the seeded week 4 plan is 7 days old
    assert [c.done for c in h.checklist] == [True, True, True, True]
    assert len(h.recent) == 4 and h.recent == sorted(h.recent, key=lambda a: a.at, reverse=True)
    assert services.next_action(sid) == h.next_action


def test_home_for_a_new_student_starts_with_a_plan(student):
    h = services.home(student)
    assert h.next_action.label == "Generate your week 1 plan"
    assert [c.done for c in h.checklist] == [True, False, False, False] and h.recent == []
    assert services.next_action(None).page == "views/onboard.py"
    assert services.next_action("nobody").page == "views/onboard.py"


def test_home_reports_an_unreadable_database_safely(student, monkeypatch):
    import sqlite3

    def broken(*_):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(db, "quiz_history", broken)
    with pytest.raises(ServiceError, match="could not be read"):
        services.home(student)


def test_usn_owner_finds_the_student_behind_a_usn(student):
    owner = services.usn_owner(" " + db.list_students()[0]["usn"].lower() + " ")
    assert owner["id"] == student and owner["name"]
    assert services.usn_owner("NOBODY01") is None
    with pytest.raises(ServiceError, match="USN is required"):
        services.usn_owner("bad usn")


def test_delete_student_needs_the_matching_usn(student):
    usn = db.list_students()[0]["usn"]
    with pytest.raises(ServiceError, match="nothing was deleted"):
        services.delete_student(student, "WRONG001")
    assert services.current_profile(student) is not None  # a wrong USN deletes nothing
    services.delete_student(student, f" {usn.lower()} ")
    assert db.list_students() == [] and services.current_profile(student) is None
    with pytest.raises(ServiceError, match="no longer exists"):
        services.delete_student(student, usn)


def test_interview_summary_averages_each_criterion_and_tips_the_weak_ones():
    from piq.config import INTERVIEW_TIPS

    def turn(**scores):
        return services.AnsweredTurn(question="q", answer="a", evaluation=f.evaluation(**scores))

    session = services.InterviewSession(
        session_id="s",
        interview_type="HR",
        past=[],
        history=[turn(relevance=5, depth=1, clarity=4), turn(relevance=4, depth=2, clarity=1)],
        done=True,
    )
    summary = services.interview_summary(session)
    assert summary.averages == {"relevance": 4.5, "depth": 1.5, "structure": 3.0, "clarity": 2.5}
    assert (summary.strongest, summary.weakest) == ("relevance", "depth")
    assert summary.tips == {"depth": INTERVIEW_TIPS["depth"], "clarity": INTERVIEW_TIPS["clarity"]}
    assert set(INTERVIEW_TIPS) == set(f.evaluation().scores)  # a tip for every criterion
    with pytest.raises(ServiceError, match="no answers yet"):
        services.interview_summary(session.model_copy(update={"history": []}))
