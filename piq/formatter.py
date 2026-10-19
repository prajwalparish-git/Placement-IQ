"""Output layer: validated models / DB rows -> markdown and chart-ready DataFrames.

Pure functions, no Streamlit import, so every rendering decision is unit-testable.
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from zoneinfo import ZoneInfo

import pandas as pd

from piq.config import PALETTE, TIMEZONE, TOPIC_COLORS, TOPICS, WEAK_THRESHOLD
from piq.schemas import AnswerEvaluation, InterviewTurn, QuizSet, StudentProfile, WeeklyPlan

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
    return _QUESTION_N.sub(lambda m: f"Q{int(m[1]) + 1}:", md_escape(msg))


def _bullets(items: Iterable[str], empty: str = "_none_") -> str:
    items = list(items)
    return "\n".join(f"- {md_escape(i)}" for i in items) if items else empty


# --- profile (Onboard) ----------------------------------------------------------------


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


def quiz_review_md(quiz: QuizSet, chosen: list[int | None]) -> str:
    blocks = []
    for i, (q, a) in enumerate(zip(quiz.questions, chosen, strict=True), 1):
        ok = a == q.correct_index
        mark = "✅" if ok else "❌"
        yours = md_escape(q.options[a]) if a is not None else "_no answer_"
        line = f"{mark} **Q{i}. {md_escape(q.text)}**\n\nYour answer: {yours}"
        if not ok:
            line += f"  \nCorrect: {md_escape(q.options[q.correct_index])}"
        blocks.append(f"{line}  \n_{md_escape(q.explanation)}_")
    return "\n\n".join(blocks)


def score_line(pct: float, topic: str, next_difficulty: str) -> str:
    return f"**{topic}: {pct:.0f}%** — next suggested difficulty: **{next_difficulty}**"


def turn_label(turn: InterviewTurn) -> str:
    return "follow-up" if turn.is_followup else "new question"


def evaluation_md(ev: AnswerEvaluation) -> str:
    scores = " · ".join(f"{k.title()} {v}/5" for k, v in ev.scores.items())
    quote = "\n".join(f"> {line}" for line in md_escape(ev.model_answer).splitlines())
    return (
        f"**Overall {ev.overall}/5** — {scores}\n\n"
        f"**Strengths**\n{_bullets(ev.strengths)}\n\n"
        f"**Improve**\n{_bullets(ev.improvements)}\n\n"
        f"**Model answer**\n{quote}"
    )


def weakness_table(weakness: Mapping[str, float]) -> pd.DataFrame:
    return (
        pd.DataFrame({"Weakness": dict(weakness)})
        .rename_axis("Topic")
        .sort_values("Weakness", ascending=False)
    )


def score_trend(rows: Iterable[Mapping]) -> pd.DataFrame:
    """quiz_history rows -> one column per topic, indexed by attempt order."""
    df = pd.DataFrame([dict(r) for r in rows])
    if df.empty:
        return df
    df["attempt"] = df.groupby("topic").cumcount() + 1
    return df.pivot_table(index="attempt", columns="topic", values="score_pct")


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
        f"Rates run from 0 to 1; higher is better{exception}. "
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
