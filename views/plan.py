import streamlit as st

from piq import agents, checks, db, formatter
from piq.ui import require_profile, run_agent, show_last_run

st.header("Weekly plan")
sid, profile = require_profile()

plans = db.list_plans(sid)
scores = db.topic_performance(sid)
weakness = checks.topic_weakness(scores, agents.missing_topics(profile))
next_week = plans[-1].week_no + 1 if plans else 1

left, right = st.columns([1, 2])
with left:
    st.subheader("Current weakness")
    st.dataframe(formatter.weakness_table(weakness), width="stretch")
    st.caption("1 = weak. From the last 3 quiz scores per topic, else from resume gaps.")
    if st.button(f"Generate week {next_week} plan", type="primary"):
        plan = run_agent(
            "Planner agent",
            lambda ev: agents.plan_week(
                profile, scores, next_week, plans[-1] if plans else None, sid, ev
            ),
        )
        if plan:
            db.save_plan(sid, plan)
            st.rerun()
    show_last_run("Planner agent")

with right:
    if not plans:
        st.info("No plan yet. Generate week 1.")
        st.stop()
    week = st.selectbox("Week", [p.week_no for p in plans], index=len(plans) - 1)
    shown = next(p for p in plans if p.week_no == week)
    st.markdown(f"**Rationale:** {shown.rationale}")
    st.dataframe(formatter.plan_table(shown), width="stretch")

if len(plans) >= 2:
    st.subheader("Minutes per topic, week over week")
    st.bar_chart(formatter.plan_minutes(plans[-2:]), stack=False)
