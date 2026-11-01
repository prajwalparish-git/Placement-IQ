"""ATS resume builder: the student's own details as a single-column resume, an ATS keyword
audit against the target role, version-to-version differences and a vector PDF (fpdf2).

Only what the student entered goes on the resume. The role's keywords and the catalog's
sample projects are suggestions shown beside the form, never written into the resume.
"""

import re
from dataclasses import dataclass
from typing import Any

from fpdf import FPDF

from piq import syllabus


@dataclass(frozen=True)
class ATSScoreResult:
    score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    action_verbs_count: int
    has_metrics: bool
    suggestions: list[str]


def load_catalog() -> dict[str, Any]:
    return syllabus.catalog()


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
    github_url: str = "",
    certifications: list[str] | None = None,
    extra_projects: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """The resume from the student's inputs only. `extra_projects` ({title, tech, bullets})
    come from their Project space. Nothing is invented: no keyword is added to the skills, no
    sample project and no certificate the student did not enter. The raw inputs are kept
    under "form" so the next version starts from them."""
    skills = list(dict.fromkeys(s.strip() for s in selected_skills if s.strip()))
    fresher = experience_level.lower().startswith("fresher")
    lead = "Entry-level" if fresher else f"{experience_level.strip()}"
    focus = f" with hands-on work in {', '.join(skills[:4])}" if skills else ""
    summary = (
        f"{lead} {role_name}{focus}. Builds and documents projects end to end and keeps "
        "learning the fundamentals the role depends on."
    )

    projects = []
    if custom_project_title.strip():
        bullets = [b.strip().lstrip("-*• ") for b in custom_project_desc.split("\n") if b.strip()]
        projects.append(
            {
                "title": custom_project_title.strip(),
                "tech": custom_project_tech.strip(),
                "bullets": bullets,
            }
        )
    for extra in extra_projects or []:
        if extra["title"] not in {p["title"] for p in projects}:
            projects.append(extra)

    links = [linkedin_url, github_url]
    contact_parts = [p.strip() for p in [location, email, phone, *links] if p.strip()]
    return {
        "full_name": full_name.strip(),
        "contact_line": " | ".join(contact_parts),
        "target_role": role_name,
        "summary": summary,
        "skills": skills,
        "education": {
            "degree": degree.strip(),
            "institution": institution.strip(),
            "year": grad_year.strip(),
            "gpa": gpa.strip(),
        },
        "projects": projects,
        "certifications": [c.strip() for c in certifications or [] if c.strip()],
        "form": {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "location": location,
            "linkedin_url": linkedin_url,
            "github_url": github_url,
            "experience_level": experience_level,
            "degree": degree,
            "institution": institution,
            "grad_year": grad_year,
            "gpa": gpa,
            "project_title": custom_project_title,
            "project_tech": custom_project_tech,
            "project_desc": custom_project_desc,
            "certifications": "\n".join(certifications or []),
        },
    }


def resume_text(res: dict[str, Any]) -> str:
    """The resume as plain text, for the profile agent (same sections as the PDF)."""
    edu = res["education"]
    projects = "\n".join(
        f"Project: {p['title']} ({p['tech']})\n" + "\n".join(f"- {b}" for b in p["bullets"])
        for p in res["projects"]
    )
    certs = "\n".join(f"- {c}" for c in res.get("certifications", []))
    parts = [
        res["full_name"],
        res["contact_line"],
        f"OBJECTIVE: {res['summary']}",
        f"SKILLS: {', '.join(res['skills'])}",
        f"EDUCATION: {edu['degree']}, {edu['institution']} ({edu['year']}) {edu['gpa']}".strip(),
        f"PROJECTS:\n{projects}" if projects else "",
        f"CERTIFICATIONS:\n{certs}" if certs else "",
    ]
    return "\n\n".join(p for p in parts if p)


