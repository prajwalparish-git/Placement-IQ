"""Output layer: validated models / DB rows -> markdown and chart-ready DataFrames.

Pure functions, no Streamlit import, so every rendering decision is unit-testable.
"""

from collections.abc import Iterable, Mapping

import pandas as pd

from piq.config import TOPICS
from piq.schemas import AnswerEvaluation, InterviewTurn, QuizSet, StudentProfile, WeeklyPlan


def _bullets(items: Iterable[str], empty: str = "_none_") -> str:
    items = list(items)
    return "\n".join(f"- {i}" for i in items) if items else empty


def profile_md(p: StudentProfile) -> str:
    return (
        f"### {p.name} — {p.target_role}\n"
        f"**Readiness:** {p.readiness_score}/100 "
        f"({len(p.matched_skills)} of {len(p.matched_skills) + len(p.missing_skills)} "
        "required skills evidenced)\n\n"
        f"**Education:** {p.education}\n\n"
        f"**Matched skills:** {', '.join(p.matched_skills) or '_none_'}\n\n"
        f"**Missing skills:** {', '.join(p.missing_skills) or '_none_'}\n\n"
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
        yours = q.options[a] if a is not None else "_no answer_"
        line = f"{mark} **Q{i}. {q.text}**\n\nYour answer: {yours}"
        if not ok:
            line += f"  \nCorrect: {q.options[q.correct_index]}"
        blocks.append(f"{line}  \n_{q.explanation}_")
    return "\n\n".join(blocks)


def score_line(pct: float, topic: str, next_difficulty: str) -> str:
    return f"**{topic}: {pct:.0f}%** — next suggested difficulty: **{next_difficulty}**"


def turn_label(turn: InterviewTurn) -> str:
    return "follow-up" if turn.is_followup else "new question"


def evaluation_md(ev: AnswerEvaluation) -> str:
    scores = " · ".join(f"{k.title()} {v}/5" for k, v in ev.scores.items())
    return (
        f"**Overall {ev.overall}/5** — {scores}\n\n"
        f"**Strengths**\n{_bullets(ev.strengths)}\n\n"
        f"**Improve**\n{_bullets(ev.improvements)}\n\n"
        f"**Model answer**\n> {ev.model_answer}"
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
