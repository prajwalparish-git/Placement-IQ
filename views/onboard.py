"""Onboard: analyse a resume against a target role for a readiness score, the skills that
are there and missing, and what to fix on the resume."""

import streamlit as st

from piq import charts, formatter, services
from piq.ui import current_student, page_header, run_agent, set_student, show_last_run

NEXT = (
    ("badge", "Enter your USN and the role you are aiming for."),
    ("upload_file", "Upload your resume, or pick a sample to try the app."),
    (
        "fact_check",
        "The profile agent reads it and a critic checks the result. You get a readiness "
        "score, the skills to work on and fixes for the resume.",
    ),
)


def _form(roles: list[str], role_index: int) -> None:
    """The resume form; a valid submission runs the profile agent and opens the profile."""
    with st.form("onboard", border=False):
        usn = st.text_input(
            "USN (required)",
            value=(current_student() or {}).get("usn", ""),
            placeholder="For example 1DB22CS001",
        )
        role = st.selectbox("Target role", roles, index=role_index)
        st.caption("Use one: upload your resume, or pick a sample to try the app.")
        upload = st.file_uploader("Resume file", type=["pdf", "docx", "txt"])
        sample = st.selectbox(
            "…or use a sample resume", ["—", *services.sample_resumes()], key="onboard_sample"
        )
        submitted = st.form_submit_button(
            "Analyse resume", type="primary", icon=":material/fact_check:"
        )
    if not submitted:
        return
    try:
        usn = services.normalise_usn(usn)
        if upload:
            text = services.read_resume(upload.name, upload.getvalue())
        elif sample != "—":
            text = services.load_sample(sample)
        else:
            raise services.ServiceError("Upload a resume or pick a sample.")
    except (services.ServiceError, services.ResumeError) as e:
        st.error(formatter.md_escape(str(e)), icon=":material/error:")
        return
    result = run_agent("Profile agent", lambda ev: services.onboard(usn, role, text, ev))
    if result:
        set_student(result[0], keep_runs=("Profile agent",))
        st.rerun()


def _readiness_card(profile: services.StudentProfile) -> None:
    score = profile.readiness_score
    with st.container(border=True):
        st.subheader(formatter.md_escape(profile.name), anchor=False)
        st.markdown(f":gray[Target role: {formatter.md_escape(profile.target_role)}]")
        # A row even on a phone: the ring is a picture of the number beside it.
        with st.container(horizontal=True, vertical_alignment="center", gap="large"):
            st.metric(
                "Readiness",
                f"{score}/100",
                help="How much of the target role's skill list the resume shows.",
                width="content",
            )
            st.vega_lite_chart(
                spec=charts.readiness_ring_spec(score),
                width="content",
                alt=f"Readiness {score} out of 100",
            )
        st.caption(formatter.readiness_summary(profile))
        st.markdown("**On the resume**")
        st.markdown(
            formatter.skill_chips(profile.matched_skills, present=True) or ":gray[None yet.]"
        )
        st.markdown("**Missing for this role**")
        st.markdown(
            formatter.skill_chips(profile.missing_skills, present=False)
            or ":gray[None: the resume shows every skill this role needs.]"
        )


def _resume_card(profile: services.StudentProfile) -> None:
    with st.container(border=True):
        st.subheader("From the resume", anchor=False)
        st.markdown(f"**Education**  \n{formatter.md_escape(profile.education)}")
        for title, items in (("Projects", profile.projects), ("Internships", profile.internships)):
            st.markdown(f"**{title}**  \n{formatter.list_md(items, 'None listed.')}")
        st.markdown(f"**Resume fixes**  \n{formatter.fixes_md(profile.resume_feedback)}")


profile = services.current_profile(st.session_state.get("student_id"))
roles = services.target_roles()
role_index = roles.index(profile.target_role) if profile and profile.target_role in roles else 0

page_header(
    "Onboard",
    "Analyse a resume against a target role: readiness, the skills it shows and lacks, and "
    "what to fix.",
)

if profile is None:
    form_col, next_col = st.columns([2, 3], gap="medium")
    with form_col, st.container(border=True):
        st.subheader("New student", anchor=False)
        _form(roles, role_index)
    with next_col, st.container(border=True):
        st.subheader("What happens next", anchor=False)
        for n, (icon, text) in enumerate(NEXT, 1):
            st.markdown(f":primary[:material/{icon}:] **{n}.** {text}")
else:
    # A returning student came to read their profile, so it leads (first on a phone) and
    # re-profiling waits behind one click.
    readiness_col, resume_col = st.columns(2, gap="medium")
    with readiness_col:
        _readiness_card(profile)
    with resume_col:
        _resume_card(profile)
        show_last_run("Profile agent")
        with st.expander("Re-profile with a new resume", icon=":material/refresh:"):
            _form(roles, role_index)
