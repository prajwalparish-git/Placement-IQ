"""Project space (computing domains): the student's repositories in one place, GitHub-style:
what each project is, its stack and link, a README, a log of the work done on it and a
contribution calendar. Projects marked "On resume" feed the Resume builder."""

import streamlit as st

from piq import charts, formatter, services
from piq.config import PROJECT_STATUSES
from piq.ui import Stat, empty_state, page_header, require_profile, stat_row


def _fields(prefix: str, row: dict | None = None) -> dict:
    """The project inputs (inside a form), prefilled from `row` when editing."""
    row = row or {}
    name = st.text_input("Repository name *", value=row.get("name", ""), key=f"{prefix}_name")
    repo = st.text_input(
        "Repository link",
        value=row.get("repo_url", ""),
        placeholder="https://github.com/you/project",
        key=f"{prefix}_repo",
    )
    tech = st.text_input(
        "Stack (comma-separated)",
        value=row.get("tech", ""),
        placeholder="e.g. C, STM32, FreeRTOS",
        key=f"{prefix}_tech",
    )
    status = st.segmented_control(
        "Status",
        PROJECT_STATUSES,
        default=row.get("status", "In progress"),
        required=True,
        key=f"{prefix}_status",
    )
    summary = st.text_area(
        "Highlights (one per line; the first is the description, all become resume bullets)",
        value=row.get("summary", ""),
        placeholder="Logged sensor data at 1 kHz to an SD card\nCut data loss below 0.1% with DMA",
        key=f"{prefix}_summary",
        height=100,
    )
    readme = st.text_area("README", value=row.get("readme", ""), key=f"{prefix}_readme", height=140)
    on_resume = st.checkbox(
        "On resume", value=bool(row.get("on_resume", True)), key=f"{prefix}_resume"
    )
    return {
        "name": name,
        "repo_url": repo,
        "tech": tech,
        "status": status,
        "summary": summary,
        "readme": readme,
        "on_resume": on_resume,
    }


def _save(sid: str, fields: dict, project_id: int | None = None) -> bool:
    try:
        services.save_project(sid, project_id=project_id, **fields)
    except services.ServiceError as e:
        st.error(formatter.md_escape(str(e)), icon=":material/error:")
        return False
    return True


def _repository(sid: str, row, updates: list) -> None:
    pid = row["id"]
    with st.container(border=True):
        st.markdown(formatter.project_head_md(row))
        st.markdown(formatter.project_meta_md(row, row["updates"]))
        with st.expander("README and work log", icon=":material/menu_book:"):
            st.markdown(formatter.readme_md(row["readme"]))
            st.markdown("**Work log**")
            mine = [u for u in updates if u["project_id"] == pid]
            if mine:
                st.markdown("  \n".join(formatter.update_line_md(u) for u in mine[:10]))
            else:
                st.caption("No updates yet. Log what you did each time you work on it.")
            with st.form(f"log_{pid}", border=False, clear_on_submit=True):
                note = st.text_input(
                    "Log an update",
                    placeholder="e.g. Added DMA for UART receive",
                    key=f"note_{pid}",
                )
                if st.form_submit_button("Log update", icon=":material/commit:"):
                    try:
                        services.log_project_update(sid, pid, note)
                    except services.ServiceError as e:
                        st.error(formatter.md_escape(str(e)), icon=":material/error:")
                    else:
                        st.rerun()
        with st.expander("Edit", icon=":material/edit:"):
            with st.form(f"edit_{pid}", border=False):
                fields = _fields(f"edit_{pid}", dict(row))
                if st.form_submit_button("Save changes", type="primary") and _save(
                    sid, fields, pid
                ):
                    st.rerun()
            with st.popover("Delete repository", icon=":material/delete:"):
                st.markdown(f"Delete **{formatter.md_escape(row['name'])}** and its work log?")
                if st.button("Delete for good", type="primary", key=f"del_{pid}"):
                    services.delete_project(sid, pid)
                    st.rerun()


page_header(
    "Project space",
    "Your repositories in one place: what each project is, its stack and link, a README and "
    "a log of your work. Projects marked On resume go into the Resume builder.",
)
sid, profile = require_profile()
if not services.has_project_space(profile):
    empty_state(
        "code_off",
        "Not part of your domain",
        "The Project space is for computing domains. Add your projects in the Resume builder.",
    )
    st.stop()

space = services.project_space(sid)
today = formatter.local_today()
recent = sum(n for day, n in space.activity.items() if (today - day).days < 7 * 12)
stat_row(
    [
        Stat("Repositories", str(len(space.projects))),
        Stat("Done", str(sum(p["status"] == "Done" for p in space.projects))),
        Stat("In progress", str(sum(p["status"] == "In progress" for p in space.projects))),
        Stat("Updates, last 12 weeks", str(recent)),
    ]
)

list_col, side_col = st.columns([3, 2], gap="medium")
with list_col:
    with (
        st.expander("New repository", icon=":material/add:", expanded=not space.projects),
        st.form("new_project", border=False, clear_on_submit=True),
    ):
        fields = _fields("new")
        if st.form_submit_button("Create repository", type="primary") and _save(sid, fields):
            st.rerun()
    if not space.projects:
        st.caption("No repositories yet. Add one above; finished ones belong on your resume.")
    for row in space.projects:
        _repository(sid, row, space.updates)

with side_col:
    with st.container(border=True):
        noun = "update" if recent == 1 else "updates"
        st.subheader(f"{recent} {noun} in the last 12 weeks", anchor=False)
        st.vega_lite_chart(
            spec=charts.activity_heatmap_spec(space.activity, today),
            width="stretch",
            alt=f"Project updates over the last 12 weeks: {recent} in all.",
        )
        st.caption(
            "Your contribution calendar: one square per day, stronger teal for more updates."
        )
    with st.container(border=True):
        st.subheader("Latest activity", anchor=False)
        if space.updates:
            st.markdown(
                "  \n".join(
                    f"**{formatter.md_escape(u['project'])}** {formatter.update_line_md(u)}"
                    for u in space.updates[:8]
                )
            )
        else:
            st.caption("Updates you log on any repository appear here.")
