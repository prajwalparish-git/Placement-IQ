"""The telemetry layer's dual-database failover: a dead or unusable PostgreSQL falls back to
SQLite at start-up and mid-session without the caller seeing an error, the event is logged
without the password, and the CRUD and analytics work on the fallback. Fully offline: the
"PostgreSQL" here is a closed local port, a broken URL or a driver that does not exist."""

import logging

import pytest

from database import crud
from database.connection import POSTGRES, SQLITE, DatabaseManager, get_manager, reset_manager
from piq.config import settings

PASSWORD = "s3cret-pass"
DEAD_PG = f"postgresql://nexus:{PASSWORD}@127.0.0.1:1/nexus"  # port 1: nothing listens there


@pytest.fixture
def sqlite_path(tmp_path):
    return tmp_path / "placement_nexus.db"


def _student(db: DatabaseManager, usn: str = "1db22cs001", stream: str = "Engineering"):
    return crud.save_student(usn, "Test Student", stream, "Software Engineer", db=db)


def test_without_a_database_url_sqlite_is_used_and_nothing_fails_over(sqlite_path):
    db = DatabaseManager("", sqlite_path)
    student = _student(db)
    assert db.backend == SQLITE and not db.failed_over
    assert sqlite_path.is_file() and student.id and student.usn == "1DB22CS001"


def test_an_unreachable_postgres_falls_back_to_sqlite_and_logs_it(sqlite_path, caplog):
    db = DatabaseManager(DEAD_PG, sqlite_path, connect_timeout=2)
    with caplog.at_level(logging.WARNING, logger="database"):
        student = _student(db)  # no exception reaches the caller
    assert db.backend == SQLITE and sqlite_path.is_file()
    [event] = db.events
    assert event.fallback == sqlite_path and event.reason.startswith("OperationalError")
    assert "Telemetry failover" in caplog.text and "127.0.0.1" in caplog.text
    assert PASSWORD not in caplog.text and PASSWORD not in event.reason
    assert crud.get_student("1DB22CS001", db=db).id == student.id  # reads work too


@pytest.mark.parametrize(
    "url",
    [
        "not a url at all",
        f"mysql://nexus:{PASSWORD}@localhost/nexus",  # another database
        f"postgresql+nodriver://nexus:{PASSWORD}@localhost/nexus",  # a driver that is missing
    ],
)
def test_a_broken_or_foreign_database_url_falls_back_without_crashing(url, sqlite_path, caplog):
    db = DatabaseManager(url, sqlite_path)
    with caplog.at_level(logging.WARNING, logger="database"):
        _student(db)
    assert db.backend == SQLITE and len(db.events) == 1
    assert PASSWORD not in caplog.text and PASSWORD not in db.events[0].reason


def test_postgres_dying_mid_session_fails_over_and_retries_the_operation(
    sqlite_path, monkeypatch, caplog
):
    # The start-up probe "succeeds", so the manager holds a PostgreSQL engine; the server is in
    # fact gone, so the first real query hits the outage, as a crash after start-up would.
    real_probe = DatabaseManager._probe
    probes = []

    def probe_once(self, engine):
        probes.append(engine)
        if len(probes) > 1:
            real_probe(self, engine)

    monkeypatch.setattr(DatabaseManager, "_probe", probe_once)
    db = DatabaseManager(DEAD_PG, sqlite_path, connect_timeout=2)
    assert db.engine is not None and db.backend == POSTGRES and not db.failed_over

    with caplog.at_level(logging.WARNING, logger="database"):
        student = _student(db)  # fails on PostgreSQL, is retried on SQLite
    assert db.backend == SQLITE and len(db.events) == 1 and len(probes) == 2
    assert student.id and crud.get_student("1db22cs001", db=db).name == "Test Student"
    assert "Telemetry failover" in caplog.text and PASSWORD not in caplog.text

    attempt = crud.save_quiz_attempt(
        student.id, "Engineering", "Computer Science & IT", 4, 5, db=db
    )
    assert attempt.id and len(db.events) == 1  # once on SQLite it stays there


