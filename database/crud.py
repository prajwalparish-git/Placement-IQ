"""Save and fetch telemetry: students, resume analyses, study plans, quiz attempts and voice
interview sessions; a student's whole session history; and analytics aggregated across them.

Each function runs in one transaction through DatabaseManager.run, so a PostgreSQL outage
fails over to SQLite without the caller noticing. Pass `db` to use a specific manager (tests);
by default the process-wide one from connection.get_manager() is used. Inputs are checked here
and a bad one raises ValueError with a message safe to show; JSON fields take plain lists and
dicts. Returned rows are detached ORM objects (read their attributes freely).
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Float, cast, func, select
from sqlalchemy.orm import Session

from database.connection import DatabaseManager, get_manager
from database.models import (
    QuizAttempt,
    ResumeAnalysis,
    StudentProfile,
    StudyPlan,
    VoiceInterviewSession,
)
from piq.config import EMAIL_RE, USN_RE, VOICE_CRITERION_MAX, VOICE_RUBRIC_MAX


@dataclass(frozen=True)
class StudentSession:
    """Everything recorded for one student, oldest first within each list."""

    profile: StudentProfile
    resume: ResumeAnalysis | None  # the latest analysis
    plans: list[StudyPlan] = field(default_factory=list)
    quiz_attempts: list[QuizAttempt] = field(default_factory=list)
    interviews: list[VoiceInterviewSession] = field(default_factory=list)


@dataclass(frozen=True)
class QuizStat:
    stream: str
    domain: str
    attempts: int
    average_pct: float  # mean of score / total_questions, as a percentage


@dataclass(frozen=True)
class InterviewStat:
    role: str
    sessions: int
    average_rubric: float  # out of VOICE_RUBRIC_MAX


@dataclass(frozen=True)
class Analytics:
    students_by_stream: dict[str, int]
    average_match_by_stream: dict[str, float]  # latest resume analysis per student
    quizzes: list[QuizStat]
    interviews: list[InterviewStat]


def _db(db: DatabaseManager | None) -> DatabaseManager:
    return db or get_manager()


def _text(value: str | None, what: str, limit: int) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{what} is required.")
    if len(value) > limit:
        raise ValueError(f"{what} must be at most {limit} characters.")
    return value


def _optional(value: str | None, what: str, limit: int) -> str | None:
    return _text(value, what, limit) if value and value.strip() else None


def _strings(values: Iterable[str], what: str) -> list[str]:
    """A JSON list of distinct, non-empty strings, in the order given."""
    if isinstance(values, str):
        raise ValueError(f"{what} must be a list, not a single string.")
    return list(dict.fromkeys(str(v).strip() for v in values if str(v).strip()))


def _in_range(value: float, low: float, high: float, what: str) -> float:
    if not low <= value <= high:
        raise ValueError(f"{what} must be between {low:g} and {high:g}.")
    return value


def normalise_usn(usn: str | None) -> str:
    usn = (usn or "").strip().upper()
    if not USN_RE.match(usn):
        raise ValueError("USN is required: 4-20 letters/digits, no spaces.")
    return usn


def _student(session: Session, student_id: int) -> StudentProfile:
    student = session.get(StudentProfile, student_id)
    if student is None:  # also the case after a failover to a SQLite file that never saw them
        raise ValueError(f"No telemetry student with id {student_id}.")
    return student


def _insert[M](session: Session, model: type[M], values: Mapping[str, Any]) -> M:
    """A new row for a known student. Built inside the transaction, so a retry after a
    failover inserts a fresh object rather than one from the rolled-back session."""
    _student(session, values["student_id"])
    row = model(**values)
    session.add(row)
    session.flush()
    return row


# --- students -------------------------------------------------------------------------------
def save_student(
    usn: str,
    name: str,
    stream: str,
    target_role: str,
    *,
    email: str | None = None,
    department: str | None = None,
    db: DatabaseManager | None = None,
) -> StudentProfile:
    """Create the student, or update the one with this USN (its id and created_at stay)."""
    values = {
        "usn": normalise_usn(usn),
        "name": _text(name, "Name", 120),
        "stream": _text(stream, "Stream", 40),
        "target_role": _text(target_role, "Target role", 160),
        "email": _optional(email, "Email", 254),
        "department": _optional(department, "Department", 120),
    }
    if values["email"] and not EMAIL_RE.match(values["email"]):
        raise ValueError("Email does not look like an address.")

    def work(s: Session) -> StudentProfile:
        student = s.scalar(select(StudentProfile).where(StudentProfile.usn == values["usn"]))
        if student is None:
            student = StudentProfile(**values)
            s.add(student)
        else:
            for k, v in values.items():
                setattr(student, k, v)
        s.flush()
        return student

    return _db(db).run(work)


def get_student(usn: str, db: DatabaseManager | None = None) -> StudentProfile | None:
    key = normalise_usn(usn)
    return _db(db).run(lambda s: s.scalar(select(StudentProfile).where(StudentProfile.usn == key)))


# --- resume analyses ------------------------------------------------------------------------
def save_resume_analysis(
    student_id: int,
    matched_skills: Iterable[str],
    missing_skills: Iterable[str],
    match_percentage: float,
    db: DatabaseManager | None = None,
) -> ResumeAnalysis:
    values = {
        "student_id": student_id,
        "matched_skills": _strings(matched_skills, "Matched skills"),
        "missing_skills": _strings(missing_skills, "Missing skills"),
        "match_percentage": _in_range(float(match_percentage), 0, 100, "Match percentage"),
    }
    return _db(db).run(lambda s: _insert(s, ResumeAnalysis, values))


def latest_resume_analysis(
    student_id: int, db: DatabaseManager | None = None
) -> ResumeAnalysis | None:
    return _db(db).run(
        lambda s: s.scalar(
            select(ResumeAnalysis)
            .where(ResumeAnalysis.student_id == student_id)
            .order_by(ResumeAnalysis.id.desc())
            .limit(1)
        )
    )


# --- study plans ----------------------------------------------------------------------------
def save_study_plan(
    student_id: int,
    week_number: int,
    plan_data: Mapping[str, Any],
    completed_tasks: Iterable[str] = (),
    db: DatabaseManager | None = None,
) -> StudyPlan:
    """Save the plan for a week; saving the same week again replaces it."""
    if int(week_number) < 1:
        raise ValueError("Week number must be 1 or more.")
    if not isinstance(plan_data, Mapping):
        raise ValueError("Plan data must be a JSON object.")
    week, data = int(week_number), dict(plan_data)
    done = _strings(completed_tasks, "Completed tasks")

    def work(s: Session) -> StudyPlan:
        _student(s, student_id)
        plan = s.scalar(
            select(StudyPlan).where(
                StudyPlan.student_id == student_id, StudyPlan.week_number == week
            )
        )
        if plan is None:
            plan = StudyPlan(student_id=student_id, week_number=week)
            s.add(plan)
        plan.plan_data, plan.completed_tasks = data, done
        s.flush()
        return plan

    return _db(db).run(work)


def mark_tasks_completed(
    student_id: int, week_number: int, tasks: Iterable[str], db: DatabaseManager | None = None
) -> StudyPlan:
    """Add tasks to a saved week's completed list (each once, in the order first done)."""
    new = _strings(tasks, "Tasks")

    def work(s: Session) -> StudyPlan:
        plan = s.scalar(
            select(StudyPlan).where(
                StudyPlan.student_id == student_id, StudyPlan.week_number == int(week_number)
            )
        )
        if plan is None:
            raise ValueError(f"No study plan for week {week_number}.")
        plan.completed_tasks = list(dict.fromkeys([*plan.completed_tasks, *new]))
        s.flush()
        return plan

    return _db(db).run(work)


