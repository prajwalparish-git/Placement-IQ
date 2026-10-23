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


def test_plan_csv_has_the_table_columns_and_one_row_per_day():
    rows = formatter.plan_csv(f.plan()).decode("utf-8-sig").splitlines()
    assert rows[0] == "Day,Topic,Subtopics,Minutes,Goal"
    assert len(rows) == 8 and rows[1] == '1,OS,"a, b",60,g'


@pytest.mark.parametrize(
    ("today", "monday"),
    [("2026-10-19", "2026-10-19"), ("2026-10-20", "2026-10-26"), ("2026-10-25", "2026-10-26")],
)
def test_next_monday_is_the_coming_monday(today, monday):
    from datetime import date

    assert formatter.next_monday(date.fromisoformat(today)) == date.fromisoformat(monday)


def _ics(plan, **kw):
    from datetime import UTC, date, datetime, time

    now = datetime(2026, 10, 19, 6, 0, tzinfo=UTC)
    return formatter.plan_ics(plan, date(2026, 10, 26), time(19, 0), now=now, **kw).decode()


def test_plan_ics_is_a_calendar_with_one_event_per_day():
    ics = _ics(f.plan(minutes=(90,) * 7))
    assert ics.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:")
    assert ics.endswith("END:VCALENDAR\r\n")
    assert "\n" not in ics.replace("\r\n", "")  # CRLF line endings only
    assert ics.count("BEGIN:VEVENT") == ics.count("END:VEVENT") == 7
    # 19:00 in India is 13:30 UTC; the event lasts the day's 90 minutes.
    assert "DTSTART:20261026T133000Z\r\nDTEND:20261026T150000Z" in ics
    assert "DTSTART:20261101T133000Z" in ics  # day 7 is six days later
    assert ics.count("DTSTAMP:20261019T060000Z") == 7
    uids = [ln for ln in ics.split("\r\n") if ln.startswith("UID:")]
    assert len(set(uids)) == 7 and uids[0] == "UID:week1-day1-20261026@placementiq"
    assert "SUMMARY:OS: a\\, b" in ics


def test_plan_ics_escapes_text_and_folds_long_lines():
    plan = f.plan()
    goal = "Revise; deadlocks, paging \\ swapping, then " + "practise " * 12 + "with notes"
    day = plan.days[0].model_copy(update={"practice_goal": goal, "subtopics": ["é" * 40, "b"]})
    ics = _ics(plan.model_copy(update={"days": [day, *plan.days[1:]]}))
    lines = ics.split("\r\n")
    assert all(len(ln.encode("utf-8")) <= 75 for ln in lines)  # folded at 75 octets
    unfolded = ics.replace("\r\n ", "")
    assert "Goal: Revise\\; deadlocks\\, paging \\\\ swapping\\, then practise" in unfolded
    assert "SUMMARY:OS: " + "é" * 40 + "\\, b" in unfolded  # no character split by a fold


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


def test_plan_days_html_marks_done_days_in_words():
    html = formatter.plan_days_html(f.plan(), done={2, 5})
    assert html.count('<span class="piq-done">Done</span>') == 2
    day2 = html[html.index(">Day 2<") : html.index(">Day 3<")]
    assert "Done" in day2 and "Done" not in html[: html.index(">Day 2<")]
    assert formatter.days_done_md(4, 3) == (
        ":primary[:material/task_alt:] Week 4: 3 of 7 days done."
    )


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


def test_quiz_review_marks_right_wrong_and_unanswered_with_icon_and_word():
    # Was ✅/❌ only; now an icon, a word and a colour, never colour alone.
    q = f.quiz(n=3)
    right, blank, wrong = formatter.quiz_review(q, [q.questions[0].correct_index, None, 3])
    assert right.startswith(":green-badge[:material/check_circle: Correct] **Q1. ")
    assert blank.startswith(":gray-badge[:material/radio_button_unchecked: Not answered] **Q2. ")
    assert wrong.startswith(":red-badge[:material/error: Wrong] **Q3. ")
    assert "Your answer" not in blank and "Your answer: z" in wrong  # option 3 of w, x, y, z
    assert [b.count("Correct answer:") for b in (right, blank, wrong)] == [0, 1, 1]
    assert all(b.endswith(":gray[e]") for b in (right, blank, wrong))  # the explanation


