"""Output layer: validated models / DB rows -> markdown and chart-ready DataFrames.

Pure functions, no Streamlit import, so every rendering decision is unit-testable.
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from html import escape
from zoneinfo import ZoneInfo

import pandas as pd

from piq.config import (
    BRAND_COLOR,
    DIFFICULTIES,
    DIFFICULTY_DOWN_BELOW,
    DIFFICULTY_UP_AT,
    PALETTE,
    TIMEZONE,
    TOPIC_COLORS,
    TOPICS,
    WEAK_THRESHOLD,
)
from piq.schemas import (
    AnswerEvaluation,
    InterviewTurn,
    Question,
    QuizSet,
    StudentProfile,
    WeeklyPlan,
)

_CODE = re.compile(r"(```.*?```|`[^`\n]+`)", re.S)
_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()<>#+\-.!|~$&=])")


def md_escape(text: str) -> str:
    """Show resume, LLM or user text literally wherever Streamlit renders Markdown.

    Inline `code` and fenced blocks are kept, so code in model answers stays readable
    (code is never interpreted as Markdown or HTML anyway).
    """
    parts = _CODE.split(text)
    return "".join(p if i % 2 else _MD_SPECIAL.sub(r"\\\1", p) for i, p in enumerate(parts))


# Every status shows an icon and words, never colour alone: state -> (icon, colour).
STATUS = {
    "done": ("check_circle", "green"),
    "todo": ("radio_button_unchecked", "gray"),
    "warning": ("warning", "yellow"),
    "error": ("error", "red"),
    "info": ("info", "blue"),
}


def status_md(state: str, text: str) -> str:
    """An inline status badge in Markdown; `text` is escaped."""
    icon, color = STATUS[state]
    return f":{color}-badge[:material/{icon}: {md_escape(text)}]"


def _light_dark(light: str, dark: str) -> str:
    """A CSS colour that follows Streamlit's theme switch (it sets color-scheme on the app)."""
    return f"light-dark({light}, {dark})"


def topic_chip_html(topic: str) -> str:
    """A topic chip: the topic's colour as a dot next to its name (never colour alone)."""
    light, dark = TOPIC_COLORS["light"].get(topic), TOPIC_COLORS["dark"].get(topic)
    dot = _light_dark(light, dark) if light and dark else "currentColor"
    edge = _light_dark(PALETTE["light"]["hairline"], PALETTE["dark"]["hairline"])
    return (
        '<span style="display:inline-flex;align-items:center;gap:0.45em;padding:0.15em 0.7em;'
        f'border:1px solid {edge};border-radius:999px;font-size:0.875rem;line-height:1.5">'
        '<span aria-hidden="true" style="width:0.65em;height:0.65em;border-radius:50%;'
        f'background:{dot}"></span>{escape(topic)}</span>'
    )


_QUESTION_N = re.compile(r"\bquestion (\d+):")


def critic_text(msg: str) -> str:
    """A step or critic message for display: escaped, and the critic's 0-based
    "question N:" (a protocol checks.question_issues parses) shown as the quiz's "Q{N+1}:"."""
    return critic_plain(md_escape(msg))


def _bullets(items: Iterable[str], empty: str = "_none_") -> str:
    items = list(items)
    return "\n".join(f"- {md_escape(i)}" for i in items) if items else empty


# --- profile (Onboard) ----------------------------------------------------------------


def usn_taken_md(usn: str, name: str, role: str) -> str:
    """Why onboarding stops for a confirmation: the USN is someone else's."""
    return (
        f"{md_escape(usn)} already belongs to {md_escape(name)} ({md_escape(role)}). "
        "Analysing this resume replaces their profile, and their name, with this one."
    )


def readiness_summary(p: StudentProfile) -> str:
    total = len(p.matched_skills) + len(p.missing_skills)
    role = md_escape(p.target_role)
    return f"{len(p.matched_skills)} of the {total} skills {role} needs are on the resume."


def skill_chips(skills: Iterable[str], present: bool) -> str:
    """Skills as badges: a filled check for one on the resume, an empty circle for a
    missing one, so the difference never rests on colour alone."""
    state = "done" if present else "todo"
    return " ".join(status_md(state, s) for s in skills)


def list_md(items: Iterable[str], empty: str) -> str:
    return _bullets(items, f":gray[{empty}]")