@dataclass(frozen=True)
class ResumeDiff:
    """What changed from one resume version to the next."""

    skills_added: list[str]
    skills_removed: list[str]
    projects_added: list[str]
    projects_removed: list[str]
    certifications_added: list[str]
    role_changed: tuple[str, str] | None
    ats_change: int

    @property
    def empty(self) -> bool:
        return not (
            self.skills_added
            or self.skills_removed
            or self.projects_added
            or self.projects_removed
            or self.certifications_added
            or self.role_changed
            or self.ats_change
        )


def _added(old: list[str], new: list[str]) -> list[str]:
    before = {x.lower() for x in old}
    return [x for x in new if x.lower() not in before]


def diff_resumes(
    old: dict[str, Any], new: dict[str, Any], old_ats: int = 0, new_ats: int = 0
) -> ResumeDiff:
    old_projects = [p["title"] for p in old.get("projects", [])]
    new_projects = [p["title"] for p in new.get("projects", [])]
    role = (old.get("target_role", ""), new.get("target_role", ""))
    return ResumeDiff(
        skills_added=_added(old.get("skills", []), new.get("skills", [])),
        skills_removed=_added(new.get("skills", []), old.get("skills", [])),
        projects_added=_added(old_projects, new_projects),
        projects_removed=_added(new_projects, old_projects),
        certifications_added=_added(old.get("certifications", []), new.get("certifications", [])),
        role_changed=role if role[0] != role[1] else None,
        ats_change=new_ats - old_ats,
    )


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
        # Whole words only: "Git" must not match inside "digital".
        if re.search(rf"(?<!\w){re.escape(kw.lower())}(?!\w)", corpus):
            matched.append(kw)
        else:
            missing.append(kw)

    # Check action verbs
    found_verbs = [v for v in ACTION_VERBS if re.search(rf"\b{v}\b", corpus)]
    has_metrics = any(char.isdigit() for char in corpus)

    # Compute ATS Score
    # 50 pts: keyword match ratio
    kw_ratio = len(matched) / max(len(target_keywords), 1)
    kw_score = min(50, int(kw_ratio * 50))

    # 20 pts: action verbs
    verb_score = min(20, len(found_verbs) * 4)

    # 15 pts: structure & metrics
    metric_score = 15 if has_metrics else 5

    # 15 pts: contact and completeness, 3 per section that is filled in
    edu = resume_data.get("education") or {}
    sections = [
        bool(resume_data.get("full_name")),
        bool(resume_data.get("contact_line")),
        bool(edu.get("degree") and edu.get("institution")),
        bool(resume_data.get("projects")),
        any(len(p.get("bullets", [])) >= 2 for p in resume_data.get("projects", [])),
    ]
    completeness = 3 * sum(sections)

    total_score = min(98, kw_score + verb_score + metric_score + completeness)

    suggestions = []
    if not sections[3]:
        suggestions.append("Add at least one project: it is where ATS keywords carry weight.")
    elif not sections[4]:
        suggestions.append("Give each project two or more bullets: what you built and its result.")
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


_PDF_SUBSTITUTES = str.maketrans(
    {
        "–": "-",
        "—": "-",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "•": "-",
        "…": "...",
        "₹": "Rs.",
        "→": "->",
        " ": " ",
        "​": "",
    }
)


def pdf_safe(text: str) -> str:
    """Text the PDF's core fonts can draw (Latin-1): common typography mapped to ASCII, any
    other character replaced, so a pasted dash or a rupee sign never breaks the export."""
    return text.translate(_PDF_SUBSTITUTES).encode("latin-1", "replace").decode("latin-1")


class ATSDoc(FPDF):
    def normalize_text(self, text: str) -> str:
        return super().normalize_text(pdf_safe(text))

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

        if proj.get("tech"):
            pdf.set_font("Helvetica", "I", 8.5)
            pdf.set_text_color(70, 80, 85)
            pdf.cell(0, 4, f"Technologies: {proj['tech']}", new_x="LMARGIN", new_y="NEXT")

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
    details = [
        edu.get("institution", ""),
        f"Year: {edu['year']}" if edu.get("year") else "",
        f"Performance: {edu['gpa']}" if edu.get("gpa") else "",
    ]
    pdf.cell(0, 4, " | ".join(d for d in details if d), new_x="LMARGIN", new_y="NEXT")
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