def study_plans(student_id: int, db: DatabaseManager | None = None) -> list[StudyPlan]:
    return _db(db).run(
        lambda s: list(
            s.scalars(
                select(StudyPlan)
                .where(StudyPlan.student_id == student_id)
                .order_by(StudyPlan.week_number)
            )
        )
    )


# --- quiz attempts --------------------------------------------------------------------------
def save_quiz_attempt(
    student_id: int,
    stream: str,
    domain: str,
    score: int,
    total_questions: int,
    critique_notes: str | None = None,
    db: DatabaseManager | None = None,
) -> QuizAttempt:
    total = int(total_questions)
    if total < 1:
        raise ValueError("Total questions must be 1 or more.")
    values = {
        "student_id": student_id,
        "stream": _text(stream, "Stream", 40),
        "domain": _text(domain, "Domain", 80),
        "score": int(_in_range(int(score), 0, total, "Score")),
        "total_questions": total,
        "critique_notes": (critique_notes or "").strip() or None,
    }
    return _db(db).run(lambda s: _insert(s, QuizAttempt, values))


def quiz_attempts(student_id: int, db: DatabaseManager | None = None) -> list[QuizAttempt]:
    return _db(db).run(
        lambda s: list(
            s.scalars(
                select(QuizAttempt)
                .where(QuizAttempt.student_id == student_id)
                .order_by(QuizAttempt.timestamp, QuizAttempt.id)
            )
        )
    )


