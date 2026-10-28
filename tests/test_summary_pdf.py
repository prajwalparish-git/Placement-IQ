"""The summary PDF's page: numbers from summary.json, nothing fetched, every value escaped."""

import pytest

from scripts import summary_pdf

TOPICS = ["CN", "DBMS", "DSA", "OS"]


def _summary(**changes: object) -> dict:
    summary = {
        "mode": "live",
        "baseline": {"cases": 20, "plan_valid_rate": 0.2, "quiz_valid_rate": 0.65},
        "placementiq": {"cases": 20, "plan_valid_rate": 1.0, "quiz_valid_rate": 1.0},
        "interviews": {"cases": 20, "followup_relevance": 0.9},
        "consecutive": {
            "quizzes_per_topic": 5,
            "baseline_duplicate_rate": 0.053,
            "placementiq_duplicate_rate": 0.0,
            "topics": ["CN", "DBMS", "DSA"],
        },
    }
    return summary | changes


def _page(**changes: object) -> str:
    """The page with whitespace collapsed, so assertions ignore where the source wraps."""
    return " ".join(summary_pdf.build_html(_summary(**changes), TOPICS).split())


def test_quotes_the_evaluation_numbers():
    page = _page()
    assert "On 20 frozen evaluation cases" in page
    assert "valid plans in 100% of cases (baseline 20%)" in page
    assert "plan validity 100% vs 20%, quiz validity 100% vs 65%" in page
    assert "(90% relevant in the evaluation)" in page
    assert "0% of questions repeated (baseline 5.3%)" in page


def test_facts_come_from_the_code():
    from piq.agents import roles

    page = _page()
    assert f"one of {summary_pdf._words(len(roles()))} roles" in page
    assert "five questions never repeated" in page
    assert "HR, technical and project rounds" in page
    assert "scored on relevance, depth, structure and clarity" in page


def test_names_the_topics_when_the_duplicate_run_stopped_early():
    assert "per topic, measured for CN, DBMS and DSA," in _page()
    every = _summary()["consecutive"] | {"topics": TOPICS}
    assert "measured for" not in _page(consecutive=every)


def test_leaves_out_what_was_not_measured():
    page = _page(interviews=None, consecutive=None)
    assert "relevant in the evaluation" not in page
    assert "questions repeated" not in page
    assert "None" not in page


@pytest.mark.parametrize(
    ("changes", "message"),
    [({"mode": "mock"}, "mock run"), ({"baseline": None}, "both systems")],
)
def test_refuses_a_mock_or_incomplete_summary(changes, message):
    with pytest.raises(SystemExit, match=message):
        _page(**changes)


def test_topic_names_are_escaped():
    hostile = _summary()["consecutive"] | {"topics": ["<script>alert(1)</script>"]}
    page = _page(consecutive=hostile)
    assert "<script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_fonts_and_mark_are_embedded_so_nothing_is_fetched():
    page = _page()
    assert page.count("url(data:font/woff2;base64,") == 2
    assert '<img src="data:image/svg+xml;base64,' in page
    assert "url(http" not in page
    assert 'src="http' not in page


@pytest.mark.parametrize(
    ("rate", "digits", "text"),
    [(0.65, 0, "65%"), (1.0, 0, "100%"), (0.053, 1, "5.3%"), (0.0, 1, "0%"), (0.25, 1, "25%")],
)
def test_percentages_drop_trailing_zeros(rate, digits, text):
    assert summary_pdf._pct(rate, digits) == text
