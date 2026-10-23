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


def test_mock_interview_never_repeats_a_follow_up(profile):
    """Two vague answers with the same opening used to deadlock the critic (B5)."""
    first = agents.next_question(profile, "HR", [], [])
    history = [{"question": first.question, "answer": "I like coding."}]
    second = agents.next_question(profile, "HR", history, [])
    history.append({"question": second.question, "answer": "I like coding."})
    third = agents.next_question(profile, "HR", history, [])
    assert third.question not in (first.question, second.question)


def test_mock_follow_up_quotes_answers_cleanly(profile):
    first = agents.next_question(profile, "HR", [], [])
    short = [{"question": first.question, "answer": "I like coding."}]
    assert agents.next_question(profile, "HR", short, []).question.startswith(
        "You said 'I like coding'. Can you"
    )
    long = [{"question": first.question, "answer": "I mostly worked on the backend of our app."}]
    assert agents.next_question(profile, "HR", long, []).question.startswith(
        "You said 'I mostly worked on the backend...'. Can you"
    )


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


def test_only_flagged_questions_are_regenerated(monkeypatch):
    asked: list[int] = []
    real_quiz = mock._HANDLERS["quiz"]
    monkeypatch.setitem(
        mock._HANDLERS, "quiz", lambda ctx: asked.append(ctx["count"]) or real_quiz(ctx)
    )
    first = graph.run(agents.QUIZ_TASK, agents.quiz_inputs("DBMS", "easy", []))
    # attempt 1: 5 questions, q0 has duplicate options; attempt 2 asks for 1 replacement only
    assert first.approved and asked == [5, 1]
    assert len({q.text for q in first.output.questions}) == 5


def test_critic_judges_each_question_once(monkeypatch):
    batches: list[int] = []
    rejected_once = {"done": False}

    def critic(ctx):
        batches.append(ctx["count"])
        reject = not rejected_once["done"]
        rejected_once["done"] = True
        return {
            "verdicts": [
                {"index": i, "valid": not (reject and i == 3), "reason": "ambiguous"}
                for i in range(ctx["count"])
            ]
        }

    monkeypatch.setitem(mock._HANDLERS, "critic", critic)
    r = graph.run(agents.QUIZ_TASK, agents.quiz_inputs("CN", "medium", []))
    assert r.approved
    assert batches == [5, 1]  # the 4 approved questions are not re-sent
    # Re-verifying the final quiz (as the evaluation harness does) costs no LLM call.
    assert agents.verify_quiz(agents.quiz_inputs("CN", "medium", []), r.output) == []
    assert batches == [5, 1]


def test_critic_with_one_based_indices_is_understood(monkeypatch):
    def one_based(ctx):
        return {
            "verdicts": [{"index": i + 1, "valid": True, "reason": ""} for i in range(ctx["count"])]
        }

    monkeypatch.setitem(mock._HANDLERS, "critic", one_based)
    assert graph.run(agents.QUIZ_TASK, agents.quiz_inputs("OS", "easy", [])).approved


@pytest.mark.parametrize(
    ("indices", "cached"),
    [
        ([1, 2, 3, 4, 5], 5),  # 1-based and complete: understood
        ([0, 1, 2, 3, 4], 5),  # 0-based and complete
        ([1, 2, 4, 5], 0),  # 1-based with one missing
        ([1, 2, 3, 4], 0),  # 0-based without 0 (or 1-based without 5): ambiguous
        ([0, 1, 2, 3], 0),  # 0-based with one missing
        ([0, 0, 1, 2, 3, 4], 0),  # a duplicate
        ([0, 1, 2, 3, 9], 0),  # out of range
    ],
)
def test_critic_verdicts_count_only_when_their_numbering_is_unambiguous(
    monkeypatch, indices, cached
):
    r = graph.run(agents.QUIZ_TASK, agents.quiz_inputs("OS", "easy", []))
    assert r.approved and len(r.output.questions) == 5
    agents.clear_verdict_cache()
    verdicts = [{"index": i, "valid": True, "reason": ""} for i in indices]
    monkeypatch.setitem(mock._HANDLERS, "critic", lambda ctx: {"verdicts": verdicts})
    reasons = agents.verify_quiz(agents.quiz_inputs("OS", "easy", []), r.output)
    assert len(agents._VERDICTS) == cached  # a guessed mapping is never cached
    assert len(reasons) == 5 - cached  # every unjudged question counts as rejected
    assert all(reason.endswith("the critic gave no verdict") for reason in reasons)


def test_missing_critic_verdict_counts_as_rejection(monkeypatch):
    monkeypatch.setitem(mock._HANDLERS, "critic", lambda ctx: {"verdicts": []})
    r = graph.run(agents.QUIZ_TASK, agents.quiz_inputs("OS", "easy", []))
    assert not r.approved
    assert r.reasons[0] == "question 0: the critic gave no verdict"


def test_unknown_role_is_rejected_before_any_llm_call():
    with pytest.raises(ValueError, match="unknown target role"):
        agents.create_profile(RESUME, "Astronaut")
    assert db.agent_stats() == []
