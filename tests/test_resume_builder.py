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
