"""piq/offline.py, Layer 3's last tier: answers built from data/ that pass the same schemas,
come from the question bank where it can, and never look like mock output."""

import json

import pytest

from piq import offline
from piq.config import INTERVIEW_TIPS
from piq.schemas import AnswerEvaluation, QuizSet, WeeklyPlan


def _quiz(**ctx) -> QuizSet:
    base = {"topic": "DBMS", "difficulty": "easy", "count": 3, "previous": []}
    return QuizSet.model_validate(offline.respond("quiz", base | ctx))


def test_quiz_questions_come_from_the_bank(bank):
    quiz = _quiz(count=3)
    assert len(quiz.questions) == 3
    assert all(q.text.startswith("Bank question number") for q in quiz.questions)


def test_quiz_never_repeats_an_asked_question_and_reaches_for_other_difficulties(bank):
    first = _quiz(count=4)
    asked = [q.text for q in first.questions]
    second = _quiz(count=4, previous=asked)
    assert not {q.text for q in second.questions} & set(asked)


def test_quiz_without_a_bank_still_answers_without_mock_labels():
    quiz = _quiz(count=2)
    text = json.dumps(quiz.model_dump())
    assert len(quiz.questions) == 2 and "[mock]" not in text
    assert len({tuple(q.options) for q in quiz.questions}) >= 1
    assert all(len(set(q.options)) == 4 for q in quiz.questions)  # no deliberate flaw


def test_evaluator_coaches_with_the_fixed_tips():
    ev = AnswerEvaluation.model_validate(offline.respond("evaluator", {"answer": "I like coding"}))
    assert set(ev.improvements) <= set(INTERVIEW_TIPS.values()) and ev.improvements
    assert "[mock]" not in json.dumps(ev.model_dump())
    strong = offline.respond(
        "evaluator",
        {
            "answer": "Situation: the nightly job failed. Task: fix it. Action: I profiled it "
            "and batched inserts. Result: it ran in 6 minutes instead of 40, and the team kept "
            "the approach for the other reports we owned over the next term."
        },
    )
    assert strong["structure"] == 5 and any("figure" in s for s in strong["strengths"])


def test_planner_explains_itself_plainly():
    plan = WeeklyPlan.model_validate(
        offline.respond("planner", {"week_no": 2, "weakness": {"OS": 0.8, "DBMS": 0.6, "CN": 0.1}})
    )
    assert "[mock]" not in plan.rationale and plan.rationale.startswith("The weakest topics")
    assert plan.days[0].topic == "OS"


def test_unknown_agents_raise_so_agents_package_falls_back():
    with pytest.raises(KeyError):
        offline.respond("no-such-agent", {})
