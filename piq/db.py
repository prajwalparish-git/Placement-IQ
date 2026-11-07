"""SQLite persistence: connection handling and every read/write the app performs.

One short-lived connection per call keeps this safe under Streamlit's threads.
"""

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from piq.checks import text_hash
from piq.config import settings
from piq.schemas import AnswerEvaluation, QuizSet, StudentProfile, WeeklyPlan

SCHEMA = Path(__file__).with_name("schema.sql")
FAILED = "failed: "  # reject_reason prefix of an agent_logs row whose call or check failed


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    path = settings().db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:  # commits on success, rolls back on exception
            yield conn
    finally:
        conn.close()


def init_db() -> None:
    with tx() as c:
        c.executescript(SCHEMA.read_text(encoding="utf-8"))


# --- students & profiles -------------------------------------------------------


def save_profile(usn: str, profile: StudentProfile, at: str | None = None) -> str:
    """Create or update the student identified by USN, append a profile row, return student id."""
    usn = usn.strip().upper()
    with tx() as c:
        row = c.execute("SELECT id FROM students WHERE usn = ?", (usn,)).fetchone()
        sid = row["id"] if row else uuid.uuid4().hex
        c.execute(
            """INSERT INTO students (id, name, usn, target_role, readiness_score, created_at)
               VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
               ON CONFLICT(id) DO UPDATE SET name = excluded.name,
                 target_role = excluded.target_role, readiness_score = excluded.readiness_score""",
            (sid, profile.name, usn, profile.target_role, profile.readiness_score, at),
        )
        c.execute(
            """INSERT INTO profiles (student_id, profile_json, readiness_score, created_at)
               VALUES (?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))""",
            (sid, profile.model_dump_json(), profile.readiness_score, at),
        )
    return sid


def student_by_usn(usn: str) -> sqlite3.Row | None:
    """The student who owns `usn` (id, name, target_role), or None."""
    with tx() as c:
        return c.execute(
            "SELECT id, name, target_role FROM students WHERE usn = ?", (usn.strip().upper(),)
        ).fetchone()


def delete_student(usn: str) -> None:
    """Remove a student and (via ON DELETE CASCADE) all of their history."""
    with tx() as c:
        c.execute("DELETE FROM students WHERE usn = ?", (usn.strip().upper(),))


def student(student_id: str) -> sqlite3.Row | None:
    """One student's id, name, usn, target_role and readiness_score."""
    with tx() as c:
        return c.execute(
            "SELECT id, name, usn, target_role, readiness_score FROM students WHERE id = ?",
            (student_id,),
        ).fetchone()


def list_students() -> list[sqlite3.Row]:
    with tx() as c:
        return c.execute(
            "SELECT id, name, usn, target_role, readiness_score FROM students ORDER BY usn"
        ).fetchall()


def latest_profile(student_id: str) -> StudentProfile | None:
    with tx() as c:
        row = c.execute(
            "SELECT profile_json FROM profiles WHERE student_id = ? ORDER BY id DESC LIMIT 1",
            (student_id,),
        ).fetchone()
    return StudentProfile.model_validate_json(row["profile_json"]) if row else None


def readiness_history(student_id: str) -> list[sqlite3.Row]:
    with tx() as c:
        return c.execute(
            "SELECT created_at, readiness_score FROM profiles WHERE student_id = ? ORDER BY id",
            (student_id,),
        ).fetchall()


# --- plans ---------------------------------------------------------------------


def save_plan(student_id: str, plan: WeeklyPlan, at: str | None = None) -> None:
    with tx() as c:
        c.execute(
            """INSERT INTO plans (student_id, week_no, plan_json, rationale, created_at)
               VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
               ON CONFLICT(student_id, week_no) DO UPDATE SET
                 plan_json = excluded.plan_json, rationale = excluded.rationale""",
            (student_id, plan.week_no, plan.model_dump_json(), plan.rationale, at),
        )