def test_blanks_md_names_the_unanswered_questions():
    assert formatter.blanks_md([3]).startswith("Q3 has no answer.")
    assert formatter.blanks_md([2, 4, 5]).startswith("Q2, Q4 and Q5 have no answer.")
    assert formatter.blanks_md([1, 2]).endswith("a blank counts as wrong.")


def test_quiz_setup_lines_explain_the_hint_and_the_suggestion():
    assert formatter.topic_option("OS", 0.43) == "OS · 43% weak"
    assert formatter.suggestion_md("CN", None, "medium") == (
        ":gray-badge[:material/recommend: Suggested: medium] No CN quiz yet, so start at medium."
    )
    assert formatter.suggestion_md("OS", (80.0, "medium"), "hard") == (
        ":gray-badge[:material/recommend: Suggested: hard] Your last OS quiz: 80% on medium. "
        "80% or more moves you up a level; under 50%, down."
    )


@pytest.mark.parametrize(
    ("difficulty", "after", "icon"),
    [
        ("easy", "medium", "trending_up"),
        ("hard", "hard", "trending_flat"),
        ("hard", "medium", "trending_down"),
    ],
)
def test_result_md_says_what_the_score_changes(difficulty, after, icon):
    md = formatter.result_md(3, 5, "OS", difficulty, after)
    assert md.startswith(f":primary[:material/{icon}:] 3 of 5 correct")
    assert f"next suggested difficulty is **{after}**" in md and "next week's plan" in md


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
        formatter.usn_taken_md("USN1", hostile, hostile),
        formatter.delete_warning_md("USN1", hostile),
        formatter.skill_chips([hostile], present=False),
        formatter.list_md(profile.projects, "none"),
        formatter.fixes_md(profile.resume_feedback),
        "\n".join(formatter.quiz_review(quiz, [1])),
        formatter.evaluation_md(ev),
        formatter.results_caption(f.eval_summary(stopped_early=hostile)),
    ):
        assert safe in md
        assert hostile not in md.replace(safe, "")


@pytest.mark.parametrize("hostile", ["<script>alert(1)</script>", '"><img src=x onerror=alert(1)>'])
def test_criteria_html_escapes_criterion_names(hostile):
    html = formatter.criteria_html({hostile: 3})
    assert hostile not in html and escape(hostile.title()) in html


def test_quiz_notes_are_plain_markdown_with_every_question():
    from datetime import date

    q = f.quiz(n=3)
    chosen = [q.questions[0].correct_index, None, 3]
    notes = formatter.quiz_notes(q, chosen, 33.3, "easy", date(2026, 10, 20))
    assert notes.startswith("# OS quiz (easy), 20 Oct 2026\n\nScore: 33% (1 of 3 correct).")
    assert notes.count("\n## Q") == 3
    assert "- Your answer (correct): " in notes and "- Your answer: none" in notes
    assert "- Your answer (wrong): z" in notes and notes.count("- Correct answer:") == 2
    assert ":gray[" not in notes and "-badge[" not in notes  # no Streamlit-only syntax


def test_interview_notes_quote_answers_and_list_feedback():
    from datetime import date

    ev = f.evaluation(relevance=4, depth=2).model_copy(update={"strengths": []})
    turns = [("Tell me about yourself?", "I build things.\nMostly in Python.", ev)]
    notes = formatter.interview_notes("HR", turns, date(2026, 10, 20), {"depth": "Add a number."})
    assert notes.startswith("# HR mock interview, 20 Oct 2026\n\nAverage 3.0/5 over 1 questions.")
    assert "## What to work on\n\n- Depth: Add a number." in notes
    assert "> I build things\\.  \n> Mostly in Python\\.  " in notes  # quoted line by line
    assert "Scores: Relevance 4/5 · Depth 2/5 · Structure 3/5 · Clarity 3/5" in notes
    assert "**Strengths**\n- None this time." in notes and ":gray[" not in notes


