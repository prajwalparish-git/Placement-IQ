import pandas as pd
import streamlit as st

from piq import db, formatter
from piq.ui import require_profile

st.header("Dashboard")
sid, profile = require_profile()

c1, c2, c3 = st.columns(3)
c1.metric("Readiness", f"{profile.readiness_score}/100")
quizzes = db.quiz_history(sid)
c2.metric("Quizzes taken", len(quizzes))
sessions = db.interview_history(sid)
c3.metric("Interview sessions", len(sessions))

st.subheader("Quiz score by topic (attempt order)")
trend = formatter.score_trend(quizzes)
if trend.empty:
    st.caption("No quizzes yet.")
else:
    st.line_chart(trend, y_label="score %")

plans = db.list_plans(sid)
if plans:
    st.subheader("Plan minutes per topic, all weeks")
    st.bar_chart(formatter.plan_minutes(plans), stack=False)

if sessions:
    st.subheader("Interview average score per session")
    df = pd.DataFrame([dict(r) for r in sessions])
    st.line_chart(df.set_index("started")["avg_overall"], y_label="overall /5")

st.subheader("Agent activity (all students)")
stats = db.agent_stats()
if stats:
    st.dataframe(pd.DataFrame([dict(r) for r in stats]).set_index("agent_name"), width="stretch")
rejections = db.recent_rejections()
if rejections:
    st.caption("Recent critic rejections — each one triggered a regeneration.")
    st.dataframe(pd.DataFrame([dict(r) for r in rejections]), width="stretch", hide_index=True)
