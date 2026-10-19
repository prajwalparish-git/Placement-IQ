from html import escape

import pytest

from piq import formatter
from tests import factories as f


def test_profile_pieces_show_counts_and_handle_empty_sections():
    p = f.profile(projects=[], internships=[])
    assert formatter.readiness_summary(p) == (
        "2 of the 4 skills Java Backend Developer needs are on the resume."
    )
    assert formatter.skill_chips(["Java"], present=True) == (
        ":green-badge[:material/check_circle: Java]"
    )
    assert formatter.skill_chips(["Docker"], present=False) == (
        ":gray-badge[:material/radio_button_unchecked: Docker]"
    )
    assert formatter.list_md([], "None listed.") == ":gray[None listed.]"
    assert formatter.fixes_md(["Add numbers."]) == (
        ":gray[:material/check_box_outline_blank:] Add numbers\\."
    )
    assert formatter.fixes_md([]) == ":gray[Nothing to fix.]"


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


def test_plan_summary_totals_the_week_and_names_its_main_topic():
    plan = f.plan(topics=("OS",) * 4 + ("DBMS",) * 3, minutes=(90,) * 7)
    assert formatter.plan_summary(plan) == "630 minutes over 7 days, most of them on OS."


def test_plan_days_html_lists_every_day_in_order_with_its_topic_chip():
    plan = f.plan(topics=("DBMS", "OS") * 3 + ("CN",), minutes=tuple(range(60, 130, 10)))
    plan.days.reverse()
    html = formatter.plan_days_html(plan)
    assert html.startswith('<ol class="piq-days" aria-label="Week 1, day by day">')
    assert html.count('<li class="piq-day">') == 7
    days = [html.index(f">Day {n}<") for n in range(1, 8)]
    assert days == sorted(days)  # day 1 first, whatever order the model returned
    assert formatter.topic_chip_html("DBMS") in html and "120 min" in html
    assert "a · b" in html and "Goal: g" in html


@pytest.mark.parametrize("hostile", ["<script>alert(1)</script>", '"><img src=x onerror=alert(1)>'])
def test_plan_days_html_escapes_model_text(hostile):
    plan = f.plan()
    day = plan.days[0].model_copy(update={"subtopics": [hostile, "b"], "practice_goal": hostile})
    html = formatter.plan_days_html(plan.model_copy(update={"days": [day, *plan.days[1:]]}))
    assert hostile not in html and escape(hostile) in html


@pytest.mark.parametrize(
    ("before", "after", "headline"),
    [
        ({"DBMS": 360, "OS": 300}, {"OS": 840}, "OS now gets the most minutes"),
        (
            {"OS": 600, "DBMS": 360},
            {"OS": 840},
            "OS gets 240 more minutes and DBMS 360 fewer than in week 3",
        ),
        ({"OS": 600}, {"OS": 600, "CN": 60}, "CN gets 60 more minutes than in week 3"),
        ({"OS": 600, "DBMS": 360}, {"OS": 600}, "DBMS gets 360 fewer minutes than in week 3"),
        ({"OS": 600}, {"OS": 600}, "The same minutes per topic as in week 3"),
    ],
)
def test_minutes_shift_headline_states_the_change(before, after, headline):
    assert formatter.minutes_shift_headline(before, after, 3) == headline


def test_minutes_shift_alt_reads_every_topic():
    alt = formatter.minutes_shift_alt({"OS": 600}, {"OS": 840, "DBMS": 120}, (3, 4))
    assert alt.startswith("Minutes per topic, week 3 to week 4: Aptitude 0 to 0, DBMS 0 to 120")
    assert "OS 600 to 840" in alt


def test_weakness_source_explains_both_inputs():
    text = formatter.weakness_source()
    assert "last three quizzes" in text and "70%" in text and "40%" in text


def test_quiz_review_marks_right_wrong_and_unanswered():
    q = f.quiz(n=3)
    md = formatter.quiz_review_md(q, [q.questions[0].correct_index, None, 3])
    assert md.count("✅") == 1 and md.count("❌") == 2
    assert "_no answer_" in md and md.count("Correct:") == 2


HOSTILE = ["*p", "__init__", "![x](http://example.com/a.png)", "<script>alert(1)</script>"]


@pytest.mark.parametrize(
    ("raw", "escaped"),
    [
        ("*p", r"\*p"),
        ("__init__", r"\_\_init\_\_"),
        ("![x](http://example.com/a.png)", r"\!\[x\]\(http://example\.com/a\.png\)"),
        ("<script>alert(1)</script>", r"\<script\>alert\(1\)\</script\>"),
        ("Costs $5 to $10", r"Costs \$5 to \$10"),
        ("# 1. ---", r"\# 1\. \-\-\-"),
    ],
)
def test_md_escape_shows_text_literally(raw, escaped):
    assert formatter.md_escape(raw) == escaped


