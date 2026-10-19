"""Weekly plan: what to study on each day of the week, why, and how the plan moved since the
week before. The next week is generated from the latest weakness scores."""

import streamlit as st

from piq import charts, formatter, services
from piq.ui import empty_state, page_header, require_profile, run_agent, show_last_run

page_header(
    "Weekly plan",
    "Seven days of study, most of it on your weakest topics. Each new week is planned from "
    "your latest quiz scores, and a critic checks it before you see it.",
)
sid, profile = require_profile()
ov = services.plan_overview(sid, profile)

if st.button(
    f"Generate week {ov.next_week} plan", type="primary", icon=":material/autorenew:"
) and run_agent("Planner agent", lambda ev: services.generate_next_plan(sid, ev)):
    st.rerun()
show_last_run("Planner agent")

plan_col, side_col = st.columns([2, 1], gap="medium")
previous = None
with plan_col:
    if not ov.plans:
        empty_state(
            "calendar_month",
            "No plan yet",
            "Generate week 1 with the button above. The planner turns your weakness scores "
            "into seven days of practice, most of it on your weakest topics.",
        )
    else:
        weeks = [p.week_no for p in ov.plans]
        week = st.pills(  # chips wrap onto more rows on a phone, however many weeks
            "Week",
            weeks,
            format_func=lambda w: f"Week {w}",
            default=weeks[-1],
            required=True,
            label_visibility="collapsed",
            wrap=True,
        )
        shown = next(p for p in ov.plans if p.week_no == week)
        previous = next((p for p in ov.plans if p.week_no == shown.week_no - 1), None)
        with st.container(border=True):
            st.subheader(f"Week {shown.week_no}", anchor=False)
            st.caption(formatter.plan_summary(shown))
            st.info(
                f"**Why this plan.** {formatter.md_escape(shown.rationale)}",
                icon=":material/lightbulb:",
            )
            if st.toggle("Table view", help="The same seven days as a table."):
                st.dataframe(formatter.plan_table(shown), width="stretch")
            else:
                st.html(formatter.plan_days_html(shown))

with side_col:
    # What changed in the week shown, then the weakness the next week will be planned from.
    if previous:
        before, after = previous.minutes_by_topic(), shown.minutes_by_topic()
        pair = (previous.week_no, shown.week_no)
        with st.container(border=True):
            st.subheader(
                formatter.minutes_shift_headline(before, after, previous.week_no), anchor=False
            )
            st.vega_lite_chart(
                spec=charts.minutes_shift_spec(before, after, pair),
                width="stretch",
                alt=formatter.minutes_shift_alt(before, after, pair),
            )
            st.caption(
                f"Minutes per topic. Hollow grey dot: week {pair[0]}. Filled dot, in the "
                f"topic's colour: week {pair[1]}."
            )
    with st.container(border=True):
        st.subheader(formatter.weakness_headline(ov.weakness), anchor=False)
        st.vega_lite_chart(
            spec=charts.weakness_spec(ov.weakness),
            width="stretch",
            alt=formatter.weakness_alt(ov.weakness),
        )
        st.caption(f"{formatter.weakness_caption()} {formatter.weakness_source()}")
