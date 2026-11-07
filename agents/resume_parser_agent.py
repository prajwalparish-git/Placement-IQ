"""Resume Parser Agent for Skill Scout Nexus (Layer 2 Multi-Agent Orchestration).

Responsibilities:
- Accepts `.pdf`, `.docx`, and `.txt` files (bytes or filesystem path).
- Extracts candidate text using `pypdf` and `python-docx` without OCR overhead.
- Uses regex + alias taxonomy matching against `data/role_skills.json`.
- Accurately detects degree/stream qualification using `data/degrees.json` / `piq.degrees`.
- Returns extracted candidate skills, detected degree/stream, match percentage, and list of
  missing gap skills.
"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePath

from pydantic import BaseModel, Field

from piq import degrees, resume
from piq.checks import evidenced, tokens
from piq.config import DATA_DIR

ROLE_SKILLS_PATH = DATA_DIR / "role_skills.json"


class CandidateDegree(BaseModel):
    code: str = Field(description="Degree code, e.g. 'B.E' or 'B.Tech' or 'Other'")
    name: str = Field(description="Full qualification name")
    level: str = Field(description="Degree level: Bachelor's, Master's, etc.")
    field: str = Field(default="", description="Field or branch mentioned")
    specialization: str = Field(default="", description="Detected specialization/stream")


class ResumeAnalysisResult(BaseModel):
    filename: str = Field(description="Original filename uploaded")
    extracted_text_length: int = Field(description="Total characters extracted from resume")
    raw_text: str = Field(description="Cleaned extracted plain text")
    target_role: str = Field(description="Target role evaluated against")
    required_skills: list[str] = Field(description="All required skills for the target role")
    extracted_skills: list[str] = Field(
        description="Candidate skills identified in resume (all skills cataloged)"
    )
    matched_skills: list[str] = Field(
        description="Subset of target role required skills matched in resume"
    )
    missing_gap_skills: list[str] = Field(
        description="Required target skills missing from candidate's resume"
    )
    match_percentage: float = Field(
        ge=0.0,
        le=100.0,
        description="Match score percentage: len(matched_skills) / len(required_skills) * 100",
    )
    degree: CandidateDegree | None = Field(
        default=None, description="Detected qualification or stream"
    )
    detected_stream: str = Field(
        default="", description="Human-readable detected degree/stream summary"
    )


def load_role_skills_catalog() -> tuple[dict[str, dict[str, str | None]], dict[str, list[str]]]:
    """Loads roles map and alias taxonomy from data/role_skills.json."""
    if not ROLE_SKILLS_PATH.exists():
        raise FileNotFoundError(f"Role skills file not found at {ROLE_SKILLS_PATH}")

    data = json.loads(ROLE_SKILLS_PATH.read_text(encoding="utf-8"))
    roles: dict[str, dict[str, str | None]] = data.get("roles", {})
    aliases: dict[str, list[str]] = data.get("aliases", {})
    return roles, aliases


def detect_candidate_stream(text: str) -> tuple[CandidateDegree | None, str]:
    """Scans text for academic degrees and branch/specialization."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # 1. First search line-by-line for specific degree mentions
    best_degree = None
    specialization = ""
    for line in lines:
        d = degrees.parse(line)
        if d:
            best_degree = d
            # Extract specialization clue if present in the same line
            m = re.search(
                r"\b(?:in|of|branch|dept|department|specialization)\s+([A-Za-z\s&/]{3,35})",
                line,
                re.IGNORECASE,
            )
            if m:
                specialization = m.group(1).strip()
            break

    # 2. If not found in individual lines, check the first 2500 chars
    if not best_degree:
        header_text = text[:2500]
        best_degree = degrees.parse(header_text)

    # 3. Detect engineering/tech/commerce stream cues if specialization was empty
    if not specialization:
        stream_patterns = [
            (
                r"\b(computer\s+science(?:\s+and\s+engineering)?|cse|it|information\s+technology)\b",
                "Computer Science & Engineering",
            ),
            (
                r"\b(electronics\s+(?:and\s+)?communication(?:\s+engineering)?|ece)\b",
                "Electronics & Communication",
            ),
            (
                r"\b(electrical\s+(?:and\s+)?electronics(?:\s+engineering)?|eee)\b",
                "Electrical & Electronics",
            ),
            (r"\b(mechanical(?:\s+engineering)?|mech)\b", "Mechanical Engineering"),
            (r"\b(civil(?:\s+engineering)?)\b", "Civil Engineering"),
            (r"\b(biotechnology|biotech)\b", "Biotechnology"),
            (
                r"\b(data\s+science|artificial\s+intelligence|ai\s*&\s*ml|aiml)\b",
                "Data Science & AI",
            ),
            (r"\b(commerce|b\.?com|accounting|finance)\b", "Commerce & Finance"),
            (r"\b(business\s+administration|management|bba|mba)\b", "Business Administration"),
            (r"\b(law|ll\.?b|legal)\b", "Corporate Law"),
        ]
        lower_sample = text[:3500].lower()
        for pat, name in stream_patterns:
            if re.search(pat, lower_sample, re.IGNORECASE):
                specialization = name
                break

    if best_degree:
        cand_degree = CandidateDegree(
            code=best_degree.code,
            name=best_degree.name,
            level=best_degree.level,
            field=best_degree.field,
            specialization=specialization,
        )
        stream_desc = (
            f"{best_degree.code} in {specialization}" if specialization else best_degree.name
        )
        return cand_degree, stream_desc

    if specialization:
        return None, specialization

    return None, "Not specified"


