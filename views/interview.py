import streamlit as st

from piq import formatter, services
from piq.config import INTERVIEW_TYPES
from piq.ui import require_profile, run_agent, show_last_run

st.header("Mock interview")
sid, _ = require_profile()
session: services.InterviewSession | None = st.session_state.get("interview")

if session is None:
    kind = st.radio("Interview type", INTERVIEW_TYPES, horizontal=True)
    if st.button("Start session", type="primary"):
        session = run_agent("Interview agent", lambda ev: services.start_interview(sid, kind, ev))
        if session:
            st.session_state["interview"] = session
            st.rerun()
    show_last_run("Interview agent")
    st.stop()

for turn in session.history:
    st.chat_message("assistant").markdown(formatter.md_escape(turn.question))
    st.chat_message("user").markdown(formatter.md_escape(turn.answer))
    with (
        st.chat_message("assistant", avatar="📊"),
        st.expander(f"Feedback — {turn.evaluation.overall}/5"),
    ):
        st.markdown(formatter.evaluation_md(turn.evaluation))

if session.done:
    st.success(
        f"Session complete — average {session.average:.2f}/5 over {len(session.history)} questions."
    )
    if st.button("New session"):
        st.session_state.pop("interview")
        st.rerun()
    st.stop()

show_last_run("Interview agent")
if session.current is None:  # the answer is saved; only the follow-up question failed
    if st.button("Retry next question", type="primary"):
        nxt = run_agent("Interview agent", lambda ev: services.continue_interview(sid, session, ev))
        if nxt:
            st.session_state["interview"] = nxt
            st.rerun()
    st.stop()

current = session.current
st.chat_message("assistant").markdown(
    f"{formatter.md_escape(current.question)}  \n_{formatter.turn_label(current)}_"
)
if answer := st.chat_input("Your answer"):
    answered = run_agent("Evaluator", lambda _: services.answer_question(sid, session, answer))
    if answered is None:
        st.stop()
    st.session_state["interview"] = answered
    if not answered.done:
        nxt = run_agent(
            "Interview agent", lambda ev: services.continue_interview(sid, answered, ev)
        )
        if nxt:
            st.session_state["interview"] = nxt
    st.rerun()
