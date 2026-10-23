import sqlite3

import pytest

from piq import db
from tests import factories as f


def test_usn_is_normalised_and_identifies_the_student():
    a = db.save_profile(" ab12 ", f.profile())
    b = db.save_profile("AB12", f.profile(name="Renamed"))
    assert a == b
    [row] = db.list_students()
    assert (row["usn"], row["name"]) == ("AB12", "Renamed")
    assert len(db.readiness_history(a)) == 2  # every re-profile is kept


def test_usn_is_required():
    with pytest.raises(sqlite3.IntegrityError), db.tx() as c:
        c.execute("INSERT INTO students (id, name, target_role) VALUES ('x', 'n', 'r')")


def test_profile_roundtrip_and_unknown_student():
    sid = db.save_profile("P0", f.profile())
    assert db.latest_profile(sid) == f.profile()
    assert db.latest_profile("missing") is None


def test_failed_transaction_rolls_back():
    with pytest.raises(sqlite3.IntegrityError), db.tx() as c:
        c.execute("INSERT INTO agent_logs (agent_name, model_used) VALUES ('a', 'm')")
        c.execute("INSERT INTO students (id, name, target_role) VALUES ('x', 'n', 'r')")
    assert db.agent_stats() == []


def test_save_plan_upserts_the_same_week():
    sid = db.save_profile("P1", f.profile())
    db.save_plan(sid, f.plan(week=1))
    db.save_plan(sid, f.plan(week=1, topics=("DBMS",) * 7))
    db.save_plan(sid, f.plan(week=2))
    plans = db.list_plans(sid)
    assert [p.week_no for p in plans] == [1, 2]
    assert plans[0].days[0].topic == "DBMS"


def test_quiz_attempt_score_history_and_asked_questions():
    sid = db.save_profile("P2", f.profile())
    q = f.quiz(n=4)
    assert db.save_quiz_attempt(sid, q, f.answers(q, 3)) == 75.0
    assert db.last_attempt(sid, "OS")["score_pct"] == 75.0
    assert db.last_attempt(sid, "CN") is None
    assert set(db.asked_questions(sid, "OS")) == {x.text for x in q.questions}
    assert db.asked_questions(sid, "CN") == []
    assert len(db.asked_questions(sid, "OS", limit=2)) == 2


def test_unanswered_question_counts_as_wrong_and_lengths_must_match():
    sid = db.save_profile("P3", f.profile())
    q = f.quiz(n=2)
    assert db.save_quiz_attempt(sid, q, [q.questions[0].correct_index, None]) == 50.0
    with pytest.raises(ValueError):
        db.save_quiz_attempt(sid, q, [0])


def test_topic_performance_uses_the_three_most_recent_attempts():
    sid = db.save_profile("P4", f.profile())
    q = f.quiz(topic="DBMS", n=2)
    for day, right in enumerate([0, 2, 2, 2], 1):  # 0% is the oldest, so it drops out
        db.save_quiz_attempt(sid, q, f.answers(q, right), at=f"2026-01-0{day} 10:00:00")
    db.save_quiz_attempt(sid, f.quiz(n=2), [None, None], at="2026-01-05 10:00:00")
    assert db.topic_performance(sid) == {"DBMS": 100.0, "OS": 0.0}
    assert len(db.quiz_history(sid)) == 5
    # The same query also returns each topic's latest attempt (for the quiz setup).
    stats = db.topic_stats(sid)
    assert stats["DBMS"] == {"avg_pct": 100.0, "last_pct": 100.0, "last_difficulty": "easy"}
    assert stats["OS"]["last_pct"] == 0.0


def test_agent_stats_count_failed_calls_apart_from_rejections():
    rejected = db.log_call("quiz", "mock", 1, 1, 10)
    db.mark_log(rejected, False, 0, "bad")
    db.log_call("quiz", "mock", 1, 1, 10, failed="Groq API error")
    [row] = db.agent_stats()
    assert (row["calls"], row["rejections"], row["failures"]) == (2, 1, 1)
    assert row["rejection_rate"] == 1.0  # a failed call had no critic, so it is not a rejection
    assert [r["reject_reason"] for r in db.recent_rejections()] == ["bad"]


def test_past_turns_exclude_current_session_newest_first():
    sid = db.save_profile("P5", f.profile())
    ev = f.evaluation(relevance=5)
    db.save_turn(sid, "s1", "HR", "old q", "a", ev, at="2026-01-01 10:00:00")
    db.save_turn(sid, "s2", "HR", "new q", "a", ev, at="2026-01-02 10:00:00")
    assert [t["question"] for t in db.past_turns(sid)] == ["new q", "old q"]
    assert [t["question"] for t in db.past_turns(sid, exclude_session="s2")] == ["old q"]
    first, second = db.interview_history(sid)
    assert (first["session_id"], second["turns"], first["avg_overall"]) == ("s1", 1, 3.5)


def test_delete_student_cascades_to_all_history():
    sid = db.save_profile("P6", f.profile())
    db.save_plan(sid, f.plan())
    db.save_quiz_attempt(sid, f.quiz(), [0, 0])
    db.save_turn(sid, "s", "HR", "q", "a", f.evaluation())
    db.delete_student("p6")
    with db.tx() as c:
        counts = [
            c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("profiles", "plans", "quiz_attempts", "quiz_questions", "interview_turns")
        ]
    assert counts == [0, 0, 0, 0, 0]


def test_agent_log_marking_and_stats():
    a = db.log_call("quiz", "m", 10, 5, 100)
    b = db.log_call("quiz", "m", 10, 5, 300)
    db.mark_log(a, approved=False, retry_count=0, reject_reason="dup")
    db.mark_log(b, approved=True, retry_count=1, reject_reason=None)
    db.log_call("evaluator", "m", 1, 1, 1)
    stats = {r["agent_name"]: r for r in db.agent_stats()}
    assert (stats["quiz"]["calls"], stats["quiz"]["avg_latency_ms"]) == (2, 200)
    assert (stats["quiz"]["rejections"], stats["quiz"]["rejection_rate"]) == (1, 0.5)
    assert (stats["evaluator"]["rejections"], stats["evaluator"]["rejection_rate"]) == (0, None)
    [rejection] = db.recent_rejections()
    assert rejection["reject_reason"] == "dup"


def test_plan_progress_marks_days_and_joins_onto_the_plans():
    sid = db.save_profile("P9", f.profile())
    db.save_plan(sid, f.plan(week=1))
    db.save_plan(sid, f.plan(week=2))
    db.set_days_done(sid, 1, {1, 3})
    with db.tx() as c:
        first = c.execute(
            "SELECT done_at FROM plan_progress WHERE week_no = 1 AND day = 1"
        ).fetchone()["done_at"]
    db.set_days_done(sid, 1, {1, 4})  # day 3 undone, day 4 added, day 1 kept
    assert [(p.week_no, done) for p, done in db.plans_with_progress(sid)] == [
        (1, {1, 4}),
        (2, set()),
    ]
    with db.tx() as c:
        kept = c.execute(
            "SELECT done_at FROM plan_progress WHERE week_no = 1 AND day = 1"
        ).fetchone()["done_at"]
    assert kept == first  # a day already done keeps its time
    db.set_days_done(sid, 2, {7})
    assert (db.latest_plan(sid)["week_no"], db.latest_plan(sid)["days_done"]) == (2, 1)
    db.delete_student("P9")  # cascades to plan_progress too
    with db.tx() as c:
        assert c.execute("SELECT COUNT(*) FROM plan_progress").fetchone()[0] == 0
