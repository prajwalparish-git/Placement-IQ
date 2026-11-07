"""Telemetry tables as SQLAlchemy 2 typed models, portable across PostgreSQL and SQLite.

Only portable column types are used (JSON, DateTime, Text, Integer, Float), so the same
metadata creates the same tables on either engine. Ranges are enforced twice: by crud.py with a
readable message, and by CHECK constraints as the last line of defence. Timestamps are stored
in UTC and always read back timezone-aware (UTCDateTime), whichever engine holds them.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from piq.config import VOICE_CRITERION_MAX, VOICE_RUBRIC_MAX


def utc_now() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """A UTC timestamp that reads back timezone-aware on PostgreSQL and SQLite alike. SQLite
    has no zone, so it stores naive UTC; a naive value written by a caller counts as UTC."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        value = (value if value.tzinfo else value.replace(tzinfo=UTC)).astimezone(UTC)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class Base(DeclarativeBase):
    pass


def _student_fk() -> Mapped[int]:
    return mapped_column(Integer, ForeignKey("student_profiles.id", ondelete="CASCADE"), index=True)


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usn: Mapped[str] = mapped_column(String(20), unique=True)  # upper-cased, as piq stores it
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(254))
    stream: Mapped[str] = mapped_column(String(40), index=True)  # Engineering, Commerce, ...
    department: Mapped[str | None] = mapped_column(String(120))
    target_role: Mapped[str] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)


class ResumeAnalysis(Base):
    __tablename__ = "resume_analyses"
    __table_args__ = (
        CheckConstraint("match_percentage BETWEEN 0 AND 100", name="ck_resume_match_pct"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = _student_fk()
    matched_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    missing_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    match_percentage: Mapped[float] = mapped_column(Float)


class StudyPlan(Base):
    __tablename__ = "study_plans"
    __table_args__ = (
        UniqueConstraint("student_id", "week_number", name="uq_plan_week"),
        CheckConstraint("week_number >= 1", name="ck_plan_week"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = _student_fk()
    week_number: Mapped[int] = mapped_column(Integer)
    plan_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    completed_tasks: Mapped[list[str]] = mapped_column(JSON, default=list)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        CheckConstraint("total_questions > 0", name="ck_quiz_total"),
        CheckConstraint("score BETWEEN 0 AND total_questions", name="ck_quiz_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = _student_fk()
    stream: Mapped[str] = mapped_column(String(40), index=True)
    domain: Mapped[str] = mapped_column(String(80), index=True)
    score: Mapped[int] = mapped_column(Integer)  # questions answered correctly
    total_questions: Mapped[int] = mapped_column(Integer)
    critique_notes: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)


class VoiceInterviewSession(Base):
    """Text and scores of a spoken interview. Nothing in the app records audio or proctors a
    session yet (voice is out of scope); this only gives such data a place to live."""

    __tablename__ = "voice_interview_sessions"
    __table_args__ = (
        CheckConstraint(f"rubric_score BETWEEN 0 AND {VOICE_RUBRIC_MAX}", name="ck_voice_rubric"),
        CheckConstraint(
            f"verbal_clarity_score BETWEEN 0 AND {VOICE_CRITERION_MAX}", name="ck_voice_clarity"
        ),
        CheckConstraint(
            f"relevance_score BETWEEN 0 AND {VOICE_CRITERION_MAX}", name="ck_voice_relevance"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = _student_fk()
    role: Mapped[str] = mapped_column(String(160), index=True)
    audio_transcript: Mapped[str] = mapped_column(Text)
    rubric_score: Mapped[int] = mapped_column(Integer)
    verbal_clarity_score: Mapped[float] = mapped_column(Float)
    relevance_score: Mapped[float] = mapped_column(Float)
    feedback: Mapped[str] = mapped_column(Text)
    proctor_flags: Mapped[list[str]] = mapped_column(JSON, default=list)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utc_now)
