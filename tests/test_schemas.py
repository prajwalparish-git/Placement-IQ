import pytest
from pydantic import ValidationError

from piq.schemas import DayPlan, Question
from tests import factories as f

VALID_Q = {
    "text": "What is a page fault?",
    "options": ["a", "b", "c", "d"],
    "correct_index": 0,
    "explanation": "e",
    "bloom_level": "remember",
}


def test_bloom_level_is_normalised():
    assert f.question(bloom="  Apply ").bloom_level == "apply"


@pytest.mark.parametrize(
    "bad",
    [
        {"options": ["a", "b", "c"]},
        {"options": ["a", "b", "c", "d", "e"]},
        {"correct_index": 4},
        {"correct_index": -1},
        {"text": "short"},
        {"bloom_level": "create"},
    ],
)
def test_question_rejects_invalid_fields(bad):
    with pytest.raises(ValidationError):
        Question(**(VALID_Q | bad))


def test_plan_needs_exactly_seven_days_and_bounded_minutes():
    with pytest.raises(ValidationError):
        f.plan(topics=("OS",) * 6, minutes=(60,) * 6)
    with pytest.raises(ValidationError):
        f.plan(minutes=(60,) * 6 + (300,))
    with pytest.raises(ValidationError):
        DayPlan(day=1, topic="Maths", subtopics=["a", "b"], duration_min=60, practice_goal="g")
    with pytest.raises(ValidationError):
        DayPlan(day=8, topic="OS", subtopics=["a", "b"], duration_min=60, practice_goal="g")


def test_minutes_by_topic_sums_per_topic():
    p = f.plan(
        topics=("OS", "OS", "DBMS", "CN", "CN", "CN", "DSA"),
        minutes=(60, 90, 30, 30, 30, 30, 240),
    )
    assert p.minutes_by_topic() == {"OS": 150, "DBMS": 30, "CN": 90, "DSA": 240}


def test_answer_evaluation_bounds_and_overall():
    ev = f.evaluation(relevance=5, depth=4, structure=3, clarity=2)
    assert ev.overall == 3.5
    assert ev.scores == {"relevance": 5, "depth": 4, "structure": 3, "clarity": 2}
    with pytest.raises(ValidationError):
        f.evaluation(depth=6)