def latest_plan(student_id: str) -> sqlite3.Row | None:
    """The newest plan's week_no, created_at (UTC) and days_done, or None before week 1."""
    with tx() as c:
        return c.execute(
            """SELECT week_no, created_at,
                      (SELECT COUNT(*) FROM plan_progress pp
                       WHERE pp.student_id = plans.student_id
                         AND pp.week_no = plans.week_no) AS days_done
               FROM plans WHERE student_id = ? ORDER BY week_no DESC LIMIT 1""",
            (student_id,),
        ).fetchone()


def plans_with_progress(student_id: str) -> list[tuple[WeeklyPlan, set[int]]]:
    """Every plan, oldest week first, with the days marked done, in one query."""
    with tx() as c:
        rows = c.execute(
            """SELECT p.plan_json, GROUP_CONCAT(pp.day) AS done FROM plans p
               LEFT JOIN plan_progress pp
                 ON pp.student_id = p.student_id AND pp.week_no = p.week_no
               WHERE p.student_id = ? GROUP BY p.id ORDER BY p.week_no""",
            (student_id,),
        ).fetchall()
    return [
        (
            WeeklyPlan.model_validate_json(r["plan_json"]),
            {int(d) for d in r["done"].split(",")} if r["done"] else set(),
        )
        for r in rows
    ]


def set_days_done(student_id: str, week_no: int, days: set[int]) -> None:
    """Make exactly `days` (1-7) the done days of a week; a day already done keeps its time."""
    with tx() as c:
        c.executemany(
            "DELETE FROM plan_progress WHERE student_id = ? AND week_no = ? AND day = ?",
            [(student_id, week_no, d) for d in range(1, 8) if d not in days],
        )
        c.executemany(
            "INSERT OR IGNORE INTO plan_progress (student_id, week_no, day) VALUES (?, ?, ?)",
            [(student_id, week_no, d) for d in sorted(days)],
        )


def list_plans(student_id: str) -> list[WeeklyPlan]:
    with tx() as c:
        rows = c.execute(
            "SELECT plan_json FROM plans WHERE student_id = ? ORDER BY week_no", (student_id,)
        ).fetchall()
    return [WeeklyPlan.model_validate_json(r["plan_json"]) for r in rows]


# --- quizzes -------------------------------------------------------------------


def _insert_attempt(
    c: sqlite3.Connection,
    student_id: str,
    quiz: QuizSet,
    chosen: list[int | None],
    at: str | None,
) -> tuple[int, int, int]:
    """One quiz part and its questions; returns (attempt id, correct, total)."""
    correct = sum(q.correct_index == a for q, a in zip(quiz.questions, chosen, strict=True))
    total = len(quiz.questions)
    cur = c.execute(
        """INSERT INTO quiz_attempts
           (student_id, topic, difficulty, total, correct, score_pct, attempted_at)
           VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))""",
        (
            student_id,
            quiz.topic,
            quiz.difficulty,
            total,
            correct,
            round(100 * correct / total, 1),
            at,
        ),
    )
    c.executemany(
        """INSERT INTO quiz_questions
           (attempt_id, question_hash, text, correct_index, chosen_index)
           VALUES (?, ?, ?, ?, ?)""",
        [
            (cur.lastrowid, text_hash(q.text), q.text, q.correct_index, a)
            for q, a in zip(quiz.questions, chosen, strict=True)
        ],
    )
    return cur.lastrowid, correct, total


def save_quiz_attempt(
    student_id: str, quiz: QuizSet, chosen: list[int | None], at: str | None = None
) -> float:
    with tx() as c:
        _, correct, total = _insert_attempt(c, student_id, quiz, chosen, at)
    return round(100 * correct / total, 1)


def save_quiz_run(
    student_id: str, parts: list[tuple[QuizSet, list[int | None]]], at: str | None = None
) -> int:
    """A quiz of several parts (topic x difficulty) in one transaction: each part an attempt,
    in the order given (so the last part of a topic is its latest attempt). Returns run id."""
    with tx() as c:
        saved = [_insert_attempt(c, student_id, quiz, chosen, at) for quiz, chosen in parts]
        correct, total = sum(s[1] for s in saved), sum(s[2] for s in saved)
        cur = c.execute(
            """INSERT INTO quiz_runs (student_id, total, correct, score_pct, attempted_at)
               VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))""",
            (student_id, total, correct, round(100 * correct / total, 1), at),
        )
        c.executemany(
            "INSERT INTO quiz_run_parts (run_id, attempt_id) VALUES (?, ?)",
            [(cur.lastrowid, s[0]) for s in saved],
        )
        return cur.lastrowid


