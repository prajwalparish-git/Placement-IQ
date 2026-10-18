import uuid

import streamlit as st

from piq import agents, db, formatter
from piq.config import INTERVIEW_TYPES
from piq.ui import require_profile, run_agent, show_last_run

st.header("Mock interview")
sid, profile = require_profile()
iv = st.session_state.get("interview")

if iv is None:
    kind = st.radio("Interview type", INTERVIEW_TYPES, horizontal=True)
    if st.button("Start session", type="primary"):
        session_id = uuid.uuid4().hex
        past = db.past_turns(sid, exclude_session=session_id)
        turn = run_agent(
            "Interview agent", lambda ev: agents.next_question(profile, kind, [], past, sid, ev)
        )
        if turn:
            st.session_state["interview"] = {
                "session_id": session_id,
                "type": kind,
                "past": past,
                "history": [],
                "turn": turn,
                "done": False,
            }
            st.rerun()
    st.stop()

for h in iv["history"]:
    st.chat_message("assistant").markdown(h["question"])
    st.chat_message("user").markdown(h["answer"])
    with (
        st.chat_message("assistant", avatar="📊"),
        st.expander(f"Feedback — {h['eval'].overall}/5"),
    ):
        st.markdown(formatter.evaluation_md(h["eval"]))

if iv["done"]:
    avg = sum(h["eval"].overall for h in iv["history"]) / len(iv["history"])
    st.success(f"Session complete — average {avg:.2f}/5 over {len(iv['history'])} questions.")
    if st.button("New session"):
        st.session_state.pop("interview")
        st.rerun()
    st.stop()

turn = iv["turn"]
show_last_run("Interview agent")
st.chat_message("assistant").markdown(f"{turn.question}  \n_{formatter.turn_label(turn)}_")
if answer := st.chat_input("Your answer"):
    ev = run_agent(
        "Evaluator",
        lambda _: agents.evaluate_answer(profile, iv["type"], turn.question, answer, sid),
    )
    if ev is None:
        st.stop()
    db.save_turn(sid, iv["session_id"], iv["type"], turn.question, answer, ev)
    iv["history"].append({"question": turn.question, "answer": answer, "eval": ev})
    if turn.is_final:
        iv["done"] = True
    else:
        qa = [{"question": h["question"], "answer": h["answer"]} for h in iv["history"]]
        nxt = run_agent(
            "Interview agent",
            lambda e: agents.next_question(profile, iv["type"], qa, iv["past"], sid, e),
        )
        if nxt is None:
            st.stop()
        iv["turn"] = nxt
    st.rerun()
