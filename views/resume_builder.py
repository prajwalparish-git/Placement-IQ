"""ATS Resume Builder: build an industry-tailored, ATS-optimized resume from scratch
with automatic keyword integration, scoring audit, and instant vector PDF export.
"""

import streamlit as st

from piq import formatter, resume_builder, services, ui

ui.page_header(
    "ATS Resume Builder",
    "Build a high-scoring, ATS-optimized professional resume tailored to your target career. "
    "Automatically incorporates industry keywords, metrics, and single-column formatting.",
)

# Step 1: Select Career Domain & Target Role
domains = resume_builder.list_domains()
domain_names = [d["name"] for d in domains]

col_dom, col_role = st.columns([1, 1], gap="medium")
with col_dom:
    chosen_domain = st.selectbox("Career Domain", domain_names, index=0)

domain_roles = resume_builder.roles_for_domain(chosen_domain)
role_names = [r["name"] for r in domain_roles] if domain_roles else ["Software Engineer"]

with col_role:
    chosen_role = st.selectbox("Target Job Role", role_names, index=0)

role_info = resume_builder.get_role_info(chosen_role) or {}

# Show role overview
if role_info:
    with st.container(border=True):
        st.markdown(f"**Target Role:** `{chosen_role}` · *{chosen_domain}*")
        st.caption(role_info.get("description", ""))
        st.markdown(
            f"**Recommended Background:** {role_info.get('recommended_degree', 'Any Graduate')}"
        )
        kw_preview = ", ".join(role_info.get("ats_keywords", [])[:8])
        st.caption(f"**High-Yield ATS Keywords:** {kw_preview}")

st.divider()

# Input Form
with st.form("builder_form", border=False):
    st.subheader("1. Contact & Personal Details", anchor=False)
    p_col1, p_col2 = st.columns(2, gap="medium")
    with p_col1:
        full_name = st.text_input("Full Name *", value="Prajwal K", placeholder="e.g. Alex Morgan")
        email = st.text_input(
            "Email Address *", value="prajwal@example.com", placeholder="alex.morgan@email.com"
        )
        phone = st.text_input(
            "Phone Number", value="+91 98765 43210", placeholder="+91 98765 43210"
        )
    with p_col2:
        location = st.text_input(
            "Location / City", value="Bengaluru, India", placeholder="City, State / Country"
        )
        linkedin = st.text_input(
            "LinkedIn / Portfolio URL",
            value="linkedin.com/in/prajwal-k",
            placeholder="linkedin.com/in/yourprofile",
        )
        exp_level = st.selectbox(
            "Career Experience Level",
            ["Fresher / Entry Level", "1-3 Years Experience", "Senior / Lead"],
            index=0,
        )

    st.subheader("2. Education & Academics", anchor=False)
    e_col1, e_col2 = st.columns(2, gap="medium")
    with e_col1:
        degree = st.text_input(
            "Degree & Specialization *",
            value="B.E in Computer Science & Engineering",
            placeholder="e.g. B.Tech in Mechanical Engineering",
        )
        institution = st.text_input(
            "Institution / University *",
            value="Don Bosco Institute of Technology",
            placeholder="e.g. National Institute of Technology",
        )
    with e_col2:
        grad_year = st.text_input("Graduation Year", value="2026", placeholder="e.g. 2026")
        gpa = st.text_input(
            "CGPA / Percentage", value="8.75 CGPA", placeholder="e.g. 8.5 CGPA or 82%"
        )

    st.subheader("3. Existing Skills & ATS Keywords", anchor=False)
    recommended_kws = role_info.get(
        "ats_keywords", ["Problem Solving", "Communication", "Teamwork"]
    )
    selected_kws = st.multiselect(
        "Select skills you currently possess (recommended for this role):",
        options=recommended_kws,
        default=recommended_kws[: min(5, len(recommended_kws))],
        help="These keywords match industry ATS scanner parameters for your chosen role.",
    )
    extra_skills_raw = st.text_input(
        "Additional Skills (comma-separated)",
        placeholder="e.g. Git, Agile Scrum, Docker, Analytical Thinking",
    )

    st.subheader("4. Projects & Technical Experience", anchor=False)
    st.caption(
        "Highlight a custom project. Our engine formats it with Google's XYZ impact structure."
    )
    proj_title = st.text_input(
        "Project / Initiative Title",
        value="CareerMatrix Multi-Disciplinary Prep Engine",
        placeholder="e.g. IoT Sensor Automation System",
    )
    proj_tech = st.text_input(
        "Technologies & Tools Used",
        value="Python, Streamlit, SQLite, Groq LLM",
        placeholder="e.g. React, Node.js, PostgreSQL",
    )
    proj_bullets = st.text_area(
        "Key Responsibilities & Quantifiable Outcomes (one per line)",
        value=(
            "Engineered multi-agent placement prep system serving curated career roles.\n"
            "Curated offline database of 5,600+ high-yield assessment questions."
        ),
        placeholder="Engineered X that achieved Y by implementing Z\nReduced latency by 30%",
        height=100,
    )

    submitted = st.form_submit_button(
        "Generate ATS-Optimized Resume",
        type="primary",
        icon=":material/auto_awesome:",
    )