def quiz_runs(student_id: str, limit: int = 20) -> list[sqlite3.Row]:
    """Recent multi-part quizzes, newest first: when, size, score and the topics in it."""
    with tx() as c:
        return c.execute(
            """SELECT r.id, r.attempted_at, r.total, r.correct, r.score_pct,
                      GROUP_CONCAT(DISTINCT a.topic) AS topics
               FROM quiz_runs r
               JOIN quiz_run_parts p ON p.run_id = r.id
               JOIN quiz_attempts a ON a.id = p.attempt_id
               WHERE r.student_id = ? GROUP BY r.id ORDER BY r.id DESC LIMIT ?""",
            (student_id, limit),
        ).fetchall()


def accuracy_grid(student_id: str) -> list[sqlite3.Row]:
    """Every question answered, summed per topic and difficulty."""
    with tx() as c:
        return c.execute(
            """SELECT topic, difficulty, SUM(correct) AS correct, SUM(total) AS total
               FROM quiz_attempts WHERE student_id = ? GROUP BY topic, difficulty""",
            (student_id,),
        ).fetchall()


def topic_stats(student_id: str) -> dict[str, dict]:
    """Per quizzed topic, in one query: avg_pct, the share of questions answered correctly
    over its three most recent attempts (weighted by size; for equal-sized quizzes the plain
    average), and the latest attempt's last_pct and last_difficulty."""
    with tx() as c:
        rows = c.execute(
            """SELECT topic, 100.0 * SUM(correct) / SUM(total) AS avg_pct,
                      MAX(CASE WHEN rn = 1 THEN score_pct END) AS last_pct,
                      MAX(CASE WHEN rn = 1 THEN difficulty END) AS last_difficulty
               FROM (SELECT topic, score_pct, difficulty, correct, total, ROW_NUMBER() OVER (
                       PARTITION BY topic ORDER BY attempted_at DESC, id DESC) AS rn
                     FROM quiz_attempts WHERE student_id = ?)
               WHERE rn <= 3 GROUP BY topic""",
            (student_id,),
        ).fetchall()
    return {
        r["topic"]: {
            "avg_pct": round(r["avg_pct"], 1),
            "last_pct": r["last_pct"],
            "last_difficulty": r["last_difficulty"],
        }
        for r in rows
    }


def topic_performance(student_id: str) -> dict[str, float]:
    """Average score_pct over each topic's three most recent attempts."""
    return {t: s["avg_pct"] for t, s in topic_stats(student_id).items()}


def last_attempt(student_id: str, topic: str) -> sqlite3.Row | None:
    with tx() as c:
        return c.execute(
            """SELECT score_pct, difficulty FROM quiz_attempts WHERE student_id = ? AND topic = ?
               ORDER BY attempted_at DESC, id DESC LIMIT 1""",
            (student_id, topic),
        ).fetchone()


def asked_questions(student_id: str, topic: str, limit: int = 30) -> list[str]:
    with tx() as c:
        rows = c.execute(
            """SELECT qq.text FROM quiz_questions qq
               JOIN quiz_attempts qa ON qa.id = qq.attempt_id
               WHERE qa.student_id = ? AND qa.topic = ?
               ORDER BY qq.id DESC LIMIT ?""",
            (student_id, topic, limit),
        ).fetchall()
    return [r["text"] for r in rows]


def quiz_history(student_id: str) -> list[sqlite3.Row]:
    with tx() as c:
        return c.execute(
            """SELECT a.attempted_at, a.topic, a.difficulty, a.score_pct, a.correct, a.total,
                      p.run_id
               FROM quiz_attempts a LEFT JOIN quiz_run_parts p ON p.attempt_id = a.id
               WHERE a.student_id = ? ORDER BY a.attempted_at, a.id""",
            (student_id,),
        ).fetchall()


