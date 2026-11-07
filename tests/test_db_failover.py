"""The telemetry layer's hybrid storage: local SQLite (WAL) answers every read and write at
once, and a background worker copies records to the cloud PostgreSQL (Supabase) without ever
blocking the caller; while the cloud is unreachable records wait in the outbox and are pushed
when it is back, without duplicates or cross-machine id clashes. Fully offline: the "cloud"
here is a closed local port, a broken URL, or a second SQLite file standing in for PostgreSQL.
"""

import logging
import statistics
import threading
import time

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import connection, crud
from database.connection import (
    DatabaseManager,
    cloud_connect_args,
    create_cloud_engine,
    get_manager,
    local_only,
    normalize_cloud_url,
    reset_manager,
    safe_url,
)
from database.models import (
    QuizAttempt,
    StudentProfile,
    StudyPlan,
    SyncMeta,
    SyncOutbox,
    SyncReceipt,
    VoiceInterviewSession,
)
from piq.config import (
    CLOUD_MAX_OVERFLOW,
    CLOUD_POOL_SIZE,
    CLOUD_POOL_TIMEOUT_S,
    DEMO_USN_PREFIX,
    SQLITE_BUSY_TIMEOUT_MS,
    SYNC_MAX_ATTEMPTS,
    settings,
)

PASSWORD = "s3cret-pass"
DEAD_PG = f"postgresql://nexus:{PASSWORD}@127.0.0.1:1/nexus"  # port 1: nothing listens there
SUPABASE = f"postgres://postgres.abc:{PASSWORD}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"


@pytest.fixture
def sqlite_path(tmp_path):
    return tmp_path / "placement_nexus.db"


@pytest.fixture
def cloud(tmp_path):
    """A second SQLite file standing in for the cloud PostgreSQL (the sync code is portable)."""
    engine = create_engine(f"sqlite:///{tmp_path / 'cloud.db'}")
    yield engine
    engine.dispose()


@pytest.fixture
def managers():
    made: list[DatabaseManager] = []

    def make(*args, **kwargs) -> DatabaseManager:
        db = DatabaseManager(*args, **kwargs)
        made.append(db)
        return db

    yield make
    for db in made:
        db.dispose()


def _student(db: DatabaseManager, usn: str = "1db22cs001", stream: str = "Engineering"):
    return crud.save_student(usn, "Test Student", stream, "Software Engineer", db=db)


def _activity(db: DatabaseManager, sid: int) -> None:
    crud.save_resume_analysis(sid, ["SQL"], ["OS"], 50, db=db)
    crud.save_study_plan(sid, 1, {"days": ["DBMS"]}, db=db)
    crud.save_quiz_attempt(sid, "Engineering", "Computer Science & IT", 4, 5, db=db)
    crud.save_voice_session(sid, "Software Engineer", "Q/A", 11, 4, 4, "Good", ["brief"], db=db)


def _count(engine, model) -> int:
    with Session(engine) as s:
        return s.scalar(select(func.count()).select_from(model))


# --- the local engine -------------------------------------------------------------------------


def test_local_sqlite_runs_in_wal_mode_shared_across_threads(managers, sqlite_path):
    db = managers("", sqlite_path)
    _student(db)
    with db.local.connect() as c:
        assert c.execute(text("PRAGMA journal_mode")).scalar() == "wal"
        assert c.execute(text("PRAGMA synchronous")).scalar() == 1  # NORMAL
        assert c.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert c.execute(text("PRAGMA busy_timeout")).scalar() == SQLITE_BUSY_TIMEOUT_MS
    errors: list[BaseException] = []

    def other_thread() -> None:
        try:
            _student(db, "1DB22CS002")
        except BaseException as e:  # noqa: BLE001 - surfaced by the assert below
            errors.append(e)

    t = threading.Thread(target=other_thread)
    t.start()
    t.join()
    assert errors == [] and crud.get_student("1DB22CS002", db=db) is not None