def test_errors_that_are_not_outages_reach_the_caller_and_roll_back(sqlite_path):
    db = DatabaseManager("", sqlite_path)
    sid = _student(db).id

    def boom(session):
        crud._insert(
            session,
            crud.QuizAttempt,
            {
                "student_id": sid,
                "stream": "Engineering",
                "domain": "CS",
                "score": 1,
                "total_questions": 2,
                "critique_notes": None,
            },
        )
        raise RuntimeError("bug in the caller")

    with pytest.raises(RuntimeError):
        db.run(boom)
    assert crud.quiz_attempts(sid, db=db) == []  # the half-done transaction rolled back
    assert not db.failed_over


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda db, sid: crud.save_student("x y", "N", "Law", "Role", db=db), "USN"),
        (
            lambda db, sid: crud.save_student("ABCD1", "N", "Law", "Role", email="no", db=db),
            "Email",
        ),
        (lambda db, sid: crud.save_quiz_attempt(sid, "Law", "Law", 6, 5, db=db), "Score"),
        (lambda db, sid: crud.save_quiz_attempt(sid, "Law", "Law", 0, 0, db=db), "Total"),
        (lambda db, sid: crud.save_resume_analysis(sid, [], [], 101, db=db), "Match"),
        (lambda db, sid: crud.save_resume_analysis(sid, "SQL", [], 50, db=db), "list"),
        (lambda db, sid: crud.save_study_plan(sid, 0, {}, db=db), "Week"),
        (lambda db, sid: crud.mark_tasks_completed(sid, 9, ["x"], db=db), "No study plan"),
        (lambda db, sid: crud.save_quiz_attempt(999, "Law", "Law", 1, 2, db=db), "No telemetry"),
        (
            lambda db, sid: crud.save_voice_session(sid, "Role", "t", 16, 3, 3, "f", db=db),
            "Rubric",
        ),
        (
            lambda db, sid: crud.save_voice_session(sid, "Role", "t", 10, 6, 3, "f", db=db),
            "clarity",
        ),
    ],
)
def test_bad_input_is_rejected_with_a_readable_message(call, message, sqlite_path):
    db = DatabaseManager("", sqlite_path)
    sid = _student(db).id
    with pytest.raises(ValueError, match=message):
        call(db, sid)


def test_saving_a_student_again_updates_them_and_plans_upsert_by_week(sqlite_path):
    db = DatabaseManager("", sqlite_path)
    first = _student(db)
    again = crud.save_student("1DB22CS001", "Renamed", "Engineering", "Data Analyst", db=db)
    assert again.id == first.id and again.name == "Renamed"
    assert again.created_at == first.created_at

    crud.save_study_plan(first.id, 1, {"days": ["DBMS"]}, db=db)
    crud.save_study_plan(first.id, 1, {"days": ["OS", "CN"]}, ["OS"], db=db)
    done = crud.mark_tasks_completed(first.id, 1, ["CN", "OS"], db=db)
    assert done.completed_tasks == ["OS", "CN"]
    [plan] = crud.study_plans(first.id, db=db)
    assert plan.plan_data == {"days": ["OS", "CN"]} and plan.completed_tasks == ["OS", "CN"]


def test_a_student_session_and_analytics_aggregate_across_streams(sqlite_path):
    db = DatabaseManager("", sqlite_path)
    eng = _student(db)
    law = crud.save_student("1DB22LW001", "Law Student", "Law", "Contract Analyst", db=db)
    crud.save_resume_analysis(eng.id, ["SQL"], ["OS"], 40, db=db)
    crud.save_resume_analysis(eng.id, ["SQL", "OS"], [], 80, db=db)  # the latest one counts
    crud.save_resume_analysis(law.id, ["Contract Law"], ["Legal Research"], 50, db=db)
    crud.save_quiz_attempt(eng.id, "Engineering", "Computer Science & IT", 4, 5, db=db)
    crud.save_quiz_attempt(eng.id, "Engineering", "Computer Science & IT", 3, 5, db=db)
    crud.save_quiz_attempt(law.id, "Law", "Law & Legal Services", 1, 4, "Two weak areas", db=db)
    crud.save_voice_session(
        law.id,
        "Contract Analyst",
        "I would redline the indemnity...",
        12,
        4,
        4.5,
        "Clear and on point",
        ["looked away twice"],
        db=db,
    )
    crud.save_voice_session(law.id, "Contract Analyst", "Transcript", 9, 3, 3, "Fine", db=db)

    history = crud.student_session("1db22lw001", db=db)
    assert history.profile.id == law.id and history.resume.match_percentage == 50
    assert [a.score for a in history.quiz_attempts] == [1]
    assert [v.rubric_score for v in history.interviews] == [12, 9]
    assert history.interviews[0].proctor_flags == ["looked away twice"]
    assert crud.student_session("NOBODY1", db=db) is None

    stats = crud.analytics(db=db)
    assert stats.students_by_stream == {"Engineering": 1, "Law": 1}
    assert stats.average_match_by_stream == {"Engineering": 80.0, "Law": 50.0}
    assert [(q.stream, q.domain, q.attempts, q.average_pct) for q in stats.quizzes] == [
        ("Engineering", "Computer Science & IT", 2, 70.0),
        ("Law", "Law & Legal Services", 1, 25.0),
    ]
    assert [(i.role, i.sessions, i.average_rubric) for i in stats.interviews] == [
        ("Contract Analyst", 2, 10.5)
    ]


def test_the_shared_manager_reads_its_settings_and_can_be_reset(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"postgresql+nodriver://u:{PASSWORD}@localhost/x")
    monkeypatch.setenv("TELEMETRY_DB_PATH", str(tmp_path / "shared.db"))
    settings.cache_clear()
    reset_manager()
    _student(get_manager())  # the default manager, as the app would use it
    assert get_manager().backend == SQLITE and get_manager().failed_over
    assert get_manager().sqlite_path == tmp_path / "shared.db"
    reset_manager()
    assert not get_manager().events  # a fresh manager probes PostgreSQL again