if submitted:
    # Process extra skills
    extra_list = [s.strip() for s in extra_skills_raw.split(",") if s.strip()]
    all_selected_skills = list(dict.fromkeys(selected_kws + extra_list))

    resume_payload = resume_builder.build_ats_resume_data(
        full_name=full_name,
        email=email,
        phone=phone,
        location=location,
        linkedin_url=linkedin,
        role_name=chosen_role,
        selected_skills=all_selected_skills,
        experience_level=exp_level,
        degree=degree,
        institution=institution,
        grad_year=grad_year,
        gpa=gpa,
        custom_project_title=proj_title,
        custom_project_tech=proj_tech,
        custom_project_desc=proj_bullets,
    )
    st.session_state["built_resume"] = resume_payload
    st.session_state["built_ats_eval"] = resume_builder.evaluate_ats_compatibility(
        resume_payload, chosen_role
    )
    st.rerun()

# Display Generated Resume & Audit
if "built_resume" in st.session_state:
    res = st.session_state["built_resume"]
    eval_res: resume_builder.ATSScoreResult = st.session_state["built_ats_eval"]

    st.divider()
    st.subheader("ATS Compatibility Scorecard", anchor=False)

    col_score, col_details = st.columns([1, 2], gap="large")
    with col_score, st.container(border=True):
        st.metric("ATS Match Score", f"{eval_res.score} / 100")
        if eval_res.score >= 80:
            st.success("High ATS Compatibility — Ready for submission!", icon=":material/verified:")
        elif eval_res.score >= 60:
            st.info("Moderate ATS Match — Incorporate more keywords.", icon=":material/info:")
        else:
            st.warning("Low ATS Match — Add recommended skills.", icon=":material/warning:")
        st.caption(f"**Action Verbs Detected:** {eval_res.action_verbs_count}")
        st.caption(f"**Quantifiable Metrics:** {'Yes' if eval_res.has_metrics else 'None found'}")

    with col_details, st.container(border=True):
        st.markdown(f"**Matched Keywords ({len(eval_res.matched_keywords)}):**")
        st.write(", ".join(eval_res.matched_keywords) if eval_res.matched_keywords else "None yet")
        if eval_res.missing_keywords:
            st.markdown(f"**Recommended Keywords to Add ({len(eval_res.missing_keywords)}):**")
            st.caption(", ".join(eval_res.missing_keywords[:6]))
        if eval_res.suggestions:
            for s in eval_res.suggestions:
                st.markdown(f":material/lightbulb: {formatter.md_escape(s)}")

    # PDF Download & Profile Activation
    pdf_bytes = resume_builder.generate_ats_pdf(res)
    safe_name = res["full_name"].replace(" ", "_").lower()
    pdf_filename = f"{safe_name}_{chosen_role.replace(' ', '_').lower()}_resume.pdf"

    st.subheader("Download & Onboard", anchor=False)
    btn_col1, btn_col2 = st.columns([1, 1], gap="medium")
    with btn_col1:
        st.download_button(
            "Download ATS-Optimized PDF",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
            type="primary",
            icon=":material/download:",
        )
    with btn_col2:
        if st.button("Save & Start Career Coaching", icon=":material/rocket_launch:"):
            # Turn the resume data into plain text resume for profile extraction
            edu_d = res["education"]["degree"]
            edu_i = res["education"]["institution"]
            edu_y = res["education"]["year"]
            resume_text = (
                f"{res['full_name']}\n{res['contact_line']}\n\n"
                f"OBJECTIVE: {res['summary']}\n\n"
                f"SKILLS: {', '.join(res['skills'])}\n\n"
                f"EDUCATION: {edu_d}, {edu_i} ({edu_y})\n\n"
                f"PROJECTS:\n"
                + "\n".join(
                    f"{p['title']} ({p['tech']})\n" + "\n".join(f"- {b}" for b in p["bullets"])
                    for p in res["projects"]
                )
            )
            # Onboard without requiring a USN!
            target_role_for_profile = chosen_role
            if target_role_for_profile not in services.target_roles():
                target_role_for_profile = "Software Engineer"
            try:
                sid, prof = services.onboard_candidate(
                    res["full_name"], target_role_for_profile, resume_text
                )
                ui.set_student(sid, fresh=True)
                st.success(
                    f"Profile created for {res['full_name']}! Redirecting to Career Dashboard...",
                    icon=":material/task_alt:",
                )
                st.switch_page("views/home.py")
            except services.ServiceError as err:
                st.error(f"Error creating profile: {err}")

    # Live Document Preview
    with st.expander("Preview Formatted Resume", expanded=True, icon=":material/visibility:"):
        st.markdown(f"## {res['full_name']}")
        st.markdown(f"**{res['target_role']}** | {res['contact_line']}")
        st.markdown("---")
        st.markdown("### Professional Summary")
        st.write(res["summary"])
        st.markdown("### Core Competencies & Skills")
        st.write(" • ".join(res["skills"]))
        st.markdown("### Projects & Key Experience")
        for p in res["projects"]:
            st.markdown(f"**{p['title']}** *({p['tech']})*")
            for b in p["bullets"]:
                st.markdown(f"- {b}")
        st.markdown("### Education")
        edu = res["education"]
        st.markdown(f"**{edu['degree']}** — {edu['institution']} *({edu['year']})* | {edu['gpa']}")
