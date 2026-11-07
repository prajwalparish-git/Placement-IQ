"""Comprehensive unit and integration tests for Layer 2 Multi-Agent Orchestration."""

from pathlib import Path

from agents.critic_quiz_agent import (
    GeneratedMCQ,
    generate_critic_quiz,
    validate_mcq_with_critic,
)
from agents.resume_parser_agent import (
    parse_resume,
)
from agents.study_planner_agent import SevenDayRoadmap, generate_study_roadmap

SAMPLE_RESUME_TEXT = """
Prajwal Parish
Bengaluru, Karnataka | 1DB22CS001 | prajwal@example.com

EDUCATION
B.E in Computer Science and Engineering
Don Bosco Institute of Technology, 2022 - 2026 | CGPA: 8.8

SKILLS
Programming: Python, Java, SQL, JavaScript
Frameworks & Libraries: React, Node.js, Spring Boot, Scikit-Learn
Core CS: Object-Oriented Programming, Data Structures, Algorithms,
Operating Systems, Database Design
Tools & Cloud: Git, GitHub, Linux, Docker, REST APIs

PROJECTS
Skill Scout Nexus - AI Placement Preparation Platform
- Built end-to-end full-stack platform using Python, Streamlit, and SQLite.
- Integrated multi-agent evaluation pipeline with automated critic verification.
"""


def test_resume_parser_agent_with_text():
    res = parse_resume(
        file_input=SAMPLE_RESUME_TEXT.encode("utf-8"),
        target_role="Java Backend Developer",
        filename="prajwal_resume.txt",
    )
    assert res.target_role == "Java Backend Developer"
    assert res.extracted_text_length > 0
    assert "Java" in res.matched_skills
    assert "SQL" in res.matched_skills
    assert "Data Structures" in res.matched_skills
    assert res.match_percentage > 50.0
    assert res.detected_stream == "B.E in Computer Science and Engineering"
    assert res.degree is not None
    assert res.degree.code == "B.E"


def test_resume_parser_agent_with_file_path(tmp_path: Path):
    doc_path = tmp_path / "candidate_cv.txt"
    doc_path.write_text(SAMPLE_RESUME_TEXT, encoding="utf-8")

    res = parse_resume(
        file_input=doc_path,
        target_role="Python Developer",
    )
    assert res.target_role == "Python Developer"
    assert "Python" in res.matched_skills
    assert "Django" in res.missing_gap_skills
    assert res.match_percentage > 0.0


def test_study_planner_agent_roadmap():
    gaps = ["Django", "Unit Testing", "REST APIs"]
    roadmap = generate_study_roadmap(
        missing_gap_skills=gaps,
        target_role="Python Developer",
        target_stream="Computer Science & Engineering",
    )
    assert isinstance(roadmap, SevenDayRoadmap)
    assert len(roadmap.days) == 7
    assert roadmap.target_role == "Python Developer"
    assert roadmap.addressed_gaps == gaps

    # Verify Day 1 through Day 7 sequence
    for i, d in enumerate(roadmap.days, start=1):
        assert d.day == i
        assert len(d.learning_objectives) >= 1
        assert len(d.resources) >= 1
        assert len(d.micro_tasks) >= 1
        assert d.resources[0].url.startswith("http")


def test_critic_mcq_validation():
    # Valid Question
    valid_q = GeneratedMCQ(
        text="What is the time complexity of searching in a balanced Binary Search Tree?",
        options=["O(1)", "O(log n)", "O(n)", "O(n log n)"],
        correct_index=1,
        explanation=(
            "In a balanced BST, each comparison halves the search space, giving O(log n) time."
        ),
        bloom_level="understand",
        difficulty="medium",
        skill_tag="Algorithms",
    )
    eval_res = validate_mcq_with_critic(valid_q, "Algorithms")
    assert eval_res.is_valid is True
    assert len(eval_res.rejection_reasons) == 0

    # Invalid Question (duplicate options + all of the above)
    invalid_q = GeneratedMCQ(
        text="Which of these are valid?",
        options=["Option A", "Option A", "All of the above", "Option D"],
        correct_index=2,
        explanation="Testing invalid question.",
        bloom_level="remember",
        difficulty="easy",
    )
    eval_invalid = validate_mcq_with_critic(invalid_q, "General")
    assert eval_invalid.is_valid is False
    assert any("duplicate" in r.lower() for r in eval_invalid.rejection_reasons)
    assert any("all of the above" in r.lower() for r in eval_invalid.rejection_reasons)


def test_critic_quiz_agent_generation_and_fallback():
    # Should work seamlessly either via critic or mcq_bank fallback
    batch = generate_critic_quiz(
        skill_gap="SQL",
        target_role="Java Backend Developer",
        difficulty="easy",
        count=3,
    )
    assert batch.topic_or_skill == "SQL"
    assert len(batch.questions) == 3
    assert batch.source in ("critic_generated", "question_bank_fallback")
    for q in batch.questions:
        assert len(q.options) == 4
        assert 0 <= q.correct_index <= 3
        assert len(q.text) > 10
