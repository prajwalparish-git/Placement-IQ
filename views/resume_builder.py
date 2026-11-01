"""Resume builder: the student's own details as an ATS-friendly resume, audited against
the target role, saved as numbered versions. The first saved version locks the domain; the
history shows what changed between versions, and "What to add next" says what the student's
quiz scores and projects now justify adding."""

from functools import partial

import streamlit as st

from piq import charts, formatter, resume_builder, services, ui

BUILT = "built_resume"  # (domain id, resume dict, ATS result) of the last Generate
SAVED = "resume_saved"  # the version number just saved, shown once

ui.page_header(
    "Resume builder",
    "Build a single-column, ATS-friendly resume from your own details, see how it matches "
    "your target role, and save each improvement as a new version. Only what you enter goes "
    "on the resume; keywords and project ideas are suggestions.",
)

student = ui.current_student()
sid = student["id"] if student else None
profile = services.current_profile(sid)
versions = services.resume_history(sid)
latest = versions[-1] if versions else None
lock = services.locked_domain(sid)
key = sid or "new"  # widget keys per student: a switch never carries another's inputs over

# --- domain and role -------------------------------------------------------------------
domains = list(services.domains())
col_dom, col_role = st.columns(2, gap="medium")
with col_dom:
    if lock:
        domain = lock.domain
        st.selectbox("Career domain", [domain.name], disabled=True, key=f"rb_domain_lock_{key}")
    else:
        role_now = latest.target_role if latest else profile.target_role if profile else None
        current = services.domain_of_role(role_now).id if role_now else domains[0].id
        domain = st.selectbox(
            "Career domain",
            domains,
            index=next((i for i, d in enumerate(domains) if d.id == current), 0),
            format_func=lambda d: d.name,
            key=f"rb_domain_{key}",
        )
roles = services.domain_roles(domain.id)
with col_role:
    wanted = latest.target_role if latest else profile.target_role if profile else None
    role = st.selectbox(
        "Target job role",
        roles,
        index=roles.index(wanted) if wanted in roles else 0,
        key=f"rb_role_{key}_{domain.id}",
    )
if lock:
    st.markdown(formatter.locked_md(domain.name, lock.since))
elif sid:
    st.caption(
        ":material/lock_open: Saving your first version locks your domain, so your plans and "
        "quizzes stay on one syllabus. You can still change role within it."
    )

role_info = resume_builder.get_role_info(role) or {}
# The original CS roles have no catalog entry (no description or keywords): no empty card.
if role_info:
    with st.container(border=True):
        st.markdown(f"**{formatter.md_escape(role)}** · {formatter.md_escape(domain.name)}")
        st.caption(role_info.get("description", ""))
        if degree := role_info.get("recommended_degree"):
            st.markdown(f"**Usual background:** {formatter.md_escape(degree)}")
        if keywords := role_info.get("ats_keywords"):
            st.caption(f"**Keywords recruiters scan for:** {', '.join(keywords)}")
        if ideas := role_info.get("sample_projects"):
            with st.expander("Project ideas for this role", icon=":material/lightbulb:"):
                st.caption(
                    "Ideas to build, not to copy onto the resume: add a project once it is yours."
                )
                for idea in ideas:
                    title = formatter.md_escape(idea["title"])
                    tech = formatter.md_escape(idea["tech"])
                    st.markdown(f"**{title}** :gray[({tech})]")

if saved_n := st.session_state.pop(SAVED, None):  # once, right after a save
    st.success(
        f"Saved version {saved_n}. Your profile and readiness now follow this resume.",
        icon=":material/task_alt:",
    )
    ui.show_last_run("Profile agent")

# --- what to add next (a returning student) -------------------------------------------------
if sid and profile:
    advice = services.resume_advice(sid, profile)
    lines = formatter.advice_lines(advice, formatter.local_today())
    with st.container(border=True):
        st.subheader("What to add next", anchor=False)
        if advice.due(formatter.local_today()):
            st.warning("Your resume is due for a review.", icon=":material/event:")
        if lines:
            st.markdown("  \n".join(lines))
        else:
            st.caption(
                "Nothing new yet. Average 70% or more on a topic over two quizzes, or finish a "
                "project, and it will be suggested here."
            )

st.divider()

# --- the form -----------------------------------------------------------------------------
form = (latest.resume.get("form") if latest else None) or {}
if not form and profile:
    form = {"full_name": profile.name}
    if profile.education and profile.education != "Not stated":
        form["degree"] = profile.education
