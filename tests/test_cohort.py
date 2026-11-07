"""piq/cohort.py (pure cohort analytics, the readiness report) and the faculty chart builders."""

import csv
import io
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from piq import charts, cohort
from piq.config import NEARLY_READY_AT, READY_AT


@dataclass
class S:
    id: int
    usn: str
    name: str
    stream: str
    target_role: str = "Data Analyst"
    department: str | None = "Computer Science & IT"
    created_at: datetime = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass
class R:
    student_id: int
    match_percentage: float
    missing_skills: list[str]
    matched_skills: list[str] = field(default_factory=list)


@dataclass
class Q:
    student_id: int
    stream: str
    score: int
    total_questions: int
    timestamp: datetime
    domain: str = "d"


@dataclass
class V:
    student_id: int
    rubric_score: int
    verbal_clarity_score: float
    relevance_score: float
    timestamp: datetime
    proctor_flags: list[str] = field(default_factory=list)
    role: str = "r"


@dataclass
class P:
    student_id: int
    week_number: int
    completed_tasks: list[str]
    plan_data: dict = field(default_factory=dict)


@dataclass
class Snap:
    students: list
    latest_resumes: dict
    plans: list
    quiz_attempts: list
    interviews: list


def _day(d: int) -> datetime:
    return datetime(2026, 11, d, 10, tzinfo=UTC)


@pytest.fixture
def snap() -> Snap:
    students = [
        S(1, "ENG001", "Asha", "Engineering"),
        S(2, "COM001", "=HYPERLINK(1)", "Commerce"),
        S(3, "LAW001", "Nobody yet", "Law"),
    ]
    return Snap(
        students=students,
        latest_resumes={1: R(1, 80.0, ["SQL", "Python"]), 2: R(2, 40.0, ["SQL", "GST"])},
        plans=[P(1, 1, ["d1:0", "d2:0"]), P(1, 2, ["d1:0"])],
        quiz_attempts=[
            Q(1, "Engineering", 8, 10, _day(2)),  # Monday 2 Nov
            Q(1, "Engineering", 9, 10, _day(10)),
            Q(2, "Commerce", 2, 5, _day(3)),
        ],
        interviews=[V(1, 12, 4, 4, _day(4), ["Answer is very brief."]), V(2, 6, 2, 2, _day(5))],
    )


def test_readiness_weights_only_what_was_done():
    assert cohort.readiness(None, None, None) is None
    assert cohort.readiness(80, None, None) == 80
    # quiz 0.4 x 50 + voice 0.3 x 100 over weight 0.7
    assert cohort.readiness(None, 50, 15) == pytest.approx(round((20 + 30) / 0.7, 1))


@pytest.mark.parametrize(
    ("score", "band"),
    [
        (None, "Not assessed"),
        (READY_AT, "Ready"),
        (NEARLY_READY_AT, "Nearly ready"),
        (10, "Needs work"),
    ],
)
def test_bands(score, band):
    assert cohort.band(score) == band


def test_student_rows(snap):
    rows = {r.usn: r for r in cohort.student_rows(snap)}
    eng = rows["ENG001"]
    assert (eng.quizzes, eng.quiz_average, eng.voice_sessions, eng.rubric_average) == (
        2,
        85.0,
        1,
        12,
    )
    assert (eng.plans, eng.tasks_done, eng.proctor_flags) == (2, 3, 1)
    assert eng.readiness == cohort.readiness(80.0, 85.0, 12) and eng.band == "Ready"
    assert eng.last_active == _day(10)
    nobody = rows["LAW001"]
    assert nobody.readiness is None and nobody.band == "Not assessed" and nobody.last_active is None


def test_stream_summaries_and_takeaway(snap):
    rows = cohort.student_rows(snap)
    summaries = {s.stream: s for s in cohort.stream_summaries(rows)}
    assert set(summaries) == {"Commerce", "Engineering", "Law"}
    assert summaries["Law"].readiness is None and summaries["Law"].bands == {"Not assessed": 1}
    text = cohort.streams_takeaway(list(summaries.values()))
    assert text.startswith("Engineering leads at") and "Commerce trails at" in text
    assert [s for s, *_ in cohort.chart_streams(list(summaries.values()))] == [
        "Commerce",
        "Engineering",
    ]


