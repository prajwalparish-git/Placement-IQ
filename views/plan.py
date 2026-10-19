import streamlit as st

from piq import formatter, services
from piq.ui import require_profile, run_agent, show_last_run

st.header("Weekly plan")
sid, profile = require_profile()
ov = services.plan_overview(sid, profile)

left, right = st.columns([1, 2])
with left:
    st.subheader("Current weakness")
    st.dataframe(formatter.weakness_table(ov.weakness), width="stretch")
    st.caption("1 = weak. From the last 3 quiz scores per topic, else from resume gaps.")
    if st.button(f"Generate week {ov.next_week} plan", type="primary") and run_agent(
        "Planner agent", lambda ev: services.generate_next_plan(sid, ev)
    ):
        st.rerun()
    show_last_run("Planner agent")

with right:
    if not ov.plans:
        st.info("No plan yet. Generate week 1.")
        st.stop()
    week = st.selectbox("Week", [p.week_no for p in ov.plans], index=len(ov.plans) - 1)
    shown = next(p for p in ov.plans if p.week_no == week)
    st.markdown(f"**Rationale:** {formatter.md_escape(shown.rationale)}")
    st.dataframe(formatter.plan_table(shown), width="stretch")

if len(ov.plans) >= 2:
    st.subheader("Minutes per topic, week over week")
    st.bar_chart(formatter.plan_minutes(ov.plans[-2:]), stack=False)