@pytest.mark.parametrize("hostile", HOSTILE)
def test_notes_escape_every_dynamic_value(hostile):
    from datetime import date

    safe = formatter.md_escape(hostile)
    q = f.question(text=f"Explain {hostile} now", options=(hostile, "b", "c", "d"))
    quiz = f.quiz(n=1).model_copy(
        update={"questions": [q.model_copy(update={"explanation": hostile})]}
    )
    ev = f.evaluation().model_copy(update={"strengths": [hostile], "model_answer": hostile})
    for notes in (
        formatter.quiz_notes(quiz, [1], 0.0, "easy", date(2026, 10, 20)),
        formatter.interview_notes("HR", [(hostile, hostile, ev)], date(2026, 10, 20)),
    ):
        assert safe in notes and hostile not in notes.replace(safe, "")


def test_quiz_review_requires_one_answer_per_question():
    with pytest.raises(ValueError):
        formatter.quiz_review(f.quiz(n=2), [0])


def test_feedback_shows_the_overall_score_then_each_criterion():
    # Was one line ("**Overall 3.5/5** — Relevance 5/5 · ..."); now a title and four bars.
    ev = f.evaluation(relevance=5, depth=4, structure=3, clarity=2)
    assert formatter.feedback_title(ev) == "**Feedback** · 3.5/5 overall"
    html = formatter.criteria_html(ev.scores)
    assert html.count('<div class="piq-criterion">') == 4
    for name, v, width in (("Relevance", 5, 100), ("Depth", 4, 80), ("Clarity", 2, 40)):
        assert f"<span>{name}</span>" in html and f"<span>{v}/5</span>" in html
        assert f'style="width:{width}%"' in html
    assert 'aria-hidden="true"' in html  # the words and number carry the score
    md = formatter.evaluation_md(ev)
    assert md.startswith("**Strengths**  \n- s") and "**Improve**  \n- i" in md and "\n> m" in md
    empty = ev.model_copy(update={"strengths": [], "improvements": []})
    assert "**Strengths**  \n:gray[None this time.]" in formatter.evaluation_md(empty)


def test_a_multi_line_model_answer_keeps_its_lines_in_the_quote():
    answer = "Situation: a slow report.\nTask: speed it up.\n\nResult: 6 minutes, not 40."
    md = formatter.evaluation_md(f.evaluation().model_copy(update={"model_answer": answer}))
    quote = md.split("**Model answer**\n", 1)[1]
    # Each line stays its own line (a hard break), and the blank line still splits paragraphs.
    assert quote == (
        "> Situation: a slow report\\.  \n"
        "> Task: speed it up\\.  \n"
        ">\n"
        "> Result: 6 minutes, not 40\\.  "
    )


def test_session_summary_pieces_show_averages_and_tips():
    html = formatter.criteria_html({"relevance": 3.25, "depth": 2.0})
    assert "<span>3.2/5</span>" in html and 'style="width:65%"' in html  # an average
    assert "<span>2/5</span>" in html and 'style="width:40%"' in html
    averages = {"relevance": 4.2, "depth": 2.1, "structure": 3.0, "clarity": 3.5}
    assert formatter.summary_md(averages, "relevance", "depth") == (
        "Strongest: **Relevance** (4.2/5). Weakest: **Depth** (2.1/5)."
    )
    even = dict.fromkeys(averages, 3.0)
    assert formatter.summary_md(even, "relevance", "relevance") == (
        "Even across all four criteria: 3/5 each."
    )
    assert formatter.tips_md({"depth": "Add a number."}) == "- **Depth:** Add a number."
    assert formatter.tips_md({}).startswith(":gray[No criterion averaged below 3/5.")


def test_interview_questions_say_whether_they_follow_up():
    from piq.schemas import InterviewTurn

    turn = InterviewTurn(
        question="Why *this* role?", intent="probe", is_followup=True, is_final=False
    )
    assert formatter.question_md(turn) == (
        "Why \\*this\\* role?  \n:gray-badge[:material/subdirectory_arrow_right: Follow-up]"
    )
    new = formatter.question_md(turn.model_copy(update={"is_followup": False}))
    assert new.endswith(":gray-badge[:material/add_comment: New question]")


@pytest.mark.parametrize(
    ("answered", "current", "shown"),
    [
        (0, True, (0.2, "Question 1 of 5")),
        (1, False, (0.4, "Question 2 of 5")),  # waiting for the next question (or a retry)
        (4, True, (1.0, "Question 5 of 5")),
        (5, False, (1.0, "All 5 questions answered")),
    ],
)
def test_interview_progress_counts_questions(answered, current, shown):
    assert formatter.interview_progress(answered, current, 5) == shown