previous_skills = (
    list(latest.resume["skills"]) if latest else list(profile.matched_skills) if profile else []
)
options = list(dict.fromkeys([*role_info.get("ats_keywords", []), *previous_skills]))
space_projects = services.resume_projects(sid) if domain.code_space else []
levels = ["Fresher / Entry Level", "1-3 Years Experience", "Senior / Lead"]

with st.form(f"builder_{key}", border=False):
    st.subheader("1. Contact details", anchor=False)
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        full_name = st.text_input(
            "Full name *", value=form.get("full_name", ""), placeholder="Your name"
        )
        email = st.text_input("Email *", value=form.get("email", ""), placeholder="you@example.com")
        phone = st.text_input("Phone", value=form.get("phone", ""), placeholder="+91 ...")
    with c2:
        location = st.text_input("City", value=form.get("location", ""), placeholder="City, State")
        linkedin = st.text_input(
            "LinkedIn or portfolio",
            value=form.get("linkedin_url", ""),
            placeholder="linkedin.com/in/...",
        )
        github = (
            st.text_input(
                "GitHub profile", value=form.get("github_url", ""), placeholder="github.com/..."
            )
            if domain.code_space
            else ""
        )
        level = st.selectbox(
            "Experience level",
            levels,
            index=levels.index(form["experience_level"])
            if form.get("experience_level") in levels
            else 0,
        )

    st.subheader("2. Education", anchor=False)
    e1, e2 = st.columns(2, gap="medium")
    with e1:
        degree = st.text_input(
            "Degree and branch *",
            value=form.get("degree", ""),
            placeholder="e.g. B.E in Electronics & Communication",
        )
        institution = st.text_input(
            "College or university *", value=form.get("institution", ""), placeholder="Your college"
        )
    with e2:
        grad_year = st.text_input(
            "Graduation year", value=form.get("grad_year", ""), placeholder="e.g. 2026"
        )
        gpa = st.text_input(
            "CGPA or percentage", value=form.get("gpa", ""), placeholder="e.g. 8.2 CGPA"
        )

    st.subheader("3. Skills", anchor=False)
    skills = st.multiselect(
        "Skills you can show evidence for",
        options=options,
        default=[s for s in previous_skills if s in options],
        help="The role's keywords are listed; choose only those you have used.",
    )
    extra_raw = st.text_input(
        "Other skills (comma-separated)",
        value=form.get("extra_skills", ""),
        placeholder="e.g. Oscilloscope, KiCad, Python",
    )

    st.subheader("4. Projects", anchor=False)
    chosen_space = []
    if space_projects:
        titles = [p["title"] for p in space_projects]
        chosen_space = st.multiselect(
            "From your Project space",
            titles,
            default=titles,
            help="Projects marked On resume in your Project space; highlights become bullets.",
        )
    st.caption("Describe a project as: what you built, how, and the result, one bullet per line.")
    proj_title = st.text_input("Project title", value=form.get("project_title", ""))
    proj_tech = st.text_input("Tools and technologies", value=form.get("project_tech", ""))
    proj_desc = st.text_area(
        "What you did and what it achieved (one bullet per line)",
        value=form.get("project_desc", ""),
        placeholder="Built X with Y, which did Z\nReduced A by 30% by changing B",
        height=110,
    )

    st.subheader("5. Certifications", anchor=False)
    certs_raw = st.text_area(
        "Certifications you hold (one per line)", value=form.get("certifications", ""), height=80
    )
    submitted = st.form_submit_button(
        "Build resume", type="primary", icon=":material/auto_awesome:"
    )

if submitted:
    extra = [s.strip() for s in extra_raw.split(",") if s.strip()]
    res = resume_builder.build_ats_resume_data(
        full_name=full_name,
        email=email,
        phone=phone,
        location=location,
        linkedin_url=linkedin,
        role_name=role,
        selected_skills=[*skills, *extra],
        experience_level=level,
        degree=degree,
        institution=institution,
        grad_year=grad_year,
        gpa=gpa,
        custom_project_title=proj_title,
        custom_project_tech=proj_tech,
        custom_project_desc=proj_desc,
        github_url=github,
        certifications=[c for c in certs_raw.splitlines() if c.strip()],
        extra_projects=[p for p in space_projects if p["title"] in chosen_space],
    )
    res["form"]["extra_skills"] = extra_raw
    st.session_state[BUILT] = (domain.id, res, resume_builder.evaluate_ats_compatibility(res, role))
    st.rerun()

