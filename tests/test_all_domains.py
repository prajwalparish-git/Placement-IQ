"""Every role of every domain through the journey a student takes, offline in MOCK_MODE:
resume -> degree rule -> ATS -> save and profile -> readiness; and per domain: plan, instant
quiz from the real question bank, and every interview track. Before this file only the
computer-science roles had ever been exercised end to end."""

import pytest

from piq import degrees, question_bank, resume_builder, services, syllabus
from piq.config import DATA_DIR

CATALOG = syllabus.catalog()["domains"]
ROLES = [(d["id"], r["name"]) for d in CATALOG for r in d["roles"]]
DOMAIN_IDS = [d["id"] for d in CATALOG]


def _entry(rule: dict) -> dict:
    """An education entry the role's own degree rule accepts."""
    field = (rule.get("fields") or [""])[0]
    for code in sorted(degrees.expand(rule["degrees"])):
        entry = {
            "degree": code,
            "specialization": field,
            "institution": "A university",
            "status": "Completed",
            "end": "2025",
        }
        if degrees.qualifies(rule, entry):
            return entry
    raise AssertionError(f"no degree qualifies for {rule}")


def _resume(role: str) -> dict:
    info = resume_builder.get_role_info(role)
    required = list(syllabus.role_skills()[role])
    return resume_builder.build_ats_resume_data(
        full_name="Test Candidate",
        email="test@example.com",
        phone="",
        location="",
        linkedin_url="",
        role_name=role,
        selected_skills=[*info["ats_keywords"][:5], *required[:3]],
        education=[_entry(info["eligibility"])],
        custom_project_title=info["sample_projects"][0]["title"],
        custom_project_tech=info["sample_projects"][0]["tech"],
        custom_project_desc="\n".join(info["sample_projects"][0]["bullets"]),
    )


@pytest.mark.parametrize(("domain_id", "role"), ROLES, ids=[r for _, r in ROLES])
def test_a_role_works_from_resume_to_readiness(domain_id, role):
    res = _resume(role)
    ats = resume_builder.evaluate_ats_compatibility(res, role)
    assert 0 < ats.score <= 98 and ats.matched_keywords
    assert ats.degree_fit == "now", f"the role's own degree rule rejects {res['education']}"
    assert resume_builder.generate_ats_pdf(res).startswith(b"%PDF")
    assert degrees.roles_for(res["education"]), "the degree finds no role"
    assert any(f.role == role for f in degrees.roles_for(res["education"]))

    sid, version = services.save_resume(None, domain_id, res)
    profile = services.current_profile(sid)
    assert version == 1 and profile.target_role == role
    assert profile.matched_skills, "the strict profile found none of the skills the resume names"
    assert 0 < profile.readiness_score <= 100
    syl = services.student_syllabus(sid, profile)
    assert syl.domain.id == domain_id
    assert set(syl.tracked) <= set(syl.domain.topics) and syl.focus
    assert services.locked_domain(sid).domain.id == domain_id


@pytest.fixture
def real_bank(monkeypatch):
    monkeypatch.setattr(question_bank, "BANK", DATA_DIR / "questions" / "mcq_bank.csv")
    question_bank.clear_cache()


@pytest.mark.parametrize("domain_id", DOMAIN_IDS)
def test_a_domain_gets_a_plan_instant_quizzes_and_five_interview_tracks(domain_id, real_bank):
    role = next(r for d, r in ROLES if d == domain_id)
    sid, _ = services.save_resume(None, domain_id, _resume(role))
    profile = services.current_profile(sid)
    domain = syllabus.domain(domain_id)

    plan = services.generate_next_plan(sid)  # checked by the critic like a live plan
    assert {d.topic for d in plan.days} <= set(domain.topics) and len(plan.days) == 7

    counts = question_bank.counts()
    usable = [t for t in domain.topics if any(n >= 5 for n in counts.get(t, {}).values())]
    assert len(usable) >= 4, f"{domain_id}: only {usable} have 5 or more bank questions"
    for topic in usable:
        level = next(d for d, n in counts[topic].items() if n >= 5)
        quiz = services.instant_quiz(topic, level, 5, sid)
        assert len(quiz.questions) == 5
        graded = services.grade_instant_quiz(
            sid, topic, level, [(question_bank.qid(q), q.correct_index) for q in quiz.questions]
        )
        assert graded.score_pct == 100.0
    scores = services.quiz_setup(sid, profile).weakness
    assert all(scores[t] == 0.0 for t in usable if t in scores), "scores did not reach weakness"

    tracks = services.interview_tracks(profile)
    own = [t for t in tracks if t.group == domain.name]
    assert len(own) == 5, f"{domain_id}: {len(own)} domain tracks"
    for track in own:
        session = services.start_interview(sid, track.name)
        assert session.interview_type == track.name and session.current.question
        assert track.focus, "a domain track needs a focus for the interviewer"
