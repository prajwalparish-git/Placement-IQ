import re

import streamlit as st

from piq import agents, db, formatter
from piq.config import DATA_DIR
from piq.resume import ResumeError, extract_text
from piq.ui import run_agent, show_last_run

SAMPLES = sorted((DATA_DIR / "sample_resumes").glob("*.txt"))
USN_RE = re.compile(r"^[A-Z0-9]{4,20}$")

st.header("Onboard")

sid = st.session_state.get("student_id")
profile = db.latest_profile(sid) if sid else None
if profile:
    st.markdown(formatter.profile_md(profile))
    show_last_run("Profile agent")
    st.divider()

current_usn = next((s["usn"] for s in db.list_students() if s["id"] == sid), "")
role_names = list(agents.roles())
role_index = (
    role_names.index(profile.target_role) if profile and profile.target_role in role_names else 0
)

with st.form("onboard"):
    st.subheader("Re-profile this student" if profile else "New student")
    usn = st.text_input("USN (required)", value=current_usn).strip().upper()
    role = st.selectbox("Target role", role_names, index=role_index)
    upload = st.file_uploader("Resume (PDF, DOCX or TXT)", type=["pdf", "docx", "txt"])
    sample = st.selectbox("…or use a sample resume", ["—", *(p.name for p in SAMPLES)])
    submitted = st.form_submit_button("Analyse resume", type="primary")

if submitted:
    if not USN_RE.match(usn):
        st.error("USN is required: 4-20 letters/digits, no spaces.")
        st.stop()
    try:
        if upload:
            text = extract_text(upload.name, upload.getvalue())
        elif sample != "—":
            text = (DATA_DIR / "sample_resumes" / sample).read_text(encoding="utf-8")
        else:
            st.error("Upload a resume or pick a sample.")
            st.stop()
    except ResumeError as e:
        st.error(str(e))
        st.stop()

    new_profile = run_agent("Profile agent", lambda ev: agents.create_profile(text, role, ev))
    if new_profile:
        st.session_state["student_id"] = db.save_profile(usn, new_profile)
        st.rerun()
