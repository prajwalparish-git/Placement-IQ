"""Step 6, faculty dashboard: placement readiness across the cohort from the telemetry layer,
by stream; score distributions, the voice rubric breakdown, the most common skill gaps and
the weekly trend; Layer 3's service health; and the readiness report as CSV."""

from datetime import UTC, datetime

import streamlit as st

from piq import charts, cohort, journey
from piq.config import READY_AT, VOICE_RUBRIC_MAX
from piq.ui import Stat, empty_state, page_header, stat_row, status_badge

STATE_BADGE = {"ready": "done", "paused": "warning", "off": "todo"}

page_header(
    "Faculty dashboard",
    "Placement readiness across the cohort: by stream, in quizzes and voice assessments, and "
    "the skills students most often lack. Export the report for placement records.",
)

health = journey.service_status()
with st.expander(
    f"Services: AI {health.active_ai} · voice {health.voice} · records {health.telemetry}",
    icon=":material/health_and_safety:",
):
    st.caption(
        "Each service falls back on its own: a paused provider is retried after a cooldown, "
        "and answers keep coming from the next one."
    )
    for p in health.ai:
        status_badge(STATE_BADGE[p.state], f"{p.label}: {p.detail}")
    status_badge(
        "done" if health.voice == "ElevenLabs" else "info", f"Voice: {health.voice_detail}"
    )

view = journey.cohort_view()
if view.error:
    st.error(view.error, icon=":material/cloud_off:")
    st.stop()
if not view.rows:
    empty_state(
        "groups",
        "No activity recorded yet",
        "Students appear here once they scan a resume, build a roadmap, take a critic-checked "
        "quiz or a voice assessment. For a demonstration, load a fictional cohort with "
        "`python -m scripts.seed_cohort`.",
    )
    st.stop()

snap = view.snapshot
stream = st.pills("Stream", [cohort.ALL, *cohort.streams(view.rows)], default=cohort.ALL)
stream = stream or cohort.ALL
rows = cohort.in_stream(view.rows, stream)
assessed = [r for r in rows if r.readiness is not None]
stat_row(
    [
        Stat("Students", str(len(rows))),
        Stat(
            "Average readiness",
            f"{sum(r.readiness for r in assessed) / len(assessed):.0f}/100" if assessed else "-",
            help="Weighted mean of resume match, quiz average and voice rubric (as %).",
        ),
        Stat(f"Ready (>= {READY_AT})", str(sum(r.band == "Ready" for r in rows))),
        Stat("Quizzes", str(sum(r.quizzes for r in rows))),
        Stat("Voice sessions", str(sum(r.voice_sessions for r in rows))),
    ]
)

if stream == cohort.ALL:
    summaries = cohort.stream_summaries(view.rows)
    with st.container(border=True):
        st.subheader(cohort.streams_takeaway(summaries), anchor=False)
        if bars := cohort.chart_streams(summaries):
            st.vega_lite_chart(charts.stream_readiness_spec(bars), width="stretch")
        st.caption("Average placement readiness per stream (0-100). Hover a bar for its parts.")

quiz_scores = cohort.quiz_scores(snap, stream)
trend = cohort.weekly_quiz_trend(snap, stream)
left, right = st.columns(2, gap="medium")
with left, st.container(border=True, height="stretch"):
    st.subheader(f"{len(quiz_scores)} quiz attempts", anchor=False)
    if quiz_scores:
        st.vega_lite_chart(
            charts.histogram_spec(quiz_scores, top=100, step=10, noun="Score (%)"),
            width="stretch",
        )
    st.caption("How many attempts scored in each band of 10%.")
with right, st.container(border=True, height="stretch"):
    if len(trend) >= 2:
        first, last = trend[0][1], trend[-1][1]
        st.subheader(
            f"Quiz scores went from {first:.0f}% to {last:.0f}% over {len(trend)} weeks",
            anchor=False,
        )
        weeks = [(w.strftime("%d %b"), avg, n) for w, avg, n in trend]
        st.vega_lite_chart(charts.cohort_trend_spec(weeks), width="stretch")
        st.caption("Average quiz score per week (weeks start on Monday).")
    else:
        st.subheader("Weekly trend", anchor=False)
        st.caption("The trend appears once quizzes span two weeks.")

rubric_totals = cohort.rubric_totals(snap, stream)
breakdown = cohort.rubric_breakdown(snap, stream)
left, right = st.columns(2, gap="medium")
with left, st.container(border=True, height="stretch"):
    st.subheader(f"{len(rubric_totals)} voice assessments", anchor=False)
    if rubric_totals:
        st.vega_lite_chart(
            charts.histogram_spec(rubric_totals, top=VOICE_RUBRIC_MAX, step=1, noun="Rubric"),
            width="stretch",
        )
    st.caption(f"How many sessions scored each total out of {VOICE_RUBRIC_MAX}.")
with right, st.container(border=True, height="stretch"):
    weakest = min(breakdown, key=breakdown.get) if breakdown else None
    st.subheader(
        f"Weakest criterion: {weakest}" if weakest else "No voice assessments yet", anchor=False
    )
    if breakdown:
        st.vega_lite_chart(charts.rubric_breakdown_spec(breakdown), width="stretch")
    st.caption("Average score per rubric criterion, out of 5.")

gaps = cohort.skill_gaps(rows)
scanned = sum(r.resume_match is not None for r in rows)
with st.container(border=True):
    st.subheader(cohort.gaps_takeaway(gaps, scanned), anchor=False)
    if gaps:
        st.vega_lite_chart(charts.gap_bars_spec(gaps, scanned), width="stretch")
    st.caption("Skills missing from students' latest resume scan, most common first.")

st.subheader("Placement readiness report", anchor=False)
st.dataframe(cohort.report_rows(rows), hide_index=True, width="stretch")
stamp = datetime.now(UTC).strftime("%Y-%m-%d")
slug = "all" if stream == cohort.ALL else stream.lower().replace(" ", "-")
st.download_button(
    "Export placement readiness report",
    cohort.report_csv(rows),
    file_name=f"placement-readiness-{slug}-{stamp}.csv",
    mime="text/csv",
    type="primary",
    icon=":material/download:",
)
st.caption(
    "One row per student: readiness and band, resume match, quiz and voice results, proctor "
    "flags, study progress and missing skills. Opens in any spreadsheet."
)