def fixes_md(fixes: Iterable[str]) -> str:
    """Resume fixes as a to-do checklist. The boxes are grey: a list marker, not a control
    that looks clickable."""
    lines = [f":gray[:material/check_box_outline_blank:] {md_escape(f)}" for f in fixes]
    return "  \n".join(lines) or ":gray[Nothing to fix.]"


def plan_table(plan: WeeklyPlan) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Day": d.day,
                "Topic": d.topic,
                "Subtopics": ", ".join(d.subtopics),
                "Minutes": d.duration_min,
                "Goal": d.practice_goal,
            }
            for d in sorted(plan.days, key=lambda d: d.day)
        ]
    ).set_index("Day")


def plan_minutes(plans: Iterable[WeeklyPlan]) -> pd.DataFrame:
    """Rows = topics, columns = 'Week n', values = minutes. Feeds the week-vs-week chart."""
    data = {f"Week {p.week_no}": p.minutes_by_topic() for p in plans}
    return pd.DataFrame(data, index=list(TOPICS)).fillna(0).astype(int)


# --- weekly plan -----------------------------------------------------------------------


def plan_summary(plan: WeeklyPlan) -> str:
    """One line under the week's title: the total and where most of it goes."""
    minutes = plan.minutes_by_topic()
    top = max(minutes, key=lambda t: minutes[t])
    return f"{sum(minutes.values())} minutes over {len(plan.days)} days, most of them on {top}."


def plan_csv(plan: WeeklyPlan) -> bytes:
    """The week as CSV (the table view's columns), with a BOM so Excel reads it as UTF-8."""
    return plan_table(plan).to_csv().encode("utf-8-sig")


def local_today(tz: str = TIMEZONE) -> date:
    """Today on the student's calendar."""
    return datetime.now(ZoneInfo(tz)).date()


def next_monday(today: date) -> date:
    """The default first day of an exported week: the coming Monday (today if it is one)."""
    return today + timedelta(days=-today.weekday() % 7)


def _ics_text(text: str) -> str:
    """RFC 5545 TEXT: escape backslash, semicolon, comma and line breaks."""
    for raw, escaped in (
        ("\\", "\\\\"),
        (";", "\\;"),
        (",", "\\,"),
        ("\r\n", "\\n"),
        ("\n", "\\n"),
    ):
        text = text.replace(raw, escaped)
    return text


def _ics_fold(line: str) -> str:
    """RFC 5545 3.1: a content line over 75 octets continues after CRLF and a space, never
    splitting a UTF-8 character."""
    chunks, current = [], b""
    for ch in line:
        encoded = ch.encode("utf-8")
        limit = 75 if not chunks else 74  # a continuation starts with a one-octet space
        if len(current) + len(encoded) > limit:
            chunks.append(current)
            current = encoded
        else:
            current += encoded
    chunks.append(current)
    return "\r\n ".join(c.decode("utf-8") for c in chunks)


