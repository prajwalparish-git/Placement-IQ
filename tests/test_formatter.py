import pytest

from piq import formatter
from tests import factories as f


def test_profile_md_shows_score_and_handles_empty_sections():
    md = formatter.profile_md(f.profile(projects=[], internships=[]))
    assert "**Readiness:** 50/100 (2 of 4 required skills evidenced)" in md
    assert md.count("_none_") == 2


def test_plan_table_is_ordered_by_day():
    p = f.plan()
    p.days.reverse()
    df = formatter.plan_table(p)
    assert list(df.index) == list(range(1, 8))
    assert list(df.columns) == ["Topic", "Subtopics", "Minutes", "Goal"]


def test_plan_minutes_has_every_topic_and_one_column_per_week():
    w1 = f.plan(week=1)
    w2 = f.plan(week=2, topics=("DBMS",) * 7)
    df = formatter.plan_minutes([w1, w2])
    assert list(df.columns) == ["Week 1", "Week 2"] and len(df) == 6
    assert (df.loc["OS", "Week 1"], df.loc["OS", "Week 2"], df.loc["DBMS", "Week 2"]) == (
        420,
        0,
        420,
    )


def test_quiz_review_marks_right_wrong_and_unanswered():
    q = f.quiz(n=3)
    md = formatter.quiz_review_md(q, [q.questions[0].correct_index, None, 3])
    assert md.count("✅") == 1 and md.count("❌") == 2
    assert "_no answer_" in md and md.count("Correct:") == 2


def test_quiz_review_requires_one_answer_per_question():
    with pytest.raises(ValueError):
        formatter.quiz_review_md(f.quiz(n=2), [0])


def test_evaluation_md_and_small_labels():
    md = formatter.evaluation_md(f.evaluation(relevance=5, depth=4, structure=3, clarity=2))
    assert md.startswith("**Overall 3.5/5** — Relevance 5/5 · Depth 4/5")
    assert formatter.score_line(66.7, "OS", "hard") == (
        "**OS: 67%** — next suggested difficulty: **hard**"
    )


def test_weakness_table_sorted_desc():
    df = formatter.weakness_table({"OS": 0.2, "DBMS": 0.9, "CN": 0.5})
    assert list(df.index) == ["DBMS", "CN", "OS"]


def test_score_trend_pivots_by_attempt_and_handles_empty():
    assert formatter.score_trend([]).empty
    rows = [
        {"attempted_at": "t1", "topic": "OS", "difficulty": "easy", "score_pct": 40.0},
        {"attempted_at": "t2", "topic": "DBMS", "difficulty": "easy", "score_pct": 60.0},
        {"attempted_at": "t3", "topic": "OS", "difficulty": "easy", "score_pct": 80.0},
    ]
    df = formatter.score_trend(rows)
    assert df.loc[2, "OS"] == 80.0 and df.loc[1, "DBMS"] == 60.0