def test_local_reads_and_writes_take_milliseconds(managers, sqlite_path):
    db = managers("", sqlite_path)
    sid = _student(db).id
    writes, reads = [], []
    for _ in range(40):
        t0 = time.perf_counter()
        crud.save_quiz_attempt(sid, "Engineering", "CS", 3, 5, db=db)
        writes.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        crud.get_student("1DB22CS001", db=db)
        reads.append(time.perf_counter() - t0)
    # Measured on a laptop: about 3 ms per write (with its outbox row) and 1 ms per read. The
    # bounds leave room for a slow CI disk.
    assert statistics.median(writes) < 0.010 and statistics.median(reads) < 0.005


def test_without_a_cloud_everything_stays_local(managers, sqlite_path):
    db = managers("", sqlite_path)
    _activity(db, _student(db).id)
    st = crud.sync_status(db=db)
    assert not st.cloud_configured and st.state == "local only"
    assert st.pending == 5  # queued: they go up the day a cloud is configured


# --- the cloud engine -------------------------------------------------------------------------


@pytest.mark.parametrize("scheme", ["postgres", "postgresql"])
def test_cloud_urls_are_normalised_to_psycopg(scheme):
    url = normalize_cloud_url(f"{scheme}://u:p@db.example.supabase.co:6543/postgres")
    assert url.drivername == "postgresql+psycopg" and url.port == 6543


def test_supabase_connect_args_require_tls_and_skip_prepared_statements():
    args = cloud_connect_args(normalize_cloud_url(SUPABASE))
    assert args == {"connect_timeout": 3, "sslmode": "require", "prepare_threshold": None}
    local = cloud_connect_args(normalize_cloud_url("postgresql://u:p@localhost:5432/x"))
    assert local["sslmode"] == "prefer"  # a local server may not offer TLS
    explicit = cloud_connect_args(normalize_cloud_url("postgresql://u:p@h/x?sslmode=verify-full"))
    assert "sslmode" not in explicit  # the URL's own choice stands


def test_the_cloud_pool_suits_supabase_poolers():
    engine = create_cloud_engine(SUPABASE)  # opens no connection
    try:
        pool = engine.pool
        assert (pool.size(), pool._max_overflow, pool._timeout) == (
            CLOUD_POOL_SIZE,
            CLOUD_MAX_OVERFLOW,
            CLOUD_POOL_TIMEOUT_S,
        )
        assert pool._pre_ping and PASSWORD not in safe_url(SUPABASE)
    finally:
        engine.dispose()


@pytest.mark.parametrize("url", ["not a url at all", f"mysql://nexus:{PASSWORD}@localhost/nexus"])
def test_unusable_cloud_urls_are_refused_cleanly(url):
    with pytest.raises(ValueError):
        normalize_cloud_url(url)


# --- write-through and background sync -----------------------------------------------------------


def test_an_unreachable_cloud_never_blocks_a_write(managers, sqlite_path, caplog):
    db = managers(DEAD_PG, sqlite_path)
    assert db.local is not None  # the file and its tables exist: time an ordinary write
    with caplog.at_level(logging.WARNING, logger="database"):
        t0 = time.perf_counter()
        student = _student(db)
        elapsed = time.perf_counter() - t0
        db.sync.flush()
    assert elapsed < 0.1  # the local commit only; the cloud attempt runs in the background
    assert crud.get_student("1DB22CS001", db=db).id == student.id
    st = crud.sync_status(db=db)
    assert st.cloud_configured and st.state == "offline" and st.pending == 1
    assert st.retry_in_s > 0 and st.last_error.startswith("OperationalError")
    assert "Cloud sync paused" in caplog.text and "127.0.0.1" in caplog.text
    assert PASSWORD not in caplog.text and PASSWORD not in st.last_error
    t0 = time.perf_counter()
    crud.save_quiz_attempt(student.id, "Engineering", "CS", 4, 5, db=db)  # while backing off
    assert time.perf_counter() - t0 < 0.1 and crud.sync_status(db=db).pending == 2


