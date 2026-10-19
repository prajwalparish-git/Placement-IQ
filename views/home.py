"""Home: what PlacementIQ does (no student yet), or where a student stands and what to do
next (Today's focus)."""

import streamlit as st

from piq import charts, formatter, services, ui

HOW_IT_WORKS = (
    ("upload_file", "Profile", "Upload your resume. Your skills are matched to a target role."),
    ("calendar_month", "Plan", "Get seven days of study, most of it on your weakest topics."),
    ("quiz", "Quiz", "Take five-question quizzes. A critic checks every question first."),
    ("autorenew", "Adapt", "Your scores reshape next week's plan, and the loop goes on."),
)


def _go(page: str, **presets: str) -> None:
    """Open another page, preselecting its widgets through session state."""
    st.session_state.update(presets)
    st.switch_page(page)


student = ui.current_student()
if student is None:
    if ui.page_header(
        "Placement prep that adapts to you",
        "PlacementIQ reads your resume, plans a week of study, quizzes you and rewrites next "
        "week's plan from your scores. A critic checks every plan, quiz and interview question "
        "before you see it.",
        "Start with your resume",
        icon=":material/upload_file:",
        key="home_start",
    ):
        _go("views/onboard.py")
    if st.button("Try it with a sample resume", icon=":material/description:", key="home_sample"):
        _go("views/onboard.py", onboard_sample=services.sample_resumes()[0])
    if ui.student_count():
        st.caption("Already onboarded? Choose your name under Student in the sidebar.")
    st.subheader("How it works", anchor=False)
    for column, (n, (icon, title, text)) in zip(
        st.columns(4, gap="medium"), enumerate(HOW_IT_WORKS, 1), strict=True
    ):
        column.markdown(f":primary[:material/{icon}:]  \n**{n}. {title}**  \n{text}")
    st.stop()

sid = student["id"]
profile = services.current_profile(sid)
if profile is None:
    if ui.empty_state(
        "upload_file",
        "Finish onboarding",
        "This student has no profile yet. Analyse a resume to get a readiness score.",
        "Open Onboard",
        key="home_onboard",
    ):
        _go("views/onboard.py")
    st.stop()

try:
    with st.skeleton(height=420):
        overview = services.home(sid, profile)
except services.ServiceError as e:
    if ui.empty_state(
        "error", "Your overview did not load", formatter.md_escape(str(e)), "Try again"
    ):
        st.rerun()
    st.stop()

ui.page_header(
    f"Hello, {formatter.md_escape(profile.name)}",
    f"Here is where you stand for {formatter.md_escape(profile.target_role)}, and what to do next.",
)

action = overview.next_action
focus, side = st.columns([2, 1], gap="medium")
with focus, st.container(border=True, height="stretch"):
    st.markdown(f":primary[:material/{action.icon}:] **Today's focus**")
    st.subheader(action.label, anchor=False)
    st.markdown(formatter.md_escape(action.reason))
    if action.topic:
        ui.topic_chip(action.topic)
    if st.button(action.cta, type="primary", icon=f":material/{action.icon}:", key="home_next"):
        _go(action.page, **({"quiz_topic": action.topic} if action.topic else {}))
with side:
    total = len(profile.matched_skills) + len(profile.missing_skills)
    ui.stat_row(
        [
            ui.Stat(
                "Readiness",
                f"{profile.readiness_score}/100",
                help=f"{len(profile.matched_skills)} of the {total} skills your target role needs "
                "are on your resume.",
            )
        ]
    )
    st.caption(f"{len(profile.matched_skills)} of {total} required skills are on your resume.")

checklist, standing = st.columns([1, 2], gap="medium")
with checklist, st.container(border=True, height="stretch"):
    st.markdown("**Getting started**")
    for item in overview.checklist:
        state, word = ("done", "Done") if item.done else ("todo", "To do")
        st.markdown(f"{formatter.status_md(state, word)} {formatter.md_escape(item.label)}")
with standing:
    st.altair_chart(
        charts.weakness_bars(overview.weakness, formatter.weakness_headline(overview.weakness)),
        width="stretch",
        alt=formatter.weakness_alt(overview.weakness),
    )

st.subheader("Recent activity", anchor=False)
if not overview.recent:
    st.caption("Nothing yet. Your plans, quizzes and interviews will appear here.")
for item in overview.recent:
    when = formatter.relative_day(item.at)
    st.markdown(f"{formatter.md_escape(item.text)}  \n:small[:gray[{when}]]")
