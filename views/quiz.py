import streamlit as st

from piq import formatter, services
from piq.checks import text_hash
from piq.config import DIFFICULTIES, TOPICS
from piq.ui import require_profile, run_agent, show_last_run

st.header("Quiz")
sid, _ = require_profile()

if result := st.session_state.get("quiz_result"):
    st.markdown(formatter.score_line(result.score_pct, result.quiz.topic, result.next_difficulty))
    st.markdown(formatter.quiz_review_md(result.quiz, result.chosen))
    if st.button("New quiz"):
        st.session_state.pop("quiz_result")
        st.rerun()
    st.stop()

quiz = st.session_state.get("quiz")
if quiz is None:
    topic = st.selectbox("Topic", TOPICS, key="quiz_topic")  # Home can preselect it
    suggested = services.suggested_difficulty(sid, topic)
    difficulty = st.radio(
        "Difficulty",
        DIFFICULTIES,
        index=DIFFICULTIES.index(suggested),
        horizontal=True,
        help="Pre-selected from your last score on this topic.",
    )
    if st.button("Generate quiz", type="primary"):
        quiz = run_agent("Quiz agent", lambda ev: services.start_quiz(sid, topic, difficulty, ev))
        if quiz:
            st.session_state["quiz"] = quiz
            st.rerun()
    show_last_run("Quiz agent")  # keeps a failed generation visible
    st.stop()

st.subheader(f"{quiz.topic} · {quiz.difficulty}")
show_last_run("Quiz agent")
qid = text_hash(quiz.questions[0].text)  # fresh widget keys per quiz: no stale answers
with st.form(f"quiz-{qid}"):
    chosen = [
        st.radio(
            f"**Q{i}.** {formatter.md_escape(q.text)}",
            range(4),
            format_func=lambda j, q=q: formatter.md_escape(q.options[j]),
            index=None,
            key=f"{qid}-{i}",
        )
        for i, q in enumerate(quiz.questions, 1)
    ]
    if st.form_submit_button("Submit", type="primary"):
        st.session_state["quiz_result"] = services.submit_quiz(sid, quiz, chosen)
        st.session_state.pop("quiz")
        st.rerun()
