"""Quiz: five questions on one topic, each checked by a critic before you see it. The score
sets the next difficulty and counts toward next week's plan."""

import streamlit as st

from piq import formatter, services
from piq.config import DIFFICULTIES, QUIZ_SIZE
from piq.ui import page_header, require_profile, run_agent, show_last_run

NEXT = (
    (
        "fact_check",
        "A critic checks every question first. A flawed one is rewritten, and the trail shows why.",
    ),
    ("checklist", f"Answer the {QUIZ_SIZE} questions, then submit."),
    (
        "autorenew",
        "Your score sets the next difficulty and counts toward the topic's weakness in next "
        "week's plan.",
    ),
)


def _setup(sid: str, profile: services.StudentProfile) -> None:
    setup = services.quiz_setup(sid, profile)
    topics = setup.topics
    st.session_state.setdefault("quiz_topic", topics[0])  # Home may have preselected one
    setup_col, next_col = st.columns([3, 2], gap="medium")
    with setup_col, st.container(border=True):
        st.subheader("Set up a quiz", anchor=False)
        topic = st.pills(
            "Topic",
            topics,
            format_func=lambda t: formatter.topic_option(t, setup.weakness[t]),
            key="quiz_topic",
            required=True,
            wrap=True,
        )
        st.caption("Weakest first. 0% weak is strong, 100% weak needs the most practice.")
        suggested = setup.suggested(topic)
        difficulty = st.segmented_control(
            "Difficulty",
            DIFFICULTIES,
            format_func=str.capitalize,
            default=suggested,  # no key: a new topic resets it to that topic's suggestion
            required=True,
        )
        st.markdown(formatter.suggestion_md(topic, setup.last.get(topic), suggested))
        if st.button("Generate quiz", type="primary", icon=":material/quiz:"):
            quiz = run_agent(
                "Quiz agent", lambda ev: services.start_quiz(sid, topic, difficulty, ev)
            )
            if quiz:
                st.session_state["quiz"] = quiz
                st.rerun()
        show_last_run("Quiz agent")  # keeps a failed generation visible
    with next_col, st.container(border=True):
        st.subheader("What happens next", anchor=False)
        for n, (icon, text) in enumerate(NEXT, 1):
            st.markdown(f":primary[:material/{icon}:] **{n}.** {text}")


def _take(sid: str, quiz: services.QuizSet) -> None:
    st.subheader(f"{quiz.topic} quiz · {quiz.difficulty}", anchor=False)
    show_last_run("Quiz agent")
    st.caption(
        f"Pick one answer for each of the {len(quiz.questions)} questions, then submit; "
        "nothing is marked until you do."
    )
    qid = services.quiz_key(quiz)  # fresh widget keys per quiz: no stale answers
    with st.form(f"quiz-{qid}", border=False):
        chosen = []
        for i, q in enumerate(quiz.questions, 1):
            with st.container(border=True):
                chosen.append(
                    st.radio(
                        f"**Q{i}.** {formatter.md_escape(q.text)}",
                        range(4),
                        format_func=lambda j, q=q: formatter.md_escape(q.options[j]),
                        index=None,
                        key=f"{qid}-{i}",
                    )
                )
        submitted = st.form_submit_button("Submit", type="primary", icon=":material/done_all:")
    if submitted:
        st.session_state["quiz_result"] = services.submit_quiz(sid, quiz, chosen)
        st.session_state.pop("quiz")
        st.rerun()


def _review(result: services.QuizResult) -> None:
    quiz, total = result.quiz, len(result.quiz.questions)
    with st.container(border=True):
        st.subheader(f"{quiz.topic} quiz · {quiz.difficulty}: your result", anchor=False)
        with st.container(horizontal=True, gap="large"):
            st.metric("Score", f"{result.score_pct:.0f}%", width="content")
            st.metric("Correct", f"{result.correct}/{total}", width="content")
        st.markdown(
            formatter.result_md(
                result.correct, total, quiz.topic, quiz.difficulty, result.next_difficulty
            )
        )
        with st.container(horizontal=True, vertical_alignment="center"):
            if st.button("New quiz", type="primary", icon=":material/restart_alt:"):
                st.session_state.pop("quiz_result")
                st.rerun()
            st.page_link(
                "views/plan.py", label="Open Weekly plan", icon=":material/calendar_month:"
            )
    st.subheader("Question by question", anchor=False)
    for block in formatter.quiz_review(quiz, result.chosen):
        st.container(border=True).markdown(block)


page_header(
    "Quiz",
    f"Short quizzes of {QUIZ_SIZE} questions on one topic, each checked by a critic before "
    "you see it. Your score sets the next difficulty and counts toward next week's plan.",
)
sid, profile = require_profile()

if result := st.session_state.get("quiz_result"):
    _review(result)
elif quiz := st.session_state.get("quiz"):
    _take(sid, quiz)
else:
    _setup(sid, profile)
