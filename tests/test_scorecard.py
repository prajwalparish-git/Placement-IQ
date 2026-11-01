"""Evaluation scorecard: each parameter's formula, its 0-10 score, ratings and the overall."""

import pytest

from piq import scorecard
from tests import factories as f


def _q(system: str, marked: int, options: tuple[str, ...], label: str = "") -> dict:
    return {
        "system": system,
        "marked": str(marked),
        "options": " || ".join(options),
        "label_valid (y/n)": label,
    }


@pytest.mark.parametrize(
    ("score", "word", "state"),
    [
        (10.0, "Excellent", "done"),
        (9.0, "Excellent", "done"),
        (7.5, "Good", "done"),
        (5.0, "Fair", "warning"),
        (4.9, "Needs work", "error"),
        (None, "Not measured", "todo"),
    ],
)
def test_rating_thresholds(score, word, state):
    assert scorecard.rating(score) == (word, state)


def test_answer_key_balance_is_1_when_even_and_0_when_one_position():
    even = [_q("placementiq", i % 4, ("a", "b", "c", "d")) for i in range(8)]
    one = [_q("baseline", 2, ("a", "b", "c", "d")) for _ in range(8)]
    assert scorecard.answer_key_balance(even, "placementiq") == 1.0
    assert scorecard.answer_key_balance(one, "baseline") == 0.0
    assert scorecard.answer_key_balance([], "baseline") is None


def test_longest_answer_cue_counts_only_a_strictly_longest_correct_option():
    rows = [
        _q("baseline", 0, ("the longest option", "b", "c", "d")),  # cue
        _q("baseline", 1, ("a", "bb", "cc", "d")),  # tied for longest: no cue
        _q("baseline", 2, ("aaaa", "b", "c", "d")),  # correct is short
        _q("baseline", 0, ("a", "b")),  # malformed: skipped
    ]
    assert scorecard.longest_answer_cue(rows, "baseline") == round(1 / 3, 3)


def test_human_validity_needs_labels():
    rows = [_q("placementiq", 0, ("a", "b", "c", "d"), lab) for lab in ("y", "y", "n", "")]
    assert scorecard.human_validity(rows, "placementiq") == round(2 / 3, 3)
    assert scorecard.human_validity(rows, "baseline") is None


def test_first_draft_validity_counts_cases_valid_on_attempt_one():
    cases = [
        {"system": "placementiq", "quiz_valid": "True", "quiz_attempts": "1"},
        {"system": "placementiq", "quiz_valid": "True", "quiz_attempts": "2"},
        {"system": "placementiq", "quiz_valid": "False", "quiz_attempts": "1"},
        {"system": "baseline", "quiz_valid": "True", "quiz_attempts": "1"},
    ]
    assert scorecard.first_draft_validity(cases, "quiz") == round(1 / 3, 3)
    assert scorecard.first_draft_validity([], "quiz") is None


def test_followup_precision_is_the_judges_agreement_with_the_flags():
    rows = [
        {"flagged_followup": "True", "references_answer": "True"},
        {"flagged_followup": "True", "references_answer": "False"},
        {"flagged_followup": "False", "references_answer": "True"},
    ]
    assert scorecard.followup_precision(rows) == 0.5


def test_cost_per_valid_quiz_counts_critic_share_retries_and_validity():
    summary = {
        "baseline": {"quiz_valid_rate": 0.5},
        "placementiq": {"quiz_valid_rate": 1.0, "avg_quiz_attempts": 2.0},
        "agent_stats": [
            {"agent_name": "baseline_quiz", "calls": 10, "avg_tokens": 1000, "failures": 0},
            {"agent_name": "quiz", "calls": 10, "avg_tokens": 1000, "failures": 1},
            {"agent_name": "critic", "calls": 20, "avg_tokens": 500, "failures": 0},
        ],
    }
    cost = scorecard.cost_per_valid_quiz(summary, "avg_tokens")
    assert cost["baseline"] == 2000  # half its quizzes are thrown away
    assert cost["placementiq"] == (1000 + 2 * 500) * 2.0  # two critic calls per quiz call
    assert scorecard.call_success(summary, scorecard.PIQ_AGENTS) == round(1 - 1 / 30, 3)


def test_build_scores_every_measured_parameter_and_skips_the_rest():
    card = scorecard.build(f.eval_summary())
    keys = [p.key for p in card.parameters]
    assert {"plan_valid", "weak_focus", "quiz_valid", "novelty", "followup", "success"} <= set(keys)
    assert "key_balance" not in keys and "human_valid" not in keys  # no questions.csv
    for p in card.parameters:
        assert p.what and p.method and p.group
        for score in (p.baseline_score, p.placementiq_score):
            assert score is None or 0 <= score <= 10
    followup = next(p for p in card.parameters if p.key == "followup")
    assert followup.baseline is None and followup.note  # the baseline has no interviewer


def test_weak_focus_scores_the_share_between_25_and_75_percent():
    summary = f.eval_summary()
    summary["baseline"]["avg_weak_share"] = 0.5
    summary["placementiq"]["avg_weak_share"] = 0.9
    focus = next(p for p in scorecard.build(summary).parameters if p.key == "weak_focus")
    assert (focus.baseline_score, focus.placementiq_score) == (5.0, 10.0)  # capped at 10


def test_overall_is_a_weighted_mean_and_head_to_head_drops_one_sided_parameters():
    def param(key, b, p, w):
        return scorecard.Parameter(key, key, "g", "w", "m", "rate", True, w, b, p, b, p)

    card = scorecard.Scorecard(
        [param("a", 4.0, 8.0, 2.0), param("b", 10.0, 10.0, 1.0), param("c", None, 2.0, 1.0)]
    )
    assert card.overall("baseline") == round((8 + 10) / 3, 1)
    assert card.overall("placementiq") == round((16 + 10 + 2) / 4, 1)
    assert card.overall("placementiq", head_to_head=True) == round((16 + 10) / 3, 1)
    assert card.groups() == ["g"]