def test_records_made_offline_are_pushed_when_the_cloud_is_back(managers, sqlite_path, cloud):
    db = managers(DEAD_PG, sqlite_path)
    sid = _student(db).id
    _activity(db, sid)
    db.sync.flush()
    assert crud.sync_status(db=db).pending == 5  # the student and its four records

    db.use_cloud_engine(cloud)  # the connection is back
    db.sync.kick()
    db.sync.flush()
    st = crud.sync_status(db=db)
    assert st.state == "up to date" and st.pending == 0 and st.last_synced_at is not None
    for model in (StudentProfile, StudyPlan, QuizAttempt, VoiceInterviewSession):
        assert _count(cloud, model) == 1
    with Session(cloud) as s:
        [quiz] = s.scalars(select(QuizAttempt))
        assert quiz.student_id == s.scalar(select(StudentProfile.id))
        assert _count(cloud, SyncReceipt) == 3  # resume, quiz, voice


def test_sync_is_idempotent_even_if_the_local_mark_was_lost(managers, sqlite_path, cloud):
    db = managers("", sqlite_path, cloud_engine=cloud)
    _activity(db, _student(db).id)
    db.sync.flush()
    with Session(db.local) as s, s.begin():  # as if the app died after the cloud commit
        for row in s.scalars(select(SyncOutbox)):
            row.synced_at = None
    db.sync.drain()
    assert _count(cloud, QuizAttempt) == 1 and _count(cloud, StudentProfile) == 1
    assert _count(cloud, StudyPlan) == 1


def test_updates_reach_the_cloud(managers, sqlite_path, cloud):
    db = managers("", sqlite_path, cloud_engine=cloud)
    sid = _student(db).id
    crud.save_study_plan(sid, 1, {"days": ["DBMS"]}, db=db)
    db.sync.flush()
    crud.mark_tasks_completed(sid, 1, ["d1:0"], db=db)
    crud.save_student("1DB22CS001", "Renamed", "Engineering", "Data Analyst", db=db)
    db.sync.flush()
    with Session(cloud) as s:
        assert s.scalar(select(StudyPlan.completed_tasks)) == ["d1:0"]
        assert s.scalar(select(StudentProfile.name)) == "Renamed"


def test_two_machines_merge_by_usn_without_id_clashes(managers, tmp_path, cloud):
    lab1 = managers("", tmp_path / "lab1.db", cloud_engine=cloud)
    lab2 = managers("", tmp_path / "lab2.db", cloud_engine=cloud)
    # One machine after the other: the SQLite stand-in for the cloud refuses two writers at
    # once (PostgreSQL does not), and the worker rightly treats that as an outage.
    a = _student(lab1, "1DB22CS001")
    crud.save_quiz_attempt(a.id, "Engineering", "CS", 5, 5, db=lab1)
    lab1.sync.flush()
    b = _student(lab2, "1DB22CS777")  # also local id 1 on its machine
    shared = _student(lab2, "1DB22CS001")  # the same student, seen on the other machine
    assert a.id == b.id == 1
    crud.save_quiz_attempt(b.id, "Engineering", "CS", 1, 5, db=lab2)
    crud.save_quiz_attempt(shared.id, "Engineering", "CS", 3, 5, db=lab2)
    lab2.sync.flush()
    snap = crud.cohort(lab1, source="cloud")
    by_id = {s.id: s.usn for s in snap.students}
    assert sorted(by_id.values()) == ["1DB22CS001", "1DB22CS777"]
    scores = sorted((by_id[q.student_id], q.score) for q in snap.quiz_attempts)
    assert scores == [("1DB22CS001", 3), ("1DB22CS001", 5), ("1DB22CS777", 1)]