def test_mastery_words_pair_every_trend_with_an_icon_and_words():
    assert formatter.trend_md("improving") == ":green-badge[:material/trending_up: Improving]"
    assert formatter.trend_md("slipping") == ":yellow-badge[:material/trending_down: Slipping]"
    assert formatter.trend_md("steady") == ":gray-badge[:material/trending_flat: Steady]"
    assert formatter.trend_md("new") == ":gray-badge[:material/more_horiz: One quiz so far]"
    assert (
        formatter.mastery_line("OS", 0.3, [40.0, 70.0]) == "**OS** :gray[· 30% weak · 70% latest]"
    )
    assert formatter.mastery_line("CN", 0.7, []) == "**CN** :gray[· 70% weak · no quiz yet]"


@pytest.mark.parametrize(
    ("scores", "headline"),
    [
        ({"OS": [30, 70], "DBMS": [40, 50]}, "OS is up from 30% to 70%"),
        ({"OS": [70, 30], "DBMS": [50, 50]}, "OS is down from 70% to 30%"),
        ({"OS": [50, 50]}, "Scores are level since your first quizzes"),
        ({"OS": [50], "CN": []}, "Take a second quiz on a topic to see it move"),
    ],
)
def test_topic_scores_headline_names_the_biggest_move(scores, headline):
    assert formatter.topic_scores_headline(scores) == headline


def test_dashboard_headlines_and_alt_text():
    plans = [f.plan(week=1), f.plan(week=2, topics=("OS",) * 5 + ("DBMS",) * 2)]
    assert formatter.week_mix_headline(plans) == "Week 2 puts 71% of its minutes on OS"
    weeks = {p.week_no: p.minutes_by_topic() for p in plans}
    assert formatter.plan_mix_alt(weeks) == (
        "Minutes per topic by week. week 1: OS 420; week 2: OS 300, DBMS 120"
    )
    assert formatter.interview_headline([3.1]) == "Your first interview averaged 3.1/5"
    assert formatter.interview_headline([2.5, 3.75]) == (
        "Your latest interview averaged 3.8/5, up from 2.5"
    )
    assert formatter.interview_headline([3.0, 2.0]).endswith("down from 3.0")
    assert formatter.interview_headline([3.0, 3.0]).endswith("level with 3.0")


def test_telemetry_tables_are_ready_to_read():
    stats = [
        {
            "agent_name": "quiz_critic",
            "calls": 4,
            "avg_latency_ms": 120.0,
            "avg_tokens": 900.0,
            "rejections": 1,
            "failures": 2,
            "rejection_rate": 0.25,
        },
        {
            "agent_name": "profile",
            "calls": 1,
            "avg_latency_ms": 80.0,
            "avg_tokens": 300.0,
            "rejections": 0,
            "rejection_rate": None,
        },
    ]
    df = formatter.agent_table(stats)
    assert list(df.columns) == list(formatter.AGENT_COLUMNS)
    assert df.loc[0, "Agent"] == "Quiz critic" and df.loc[0, "Rejection rate"] == 25.0
    assert df["Rejection rate"].isna().tolist() == [False, True]  # no critic, no rate
    assert df["Failed calls"].tolist()[0] == 2  # an older summary without the count: blank
    assert df["Failed calls"].isna().tolist() == [False, True]
    assert list(formatter.agent_table([]).columns) == list(formatter.AGENT_COLUMNS)
    older = [{k: v for k, v in stats[0].items() if k != "failures"}]  # summary.json before H6
    assert "Failed calls" not in formatter.agent_table(older).columns
    rejected = [
        {
            "created_at": "2026-10-19 20:00:00",  # UTC; 01:30 the next day in India
            "agent_name": "quiz",
            "retry_count": 0,
            "reject_reason": "question 0: options are not distinct",
        }
    ]
    row = formatter.rejections_table(rejected).iloc[0].to_dict()
    assert row == {
        "When": "20 Oct, 01:30",
        "Agent": "Quiz",
        "Attempt": 1,
        "Critic's reason": "Q1: options are not distinct",
    }
    sessions = [{"started": "2026-10-19 20:00:00", "interview_type": "HR"}]
    assert formatter.session_labels(sessions) == ["20 Oct, HR"]