# --- interviews ----------------------------------------------------------------


def save_turn(
    student_id: str,
    session_id: str,
    interview_type: str,
    question: str,
    answer: str,
    ev: AnswerEvaluation,
    at: str | None = None,
) -> None:
    with tx() as c:
        c.execute(
            """INSERT INTO interview_turns (student_id, session_id, interview_type, question,
                 answer, scores_json, overall, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))""",
            (
                student_id,
                session_id,
                interview_type,
                question,
                answer,
                json.dumps(ev.scores),
                ev.overall,
                at,
            ),
        )


def past_turns(student_id: str, exclude_session: str | None = None, limit: int = 30) -> list[dict]:
    """Most recent Q/A pairs from earlier sessions — the interview agent's long-term memory."""
    with tx() as c:
        rows = c.execute(
            """SELECT question, answer FROM interview_turns
               WHERE student_id = ? AND session_id IS NOT ?
               ORDER BY created_at DESC, id DESC LIMIT ?""",
            (student_id, exclude_session, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def interview_history(student_id: str) -> list[sqlite3.Row]:
    with tx() as c:
        return c.execute(
            """SELECT session_id, interview_type, MIN(created_at) AS started,
                      AVG(overall) AS avg_overall, COUNT(*) AS turns
               FROM interview_turns WHERE student_id = ?
               GROUP BY session_id ORDER BY started""",
            (student_id,),
        ).fetchall()


# --- agent logs ----------------------------------------------------------------


def log_call(
    agent: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    student_id: str | None = None,
    failed: str | None = None,
) -> int:
    """One LLM call. `failed`: why the call produced nothing usable; the row then carries
    reject_reason "failed: ..." and no critic verdict (agent_logs has no status column,
    and existing tables are not altered)."""
    with tx() as c:
        cur = c.execute(
            """INSERT INTO agent_logs (student_id, agent_name, model_used, input_tokens,
                                       output_tokens, latency_ms, reject_reason)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                student_id,
                agent,
                model,
                input_tokens,
                output_tokens,
                latency_ms,
                f"{FAILED}{failed}" if failed else None,
            ),
        )
        return cur.lastrowid


def mark_failed(log_id: int, retry_count: int, reason: str) -> None:
    """A generated draft that could not be judged (verify raised): failed, not rejected."""
    with tx() as c:
        c.execute(
            "UPDATE agent_logs SET critic_approved = NULL, retry_count = ?, reject_reason = ? "
            "WHERE id = ?",
            (retry_count, f"{FAILED}{reason}", log_id),
        )


def mark_log(log_id: int, approved: bool, retry_count: int, reject_reason: str | None) -> None:
    with tx() as c:
        c.execute(
            """UPDATE agent_logs SET critic_approved = ?, retry_count = ?, reject_reason = ?
               WHERE id = ?""",
            (approved, retry_count, reject_reason, log_id),
        )


def agent_stats() -> list[sqlite3.Row]:
    with tx() as c:
        return c.execute(
            """SELECT agent_name, COUNT(*) AS calls,
                      ROUND(AVG(latency_ms)) AS avg_latency_ms,
                      ROUND(AVG(input_tokens + output_tokens)) AS avg_tokens,
                      COALESCE(SUM(critic_approved = 0), 0) AS rejections,
                      COALESCE(SUM(reject_reason LIKE 'failed: %'), 0) AS failures,
                      ROUND(AVG(CASE WHEN critic_approved IS NOT NULL
                                     THEN critic_approved = 0 END), 2) AS rejection_rate
               FROM agent_logs GROUP BY agent_name ORDER BY agent_name"""
        ).fetchall()


def recent_rejections(limit: int = 10) -> list[sqlite3.Row]:
    with tx() as c:
        return c.execute(
            """SELECT created_at, agent_name, retry_count, reject_reason FROM agent_logs
               WHERE critic_approved = 0 ORDER BY id DESC LIMIT ?""",
            (limit,),
        ).fetchall()


# --- resume versions -----------------------------------------------------------


def save_resume_version(
    student_id: str,
    domain_id: str,
    target_role: str,
    resume: dict,
    ats_score: int,
    at: str | None = None,
) -> int:
    with tx() as c:
        cur = c.execute(
            """INSERT INTO resume_versions
               (student_id, domain_id, target_role, resume_json, ats_score, created_at)
               VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))""",
            (student_id, domain_id, target_role, json.dumps(resume), ats_score, at),
        )
        return cur.lastrowid


def resume_versions(student_id: str) -> list[dict]:
    """Every saved resume, oldest first, with its JSON decoded."""
    with tx() as c:
        rows = c.execute(
            """SELECT id, domain_id, target_role, resume_json, ats_score, created_at
               FROM resume_versions WHERE student_id = ? ORDER BY id""",
            (student_id,),
        ).fetchall()
    return [{**dict(r), "resume": json.loads(r["resume_json"])} for r in rows]


def first_resume_domain(student_id: str) -> sqlite3.Row | None:
    """The domain and date of the student's first saved resume (their locked domain)."""
    with tx() as c:
        return c.execute(
            """SELECT domain_id, created_at FROM resume_versions WHERE student_id = ?
               ORDER BY id LIMIT 1""",
            (student_id,),
        ).fetchone()


def plan_days_done_since(student_id: str, since: str) -> int:
    with tx() as c:
        return c.execute(
            "SELECT COUNT(*) FROM plan_progress WHERE student_id = ? AND done_at >= ?",
            (student_id, since),
        ).fetchone()[0]


# --- project space -------------------------------------------------------------

PROJECT_FIELDS = ("name", "summary", "tech", "repo_url", "status", "readme", "on_resume")


def save_project(student_id: str, fields: dict, project_id: int | None = None) -> int:
    """Create a project, or update `project_id` (only when it is this student's)."""
    values = [fields[k] for k in PROJECT_FIELDS]
    with tx() as c:
        if project_id is None:
            cur = c.execute(
                """INSERT INTO projects
                   (student_id, name, summary, tech, repo_url, status, readme, on_resume)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (student_id, *values),
            )
            return cur.lastrowid
        c.execute(
            """UPDATE projects SET name = ?, summary = ?, tech = ?, repo_url = ?, status = ?,
                 readme = ?, on_resume = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ? AND student_id = ?""",
            (*values, project_id, student_id),
        )
        return project_id


def projects(student_id: str) -> list[sqlite3.Row]:
    """The student's projects, most recently active first (an update or an edit bumps
    updated_at), with their update count."""
    with tx() as c:
        return c.execute(
            """SELECT p.*, COUNT(u.id) AS updates
               FROM projects p LEFT JOIN project_updates u ON u.project_id = p.id
               WHERE p.student_id = ? GROUP BY p.id ORDER BY p.updated_at DESC, p.id DESC""",
            (student_id,),
        ).fetchall()


def delete_project(student_id: str, project_id: int) -> None:
    with tx() as c:
        c.execute("DELETE FROM projects WHERE id = ? AND student_id = ?", (project_id, student_id))


def add_project_update(student_id: str, project_id: int, note: str, at: str | None = None) -> bool:
    """Log work on a project; False when the project is not this student's."""
    with tx() as c:
        owned = c.execute(
            "SELECT 1 FROM projects WHERE id = ? AND student_id = ?", (project_id, student_id)
        ).fetchone()
        if not owned:
            return False
        c.execute(
            """INSERT INTO project_updates (project_id, note, created_at)
               VALUES (?, ?, COALESCE(?, CURRENT_TIMESTAMP))""",
            (project_id, note, at),
        )
        c.execute("UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (project_id,))
        return True


def project_updates(student_id: str) -> list[sqlite3.Row]:
    """Every logged update of the student's projects, newest first."""
    with tx() as c:
        return c.execute(
            """SELECT u.id, u.project_id, p.name AS project, u.note, u.created_at
               FROM project_updates u JOIN projects p ON p.id = u.project_id
               WHERE p.student_id = ? ORDER BY u.created_at DESC, u.id DESC""",
            (student_id,),
        ).fetchall()