def test_md_escape_keeps_code_readable():
    text = "Call `obj.__init__()` first.\n```python\nx = a*b\n```\nUnclosed `tick"
    assert formatter.md_escape(text) == (
        "Call `obj.__init__()` first\\.\n```python\nx = a*b\n```\nUnclosed \\`tick"
    )


def test_topic_chip_follows_the_scheme_and_escapes_its_name():
    chip = formatter.topic_chip_html("OS")
    assert "light-dark(#A55582, #DF8BB9)" in chip and chip.endswith(">OS</span>")
    hostile = formatter.topic_chip_html("<script>alert(1)</script>")
    assert "<script>" not in hostile and "&lt;script&gt;alert(1)&lt;/script&gt;" in hostile
    assert "currentColor" in hostile  # unknown topics get a neutral dot


def test_status_pairs_an_icon_with_escaped_words():
    assert set(formatter.STATUS) == {"done", "todo", "warning", "error", "info"}
    assert formatter.status_md("done", "First *quiz*") == (
        ":green-badge[:material/check_circle: First \\*quiz\\*]"
    )


@pytest.mark.parametrize(
    ("reason", "shown"),
    [
        ("critic rejected quiz: question 0: options are not distinct", "critic rejected quiz: Q1:"),
        ("quiz: rejected after retries: question 3: a; question 11: b", "Q4: a; Q12: b"),
        ('critic rejected interviewer: question already asked: "x"', "question already asked"),
    ],
)
def test_critic_text_numbers_questions_like_the_quiz(reason, shown):
    assert shown in formatter.critic_text(reason)
    assert "question 0" not in formatter.critic_text(reason)


def test_critic_text_is_escaped():
    assert (
        formatter.critic_text("question 0: duplicate of '__init__'")
        == r"Q1: duplicate of '\_\_init\_\_'"
    )


@pytest.mark.parametrize("hostile", HOSTILE)
def test_markdown_builders_escape_every_dynamic_value(hostile):
    safe = formatter.md_escape(hostile)
    q = f.question(text=f"Explain {hostile} in one line", options=(hostile, "b", "c", "d"))
    quiz = f.quiz(n=1).model_copy(
        update={"questions": [q.model_copy(update={"explanation": hostile})]}
    )
    ev = f.evaluation().model_copy(
        update={"strengths": [hostile], "improvements": [hostile], "model_answer": hostile}
    )
    profile = f.profile(name=hostile, projects=[hostile], resume_feedback=[hostile])
    for md in (
        formatter.readiness_summary(f.profile(role=hostile)),
        formatter.skill_chips([hostile], present=False),
        formatter.list_md(profile.projects, "none"),
        formatter.fixes_md(profile.resume_feedback),
        formatter.quiz_review_md(quiz, [1]),
        formatter.evaluation_md(ev),
        formatter.results_caption(f.eval_summary(stopped_early=hostile)),
    ):
        assert safe in md
        assert hostile not in md.replace(safe, "")


def test_quiz_review_requires_one_answer_per_question():
    with pytest.raises(ValueError):
        formatter.quiz_review_md(f.quiz(n=2), [0])


def test_evaluation_md_and_small_labels():
    md = formatter.evaluation_md(f.evaluation(relevance=5, depth=4, structure=3, clarity=2))
    assert md.startswith("**Overall 3.5/5** — Relevance 5/5 · Depth 4/5")
    assert formatter.score_line(66.7, "OS", "hard") == (
        "**OS: 67%** — next suggested difficulty: **hard**"
    )


def test_score_trend_pivots_by_attempt_and_handles_empty():
    assert formatter.score_trend([]).empty
    rows = [
        {"attempted_at": "t1", "topic": "OS", "difficulty": "easy", "score_pct": 40.0},
        {"attempted_at": "t2", "topic": "DBMS", "difficulty": "easy", "score_pct": 60.0},
        {"attempted_at": "t3", "topic": "OS", "difficulty": "easy", "score_pct": 80.0},
    ]
    df = formatter.score_trend(rows)
    assert df.loc[2, "OS"] == 80.0 and df.loc[1, "DBMS"] == 60.0


def test_results_table_includes_only_measured_metrics():
    import pandas as pd

    t = formatter.results_table(f.eval_summary())
    assert list(t.columns) == ["Baseline", "PlacementIQ"]
    assert t.loc["Plan valid rate", "PlacementIQ"] == 1.0
    assert pd.isna(t.loc["Interview follow-up relevance", "Baseline"])
    assert t.index[-1] == formatter.ATTEMPTS
    minimal = formatter.results_table(f.eval_summary(consecutive=None, interviews=None))
    assert len(minimal) == 4  # no consecutive or interview rows