def test_filters_by_stream(snap):
    assert cohort.quiz_scores(snap, "Commerce") == [40.0]
    assert sorted(cohort.quiz_scores(snap)) == [40.0, 80.0, 90.0]
    assert cohort.rubric_totals(snap, "Engineering") == [12]
    assert cohort.rubric_breakdown(snap, "Law") == {}
    parts = cohort.rubric_breakdown(snap)
    assert parts == {
        "Content knowledge": 3.0,
        "Clarity and structure (STAR)": 3.0,
        "Confidence and demeanour": 3.0,  # (12-4-4 + 6-2-2) / 2
    }


def test_skill_gaps_count_students_and_break_ties_by_name(snap):
    rows = cohort.student_rows(snap)
    assert cohort.skill_gaps(rows) == [("SQL", 2), ("GST", 1), ("Python", 1)]
    assert (
        cohort.gaps_takeaway(cohort.skill_gaps(rows), 2)
        == "SQL is missing for 2 of 2 scanned students"
    )


def test_weekly_trend_groups_by_monday(snap):
    trend = cohort.weekly_quiz_trend(snap)
    assert [(w.isoformat(), avg, n) for w, avg, n in trend] == [
        ("2026-11-02", 60.0, 2),
        ("2026-11-09", 90.0, 1),
    ]


def test_report_csv_is_excel_safe(snap):
    data = cohort.report_csv(cohort.student_rows(snap))
    assert data.startswith(b"\xef\xbb\xbf")  # BOM: Excel reads UTF-8 names correctly
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    header, body = rows[0], rows[1:]
    assert header[0] == "USN" and "Readiness (/100)" in header and len(body) == 3
    by_usn = {r[0]: dict(zip(header, r, strict=True)) for r in body}
    assert by_usn["COM001"]["Name"] == "'=HYPERLINK(1)"  # never a live formula
    assert by_usn["LAW001"]["Readiness (/100)"] == "" and by_usn["LAW001"]["Band"] == "Not assessed"
    assert by_usn["ENG001"]["Missing skills"] == "SQL; Python"


# --- faculty chart builders ------------------------------------------------------------------


def test_histogram_bands_include_the_top():
    assert charts.histogram_bands([0, 9.9, 10, 100], top=100, step=10)[0] == ("0-10", 2)
    assert charts.histogram_bands([0, 9.9, 10, 100], top=100, step=10)[-1] == ("90-100", 1)
    bands = charts.histogram_bands([0, 15, 15, 7], top=15, step=1)
    assert len(bands) == 16 and bands[15] == ("15", 2) and bands[7] == ("7", 1)


def _encoding(chart) -> dict:
    spec = chart.to_dict(validate=False)
    layer = spec.get("layer", [spec])[0]
    return layer["encoding"]


def test_label_bars_carry_values_tooltips_and_hover():
    chart = charts.stream_readiness([("Law", 3, 48.0, "x"), ("Commerce", 2, 72.0, "y")])
    spec = chart.to_dict(validate=False)
    enc = spec["encoding"]
    assert enc["y"]["sort"] == ["Commerce  72", "Law  48"]  # best first, value in the label
    assert enc["x"]["scale"]["domain"] == [0, 100]
    assert {t["field"] for t in enc["tooltip"]} == {"stream", "students", "readiness", "detail"}
    assert "condition" in enc["opacity"] and spec["params"][0]["select"]["on"] == "pointerover"
    assert spec["mark"]["color"] == charts.BRAND_COLOR


def test_rubric_and_gap_bars():
    enc = _encoding(charts.rubric_breakdown({"Content knowledge": 3.5}))
    assert enc["x"]["scale"]["domain"] == [0, 5]
    enc = _encoding(charts.gap_bars([("SQL", 4)], students=8))
    assert enc["x"]["scale"]["domain"] == [0, 8]
    assert any(t.get("format") == ".0%" for t in enc["tooltip"])


def test_specs_are_plain_and_cached():
    a = charts.histogram_spec([10.0, 20.0], top=100, step=10, noun="Score")
    b = charts.histogram_spec([10.0, 20.0], top=100, step=10, noun="Score")
    assert a == b and a is not b
    assert charts.cohort_trend_spec([("02 Nov", 60.0, 2), ("09 Nov", 90.0, 1)])["layer"]
