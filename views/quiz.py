import streamlit as st

from piq import agents, db, formatter
from piq.checks import text_hash
from piq.config import DIFFICULTIES, TOPICS
from piq.ui import require_profile, run_agent, show_last_run

st.header("Quiz")
sid, _ = require_profile()

if result := st.session_state.get("quiz_result"):
    quiz, chosen, pct, nxt = result
    st.markdown(formatter.score_line(pct, quiz.topic, nxt))
    st.markdown(formatter.quiz_review_md(quiz, chosen))
    if st.button("New quiz"):
        st.session_state.pop("quiz_result")
        st.rerun()
    st.stop()

quiz = st.session_state.get("quiz")
if quiz is None:
    topic = st.selectbox("Topic", TOPICS)
    last = db.last_attempt(sid, topic)
    suggested = agents.suggest_difficulty(
        last["score_pct"] if last else None, last["difficulty"] if last else "medium"
    )
    difficulty = st.radio(
        "Difficulty",
        DIFFICULTIES,
        index=DIFFICULTIES.index(suggested),
        horizontal=True,
        help="Pre-selected from your last score on this topic.",
    )
    if st.button("Generate quiz", type="primary"):
        previous = db.asked_questions(sid, topic)
        quiz = run_agent(
            "Quiz agent",
            lambda ev: agents.make_quiz(topic, difficulty, previous, student_id=sid, on_event=ev),
        )
        if quiz:
            st.session_state["quiz"] = quiz
            st.rerun()
    st.stop()

st.subheader(f"{quiz.topic} · {quiz.difficulty}")
show_last_run("Quiz agent")
qid = text_hash(quiz.questions[0].text)  # fresh widget keys per quiz: no stale answers
with st.form(f"quiz-{qid}"):
    chosen = [
        st.radio(
            f"**Q{i}.** {q.text}",
            range(4),
            format_func=lambda j, q=q: q.options[j],
            index=None,
            key=f"{qid}-{i}",
        )
        for i, q in enumerate(quiz.questions, 1)
    ]
    if st.form_submit_button("Submit", type="primary"):
        pct = db.save_quiz_attempt(sid, quiz, chosen)
        nxt = agents.suggest_difficulty(pct, quiz.difficulty)
        st.session_state["quiz_result"] = (quiz, chosen, pct, nxt)
        st.session_state.pop("quiz")
        st.rerun()