def test_a_record_the_cloud_rejects_is_set_aside_without_blocking_others(
    managers, sqlite_path, cloud, monkeypatch
):
    real = connection._push

    def picky(ls, cs, item, device):
        if item.entity == "quiz":
            raise IntegrityError("INSERT", {}, Exception("check constraint"))
        real(ls, cs, item, device)

    monkeypatch.setattr(connection, "_push", picky)
    db = managers("", sqlite_path, cloud_engine=cloud)
    _activity(db, _student(db).id)
    for _ in range(SYNC_MAX_ATTEMPTS):  # background drains may take some of these passes
        db.sync.flush()
        db.sync.drain()
    db.sync.flush()
    st = crud.sync_status(db=db)
    assert st.pending == 0 and st.set_aside == 1 and st.state == "up to date"
    assert _count(cloud, QuizAttempt) == 0 and _count(cloud, VoiceInterviewSession) == 1


def test_the_demo_cohort_never_leaves_the_machine(managers, sqlite_path, cloud):
    db = managers("", sqlite_path, cloud_engine=cloud)
    with local_only():
        _activity(db, _student(db, f"{DEMO_USN_PREFIX}001").id)
    db.sync.flush()
    db.cloud()  # the cloud tables exist; they just hold nothing from this machine
    assert crud.sync_status(db=db).pending == 0 and _count(cloud, StudentProfile) == 0


def test_records_from_before_the_outbox_are_queued_once(managers, sqlite_path, cloud):
    first = managers("", sqlite_path)
    _activity(first, _student(first).id)
    with local_only():
        _student(first, f"{DEMO_USN_PREFIX}009")
    with Session(first.local) as s, s.begin():  # a database from before this upgrade
        s.query(SyncOutbox).delete()
        s.query(SyncMeta).delete()
    first.dispose()
    again = managers("", sqlite_path, cloud_engine=cloud)
    assert crud.sync_status(db=again).pending == 5  # not the demo student
    again.sync.drain()
    assert _count(cloud, StudentProfile) == 1 and _count(cloud, QuizAttempt) == 1
    third = managers("", sqlite_path)
    assert crud.sync_status(db=third).pending == 0  # queued once, not on every start


def test_the_cloud_cohort_reports_an_unconfigured_cloud(managers, sqlite_path):
    db = managers("", sqlite_path)
    with pytest.raises(connection.CloudUnavailable):
        crud.cohort(db, source="cloud")


# --- behaviour kept from before -------------------------------------------------------------------


def test_errors_reach_the_caller_and_roll_back_with_their_outbox_row(managers, sqlite_path):
    db = managers("", sqlite_path)
    sid = _student(db).id
    before = crud.sync_status(db=db).pending

    def boom(session):
        crud._insert(
            session,
            QuizAttempt,
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
        db.write(boom, "quiz")
    assert crud.quiz_attempts(sid, db=db) == []  # the half-done transaction rolled back
    assert crud.sync_status(db=db).pending == before


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
def test_bad_input_is_rejected_with_a_readable_message(call, message, managers, sqlite_path):
    db = managers("", sqlite_path)
    sid = _student(db).id
    with pytest.raises(ValueError, match=message):
        call(db, sid)


def test_saving_a_student_again_updates_them_and_plans_upsert_by_week(managers, sqlite_path):
    db = managers("", sqlite_path)
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


def test_a_student_session_and_analytics_aggregate_across_streams(managers, sqlite_path):
    db = managers("", sqlite_path)
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
    monkeypatch.setenv("SUPABASE_DB_URL", DEAD_PG)
    monkeypatch.setenv("TELEMETRY_DB_PATH", str(tmp_path / "shared.db"))
    settings.cache_clear()
    reset_manager()
    _student(get_manager())  # the default manager, as the app would use it: local, at once
    assert get_manager().cloud_configured and get_manager().sqlite_path == tmp_path / "shared.db"
    get_manager().sync.flush()
    assert crud.sync_status().state == "offline"
    reset_manager()
    assert get_manager().sync.failures == 0  # a fresh manager tries the cloud again
