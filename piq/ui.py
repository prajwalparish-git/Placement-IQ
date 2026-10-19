"""Streamlit helpers shared by the views: student selection and the visible agent loop."""

from collections.abc import Callable

import streamlit as st

from piq import formatter, services
from piq.graph import CriticRejected, OnEvent
from piq.llm import LLMError
from piq.resume import ResumeError
from piq.schemas import StudentProfile

NEW = "— new student —"
PER_STUDENT_KEYS = ("quiz", "quiz_result", "interview")
RUN_PREFIX = "run:"  # session key prefix for persisted agent step logs
FAILED = "failed: "
USER_ERRORS = (CriticRejected, LLMError, services.ServiceError, ResumeError)


def set_student(student_id: str | None, keep_runs: tuple[str, ...] = ()) -> None:
    """Make `student_id` current. On a change, drop the previous student's quiz, interview and
    agent step logs, except the logs of `keep_runs` (labels) already made for the new student.
    """
    if student_id != st.session_state.get("student_id"):
        kept = {RUN_PREFIX + label for label in keep_runs}
        for k in list(st.session_state):
            if k in PER_STUDENT_KEYS or (str(k).startswith(RUN_PREFIX) and k not in kept):
                del st.session_state[k]
    st.session_state["student_id"] = student_id


def student_selector() -> None:
    students = services.list_students()
    labels = {f"{s['usn']} — {s['name']}": s["id"] for s in students}
    ids = list(labels.values())
    current = st.session_state.get("student_id")
    index = ids.index(current) + 1 if current in ids else 0
    choice = st.sidebar.selectbox("Student", [NEW, *labels], index=index)
    set_student(labels.get(choice))
    # Refreshed on every run before the page renders, so pages reuse it instead of a query.
    selected = next((s for s in students if s["id"] == labels.get(choice)), None)
    st.session_state["student"] = dict(selected) if selected else None


def current_student() -> dict | None:
    """The selected student's row (id, name, usn, target_role, readiness_score), or None."""
    return st.session_state.get("student")


def require_profile() -> tuple[str, StudentProfile]:
    sid = st.session_state.get("student_id")
    profile = services.current_profile(sid)
    if not profile:
        st.info("Select a student in the sidebar, or onboard one on the Onboard page.")
        st.stop()
    return sid, profile


def _rejected(events: list[str]) -> bool:
    return any(m.startswith("critic rejected") for m in events)


def _failed(events: list[str]) -> bool:
    return any(m.startswith(FAILED) for m in events)


def _line(msg: str) -> str:
    text = formatter.critic_text(msg)  # critic reasons quote LLM output
    if msg.startswith(FAILED):
        return "❌ " + text
    return ("🔁 " if msg.startswith("critic rejected") else "✔️ ") + text


def run_agent[T](label: str, fn: Callable[[OnEvent], T]) -> T | None:
    """Run an agent call inside a live status box that shows every generate/critic step.

    The step log (including a failure) is also kept in session state: views call
    `st.rerun()` after saving, which would otherwise wipe the only visible evidence
    of the critic loop. Returns None after showing a user-facing error.
    """
    events: list[str] = []
    with st.status(label, expanded=True) as box:

        def on_event(msg: str) -> None:
            events.append(msg)
            box.write(_line(msg))

        try:
            out = fn(on_event)
        except USER_ERRORS as e:
            events.append(f"{FAILED}{e}")
            box.update(label=f"{label} — failed", state="error")
            st.error(formatter.critic_text(str(e)))
            return None
        finally:
            st.session_state[RUN_PREFIX + label] = events
        box.update(label=f"{label} — done", state="complete", expanded=_rejected(events))
    return out


def show_last_run(label: str) -> None:
    """Re-render the step log of the last `run_agent(label, ...)`.

    Expanded when it contained a retry or a failure, so neither goes unnoticed.
    """
    events = st.session_state.get(RUN_PREFIX + label)
    if events:
        failed = _failed(events)
        with st.status(
            f"{label} — last run{' failed' if failed else ''}",
            state="error" if failed else "complete",
            expanded=failed or _rejected(events),
        ):
            for m in events:
                st.write(_line(m))