def extract_skills_from_text(
    text: str, all_catalog_skills: set[str], aliases: dict[str, list[str]]
) -> list[str]:
    """Matches words and phrases in resume text against the skill taxonomy (token boundaries)."""
    text_tokens = tokens(text)
    matched: set[str] = set()

    for skill in all_catalog_skills:
        skill_aliases = tuple(aliases.get(skill, []))
        if evidenced(skill, text_tokens, skill_aliases):
            matched.add(skill)

    return sorted(matched)


def parse_resume(
    file_input: str | Path | bytes,
    target_role: str,
    filename: str = "resume.pdf",
) -> ResumeAnalysisResult:
    """Main interface function for Resume Parser Agent.

    Args:
        file_input: File path (str/Path) or raw file bytes.
        target_role: Role name from career catalog (e.g. 'Java Backend Developer').
        filename: Original file name (used when file_input is bytes to inspect extension).

    Returns:
        ResumeAnalysisResult containing extracted skills, gaps, match %, and qualification.
    """
    # 1. Read bytes & filename
    if isinstance(file_input, (str, Path)):
        p = Path(file_input)
        filename = p.name
        data = p.read_bytes()
    else:
        data = file_input

    # 2. Extract plain text using piq.resume (pypdf/python-docx/txt)
    raw_text = resume.extract_text(filename, data)
    cleaned_text = re.sub(r"\r\n|\r", "\n", raw_text).strip()

    # 3. Load roles and skills taxonomy
    roles, aliases = load_role_skills_catalog()
    if target_role not in roles:
        # Fallback to closest case-insensitive match if available
        matched_role = next((r for r in roles if r.lower() == target_role.lower()), None)
        if matched_role:
            target_role = matched_role
        else:
            raise ValueError(
                f"Unknown target role '{target_role}'. Available catalog roles: "
                f"{list(roles.keys())[:10]}..."
            )

    role_skill_map = roles[target_role]
    required_skills = list(role_skill_map.keys())

    # Build unique catalog-wide skills universe for general extraction
    all_known_skills = set(required_skills)
    for r_skills in roles.values():
        all_known_skills.update(r_skills.keys())

    # 4. Extract candidate skills using tokens + regex + alias matching
    extracted_all = extract_skills_from_text(cleaned_text, all_known_skills, aliases)

    # 5. Evaluate role match against required skills
    text_token_list = tokens(cleaned_text)
    matched_for_role = [
        s for s in required_skills if evidenced(s, text_token_list, tuple(aliases.get(s, [])))
    ]
    missing_for_role = [s for s in required_skills if s not in matched_for_role]

    match_pct = (
        round((len(matched_for_role) / len(required_skills)) * 100, 1) if required_skills else 100.0
    )

    # 6. Detect degree and stream
    cand_degree, stream_desc = detect_candidate_stream(cleaned_text)

    return ResumeAnalysisResult(
        filename=PurePath(filename).name,
        extracted_text_length=len(cleaned_text),
        raw_text=cleaned_text,
        target_role=target_role,
        required_skills=required_skills,
        extracted_skills=extracted_all,
        matched_skills=matched_for_role,
        missing_gap_skills=missing_for_role,
        match_percentage=match_pct,
        degree=cand_degree,
        detected_stream=stream_desc,
    )
