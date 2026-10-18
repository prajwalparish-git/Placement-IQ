"""Agent flows in MOCK_MODE: prompts -> schema -> checks -> critic loop, end to end."""

import pytest

from piq import agents, checks, db, graph, mock
from piq.config import DATA_DIR, INTERVIEW_MAX_TURNS, TOPICS

ROLE = "Java Backend Developer"
RESUME = (DATA_DIR / "sample_resumes" / "java_backend_fresher.txt").read_text(encoding="utf-8")


@pytest.fixture
def profile():
    return agents.create_profile(RESUME, ROLE)


def test_role_map_uses_only_syllabus_topics():
    for skills in agents.roles().values():
        assert {t for t in skills.values() if t} <= set(TOPICS)


def test_profile_scores_are_computed_in_code(profile):
    required = agents.roles()[ROLE]
    assert set(profile.matched_skills) | set(profile.missing_skills) == set(required)
    assert not set(profile.matched_skills) & set(profile.missing_skills)
    assert profile.readiness_score == round(100 * len(profile.matched_skills) / len(required))
    assert "Java" in profile.matched_skills and "Operating Systems" in profile.missing_skills
    assert agents.missing_topics(profile) >= {"OS", "DSA"}


def test_profile_regenerates_when_a_skill_is_invented(monkeypatch):
    real, calls = mock._HANDLERS["profile"], []

    def invents_once(ctx):
        out = real(ctx)
        calls.append(1)
        if len(calls) == 1:
            out["matched_skills"] = [*out["matched_skills"], "Kubernetes"]
        return out

    monkeypatch.setitem(mock._HANDLERS, "profile", invents_once)
    p = agents.create_profile(RESUME, ROLE)
    assert len(calls) == 2 and "Kubernetes" not in p.matched_skills


def test_replan_shifts_minutes_toward_low_scores(profile):
    w1 = agents.plan_week(profile, {}, 1)
    w2 = agents.plan_week(profile, {"OS": 20.0, "DSA": 90.0, "OOP": 90.0}, 2, previous=w1)
    assert w2.week_no == 2
    assert w2.minutes_by_topic().get("OS", 0) > w1.minutes_by_topic().get("OS", 0)
    assert "DSA" not in w2.minutes_by_topic()  # strong now, so it is dropped


def test_planner_inputs_carry_previous_week(profile):
    w1 = agents.plan_week(profile, {}, 1)
    inp = agents.planner_inputs(profile, {"OS": 10.0}, 2, previous=w1)
    assert inp["previous_minutes"] == w1.minutes_by_topic()
    assert inp["weakness"]["OS"] == 0.9


def test_quiz_avoids_previous_questions_and_records_scores(profile):
    sid = db.save_profile("TEST01", profile)
    q1 = agents.make_quiz("OS", "easy", [], student_id=sid)
    db.save_quiz_attempt(sid, q1, [q.correct_index for q in q1.questions])
    previous = db.asked_questions(sid, "OS")
    q2 = agents.make_quiz("OS", "easy", previous, student_id=sid)
    assert not checks.check_quiz(q2, "OS", "easy", len(q2.questions), previous)
    assert db.topic_performance(sid) == {"OS": 100.0}


def test_mock_quiz_demonstrates_one_critic_rejection():
    r = graph.run(agents.QUIZ_TASK, agents.quiz_inputs("OS", "easy", []))
    assert r.approved and r.attempts == 2
    assert "options are not distinct" in db.recent_rejections()[0]["reject_reason"]


def test_llm_critic_rejection_triggers_regeneration(monkeypatch):
    critic_calls = []

    def strict_once(ctx):
        critic_calls.append(1)
        reject = len(critic_calls) == 1
        return {
            "verdicts": [
                {"index": i, "valid": not (reject and i == 0), "reason": "two answers correct"}
                for i in range(ctx["count"])
            ]
        }

    monkeypatch.setitem(mock._HANDLERS, "critic", strict_once)
    r = graph.run(agents.QUIZ_TASK, agents.quiz_inputs("OS", "easy", []))
    # attempt 1: deterministic reject (critic skipped); 2: critic rejects; 3: approved
    assert (r.approved, r.attempts, len(critic_calls)) == (True, 3, 2)
    reasons = [row["reject_reason"] for row in db.recent_rejections()]
    assert "question 0: two answers correct" in reasons


@pytest.mark.parametrize(
    ("last", "current", "expected"),
    [
        (None, "medium", "medium"),
        (85, "medium", "hard"),
        (100, "hard", "hard"),
        (30, "medium", "easy"),
        (30, "easy", "easy"),
        (60, "medium", "medium"),
        (80, "easy", "medium"),
        (49.9, "hard", "medium"),
    ],
)
def test_suggest_difficulty(last, current, expected):
    assert agents.suggest_difficulty(last, current) == expected


def test_interview_follows_up_on_vague_answers(profile):
    first = agents.next_question(profile, "HR", [], [])
    assert not first.is_followup and not first.is_final
    history = [{"question": first.question, "answer": "I like coding."}]
    second = agents.next_question(profile, "HR", history, [])
    assert second.is_followup and "I like coding" in second.question


def test_interview_memory_avoids_past_questions(profile):
    past = [{"question": "Tell me about yourself.", "answer": "A detailed answer " * 10}]
    q = agents.next_question(profile, "HR", [], past)
    assert q.question == "Why do you want to join our company?"


def test_interview_final_turn_is_enforced_in_code(profile):
    history = [{"question": f"q{i}", "answer": "a " * 40} for i in range(INTERVIEW_MAX_TURNS - 1)]
    assert agents.next_question(profile, "Technical", history, []).is_final


def test_answer_evaluation_overall_is_mean(profile):
    ev = agents.evaluate_answer(profile, "HR", "Tell me about yourself.", "situation task " * 20)
    assert ev.overall == sum(ev.scores.values()) / 4