def test_readiness_change_and_headline_never_invent_a_trend():
    assert formatter.readiness_change([42]) is None  # one profile: no delta at all
    assert formatter.readiness_change([42, 58]) == ("+16 since the last profile", "normal")
    assert formatter.readiness_change([58, 50]) == ("-8 since the last profile", "normal")
    assert formatter.readiness_change([50, 50]) == ("±0 since the last profile", "off")
    assert formatter.readiness_headline([42]) == "Readiness is 42/100 from your first profile"
    assert formatter.readiness_headline([42, 50, 58]) == (
        "Readiness rose from 42 to 58 over 3 profiles"
    )
    assert formatter.readiness_headline([58, 42]).startswith("Readiness fell from 58 to 42")
    assert formatter.readiness_headline([50, 50]) == "Readiness held at 50/100 over 2 profiles"
    assert formatter.local_day("2026-10-19 20:00:00") == "20 Oct"  # UTC evening, next day in India


def test_streak_and_activity_words():
    assert (formatter.days(1), formatter.days(3)) == ("1 day", "3 days")
    assert formatter.streak_md(3, 5) == (
        ":primary[:material/event_available:] Study streak: **3 days** (longest 5 days)."
    )
    assert "No study streak right now; your longest was 1 day." in formatter.streak_md(0, 1)
    assert formatter.streak_md(6, 6).endswith("Study streak: **6 days**, your longest.")
    assert formatter.activity_headline(0, 0) == "No quizzes or interviews in the last 12 weeks"
    assert formatter.activity_headline(9, 3) == (
        "Active on 9 days in the last 12 weeks; longest streak 3 days"
    )


def test_critic_plain_renumbers_without_escaping():
    assert formatter.critic_plain("question 2: __init__ twice") == "Q3: __init__ twice"


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
    # The rate limit's wait time was true when the run stopped, not when the page is read.
    hinted = f.eval_summary(stopped_early="c16: limit reached. Try again in about 291 s.")
    assert "Try again" not in formatter.results_caption(hinted)
    assert "stopped early (c16: limit reached\\.); continue" in formatter.results_caption(hinted)
    assert "not meaningful" in formatter.results_md(f.eval_summary(mode="mock"))


def test_results_note_names_the_duplicate_rate_only_with_that_row():
    assert "except the duplicate rate" in formatter.results_note(f.eval_summary())
    note = formatter.results_note(f.eval_summary(consecutive=None))
    assert "duplicate" not in note
    assert note.startswith("In the table, rates run from 0 to 1; higher is better.")


def test_results_metrics_define_each_rate_and_its_direction():
    metrics = formatter.results_metrics(f.eval_summary())
    assert [m.name for m in metrics] == [
        "Plan valid rate",
        "Quiz valid rate",
        "Weak-topic share of minutes",
        "Repeated questions over 5 quizzes",
        "Interview follow-up relevance",
    ]
    assert [m.higher_is_better for m in metrics] == [True, True, True, False, True]
    assert all(m.definition.endswith(".") for m in metrics)
    assert (metrics[0].baseline, metrics[0].placementiq) == (0.4, 1.0)
    assert metrics[-1].baseline is None  # the baseline has no interviewer
    minimal = formatter.results_metrics(f.eval_summary(consecutive=None, interviews=None))
    assert len(minimal) == 3
    assert formatter.direction_md(True) == ":gray-badge[:material/arrow_upward: Higher is better]"
    assert formatter.direction_md(False).endswith("Lower is better]")


def test_compare_html_draws_both_systems_in_their_colours():
    plan, *_, followup = formatter.results_metrics(f.eval_summary())
    html = formatter.compare_html(plan)
    grey, teal = formatter.SYSTEM_COLORS["Baseline"], formatter.SYSTEM_COLORS["PlacementIQ"]
    assert f'style="width:40%;background:{grey}"' in html and "<span>40%</span>" in html
    assert f'style="width:100%;background:{teal}"' in html and "<span>100%</span>" in html
    assert html.index("Baseline") < html.index("PlacementIQ")
    missing = formatter.compare_html(followup)
    assert "<span>Not measured</span>" in missing and missing.count("width:") == 1


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
