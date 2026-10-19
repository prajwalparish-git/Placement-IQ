"""Integration tests: each user flow through services -> agents -> graph -> llm(mock) -> db."""

import pytest

from piq import agents, db, llm, services
from piq.config import INTERVIEW_MAX_TURNS
from piq.resume import ResumeError
from piq.services import ServiceError

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
