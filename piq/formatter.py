"""Output layer: validated models / DB rows -> markdown and chart-ready DataFrames.

Pure functions, no Streamlit import, so every rendering decision is unit-testable.
"""

import re
from collections.abc import Iterable, Mapping
from html import escape

import pandas as pd

from piq.config import TOPICS
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


def _bullets(items: Iterable[str], empty: str = "_none_") -> str:
    items = list(items)
    return "\n".join(f"- {md_escape(i)}" for i in items) if items else empty


def _joined(items: Iterable[str]) -> str:
    return md_escape(", ".join(items)) or "_none_"


def profile_md(p: StudentProfile) -> str:
    return (
        f"### {md_escape(p.name)} — {md_escape(p.target_role)}\n"
        f"**Readiness:** {p.readiness_score}/100 "
        f"({len(p.matched_skills)} of {len(p.matched_skills) + len(p.missing_skills)} "
        "required skills evidenced)\n\n"
        f"**Education:** {md_escape(p.education)}\n\n"
        f"**Matched skills:** {_joined(p.matched_skills)}\n\n"
        f"**Missing skills:** {_joined(p.missing_skills)}\n\n"
        f"**Projects**\n{_bullets(p.projects)}\n\n"
        f"**Internships**\n{_bullets(p.internships)}\n\n"
        f"**Resume fixes**\n{_bullets(p.resume_feedback)}"
    )


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
