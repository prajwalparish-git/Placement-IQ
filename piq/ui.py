"""Streamlit helpers shared by the views: student selection and the visible agent loop."""

from collections.abc import Callable

import streamlit as st

from piq import db
from piq.graph import CriticRejected, OnEvent
from piq.llm import LLMError
from piq.schemas import StudentProfile

NEW = "— new student —"
PER_STUDENT_KEYS = ("quiz", "quiz_result", "interview")
RUN_PREFIX = "run:"  # session key prefix for persisted agent step logs


def student_selector() -> None:
    students = db.list_students()
    labels = {f"{s['usn']} — {s['name']}": s["id"] for s in students}
    ids = list(labels.values())
    current = st.session_state.get("student_id")
    index = ids.index(current) + 1 if current in ids else 0
    choice = st.sidebar.selectbox("Student", [NEW, *labels], index=index)
    new_id = labels.get(choice)
    if new_id != current:
        st.session_state["student_id"] = new_id
        for k in list(st.session_state):
            if k in PER_STUDENT_KEYS or str(k).startswith(RUN_PREFIX):
                del st.session_state[k]


def require_profile() -> tuple[str, StudentProfile]:
    sid = st.session_state.get("student_id")
    profile = db.latest_profile(sid) if sid else None
    if not profile:
        st.info("Select a student in the sidebar, or onboard one on the Onboard page.")
        st.stop()
    return sid, profile


def _rejected(events: list[str]) -> bool:
    return any(m.startswith("critic rejected") for m in events)


def _line(msg: str) -> str:
    return ("🔁 " if msg.startswith("critic rejected") else "✔️ ") + msg


def run_agent[T](label: str, fn: Callable[[OnEvent], T]) -> T | None:
    """Run an agent call inside a live status box that shows every generate/critic step.

    The step log is also kept in session state: views call `st.rerun()` after saving,
    which would otherwise wipe the only visible evidence of the critic loop.
    """
    events: list[str] = []
    with st.status(label, expanded=True) as box:

        def on_event(msg: str) -> None:
            events.append(msg)
            box.write(_line(msg))

        try:
            out = fn(on_event)
        except (CriticRejected, LLMError) as e:
            box.update(label=f"{label} — failed", state="error")
            st.error(str(e))
            return None
        finally:
            st.session_state[RUN_PREFIX + label] = events
        box.update(label=f"{label} — done", state="complete", expanded=_rejected(events))
    return out


def show_last_run(label: str) -> None:
    """Re-render the step log of the last `run_agent(label, ...)`; expanded if it had retries."""
    events = st.session_state.get(RUN_PREFIX + label)
    if events:
        with st.status(f"{label} — last run", state="complete", expanded=_rejected(events)):
            for m in events:
                st.write(_line(m))
