"""Weekly plan: what to study on each day of the week, why, and how the plan moved since the
week before. The next week is generated from the latest weakness scores."""

import streamlit as st

from piq import charts, formatter, services
from piq.config import STUDY_TIME, TIMEZONE
from piq.ui import empty_state, page_header, require_profile, run_agent, show_last_run


def _days_done(sid: str, week_no: int, saved: set[int]) -> set[int]:
    """Tick the days of the week you finished; a change is saved at once."""
    picked = st.pills(
        "Days done",
        list(range(1, 8)),
        selection_mode="multi",
        default=sorted(saved),
        format_func=lambda d: f"Day {d}",
        key=f"plan_done_{sid}_{week_no}",  # per student: a switch must not carry ticks over
        help="Home and the Dashboard count the days you mark here.",
        wrap=True,
    )
    if set(picked) != saved:
        return services.set_days_done(sid, week_no, picked)
    return saved


def _export(plan: services.WeeklyPlan) -> None:
    """The shown week as a calendar file or a table, to keep outside the app."""
    with st.expander("Export this week", icon=":material/download:"):
        first = st.date_input(
            "First day", value=formatter.next_monday(formatter.local_today()), format="DD/MM/YYYY"
        )
        at = st.time_input("Study time each day", value=STUDY_TIME, step=1800)
        st.caption(
            f"Times are {TIMEZONE} time. Each day becomes one event, as long as that day's minutes."
        )
        name = f"placementiq-week-{plan.week_no}"
        with st.container(horizontal=True):
            st.download_button(
                "Calendar (.ics)",
                formatter.plan_ics(plan, first, at),
                file_name=f"{name}.ics",
                mime="text/calendar",
                icon=":material/event:",
                on_click="ignore",
            )
            st.download_button(
                "Table (.csv)",
                formatter.plan_csv(plan),
                file_name=f"{name}.csv",
                mime="text/csv",
                icon=":material/table_view:",
                on_click="ignore",
            )


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
            done = _days_done(sid, shown.week_no, ov.done.get(shown.week_no, set()))
            st.info(
                f"**Why this plan.** {formatter.md_escape(shown.rationale)}",
                icon=":material/lightbulb:",
            )
            if st.toggle("Table view", help="The same seven days as a table."):
                st.dataframe(formatter.plan_table(shown), width="stretch")
            else:
                st.html(formatter.plan_days_html(shown, done))
            _export(shown)

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