# --- voice interview sessions ---------------------------------------------------------------
def save_voice_session(
    student_id: int,
    role: str,
    audio_transcript: str,
    rubric_score: int,
    verbal_clarity_score: float,
    relevance_score: float,
    feedback: str,
    proctor_flags: Sequence[str] = (),
    db: DatabaseManager | None = None,
) -> VoiceInterviewSession:
    values = {
        "student_id": student_id,
        "role": _text(role, "Role", 160),
        "audio_transcript": _text(audio_transcript, "Transcript", 200_000),
        "rubric_score": int(_in_range(int(rubric_score), 0, VOICE_RUBRIC_MAX, "Rubric score")),
        "verbal_clarity_score": _in_range(
            float(verbal_clarity_score), 0, VOICE_CRITERION_MAX, "Verbal clarity score"
        ),
        "relevance_score": _in_range(
            float(relevance_score), 0, VOICE_CRITERION_MAX, "Relevance score"
        ),
        "feedback": _text(feedback, "Feedback", 20_000),
        "proctor_flags": _strings(proctor_flags, "Proctor flags"),
    }
    return _db(db).run(lambda s: _insert(s, VoiceInterviewSession, values))


def voice_sessions(
    student_id: int, db: DatabaseManager | None = None
) -> list[VoiceInterviewSession]:
    return _db(db).run(
        lambda s: list(
            s.scalars(
                select(VoiceInterviewSession)
                .where(VoiceInterviewSession.student_id == student_id)
                .order_by(VoiceInterviewSession.timestamp, VoiceInterviewSession.id)
            )
        )
    )


# --- a student's history, and analytics -----------------------------------------------------
def student_session(usn: str, db: DatabaseManager | None = None) -> StudentSession | None:
    """The student's profile, latest resume analysis, plans, quiz attempts and interviews, read
    in one transaction (so from one backend), or None for an unknown USN."""
    key = normalise_usn(usn)

    def work(s: Session) -> StudentSession | None:
        profile = s.scalar(select(StudentProfile).where(StudentProfile.usn == key))
        if profile is None:
            return None
        sid = profile.id
        return StudentSession(
            profile=profile,
            resume=s.scalar(
                select(ResumeAnalysis)
                .where(ResumeAnalysis.student_id == sid)
                .order_by(ResumeAnalysis.id.desc())
                .limit(1)
            ),
            plans=list(
                s.scalars(
                    select(StudyPlan)
                    .where(StudyPlan.student_id == sid)
                    .order_by(StudyPlan.week_number)
                )
            ),
            quiz_attempts=list(
                s.scalars(
                    select(QuizAttempt)
                    .where(QuizAttempt.student_id == sid)
                    .order_by(QuizAttempt.timestamp, QuizAttempt.id)
                )
            ),
            interviews=list(
                s.scalars(
                    select(VoiceInterviewSession)
                    .where(VoiceInterviewSession.student_id == sid)
                    .order_by(VoiceInterviewSession.timestamp, VoiceInterviewSession.id)
                )
            ),
        )

    return _db(db).run(work)


