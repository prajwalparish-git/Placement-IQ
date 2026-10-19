import streamlit as st

from piq import formatter, services
from piq.resume import ResumeError
from piq.ui import run_agent, set_student, show_last_run

st.header("Onboard")

sid = st.session_state.get("student_id")
profile = services.current_profile(sid)
if profile:
    st.markdown(formatter.profile_md(profile))
    show_last_run("Profile agent")
    st.divider()

roles = services.target_roles()
role_index = roles.index(profile.target_role) if profile and profile.target_role in roles else 0

with st.form("onboard"):
    st.subheader("Re-profile this student" if profile else "New student")
    usn = st.text_input("USN (required)", value=services.usn_of(sid))
    role = st.selectbox("Target role", roles, index=role_index)
    upload = st.file_uploader("Resume (PDF, DOCX or TXT)", type=["pdf", "docx", "txt"])
    sample = st.selectbox("…or use a sample resume", ["—", *services.sample_resumes()])
    submitted = st.form_submit_button("Analyse resume", type="primary")

if submitted:
    try:
        usn = services.normalise_usn(usn)
        if upload:
            text = services.read_resume(upload.name, upload.getvalue())
        elif sample != "—":
            text = services.load_sample(sample)
        else:
            raise services.ServiceError("Upload a resume or pick a sample.")
    except (services.ServiceError, ResumeError) as e:
        st.error(str(e))
        st.stop()

    result = run_agent("Profile agent", lambda ev: services.onboard(usn, role, text, ev))
    if result:
        set_student(result[0], keep_runs=("Profile agent",))
        st.rerun()
