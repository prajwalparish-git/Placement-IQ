"""Demo cohort for the faculty dashboard: fictional students across Engineering, Commerce, Law
and Management, with resume scans, roadmaps, quiz attempts over six weeks and voice sessions.

    python -m scripts.seed_cohort            # adds the cohort to the telemetry database
    python -m scripts.seed_cohort --replace  # first deletes the earlier demo cohort

Every demo student has a USN starting COHORT and a name "Demo student NN", so the rows are
easy to recognise in the readiness report. Deterministic (fixed random seed). No LLM calls.
"""

import argparse
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database import crud
from database.connection import get_manager, local_only
from database.models import QuizAttempt, StudentProfile, VoiceInterviewSession
from piq import syllabus
from piq.config import DEMO_USN_PREFIX

PREFIX = DEMO_USN_PREFIX  # never synced to the cloud (database/connection.py)
WEEKS = 6
# (stream, domain id, roles, how strong the group starts: 0..1)
GROUPS = (
    ("Engineering", "cs", ("Data Analyst", "Java Backend Developer"), 0.55),
    ("Engineering", "ece", (), 0.45),
    ("Commerce", "commerce", (), 0.5),
    ("Law", "law", (), 0.4),
    ("Management", "corp", (), 0.6),
)
PER_GROUP = 5


def _roles(domain_id: str, preferred: tuple[str, ...]) -> list[str]:
    roles = list(syllabus.domain(domain_id).roles)
    known = [r for r in preferred if r in syllabus.role_skills()]
    return known or roles


def _clear(s: Session) -> int:
    ids = list(s.scalars(select(StudentProfile.id).where(StudentProfile.usn.like(f"{PREFIX}%"))))
    if ids:
        s.execute(delete(StudentProfile).where(StudentProfile.id.in_(ids)))
    return len(ids)


def main(argv: list[str] | None = None) -> int:
    """Seed the demo cohort on this machine only (never sent to the cloud copy); returns how
    many students it wrote."""
    with local_only():
        return _seed(argv)


def _seed(argv: list[str] | None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--replace", action="store_true", help="delete the earlier demo cohort first")
    args = ap.parse_args(argv)
    manager = get_manager()
    if args.replace:
        manager.run(_clear)

    rng = random.Random(7)
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    n = 0
    for stream, domain_id, preferred, strength in GROUPS:
        domain = syllabus.domain(domain_id)
        roles = _roles(domain_id, preferred)
        for _ in range(PER_GROUP):
            n += 1
            role = roles[(n - 1) % len(roles)]
            skills = list(syllabus.role_skills()[role])
            ability = min(0.95, max(0.15, rng.gauss(strength, 0.15)))
            student = crud.save_student(
                f"{PREFIX}{n:03d}",
                f"Demo student {n:02d}",
                stream,
                role,
                department=domain.name,
            )
            matched = [s for s in skills if rng.random() < ability]
            missing = [s for s in skills if s not in matched]
            crud.save_resume_analysis(
                student.id, matched, missing, round(len(matched) / len(skills) * 100, 1)
            )
            crud.save_study_plan(
                student.id,
                1,
                {"target_role": role, "addressed_gaps": missing[:5], "days": []},
                [f"d{d}:0" for d in range(1, 8) if rng.random() < ability],
            )

            def add_activity(
                s: Session,
                sid: int = student.id,
                ability: float = ability,
                stream: str = stream,
                domain_name: str = domain.name,
                role: str = role,
            ) -> None:
                for week in range(WEEKS):
                    if rng.random() < 0.25:  # not every student quizzes every week
                        continue
                    skill = ability + week * 0.04  # practice helps
                    total = rng.choice((5, 10))
                    score = sum(rng.random() < min(0.97, skill) for _ in range(total))
                    when = now - timedelta(weeks=WEEKS - 1 - week, days=rng.randint(0, 4))
                    s.add(
                        QuizAttempt(
                            student_id=sid,
                            stream=stream,
                            domain=domain_name,
                            score=score,
                            total_questions=total,
                            critique_notes="Demo cohort attempt.",
                            timestamp=when,
                        )
                    )
                for k in range(rng.randint(0, 2)):
                    knowledge = min(5, max(1, round(ability * 5 + rng.uniform(-1, 1))))
                    clarity = min(5, max(1, round(ability * 5 + rng.uniform(-1.5, 0.5))))
                    confidence = min(5, max(1, round(ability * 5 + rng.uniform(-1, 1))))
                    flags = ["Answer is very brief."] if knowledge + clarity < 5 else []
                    s.add(
                        VoiceInterviewSession(
                            student_id=sid,
                            role=role,
                            audio_transcript="Demo cohort session (no transcript).",
                            rubric_score=knowledge + clarity + confidence,
                            verbal_clarity_score=float(clarity),
                            relevance_score=float(knowledge),
                            feedback="Demo cohort session.",
                            proctor_flags=flags,
                            timestamp=now - timedelta(days=7 * k + rng.randint(0, 6)),
                        )
                    )

            manager.run(add_activity)
    print(f"Seeded {n} demo students into the telemetry database.")
    return n


if __name__ == "__main__":
    main()
