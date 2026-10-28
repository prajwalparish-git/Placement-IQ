"""ATS-optimized resume generator and PDF compiler.

Supports all career domains, dynamic personal inputs, ATS keyword insertion,
and instant vector PDF export using fpdf2.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from fpdf import FPDF

from piq.config import DATA_DIR

CATALOG_PATH = DATA_DIR / "career_catalog.json"


@dataclass(frozen=True)
class ATSScoreResult:
    score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    action_verbs_count: int
    has_metrics: bool
    suggestions: list[str]


@lru_cache(maxsize=1)
def load_catalog() -> dict[str, Any]:
    if not CATALOG_PATH.exists():
        return {"domains": []}
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def list_domains() -> list[dict[str, Any]]:
    return load_catalog().get("domains", [])


def roles_for_domain(domain_identifier: str) -> list[dict[str, Any]]:
    for d in list_domains():
        if d["name"] == domain_identifier or d["id"] == domain_identifier:
            return d.get("roles", [])
    return []


def all_role_names() -> list[str]:
    names = []
    for d in list_domains():
        for r in d.get("roles", []):
            names.append(r["name"])
    return names


def get_role_info(role_name: str) -> dict[str, Any] | None:
    for d in list_domains():
        for r in d.get("roles", []):
            if r["name"].strip().lower() == role_name.strip().lower():
                return {**r, "domain_name": d["name"]}
    return None


ACTION_VERBS = {
    "architected",
    "engineered",
    "designed",
    "developed",
    "implemented",
    "optimized",
    "deployed",
    "automated",
    "spearheaded",
    "authored",
    "analyzed",
    "reduced",
    "improved",
    "scaled",
    "modeled",
    "simulated",
    "directed",
    "built",
    "programmed",
}


def build_ats_resume_data(
    full_name: str,
    email: str,
    phone: str,
    location: str,
    linkedin_url: str,
    role_name: str,
    selected_skills: list[str],
    experience_level: str,
    degree: str,
    institution: str,
    grad_year: str,
    gpa: str,
    custom_project_title: str = "",
    custom_project_tech: str = "",
    custom_project_desc: str = "",
) -> dict[str, Any]:
    role_info = get_role_info(role_name) or {
        "name": role_name,
        "category": "General",
        "ats_keywords": selected_skills or ["Problem Solving", "Communication", "Leadership"],
        "sample_projects": [],
    }

    # Ensure crucial ATS keywords are represented in skills
    top_keywords = role_info.get("ats_keywords", [])
    merged_skills = list(dict.fromkeys(selected_skills + top_keywords[:8]))

    # Professional Summary synthesis
    exp_phrase = (
        "Aspiring and dedicated"
        if experience_level == "Fresher"
        else f"Results-driven {experience_level.lower()}"
    )
    core_kw_str = ", ".join(top_keywords[:4])
    skills_head = ", ".join(merged_skills[:3])
    summary = (
        f"{exp_phrase} {role_name} skilled in {core_kw_str}. "
        f"Demonstrated proficiency in {skills_head} with a strong foundation in modern methods. "
        "Committed to delivering scalable, high-quality outcomes while adhering to best practices."
    )

    # Projects
    projects = []
    if custom_project_title.strip():
        # Clean custom bullets
        bullets = [b.strip().lstrip("-*• ") for b in custom_project_desc.split("\n") if b.strip()]
        if not bullets:
            tech_label = custom_project_tech or "modern tooling"
            bullets = [
                f"Designed and deployed {custom_project_title} utilizing {tech_label}.",
                "Engineered test-driven architecture ensuring robust reliability and performance.",
            ]
        projects.append(
            {
                "title": custom_project_title.strip(),
                "tech": custom_project_tech.strip() or "Standard Stack",
                "bullets": bullets,
            }
        )

    # Add sample project from catalog if user has none or wants an additional one
    for sp in role_info.get("sample_projects", []):
        if len(projects) < 2:
            projects.append(sp)

    # Contact line
    contact_parts = [p for p in [location, email, phone, linkedin_url] if p.strip()]
    contact_line = " | ".join(contact_parts)

    return {
        "full_name": full_name.strip() or "Candidate Name",
        "contact_line": contact_line,
        "target_role": role_name,
        "summary": summary,
        "skills": merged_skills,
        "education": {
            "degree": degree.strip() or "Bachelor of Engineering",
            "institution": institution.strip() or "University / College of Engineering",
            "year": grad_year.strip() or "2026",
            "gpa": gpa.strip() or "First Class with Distinction",
        },
        "projects": projects,
        "certifications": [
            f"Certified {role_name} Fundamentals",
            "Professional Ethics & Collaborative Workplace Practices",
        ],
    }


def evaluate_ats_compatibility(resume_data: dict[str, Any], role_name: str) -> ATSScoreResult:
    role_info = get_role_info(role_name)
    target_keywords = role_info.get("ats_keywords", []) if role_info else []

    # Compile all text
    corpus = " ".join(
        [
            resume_data.get("summary", ""),
            " ".join(resume_data.get("skills", [])),
            " ".join(
                p.get("title", "") + " " + p.get("tech", "") + " " + " ".join(p.get("bullets", []))
                for p in resume_data.get("projects", [])
            ),
        ]
    ).lower()

    matched = []
    missing = []
    for kw in target_keywords:
        if kw.lower() in corpus:
            matched.append(kw)
        else:
            missing.append(kw)

    # Check action verbs
    found_verbs = [v for v in ACTION_VERBS if v in corpus]
    has_metrics = any(char.isdigit() for char in corpus)

    # Compute ATS Score
    # 50 pts: keyword match ratio
    kw_ratio = len(matched) / max(len(target_keywords), 1)
    kw_score = min(50, int(kw_ratio * 50))

    # 20 pts: action verbs
    verb_score = min(20, len(found_verbs) * 4)

    # 15 pts: structure & metrics
    metric_score = 15 if has_metrics else 5

    # 15 pts: contact and completeness
    completeness = 15 if resume_data.get("education") and resume_data.get("projects") else 10

    total_score = min(98, kw_score + verb_score + metric_score + completeness)

    suggestions = []
    if missing:
        suggestions.append(f"Incorporate missing core industry keywords: {', '.join(missing[:4])}.")
    if not has_metrics:
        suggestions.append(
            "Add quantifiable metrics (e.g. 'improved by 25%') to your project bullets."
        )
    if len(found_verbs) < 3:
        suggestions.append(
            "Begin project bullets with strong action verbs (e.g. Engineered, Optimized)."
        )

    return ATSScoreResult(
        score=total_score,
        matched_keywords=matched,
        missing_keywords=missing,
        action_verbs_count=len(found_verbs),
        has_metrics=has_metrics,
        suggestions=suggestions,
    )


class ATSDoc(FPDF):
    def section_heading(self, label: str) -> None:
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(20, 30, 35)
        self.cell(0, 6, label.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(160, 175, 175)
        self.set_line_width(0.3)
        self.line(self.get_x(), self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)


def generate_ats_pdf(resume_data: dict[str, Any]) -> bytes:
    """Generate a clean, single-column, standard-font, ATS-friendly vector PDF."""
    pdf = ATSDoc(format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.set_margins(16, 14, 16)
    pdf.add_page()

    # Name Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(13, 102, 112)  # Primary brand teal
    pdf.cell(
        0, 7, resume_data.get("full_name", "").upper(), align="C", new_x="LMARGIN", new_y="NEXT"
    )

    # Target Role Title
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(60, 70, 75)
    pdf.cell(
        0, 5, resume_data.get("target_role", "").upper(), align="C", new_x="LMARGIN", new_y="NEXT"
    )

    # Contact Info
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(80, 90, 95)
    pdf.cell(0, 4.5, resume_data.get("contact_line", ""), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # 1. Professional Summary
    pdf.section_heading("Professional Summary")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(30, 35, 40)
    pdf.multi_cell(0, 4.3, resume_data.get("summary", ""), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # 2. Technical & Core Skills
    pdf.section_heading("Core Competencies & Skills")
    pdf.set_font("Helvetica", "", 9)
    skills = resume_data.get("skills", [])
    # Render skills in 2 categorized lines with clean ASCII separators
    half = max(1, len(skills) // 2)
    row1 = ", ".join(skills[:half])
    row2 = ", ".join(skills[half:])
    pdf.multi_cell(0, 4.3, f"Core Focus: {row1}", new_x="LMARGIN", new_y="NEXT")
    if row2:
        pdf.multi_cell(0, 4.3, f"Tools & Methodologies: {row2}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # 3. Projects & Work Experience
    pdf.section_heading("Projects & Key Experience")
    for proj in resume_data.get("projects", []):
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(20, 30, 35)
        pdf.cell(0, 4.5, proj.get("title", ""), new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(70, 80, 85)
        pdf.cell(0, 4, f"Technologies: {proj.get('tech', '')}", new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(30, 35, 40)
        for bullet in proj.get("bullets", []):
            pdf.multi_cell(0, 4.2, f"  -  {bullet.strip()}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    # 4. Education
    pdf.section_heading("Education")
    edu = resume_data.get("education", {})
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(20, 30, 35)
    pdf.cell(0, 4.5, edu.get("degree", ""), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(70, 80, 85)
    inst_str = edu.get("institution", "")
    yr_str = edu.get("year", "")
    gpa_str = edu.get("gpa", "")
    pdf.cell(
        0,
        4,
        f"{inst_str} | Year: {yr_str} | Performance: {gpa_str}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(3)

    # 5. Certifications
    certs = resume_data.get("certifications", [])
    if certs:
        pdf.section_heading("Certifications & Honors")
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(30, 35, 40)
        for c in certs:
            pdf.cell(0, 4, f"  -  {c}", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
