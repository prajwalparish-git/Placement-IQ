"""Tests for ATS resume builder and PDF compilation engine."""

from piq import resume_builder, services


def test_list_domains():
    domains = resume_builder.list_domains()
    assert len(domains) >= 8
    assert any(d["name"] == "Computer Science & IT" for d in domains)
    assert any(d["name"] == "Mechanical Engineering" for d in domains)


def test_roles_for_domain():
    cs_roles = resume_builder.roles_for_domain("Computer Science & IT")
    assert len(cs_roles) >= 3
    role_names = [r["name"] for r in cs_roles]
    assert "Software Engineer" in role_names
    assert "Frontend Engineer" in role_names


def test_get_role_info():
    info = resume_builder.get_role_info("Software Engineer")
    assert info is not None
    assert "ats_keywords" in info
    assert "Python" in info["ats_keywords"]
    assert info["domain_name"] == "Computer Science & IT"


def test_build_ats_resume_data_and_eval():
    data = resume_builder.build_ats_resume_data(
        full_name="Jane Doe",
        email="jane@example.com",
        phone="555-1234",
        location="Bengaluru, India",
        linkedin_url="linkedin.com/in/janedoe",
        role_name="Software Engineer",
        selected_skills=["Python", "SQL", "Git", "Docker", "Algorithms"],
        experience_level="Fresher",
        degree="B.E Computer Science",
        institution="DBIT",
        grad_year="2026",
        gpa="8.5 CGPA",
        custom_project_title="Cloud Microservices Gateway",
        custom_project_tech="FastAPI, Redis, Docker",
        custom_project_desc=(
            "Engineered API gateway handling 10k requests.\nOptimized latency by 35% using caching."
        ),
    )

    assert data["full_name"] == "Jane Doe"
    assert "Python" in data["skills"]
    assert len(data["projects"]) >= 1

    eval_result = resume_builder.evaluate_ats_compatibility(data, "Software Engineer")
    assert eval_result.score >= 50
    assert len(eval_result.matched_keywords) >= 2
    assert eval_result.action_verbs_count >= 1
    assert eval_result.has_metrics is True


def test_generate_ats_pdf():
    data = resume_builder.build_ats_resume_data(
        full_name="Alex Smith",
        email="alex@example.com",
        phone="9876543210",
        location="Bengaluru",
        linkedin_url="linkedin.com/in/alex",
        role_name="Data Scientist",
        selected_skills=["Python", "Machine Learning", "Pandas"],
        experience_level="1-3 Years",
        degree="M.Tech Data Science",
        institution="VTU",
        grad_year="2025",
        gpa="9.0 CGPA",
        custom_project_title="Sales Prediction Engine",
        custom_project_tech="Python, Scikit-Learn",
        custom_project_desc="Developed regression model achieving 92% accuracy.",
    )
    pdf_bytes = resume_builder.generate_ats_pdf(data)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")


def test_generate_candidate_id_and_onboard():
    cid = services.generate_candidate_id("Jane Student")
    assert cid.startswith("JANE")
    assert len(cid) <= 20
    # Must pass normalise_usn regex
    norm = services.normalise_usn(cid)
    assert norm == cid

    # Fallback to CAND if name is empty or numbers only
    cid_empty = services.generate_candidate_id("")
    assert cid_empty.startswith("CAND")

    sid, prof = services.onboard_candidate("Jane Student", "Software Engineer", "Resume summary")
    assert isinstance(sid, str) and len(sid) >= 10
    saved = services.current_profile(sid)
    assert saved is not None
    assert saved.target_role == "Software Engineer"


# --- only what the student entered goes on the resume ------------------------------------


def _built(**changes):
    args = dict(
        full_name="Asha Rao",
        email="asha@example.com",
        phone="",
        location="",
        linkedin_url="",
        role_name="Embedded Systems & Firmware Engineer",
        selected_skills=["Embedded C"],
        experience_level="Fresher / Entry Level",
        degree="",
        institution="",
        grad_year="",
        gpa="",
    )
    return resume_builder.build_ats_resume_data(**(args | changes))


def test_the_builder_invents_no_skills_projects_certificates_or_education():
    data = _built()
    assert data["skills"] == ["Embedded C"]  # the role's keywords are not merged in
    assert data["projects"] == []  # no sample project from the catalog
    assert data["certifications"] == []  # no "Certified ... Fundamentals"
    assert data["education"] == {"degree": "", "institution": "", "year": "", "gpa": ""}
    assert "RTOS" not in data["summary"] and "Embedded C" in data["summary"]
    assert data["summary"].startswith("Entry-level ")  # the fresher wording now matches


def test_the_builder_keeps_entered_projects_certificates_and_the_raw_form():
    space = [{"title": "CAN logger", "tech": "C", "bullets": ["Logged frames"]}]
    data = _built(
        custom_project_title="Data logger",
        custom_project_desc="- Built it\n\n* Cut loss by 30%",
        certifications=[" NPTEL Embedded ", ""],
        extra_projects=space,
        github_url="github.com/asha",
    )
    assert [p["title"] for p in data["projects"]] == ["Data logger", "CAN logger"]
    assert data["projects"][0]["bullets"] == ["Built it", "Cut loss by 30%"]
    assert data["certifications"] == ["NPTEL Embedded"]
    assert "github.com/asha" in data["contact_line"]
    assert data["form"]["project_title"] == "Data logger"  # the next version starts from it


def test_ats_keywords_match_whole_words_only():
    data = _built(selected_skills=["Digital Electronics"])
    result = resume_builder.evaluate_ats_compatibility(data, "Software Engineer")
    assert "Git" not in result.matched_keywords  # not inside "digital"


def test_ats_completeness_counts_filled_sections():
    empty = resume_builder.evaluate_ats_compatibility(_built(), "Software Engineer")
    assert any("Add at least one project" in s for s in empty.suggestions)
    full = _built(
        degree="B.E",
        institution="A college",
        custom_project_title="P",
        custom_project_desc="Built a\nImproved b by 20%",
    )
    assert resume_builder.evaluate_ats_compatibility(full, "Software Engineer").score > empty.score


def test_the_pdf_survives_typography_and_symbols_the_core_font_lacks():
    data = _built(
        custom_project_title="Logger \u2014 v2",
        custom_project_desc="Saved \u20b9 2,000 \u2192 \u201cfast\u201d \u2022 \u4e2d",
    )
    assert resume_builder.generate_ats_pdf(data).startswith(b"%PDF")
    assert resume_builder.pdf_safe("\u2014\u20b9\u4e2d") == "-Rs.?"


def test_resume_text_has_every_section_for_the_profile_agent():
    text = resume_builder.resume_text(_built(custom_project_title="Data logger"))
    assert text.startswith("Asha Rao")
    assert "SKILLS: Embedded C" in text and "Project: Data logger" in text


def test_diff_lists_what_changed_between_versions():
    old = _built()
    new = _built(
        selected_skills=["Embedded C", "RTOS"],
        custom_project_title="Data logger",
        certifications=["NPTEL"],
        role_name="VLSI & Chip Design Engineer",
    )
    diff = resume_builder.diff_resumes(old, new, 40, 55)
    assert diff.skills_added == ["RTOS"] and diff.skills_removed == []
    assert diff.projects_added == ["Data logger"] and diff.certifications_added == ["NPTEL"]
    assert diff.role_changed == (
        "Embedded Systems & Firmware Engineer",
        "VLSI & Chip Design Engineer",
    )
    assert diff.ats_change == 15 and not diff.empty
    assert resume_builder.diff_resumes(old, old).empty