# --- the built resume -------------------------------------------------------------------
built = st.session_state.get(BUILT)
if built and built[0] == domain.id and built[1]["target_role"] == role:
    _, res, ats = built
    st.divider()
    st.subheader("ATS check", anchor=False)
    score_col, detail_col = st.columns([1, 2], gap="large")
    with score_col, st.container(border=True):
        st.metric("ATS match", f"{ats.score}/100")
        state = "done" if ats.score >= 80 else "warning" if ats.score >= 60 else "error"
        word = (
            "Strong match" if ats.score >= 80 else "Fair match" if ats.score >= 60 else "Weak match"
        )
        st.markdown(formatter.status_md(state, word))
        numbers = "yes" if ats.has_metrics else "none"
        st.caption(f"Action verbs: {ats.action_verbs_count} · Numbers in bullets: {numbers}")
    with detail_col, st.container(border=True):
        st.markdown(f"**Keywords found ({len(ats.matched_keywords)})**")
        st.markdown(formatter.skill_chips(ats.matched_keywords, present=True) or ":gray[None yet.]")
        if ats.missing_keywords:
            st.markdown(f"**Keywords not on the resume ({len(ats.missing_keywords)})**")
            st.markdown(formatter.skill_chips(ats.missing_keywords[:10], present=False))
        for tip in ats.suggestions:
            st.markdown(f":material/lightbulb: {formatter.md_escape(tip)}")
    if latest:
        diff = resume_builder.diff_resumes(latest.resume, res, latest.ats_score, ats.score)
        st.markdown(formatter.diff_md(diff, latest.n))

    pdf_name = formatter.resume_filename(res["full_name"], role)
    with st.container(horizontal=True, vertical_alignment="center"):
        st.download_button(
            "Download PDF",
            data=partial(resume_builder.generate_ats_pdf, res),  # built only when clicked
            file_name=pdf_name,
            mime="application/pdf",
            icon=":material/download:",
            on_click="ignore",
        )
        label = f"Save as version {len(versions) + 1}" if sid else "Save and start coaching"
        save = st.button(label, type="primary", icon=":material/save:")
    if save:
        saved = ui.run_agent(
            "Profile agent", lambda ev: services.save_resume(sid, domain.id, res, ev)
        )
        if saved:
            st.session_state.pop(BUILT, None)
            ui.set_student(saved[0], keep_runs=("Profile agent",), fresh=True)
            st.session_state[SAVED] = saved[1]  # after set_student, which clears old state
            st.rerun()

    with st.expander("Preview", expanded=True, icon=":material/visibility:"):
        st.markdown(formatter.resume_preview_md(res))

# --- version history -----------------------------------------------------------------------
if versions:
    st.divider()
    st.subheader("Your versions", anchor=False)
    scores = [v.ats_score for v in versions]
    hist_col, compare_col = st.columns(2, gap="medium")
    with hist_col, st.container(border=True, height="stretch"):
        first, last = scores[0], scores[-1]
        headline = (
            f"ATS score {first} at version 1, {last} now"
            if len(scores) > 1
            else f"Version 1 scores {first}/100"
        )
        st.markdown(f"**{headline}**")
        st.vega_lite_chart(
            spec=charts.ats_trend_spec(
                scores, [formatter.local_day(v.created_at) for v in versions]
            ),
            width="stretch",
            alt="ATS score by version: " + ", ".join(f"{s} of 100" for s in scores),
        )
        st.dataframe(formatter.versions_table(versions), width="stretch")
    with compare_col, st.container(border=True, height="stretch"):
        st.markdown("**Compare two versions**")
        numbers = [v.n for v in versions]
        if len(numbers) > 1:
            a, b = st.select_slider(
                "Versions", numbers, value=(numbers[-2], numbers[-1]), format_func=lambda n: f"v{n}"
            )
            old, new = versions[a - 1], versions[b - 1]
            st.markdown(
                formatter.diff_md(
                    resume_builder.diff_resumes(
                        old.resume, new.resume, old.ats_score, new.ats_score
                    ),
                    old.n,
                )
            )
        else:
            st.caption("Save a second version to compare what changed.")
        pick = st.selectbox(
            "Download a version",
            numbers,
            index=len(numbers) - 1,
            format_func=lambda n: f"Version {n}",
        )
        chosen = versions[pick - 1]
        st.download_button(
            f"Download version {pick} (PDF)",
            data=partial(resume_builder.generate_ats_pdf, chosen.resume),
            file_name=f"resume_v{pick}.pdf",
            mime="application/pdf",
            icon=":material/history:",
            on_click="ignore",
        )