def plan_ics(
    plan: WeeklyPlan, start: date, at: time, tz: str = TIMEZONE, now: datetime | None = None
) -> bytes:
    """The week as an iCalendar file: one event per day from `start`, at `at` on the
    student's clock (`tz`), as long as that day's minutes. Times are written in UTC, so no
    time-zone block is needed."""
    zone, stamp = ZoneInfo(tz), (now or datetime.now(UTC)).astimezone(UTC)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PlacementIQ//Weekly plan//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for d in sorted(plan.days, key=lambda d: d.day):
        local = datetime.combine(start + timedelta(days=d.day - 1), at, tzinfo=zone)
        begin = local.astimezone(UTC)
        end = begin + timedelta(minutes=d.duration_min)
        about = f"Week {plan.week_no}, day {d.day}. Goal: {d.practice_goal}"
        lines += [
            "BEGIN:VEVENT",
            f"UID:week{plan.week_no}-day{d.day}-{start:%Y%m%d}@placementiq",
            f"DTSTAMP:{stamp:%Y%m%dT%H%M%SZ}",
            f"DTSTART:{begin:%Y%m%dT%H%M%SZ}",
            f"DTEND:{end:%Y%m%dT%H%M%SZ}",
            f"SUMMARY:{_ics_text(f'{d.topic}: ' + ', '.join(d.subtopics))}",
            f"DESCRIPTION:{_ics_text(about)}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return ("\r\n".join(_ics_fold(line) for line in lines) + "\r\n").encode("utf-8")


def plan_days_html(plan: WeeklyPlan) -> str:
    """The week day by day: day, topic chip, minutes, subtopics and goal. One escaped HTML
    list (styled by static/app.css) rather than seven sets of widgets: it reads at any width
    and costs the page a single element."""
    rows = [
        '<li class="piq-day">'
        f'<span class="piq-day-n">Day {d.day}</span><div>'
        f'<div class="piq-day-head">{topic_chip_html(d.topic)}'
        f'<span class="piq-day-min">{d.duration_min} min</span></div>'
        f"<div>{escape(' · '.join(d.subtopics))}</div>"
        f'<div class="piq-day-goal">Goal: {escape(d.practice_goal)}</div>'
        "</div></li>"
        for d in sorted(plan.days, key=lambda d: d.day)
    ]
    label = f"Week {plan.week_no}, day by day"
    return f'<ol class="piq-days" aria-label="{label}">{"".join(rows)}</ol>'


def minutes_shift_headline(
    before: Mapping[str, int], after: Mapping[str, int], before_week: int
) -> str:
    """The week-over-week chart's takeaway: a new top topic, else the biggest gain and the
    biggest loss (the planner moves minutes from one topic to another)."""
    old = {t: before.get(t, 0) for t in TOPICS}
    new = {t: after.get(t, 0) for t in TOPICS}
    change = {t: new[t] - old[t] for t in TOPICS}
    leaders = [t for t in TOPICS if new[t] == max(new.values())]
    if len(leaders) == 1 and old[leaders[0]] < max(old.values()):
        return f"{leaders[0]} now gets the most minutes"
    gain = max(TOPICS, key=lambda t: change[t])
    loss = min(TOPICS, key=lambda t: change[t])
    since = f"than in week {before_week}"
    if change[gain] > 0 and change[loss] < 0:
        return f"{gain} gets {change[gain]} more minutes and {loss} {-change[loss]} fewer {since}"
    if change[gain] > 0:
        return f"{gain} gets {change[gain]} more minutes {since}"
    if change[loss] < 0:
        return f"{loss} gets {-change[loss]} fewer minutes {since}"
    return f"The same minutes per topic as in week {before_week}"


def minutes_shift_alt(
    before: Mapping[str, int], after: Mapping[str, int], weeks: tuple[int, int]
) -> str:
    """The same chart in words, for screen readers."""
    pairs = ", ".join(f"{t} {before.get(t, 0)} to {after.get(t, 0)}" for t in TOPICS)
    return f"Minutes per topic, week {weeks[0]} to week {weeks[1]}: {pairs}"


def weakness_source() -> str:
    """Where the weakness numbers come from: the adaptive loop, in one sentence."""
    return (
        "Weakness is 100% minus your average over the last three quizzes on a topic. Before "
        "a topic's first quiz it is 70% if your resume lacks it, else 40%."
    )


# --- quiz ------------------------------------------------------------------------------


def topic_option(topic: str, weakness: float) -> str:
    """A topic in the quiz picker, with its weakness as the hint."""
    return f"{topic} · {weakness:.0%} weak"


def suggestion_md(topic: str, last: tuple[float, str] | None, suggested: str) -> str:
    """Why a difficulty is suggested: the latest score on the topic and the rule."""
    badge = f":primary-badge[:material/recommend: Suggested: {suggested}]"
    if last is None:
        return f"{badge} No {topic} quiz yet, so start at {suggested}."
    pct, difficulty = last
    return (
        f"{badge} Your last {topic} quiz: {pct:.0f}% on {difficulty}. "
        f"{DIFFICULTY_UP_AT}% or more moves you up a level; under {DIFFICULTY_DOWN_BELOW}%, down."
    )


def result_md(correct: int, total: int, topic: str, difficulty: str, next_difficulty: str) -> str:
    """The quiz outcome in one sentence: what the score changes next (difficulty and plan)."""
    step = DIFFICULTIES.index(next_difficulty) - DIFFICULTIES.index(difficulty)
    icon = {1: "trending_up", 0: "trending_flat", -1: "trending_down"}[step]
    return (
        f":primary[:material/{icon}:] {correct} of {total} correct, so the next suggested "
        f"difficulty is **{next_difficulty}**. The score also counts toward your {topic} "
        "weakness, which shapes next week's plan."
    )


def review_md(n: int, question: Question, chosen: int | None) -> str:
    """One reviewed question: right, wrong or unanswered as an icon and a word (never colour
    alone), the answers and the explanation."""
    if chosen is None:
        badge = status_md("todo", "Not answered")
    elif chosen == question.correct_index:
        badge = status_md("done", "Correct")
    else:
        badge = status_md("error", "Wrong")
    lines = [f"{badge} **Q{n}. {md_escape(question.text)}**"]
    if chosen is not None:
        lines.append(f"Your answer: {md_escape(question.options[chosen])}")
    if chosen != question.correct_index:
        lines.append(f"Correct answer: {md_escape(question.options[question.correct_index])}")
    lines.append(f":gray[{md_escape(question.explanation)}]")
    return "  \n".join(lines)


def quiz_review(quiz: QuizSet, chosen: Sequence[int | None]) -> list[str]:
    """Every question of a submitted quiz, reviewed; one answer per question is required."""
    pairs = zip(quiz.questions, chosen, strict=True)
    return [review_md(i, q, a) for i, (q, a) in enumerate(pairs, 1)]


# --- mock interview -----------------------------------------------------------------------


def question_md(turn: InterviewTurn) -> str:
    """The interviewer's question with a quiet badge: a follow-up on the last answer, or new."""
    kind = ":gray-badge[:material/subdirectory_arrow_right: Follow-up]"
    if not turn.is_followup:
        kind = ":gray-badge[:material/add_comment: New question]"
    return f"{md_escape(turn.question)}  \n{kind}"


def interview_progress(answered: int, current: bool, max_turns: int) -> tuple[float, str]:
    """The session's position for a progress bar: its value and its words."""
    if not current and answered >= max_turns:
        return 1.0, f"All {max_turns} questions answered"
    n = min(answered + 1, max_turns)
    return n / max_turns, f"Question {n} of {max_turns}"


def feedback_title(ev: AnswerEvaluation) -> str:
    return f"**Feedback** · {ev.overall:.1f}/5 overall"


def criteria_html(scores: Mapping[str, int]) -> str:
    """The four rubric scores as small bars (styled by static/app.css); the words and the
    number carry the score, the bar only shows it at a glance."""
    rows = [
        '<div class="piq-criterion">'
        f"<span>{escape(name.title())}</span>"
        f'<span class="piq-bar" aria-hidden="true"><span style="width:{20 * int(v)}%">'
        f"</span></span><span>{int(v)}/5</span></div>"
        for name, v in scores.items()
    ]
    return f'<div class="piq-criteria">{"".join(rows)}</div>'


def evaluation_md(ev: AnswerEvaluation) -> str:
    """What to keep, what to change and a model answer, quoted."""
    # Every line keeps its own line in the quote (a hard break): consecutive "> " lines
    # would otherwise run together into one paragraph.
    lines = md_escape(ev.model_answer).splitlines()
    quote = "\n".join(f"> {line}  " if line.strip() else ">" for line in lines)
    return (
        f"**Strengths**  \n{list_md(ev.strengths, 'None this time.')}\n\n"
        f"**Improve**  \n{list_md(ev.improvements, 'Nothing to change.')}\n\n"
        f"**Model answer**\n{quote}"
    )


# --- dashboard ----------------------------------------------------------------------------


def topic_scores(rows: Iterable[Mapping]) -> dict[str, list[float]]:
    """quiz_history rows (oldest first) -> each topic's scores in attempt order, every topic
    present (empty before its first quiz)."""
    out: dict[str, list[float]] = {t: [] for t in TOPICS}
    for r in rows:
        out.setdefault(r["topic"], []).append(float(r["score_pct"]))
    return out


def topic_scores_headline(scores: Mapping[str, Sequence[float]]) -> str:
    """The quiz charts' takeaway: the biggest rise from a topic's first to its latest quiz."""
    moved = {t: s[-1] - s[0] for t, s in scores.items() if len(s) >= 2}
    if not moved:
        return "Take a second quiz on a topic to see it move"
    best = max(moved, key=lambda t: moved[t])
    first, latest = scores[best][0], scores[best][-1]
    if moved[best] > 0:
        return f"{best} is up from {first:.0f}% to {latest:.0f}%"
    worst = min(moved, key=lambda t: moved[t])
    if moved[worst] < 0:
        return f"{worst} is down from {scores[worst][0]:.0f}% to {scores[worst][-1]:.0f}%"
    return "Scores are level since your first quizzes"


def week_mix_headline(plans: Sequence[WeeklyPlan]) -> str:
    """The plan-minutes chart's takeaway: where the latest week's time goes."""
    latest = plans[-1].minutes_by_topic()
    top = max(latest, key=lambda t: latest[t])
    share = latest[top] / sum(latest.values())
    return f"Week {plans[-1].week_no} puts {share:.0%} of its minutes on {top}"


def plan_mix_alt(weeks: Mapping[int, Mapping[str, int]]) -> str:
    """The weekly-minutes chart in words, for screen readers."""
    parts = [
        f"week {w}: " + ", ".join(f"{t} {m}" for t, m in minutes.items() if m)
        for w, minutes in weeks.items()
    ]
    return "Minutes per topic by week. " + "; ".join(parts)


def local_day(timestamp: str, tz: str = TIMEZONE) -> str:
    """A SQLite UTC timestamp as a day on the student's calendar, e.g. "20 Oct"."""
    at = datetime.fromisoformat(timestamp).replace(tzinfo=UTC).astimezone(ZoneInfo(tz))
    return f"{at:%d %b}"


def session_labels(sessions: Iterable[Mapping], tz: str = TIMEZONE) -> list[str]:
    """Interview sessions for a tooltip: the day on the student's calendar and the type."""
    return [f"{local_day(s['started'], tz)}, {s['interview_type']}" for s in sessions]


def readiness_change(scores: Sequence[int]) -> tuple[str, str] | None:
    """The readiness KPI's delta and its colour: the latest profile minus the one before.
    None with a single profile: there is nothing to compare, so no delta is invented."""
    if len(scores) < 2:
        return None
    change = scores[-1] - scores[-2]
    if change == 0:
        return "±0 since the last profile", "off"
    return f"{change:+d} since the last profile", "normal"


def readiness_headline(scores: Sequence[int]) -> str:
    """The readiness chart's takeaway, first profile to latest."""
    first, latest, n = scores[0], scores[-1], len(scores)
    if n == 1:
        return f"Readiness is {latest}/100 from your first profile"
    verb = "rose" if latest > first else "fell" if latest < first else "held"
    if verb == "held":
        return f"Readiness held at {latest}/100 over {n} profiles"
    return f"Readiness {verb} from {first} to {latest} over {n} profiles"


def interview_headline(averages: Sequence[float]) -> str:
    """The interview chart's takeaway: the latest session against the one before."""
    latest = averages[-1]
    if len(averages) == 1:
        return f"Your first interview averaged {latest:.1f}/5"
    before = averages[-2]
    change = "up from" if latest > before else "down from" if latest < before else "level with"
    return f"Your latest interview averaged {latest:.1f}/5, {change} {before:.1f}"


def critic_plain(msg: str) -> str:
    """A critic message for a table (plain text): the 0-based "question N:" shown as "QN+1:"."""
    return _QUESTION_N.sub(lambda m: f"Q{int(m[1]) + 1}:", msg)


def agent_table(rows: Iterable[Mapping]) -> pd.DataFrame:
    """agent_stats rows -> one display row per agent; the rejection rate as a percentage."""
    data = [
        {
            "Agent": r["agent_name"].replace("_", " ").capitalize(),
            "Calls": r["calls"],
            "Avg latency (ms)": r["avg_latency_ms"],
            "Avg tokens": r["avg_tokens"],
            "Rejected drafts": r["rejections"],
            "Failed calls": r.get("failures"),  # absent from older summary.json files
            "Rejection rate": None if r["rejection_rate"] is None else 100 * r["rejection_rate"],
        }
        for r in map(dict, rows)
    ]
    return pd.DataFrame(data, columns=AGENT_COLUMNS)


AGENT_COLUMNS = (
    "Agent",
    "Calls",
    "Avg latency (ms)",
    "Avg tokens",
    "Rejected drafts",
    "Failed calls",
    "Rejection rate",
)


def rejections_table(rows: Iterable[Mapping], tz: str = TIMEZONE) -> pd.DataFrame:
    """recent_rejections rows -> when (the student's clock), agent, attempt and the reason."""
    zone = ZoneInfo(tz)
    data = [
        {
            "When": datetime.fromisoformat(r["created_at"])
            .replace(tzinfo=UTC)
            .astimezone(zone)
            .strftime("%d %b, %H:%M"),
            "Agent": r["agent_name"].replace("_", " ").capitalize(),
            "Attempt": (r["retry_count"] or 0) + 1,
            "Critic's reason": critic_plain(r["reject_reason"] or ""),
        }
        for r in rows
    ]
    return pd.DataFrame(data, columns=["When", "Agent", "Attempt", "Critic's reason"])


# --- evaluation results ------------------------------------------------------------

ATTEMPTS = "Avg quiz attempts"


def results_table(summary: Mapping) -> pd.DataFrame:
    """summary.json -> rows = metrics, columns = Baseline / PlacementIQ (NaN = not measured)."""
    b, p = summary.get("baseline") or {}, summary.get("placementiq") or {}
    rows: dict[str, tuple] = {
        "Plan valid rate": (b.get("plan_valid_rate"), p.get("plan_valid_rate")),
        "Quiz valid rate": (b.get("quiz_valid_rate"), p.get("quiz_valid_rate")),
        "Avg weak-topic share of minutes": (b.get("avg_weak_share"), p.get("avg_weak_share")),
    }
    if c := summary.get("consecutive"):
        rows[f"Duplicate rate over {c['quizzes_per_topic']} quizzes (lower is better)"] = (
            c["baseline_duplicate_rate"],
            c["placementiq_duplicate_rate"],
        )
    if iv := summary.get("interviews"):
        rows["Interview follow-up relevance"] = (None, iv["followup_relevance"])
    rows[ATTEMPTS] = (b.get("avg_quiz_attempts"), p.get("avg_quiz_attempts"))
    df = pd.DataFrame(rows, index=["Baseline", "PlacementIQ"], dtype=float).T
    return df.rename_axis("Metric")


@dataclass(frozen=True)
class Metric:
    """One comparison on the Results page: plain words, its direction, both systems' values
    (0-1 rates; None = not measured)."""

    name: str
    definition: str
    higher_is_better: bool
    baseline: float | None
    placementiq: float | None


# The two systems keep one colour each on the Results page (never a topic colour): a grey
# and the brand teal, both >= 3:1 on either background.
SYSTEM_COLORS = {"Baseline": PALETTE["light"]["border"], "PlacementIQ": BRAND_COLOR}


def results_metrics(summary: Mapping) -> list[Metric]:
    """The measured rates of a run_eval summary, each with its definition and direction."""
    b, p = summary.get("baseline") or {}, summary.get("placementiq") or {}
    out = [
        Metric(
            "Plan valid rate",
            "Share of weekly plans that pass every plan check: seven days for the right week, "
            "weak topics included with at least half the minutes, more minutes for weaker topics.",
            True,
            b.get("plan_valid_rate"),
            p.get("plan_valid_rate"),
        ),
        Metric(
            "Quiz valid rate",
            "Share of quizzes in which every question passes the question checks and the critic.",
            True,
            b.get("quiz_valid_rate"),
            p.get("quiz_valid_rate"),
        ),
        Metric(
            "Weak-topic share of minutes",
            "Average share of a week's study time that goes to the student's weak topics.",
            True,
            b.get("avg_weak_share"),
            p.get("avg_weak_share"),
        ),
    ]
    if c := summary.get("consecutive"):
        out.append(
            Metric(
                f"Repeated questions over {c['quizzes_per_topic']} quizzes",
                f"Share of questions that repeat an earlier one when a topic is quizzed "
                f"{c['quizzes_per_topic']} times in a row.",
                False,
                c["baseline_duplicate_rate"],
                c["placementiq_duplicate_rate"],
            )
        )
    if iv := summary.get("interviews"):
        out.append(
            Metric(
                "Interview follow-up relevance",
                "Share of follow-up questions that build on the candidate's last answer, as "
                "decided by a judge model. The baseline has no interviewer, so it is not measured.",
                True,
                None,
                iv["followup_relevance"],
            )
        )
    return out


def direction_md(higher_is_better: bool) -> str:
    """Which way is good, as a badge with an arrow and words."""
    if higher_is_better:
        return ":gray-badge[:material/arrow_upward: Higher is better]"
    return ":gray-badge[:material/arrow_downward: Lower is better]"


def compare_html(metric: Metric) -> str:
    """Both systems' values as labelled bars in their system colours (styled by app.css);
    a value that was not measured says so instead of drawing an empty bar."""
    rows = []
    for system, value in (("Baseline", metric.baseline), ("PlacementIQ", metric.placementiq)):
        if value is None:
            bar, shown = "", "Not measured"
        else:
            width = round(100 * min(max(float(value), 0.0), 1.0))
            bar = f'<span style="width:{width}%;background:{SYSTEM_COLORS[system]}"></span>'
            shown = f"{float(value):.0%}"
        rows.append(
            f'<div class="piq-criterion"><span>{system}</span>'
            f'<span class="piq-bar" aria-hidden="true">{bar}</span><span>{shown}</span></div>'
        )
    return f'<div class="piq-criteria">{"".join(rows)}</div>'


def results_caption(summary: Mapping) -> str:
    cases = (summary.get("placementiq") or {}).get("cases", 0)
    parts = [f"{md_escape(str(summary.get('mode', '?')))} run", f"{cases} cases"]
    if summary.get("errors"):
        parts.append(f"{summary['errors']} failed")
    if summary.get("stopped_early"):
        reason = md_escape(str(summary["stopped_early"]))
        parts.append(f"stopped early ({reason}); continue with --resume")
    return " · ".join(parts)


def results_note(summary: Mapping) -> str:
    """How to read the rates; names the duplicate-rate exception only when that row exists."""
    exception = " except the duplicate rate" if summary.get("consecutive") else ""
    return (
        f"In the table, rates run from 0 to 1; higher is better{exception}. "
        "Confirm quiz validity by hand with evaluation/results/questions.csv."
    )


def _md_table(df: pd.DataFrame) -> str:
    head = f"| {df.index.name or ''} | " + " | ".join(df.columns) + " |"
    rule = "|---" * (len(df.columns) + 1) + "|"
    body = [
        f"| {idx} | " + " | ".join("—" if pd.isna(v) else f"{v:.2f}" for v in row) + " |"
        for idx, row in df.iterrows()
    ]
    return "\n".join([head, rule, *body])


def results_md(summary: Mapping) -> str:
    table = results_table(summary)
    md = [
        "# Evaluation results",
        "",
        results_caption(summary),
        "",
        _md_table(table),
        "",
        "Rates run from 0 to 1. Both systems are judged by the same deterministic checks and "
        "LLM critic; quiz validity should also be confirmed by hand in `questions.csv`.",
    ]
    if summary.get("mode") == "mock":
        md += ["", "**MOCK_MODE results: not meaningful, smoke test only.**"]
    if stats := summary.get("agent_stats"):
        cols = ["agent_name", "calls", "avg_latency_ms", "avg_tokens", "rejection_rate"]
        df = pd.DataFrame(stats)[cols].set_index("agent_name").rename_axis("Agent")
        md += ["", "## Agent cost during the evaluation", "", _md_table(df.astype(float))]
    return "\n".join(md) + "\n"


def results_svg(table: pd.DataFrame) -> str:
    """Grouped horizontal bars for the 0-1 metrics; no plotting dependency needed."""
    rates = table.drop(index=ATTEMPTS, errors="ignore")
    colors = {"Baseline": "#80868b", "PlacementIQ": "#1a73e8"}
    left, bar_w, row_h = 330, 300, 56
    width, height = left + bar_w + 60, 44 + row_h * len(rates)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        'font-family="Arial, sans-serif" font-size="13">',
        "<title>Baseline vs PlacementIQ</title>",
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
    ]
    for k, (name, color) in enumerate(colors.items()):
        x = left + k * 140
        out.append(f'<rect x="{x}" y="10" width="12" height="12" fill="{color}"/>')
        out.append(f'<text x="{x + 18}" y="21">{name}</text>')
    for i, (metric, row) in enumerate(rates.iterrows()):
        y = 40 + i * row_h
        out.append(f'<text x="{left - 10}" y="{y + 24}" text-anchor="end">{escape(metric)}</text>')
        for j, system in enumerate(colors):
            v, by = row[system], y + 4 + j * 22
            if pd.isna(v):
                out.append(f'<text x="{left + 4}" y="{by + 14}" fill="#5f6368">not measured</text>')
                continue
            w = round(bar_w * float(v), 1)
            out.append(
                f'<rect x="{left}" y="{by}" width="{w}" height="18" fill="{colors[system]}"/>'
            )
            out.append(f'<text x="{left + w + 6}" y="{by + 14}">{float(v):.2f}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


# --- the critic loop, as a trail ----------------------------------------------------

FAILED = "failed: "  # prefix ui.run_agent gives a failure in the step log
# graph.Task names -> what the student sees being made
ARTEFACTS = {
    "quiz": "quiz",
    "planner": "plan",
    "profile": "profile",
    "interviewer": "next question",
}
_GENERATED = re.compile(r"^(\w+): generated \(attempt (\d+)\)$")
_REJECTED = re.compile(r"^critic rejected (\w+): (.*)$", re.S)
_APPROVED = re.compile(r"^critic approved (\w+)$")
_GAVE_UP = re.compile(r"^\w+: rejected after retries: ")


@dataclass(frozen=True)
class TrailStep:
    title: str  # plain words; also the step's status label
    reasons: tuple[str, ...] = ()  # Markdown, escaped: why the critic said no
    note: str = ""  # one quiet line: the attempt, or what happened
    failed: bool = False  # a rejection or a stop: shown in the error state


def trail_steps(events: Sequence[str]) -> list[TrailStep]:
    """The agent step log as a readable trail: generated, critic rejected (with the
    reasons), regenerated, then approved or stopped. Messages come from graph.run and
    ui.run_agent; a repeated rejection says so instead of repeating its reasons."""
    steps: list[TrailStep] = []
    previous: list[str] | None = None
    for msg in events:
        if m := _GENERATED.match(msg):
            verb = "Generated" if m[2] == "1" else "Regenerated"
            steps.append(TrailStep(f"{verb} the {_artefact(m[1])}", note=f"Attempt {m[2]}"))
        elif m := _REJECTED.match(msg):
            reasons, title = m[2].split("; "), f"Critic rejected the {_artefact(m[1])}"
            if reasons == previous:
                steps.append(TrailStep(title, note="Same reason as before.", failed=True))
            else:
                steps.append(TrailStep(title, tuple(critic_text(r) for r in reasons), failed=True))
            previous = reasons
        elif m := _APPROVED.match(msg):
            steps.append(
                TrailStep(f"Critic approved the {_artefact(m[1])}", note="Passed every check.")
            )
        elif msg.startswith(FAILED):
            error = msg.removeprefix(FAILED)
            if _GAVE_UP.match(error):
                steps.append(
                    TrailStep("Stopped", note="The critic rejected every attempt.", failed=True)
                )
            else:
                steps.append(TrailStep("Stopped", (critic_text(error),), failed=True))
        else:
            steps.append(TrailStep(critic_text(msg)))
    return steps


def _artefact(task: str) -> str:
    return ARTEFACTS.get(task, md_escape(task))


# --- home ---------------------------------------------------------------------------


def relative_day(at: datetime, now: datetime | None = None) -> str:
    """When something happened, by the student's calendar (TIMEZONE), not UTC's."""
    tz = ZoneInfo(TIMEZONE)
    local = at.astimezone(tz)
    days = ((now or datetime.now(UTC)).astimezone(tz).date() - local.date()).days
    if days <= 0:
        return "Today"
    if days == 1:
        return "Yesterday"
    return f"{days} days ago" if days < 7 else f"{local.day} {local:%b}"


def weakness_headline(weakness: Mapping[str, float]) -> str:
    """The weakness chart's takeaway, stated as a sentence."""
    topic = max(weakness, key=lambda t: weakness[t])
    if weakness[topic] > WEAK_THRESHOLD:
        return f"{topic} is your weakest topic"
    return f"No weak topics; {topic} has the most room to grow"


def checklist_line(label: str, done: bool) -> str:
    """A checklist item: an icon and a word for its state, then the item (escaped)."""
    badge = status_md("done", "Done") if done else status_md("todo", "To do")
    return f"{badge} {md_escape(label)}"


def weakness_caption() -> str:
    return (
        f"0% is strong, 100% is weak; the dashed line marks a weak topic (above "
        f"{WEAK_THRESHOLD:.0%})."
    )


def weakness_alt(weakness: Mapping[str, float]) -> str:
    """The same chart in words, for screen readers."""
    ranked = sorted(weakness.items(), key=lambda kv: -kv[1])
    return "Weakness by topic, weakest first: " + ", ".join(f"{t} {w:.0%}" for t, w in ranked)
