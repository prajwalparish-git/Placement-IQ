"""Dashboard: how the student is doing (readiness, quiz scores per topic, plan minutes,
interview scores), then how the agents and the critic behave, kept apart."""

import streamlit as st

from piq import charts, formatter, services
from piq.ui import Stat, empty_state, page_header, require_profile, stat_row


def _kpis(d: services.Dashboard, streak: services.Streak) -> None:
    change = formatter.readiness_change([r["readiness_score"] for r in d.readiness])
    delta, color = change or (None, "normal")
    stat_row(
        [
            Stat("Readiness", f"{d.profile.readiness_score}/100", delta, delta_color=color),
            Stat("Quizzes taken", str(len(d.quiz_history))),
            Stat("Interview sessions", str(len(d.sessions))),
            Stat(
                "Study streak",
                formatter.days(streak.current),
                help=f"Days in a row with a quiz or an interview. Longest: "
                f"{formatter.days(streak.longest)}.",
            ),
        ]
    )


def _activity(streak: services.Streak) -> None:
    today = formatter.local_today()
    recent = sum(1 for day in streak.days if (today - day).days < 7 * 12)
    st.subheader(formatter.activity_headline(recent, streak.longest), anchor=False)
    st.vega_lite_chart(
        spec=charts.activity_heatmap_spec(streak.days, today),
        width="stretch",
        alt=f"Calendar of the last 12 weeks: {formatter.days(recent)} with study.",
    )
    st.caption(
        "One square per day, a column per week, oldest on the left; a stronger teal is busier."
    )


def _topic_mastery(d: services.Dashboard) -> None:
    """Every topic, weakest first: weakness now, which way it moves, and its quiz scores."""
    mastery = d.mastery
    st.subheader(
        formatter.topic_scores_headline({m.topic: m.scores for m in mastery}), anchor=False
    )
    if not d.quiz_history:
        st.caption("No quizzes yet. Each topic's scores appear here after its first quiz.")
        return
    st.caption(
        "Weakest topic first. Weakness is what the next plan uses; the line is every quiz "
        "score on the topic, oldest to latest, on a 0-100% scale."
    )
    for row in (mastery[:3], mastery[3:]):
        for column, m in zip(st.columns(3, gap="small"), row, strict=True):
            with column, st.container(border=True, gap="small"):
                st.markdown(formatter.mastery_line(m.topic, m.weakness, m.scores))
                if m.scores:
                    st.markdown(formatter.trend_md(m.trend))
                    st.vega_lite_chart(
                        spec=charts.score_spark_spec(m.topic, m.scores),
                        width="stretch",
                        alt=f"{m.topic} quiz scores: " + ", ".join(f"{s:.0f}%" for s in m.scores),
                    )


def _readiness(d: services.Dashboard) -> None:
    scores = [r["readiness_score"] for r in d.readiness]
    st.subheader(formatter.readiness_headline(scores), anchor=False)
    labels = [formatter.local_day(r["created_at"]) for r in d.readiness]
    st.vega_lite_chart(
        spec=charts.readiness_trend_spec(scores, labels),
        width="stretch",
        alt="Readiness by profile: " + ", ".join(f"{s} of 100" for s in scores),
    )
    if len(scores) < 2:  # one point is not a trend: say how to get one
        st.caption(
            "One profile so far. Re-profile with an updated resume on the Onboard page; "
            "each profile adds a point here."
        )
    else:
        st.caption("Readiness out of 100 at each profile.")


def _interviews(d: services.Dashboard) -> None:
    if not d.sessions:
        st.subheader("No interview yet", anchor=False)
        st.caption("Each session's average score appears here after your first interview.")
        return
    averages = [float(s["avg_overall"]) for s in d.sessions]
    st.subheader(formatter.interview_headline(averages), anchor=False)
    st.vega_lite_chart(
        spec=charts.interview_trend_spec(averages, formatter.session_labels(d.sessions)),
        width="stretch",
        alt="Interview averages: " + ", ".join(f"{a:.1f} of 5" for a in averages),
    )
    st.caption("Average score per mock interview, out of 5.")


def _plans(d: services.Dashboard) -> None:
    if not d.plans:
        st.subheader("No plan yet", anchor=False)
        st.caption("Each week's minutes per topic appear here once you generate a plan.")
        return
    weeks = {p.week_no: p.minutes_by_topic() for p in d.plans}
    st.subheader(formatter.week_mix_headline(d.plans), anchor=False)
    st.vega_lite_chart(
        spec=charts.week_mix_spec(weeks), width="stretch", alt=formatter.plan_mix_alt(weeks)
    )
    week, done = d.plans_done[-1][0].week_no, len(d.plans_done[-1][1])
    st.markdown(formatter.days_done_md(week, done))
    st.caption("Minutes per week, split by topic.")


def _under_the_hood(d: services.Dashboard) -> None:
    st.divider()
    st.header("Under the hood: agents and critic", anchor=False)
    st.markdown(
        ":gray[Every agent call in this app, for all students: how often the critic rejected "
        "a draft and sent it back, and what it said.]"
    )
    if d.agent_stats:
        st.dataframe(
            formatter.agent_table(d.agent_stats),
            hide_index=True,
            width="stretch",
            column_config={
                "Rejection rate": st.column_config.ProgressColumn(
                    "Rejection rate", min_value=0, max_value=100, format="%.0f%%"
                ),
            },
        )
    else:
        st.caption("No agent calls yet.")
    st.subheader("Recent critic rejections", anchor=False)
    if d.rejections:
        st.caption("Each one sent a draft back for regeneration.")
        st.dataframe(formatter.rejections_table(d.rejections), hide_index=True, width="stretch")
    else:
        st.caption("None yet: the critic has approved every draft.")


page_header(
    "Dashboard",
    "Your progress across quizzes, plans and interviews, and below it how the agents and the "
    "critic worked.",
)
sid, profile = require_profile()
try:
    with st.skeleton(height=480):
        d = services.dashboard(sid, profile)
except services.ServiceError as e:
    if empty_state(
        "error", "Your dashboard did not load", formatter.md_escape(str(e)), "Try again"
    ):
        st.rerun()
    st.stop()

streak = d.streak
_kpis(d, streak)
_topic_mastery(d)
readiness_col, interview_col = st.columns(2, gap="medium")
with readiness_col, st.container(border=True, height="stretch"):
    _readiness(d)
with interview_col, st.container(border=True, height="stretch"):
    _interviews(d)
plans_col, activity_col = st.columns(2, gap="medium")
with plans_col, st.container(border=True, height="stretch"):
    _plans(d)
with activity_col, st.container(border=True, height="stretch"):
    _activity(streak)
_under_the_hood(d)
