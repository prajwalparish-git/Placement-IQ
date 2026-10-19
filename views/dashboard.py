import pandas as pd
import streamlit as st

from piq import formatter, services
from piq.ui import require_profile

st.header("Dashboard")
sid, profile = require_profile()
d = services.dashboard(sid, profile)

c1, c2, c3 = st.columns(3)
c1.metric("Readiness", f"{d.profile.readiness_score}/100")
c2.metric("Quizzes taken", len(d.quiz_history))
c3.metric("Interview sessions", len(d.sessions))

st.subheader("Quiz score by topic (attempt order)")
trend = formatter.score_trend(d.quiz_history)
if trend.empty:
    st.caption("No quizzes yet.")
else:
    st.line_chart(trend, y_label="score %")

if d.plans:
    st.subheader("Plan minutes per topic, all weeks")
    st.bar_chart(formatter.plan_minutes(d.plans), stack=False)

if d.sessions:
    st.subheader("Interview average score per session")
    df = pd.DataFrame([dict(r) for r in d.sessions])
    st.line_chart(df.set_index("started")["avg_overall"], y_label="overall /5")

st.subheader("Agent activity (all students)")
if d.agent_stats:
    stats = pd.DataFrame([dict(r) for r in d.agent_stats]).set_index("agent_name")
    st.dataframe(stats, width="stretch")
if d.rejections:
    st.caption("Recent critic rejections — each one triggered a regeneration.")
    st.dataframe(pd.DataFrame([dict(r) for r in d.rejections]), width="stretch", hide_index=True)