@dataclass(frozen=True)
class Cohort:
    """Every student's records, for the faculty dashboard and the readiness report."""

    students: list[StudentProfile]
    latest_resumes: dict[int, ResumeAnalysis]  # student id -> their latest analysis
    plans: list[StudyPlan]
    quiz_attempts: list[QuizAttempt]
    interviews: list[VoiceInterviewSession]


def cohort(db: DatabaseManager | None = None) -> Cohort:
    """All students and their records, read in one transaction (so from one backend). Students
    by USN; attempts and sessions oldest first."""

    def work(s: Session) -> Cohort:
        latest = (
            select(func.max(ResumeAnalysis.id))
            .group_by(ResumeAnalysis.student_id)
            .scalar_subquery()
        )
        return Cohort(
            students=list(s.scalars(select(StudentProfile).order_by(StudentProfile.usn))),
            latest_resumes={
                r.student_id: r
                for r in s.scalars(select(ResumeAnalysis).where(ResumeAnalysis.id.in_(latest)))
            },
            plans=list(
                s.scalars(select(StudyPlan).order_by(StudyPlan.student_id, StudyPlan.week_number))
            ),
            quiz_attempts=list(
                s.scalars(select(QuizAttempt).order_by(QuizAttempt.timestamp, QuizAttempt.id))
            ),
            interviews=list(
                s.scalars(
                    select(VoiceInterviewSession).order_by(
                        VoiceInterviewSession.timestamp, VoiceInterviewSession.id
                    )
                )
            ),
        )

    return _db(db).run(work)


def analytics(db: DatabaseManager | None = None) -> Analytics:
    """Students per stream, average resume match per stream (each student's latest analysis),
    quiz results per stream and domain, and voice-interview results per role. Averages are
    rounded to one decimal; groups are sorted by name."""

    def work(s: Session) -> Analytics:
        by_stream = dict(
            s.execute(
                select(StudentProfile.stream, func.count())
                .group_by(StudentProfile.stream)
                .order_by(StudentProfile.stream)
            ).all()
        )
        latest = (
            select(func.max(ResumeAnalysis.id))
            .group_by(ResumeAnalysis.student_id)
            .scalar_subquery()
        )
        match = s.execute(
            select(StudentProfile.stream, func.avg(ResumeAnalysis.match_percentage))
            .join(ResumeAnalysis, ResumeAnalysis.student_id == StudentProfile.id)
            .where(ResumeAnalysis.id.in_(latest))
            .group_by(StudentProfile.stream)
            .order_by(StudentProfile.stream)
        ).all()
        pct = cast(QuizAttempt.score, Float) * 100.0 / QuizAttempt.total_questions
        quizzes = s.execute(
            select(QuizAttempt.stream, QuizAttempt.domain, func.count(), func.avg(pct))
            .group_by(QuizAttempt.stream, QuizAttempt.domain)
            .order_by(QuizAttempt.stream, QuizAttempt.domain)
        ).all()
        interviews = s.execute(
            select(
                VoiceInterviewSession.role,
                func.count(),
                func.avg(cast(VoiceInterviewSession.rubric_score, Float)),
            )
            .group_by(VoiceInterviewSession.role)
            .order_by(VoiceInterviewSession.role)
        ).all()
        return Analytics(
            students_by_stream={k: int(v) for k, v in by_stream.items()},
            average_match_by_stream={k: round(float(v), 1) for k, v in match},
            quizzes=[QuizStat(st, d, int(n), round(float(a), 1)) for st, d, n, a in quizzes],
            interviews=[InterviewStat(r, int(n), round(float(a), 1)) for r, n, a in interviews],
        )

    return _db(db).run(work)
