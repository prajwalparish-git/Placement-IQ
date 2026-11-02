"""Tests for ATS resume builder and PDF compilation engine."""

from datetime import date

import pytest

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
    assert data["education"] == []  # no degree the student did not enter
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


# --- education and work entries -------------------------------------------------------------

TODAY = date(2026, 11, 2)
JOB = {
    "title": "Firmware Engineer",
    "company": "Acme Labs",
    "type": "Full-time",
    "location": "Pune",
    "start": "Jul 2024",
    "end": "",
    "current": True,
    "highlights": "- Built a CAN logger\nCut boot time by 40%",
}
INTERN = {
    "title": "Intern",
    "company": "Volt",
    "type": "Internship",
    "start": "2024-01",
    "end": "2024-03",
}
DEGREES = [
    {
        "degree": "M.Tech",
        "specialization": "VLSI Design",
        "institution": "An institute",
        "status": "Pursuing",
        "start": "2025",
        "end": "2027",
    },
    {
        "degree": "B.E",
        "specialization": "Electronics & Communication",
        "institution": "A college",
        "status": "Completed",
        "start": "2020",
        "end": "2024",
        "score": "8.4 CGPA",
    },
    {"degree": "", "specialization": "", "institution": ""},  # an empty row is dropped
]


@pytest.mark.parametrize(
    ("text", "ym"),
    [
        ("2024-06", (2024, 6)),
        ("06/2024", (2024, 6)),
        ("Jun 2024", (2024, 6)),
        ("September 2023", (2023, 9)),
        ("2025", (2025, 1)),
        ("Junk 2024", None),
        ("2024-13", None),
        ("", None),
    ],
)
def test_parse_month_reads_common_formats(text, ym):
    assert resume_builder.parse_month(text) == ym


def test_experience_months_merge_overlaps_and_keep_internships_apart():
    jobs = [
        {"type": "Full-time", "start": "Jan 2024", "end": "Dec 2024"},
        {"type": "Part-time", "start": "Jun 2024", "end": "Mar 2025"},  # overlaps by 7 months
        {"type": "Internship", "start": "2023-06", "end": "2023-08"},
        {"type": "Full-time", "start": "not a date"},
    ]
    assert resume_builder.experience_months(jobs, TODAY) == (15, 3)
    current = [{"type": "Full-time", "start": "Nov 2025", "current": True}]
    assert resume_builder.experience_months(current, TODAY) == (13, 0)
    assert resume_builder.duration_text(27) == "2 years 3 months"
    assert resume_builder.duration_text(12) == "1 year" and resume_builder.duration_text(1) == (
        "1 month"
    )


def test_entries_build_the_resume_and_years_come_from_the_dates():
    data = _built(education=DEGREES, experience=[JOB, INTERN], today=TODAY)
    assert [e["degree"] for e in data["education"]] == ["M.Tech", "B.E"]
    [job, intern] = data["experience"]
    assert job["bullets"] == ["Built a CAN logger", "Cut boot time by 40%"]
    assert job["end"] == "" and job["current"]
    assert "with 2 years 5 months of professional experience" in data["summary"]
    assert "Currently pursuing M.Tech in VLSI Design, completing in 2027." in data["summary"]
    assert data["form"]["experience"][0]["highlights"] == JOB["highlights"]
    fresher = _built(education=DEGREES, experience=[INTERN], today=TODAY)
    assert (
        fresher["summary"].startswith("Entry-level ")
        and "3 months of internships" in (fresher["summary"])
    )


def test_a_version_saved_before_entry_lists_still_reads():
    old = {
        "education": {
            "degree": "B.E in ECE",
            "institution": "A college",
            "year": "2025",
            "gpa": "8.0",
        }
    }
    [entry] = resume_builder.education_entries(old)
    assert entry["degree"] == "B.E" and entry["title"] == "B.E in ECE" and entry["end"] == "2025"
    assert resume_builder.experience_entries(old) == []
    form = {"degree": "B.E in ECE", "institution": "A college", "grad_year": "2025"}
    assert resume_builder.form_education(form)[0]["institution"] == "A college"
    assert resume_builder.education_entries({"education": {"degree": "", "institution": ""}}) == []


def test_text_pdf_and_diff_cover_work_and_education():
    data = _built(education=DEGREES, experience=[JOB], today=TODAY)
    text = resume_builder.resume_text(data)
    assert "Experience: Firmware Engineer, Acme Labs (Full-time, Jul 2024 - Present)" in text
    assert "M.Tech in VLSI Design (pursuing, 2027) | An institute | 2025 - expected 2027" in text
    assert resume_builder.generate_ats_pdf(data).startswith(b"%PDF")
    before = _built(education=DEGREES[1:], today=TODAY)
    diff = resume_builder.diff_resumes(before, data)
    assert diff.experience_added == ["Firmware Engineer, Acme Labs"]
    assert diff.education_added == ["M.Tech in VLSI Design (pursuing, 2027)"]
    assert resume_builder.diff_resumes(data, before).experience_removed == [
        "Firmware Engineer, Acme Labs"
    ]


def test_ats_reads_job_bullets_and_checks_the_degree_rule():
    role = "VLSI & Chip Design Engineer"
    data = _built(role_name=role, education=DEGREES, experience=[JOB], today=TODAY)
    ats = resume_builder.evaluate_ats_compatibility(data, role)
    assert ats.degree_fit == "now"
    assert ats.action_verbs_count >= 1  # "Built" in a job bullet
    commerce = [{"degree": "B.Com", "specialization": "Accounts", "institution": "X"}]
    wrong = resume_builder.evaluate_ats_compatibility(
        _built(role_name=role, education=commerce), role
    )
    assert wrong.degree_fit == "no match"
    assert any("none of your degrees matches" in s for s in wrong.suggestions)
    pursuing = [{**DEGREES[0], "specialization": "Electronics"}]
    later = _built(role_name=role, education=pursuing)
    assert resume_builder.evaluate_ats_compatibility(later, role).degree_fit == "on completion"
    assert resume_builder.evaluate_ats_compatibility(_built(), role).degree_fit == ""
