"""piq/journey.py: the six-step journey's controllers run the agents in MOCK_MODE and record every
activity in the telemetry layer; a telemetry outage never costs the student a result."""

import pytest

from database import crud
from piq import journey, services
from piq.config import DEFAULT_SAMPLE
from scripts import seed, seed_cohort


@pytest.fixture
def sid() -> str:
    seed.main()
    return next(s["id"] for s in services.list_students() if s["usn"] == seed.USN)


def test_student_and_catalog_streams(sid):
    me = journey.student(sid)
    assert me.usn == seed.USN and me.stream == "Engineering"
    assert {"Engineering", "Commerce", "Law", "Management"} <= set(journey.streams())
    assert journey.domains_in("Law") and journey.roles_in(journey.domains_in("Law")[0][0])
    assert journey.voice_stream("Healthcare") == "Engineering"
    with pytest.raises(services.ServiceError):
        journey.student(None)


def test_scan_records_the_analysis_and_feeds_the_roadmap(sid):
    me = journey.student(sid)
    scan = journey.scan_resume(
        sid, DEFAULT_SAMPLE, journey.read_sample(DEFAULT_SAMPLE), me.target_role
    )
    assert scan.saved and 0 <= scan.analysis.match_percentage <= 100
    t = crud.get_student(me.usn)
    latest = crud.latest_resume_analysis(t.id)
    assert latest.missing_skills == scan.analysis.missing_gap_skills
    gaps, origin = journey.latest_gaps(sid)
    assert gaps == scan.analysis.missing_gap_skills and origin == "your latest resume scan"


def test_scan_rejects_bad_input(sid):
    with pytest.raises(services.ServiceError, match="Upload a resume"):
        journey.scan_resume(sid, "", b"", "Data Analyst")
    with pytest.raises(services.ServiceError, match="Unknown target role"):
        journey.scan_resume(sid, "r.txt", b"Python SQL", "Astronaut")
    with pytest.raises(services.ServiceError, match="Unknown sample"):
        journey.read_sample("../../.env")


def test_without_a_scan_gaps_come_from_onboarding(sid):
    gaps, origin = journey.latest_gaps(sid)
    assert origin == "your onboarding profile" and isinstance(gaps, list)


def test_roadmaps_are_saved_week_by_week_with_progress(sid):
    first, saved = journey.build_roadmap(sid, ["SQL", "Statistics"])
    second, _ = journey.build_roadmap(sid, ["Python"])
    assert saved and (first.week, second.week) == (1, 2) and len(first.plan.days) == 7
    assert journey.set_tasks_done(sid, 1, {"d1:0", "d2:1"})
    weeks = {r.week: r for r in journey.roadmaps(sid)}
    assert weeks[1].done == {"d1:0", "d2:1"} and weeks[2].done == frozenset()
    assert journey.set_tasks_done(sid, 9, {"d1:0"}) is False  # no such week


def test_critic_quiz_is_graded_and_recorded(sid):
    batch = journey.critic_quiz(sid, "SQL", "medium", 3)
    assert len(batch.questions) == 3
    answers = [batch.questions[0].correct_index, None, (batch.questions[2].correct_index + 1) % 4]
    grade = journey.grade_quiz(sid, batch, answers)
    assert (grade.score, grade.total, grade.correct) == (1, 3, (True, False, False))
    assert grade.saved and grade.percent == 33
    [attempt] = crud.quiz_attempts(crud.get_student(seed.USN).id)
    assert (attempt.score, attempt.total_questions) == (
        1,
        3,
    ) and "Skill: SQL" in attempt.critique_notes


@pytest.mark.parametrize(
    ("skill", "difficulty", "count", "match"),
    [
        ("", "easy", 3, "Pick a skill"),
        ("SQL", "brutal", 3, "Difficulty"),
        ("SQL", "easy", 4, "3, 5, 10"),
    ],
)
def test_critic_quiz_validates(sid, skill, difficulty, count, match):
    with pytest.raises(services.ServiceError, match=match):
        journey.critic_quiz(sid, skill, difficulty, count)


def test_voice_question_speaks_and_the_answer_is_scored_and_recorded(sid):
    vq = journey.voice_question(sid, "Commerce", "situational")
    assert vq.question.stream == "Commerce" and vq.speech.source == "browser"  # no ElevenLabs key
    assert "speechSynthesis" in journey.browser_speech_html(vq.speech.text)
    answer = (
        "In my internship the vendor ledger did not match the stock register, so I traced the "
        "purchase orders, ran cut-off tests and reconciled the difference; as a result the "
        "audit closed on time with no qualification."
    )
    result = journey.assess_answer(sid, vq.question, answer)
    assert result.saved and 0 <= result.evaluation.rubric.total_score <= 15
    [session] = crud.voice_sessions(crud.get_student(seed.USN).id)
    assert session.rubric_score == result.evaluation.rubric.total_score
    assert session.audio_transcript.startswith("Q: ") and answer in session.audio_transcript
    with pytest.raises(services.ServiceError, match="Record or type"):
        journey.assess_answer(sid, vq.question, "   ")


def test_transcribe_without_audio_is_empty():
    assert journey.transcribe(b"") == ""


def test_a_telemetry_outage_keeps_the_result(sid, monkeypatch):
    def down(*a, **k):
        raise RuntimeError("database down")

    monkeypatch.setattr(crud, "save_student", down)
    batch = journey.critic_quiz(sid, "SQL", "easy", 3)
    grade = journey.grade_quiz(sid, batch, [None, None, None])
    assert grade.saved is False and grade.total == 3
    roadmap, saved = journey.build_roadmap(sid, ["SQL"])
    assert saved is False and len(roadmap.plan.days) == 7
    assert journey.record_student(sid) is False


def test_cohort_view_and_service_status(sid):
    assert journey.cohort_view().rows == []
    assert journey.record_student(sid)
    seed_cohort.main([])
    view = journey.cohort_view()
    assert not view.error and len(view.rows) == 1 + len(seed_cohort.GROUPS) * seed_cohort.PER_GROUP
    assert {"Engineering", "Commerce", "Law", "Management"} <= {r.stream for r in view.rows}
    status = journey.service_status()
    assert status.active_ai == "Mock mode" and status.voice == "Browser voice"
    assert status.telemetry == "SQLite"


def test_seed_cohort_replace_is_idempotent():
    seed_cohort.main([])
    seed_cohort.main(["--replace"])
    view = journey.cohort_view()
    assert len(view.rows) == len(seed_cohort.GROUPS) * seed_cohort.PER_GROUP
    assert all(r.usn.startswith(seed_cohort.PREFIX) for r in view.rows)
    assert len({r.quizzes > 0 for r in view.rows}) >= 1 and sum(r.quizzes for r in view.rows) > 20


def test_cohort_view_reports_an_unavailable_store(monkeypatch):
    monkeypatch.setattr(crud, "cohort", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    view = journey.cohort_view()
    assert view.rows == [] and "unavailable" in view.error