def test_results_markdown_and_caption():
    md = formatter.results_md(f.eval_summary())
    assert "| Plan valid rate | 0.40 | 1.00 |" in md
    assert "| Interview follow-up relevance | — | 0.90 |" in md
    assert "## Agent cost during the evaluation" in md and "not meaningful" not in md
    assert formatter.results_caption(f.eval_summary()) == "live run · 20 cases · 1 failed"
    stopped = f.eval_summary(stopped_early="c07: limit", errors=0)
    assert formatter.results_caption(stopped).endswith(
        "stopped early (c07: limit); continue with --resume"
    )
    assert "not meaningful" in formatter.results_md(f.eval_summary(mode="mock"))


def test_results_note_names_the_duplicate_rate_only_with_that_row():
    assert "except the duplicate rate" in formatter.results_note(f.eval_summary())
    note = formatter.results_note(f.eval_summary(consecutive=None))
    assert "duplicate" not in note and note.startswith("Rates run from 0 to 1; higher is better.")


def test_results_svg_is_well_formed_with_one_bar_per_measured_value():
    import xml.etree.ElementTree as ET

    svg = formatter.results_svg(formatter.results_table(f.eval_summary()))
    rects = ET.fromstring(svg).findall("{http://www.w3.org/2000/svg}rect")
    # background + 2 legend swatches + 2 bars for 4 metrics + 1 bar (baseline not measured)
    assert len(rects) == 1 + 2 + 2 * 4 + 1
    assert "not measured" in svg and formatter.ATTEMPTS not in svg


def test_trail_tells_the_critic_loop_in_order():
    events = [
        "quiz: generated (attempt 1)",
        "critic rejected quiz: question 0: options are not distinct; question 2: duplicate",
        "quiz: generated (attempt 2)",
        "critic approved quiz",
    ]
    steps = formatter.trail_steps(events)
    assert [s.title for s in steps] == [
        "Generated the quiz",
        "Critic rejected the quiz",
        "Regenerated the quiz",
        "Critic approved the quiz",
    ]
    assert steps[1].reasons == ("Q1: options are not distinct", "Q3: duplicate")
    assert [s.failed for s in steps] == [False, True, False, False]
    assert (steps[0].note, steps[2].note, steps[3].note) == (
        "Attempt 1",
        "Attempt 2",
        "Passed every check.",
    )


def test_trail_collapses_repeats_and_explains_a_stop():
    reason = 'critic rejected interviewer: question already asked: "Tell me about yourself"'
    events = [
        "interviewer: generated (attempt 1)",
        reason,
        "interviewer: generated (attempt 2)",
        reason,
        "failed: interviewer: rejected after retries: question already asked: x",
    ]
    steps = formatter.trail_steps(events)
    assert steps[1].reasons and steps[3].reasons == () and steps[3].note == "Same reason as before."
    assert steps[1].title == "Critic rejected the next question"
    assert (steps[4].title, steps[4].note, steps[4].failed) == (
        "Stopped",
        "The critic rejected every attempt.",
        True,
    )
    [stop] = formatter.trail_steps(["failed: Groq API error: __init__ <b>"])
    assert stop.reasons == (r"Groq API error: \_\_init\_\_ \<b\>",)


def test_relative_day_uses_the_students_calendar():
    from datetime import UTC, datetime

    now = datetime(2026, 10, 19, 6, 0, tzinfo=UTC)  # 11:30 in India
    assert formatter.relative_day(datetime(2026, 10, 18, 18, 45, tzinfo=UTC), now) == "Today"
    assert formatter.relative_day(datetime(2026, 10, 18, 18, 0, tzinfo=UTC), now) == "Yesterday"
    assert formatter.relative_day(datetime(2026, 10, 15, 9, 0, tzinfo=UTC), now) == "4 days ago"
    assert formatter.relative_day(datetime(2026, 10, 2, 9, 0, tzinfo=UTC), now) == "2 Oct"


def test_weakness_headline_and_alt_text_state_the_takeaway():
    calm = {"OS": 0.43, "DBMS": 0.4, "OOP": 0.13}
    assert formatter.weakness_headline(calm) == "No weak topics; OS has the most room to grow"
    assert formatter.weakness_headline({**calm, "DBMS": 0.7}) == "DBMS is your weakest topic"
    assert (
        formatter.weakness_alt(calm)
        == "Weakness by topic, weakest first: OS 43%, DBMS 40%, OOP 13%"
    )
