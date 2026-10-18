-- Rule: agent outputs that are always read whole are stored as JSON;
-- anything filtered, aggregated or charted gets its own column.

CREATE TABLE IF NOT EXISTS students (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    usn             TEXT NOT NULL UNIQUE,
    target_role     TEXT NOT NULL,
    readiness_score INTEGER,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS profiles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    profile_json    TEXT NOT NULL,
    readiness_score INTEGER NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS plans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id  TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    week_no     INTEGER NOT NULL,
    plan_json   TEXT NOT NULL,
    rationale   TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (student_id, week_no)
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id   TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    topic        TEXT NOT NULL,
    difficulty   TEXT NOT NULL,
    total        INTEGER NOT NULL,
    correct      INTEGER NOT NULL,
    score_pct    REAL NOT NULL,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quiz_questions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id    INTEGER NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
    question_hash TEXT NOT NULL,
    text          TEXT NOT NULL,
    correct_index INTEGER NOT NULL,
    chosen_index  INTEGER
);

CREATE TABLE IF NOT EXISTS interview_turns (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id     TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    session_id     TEXT NOT NULL,
    interview_type TEXT NOT NULL,
    question       TEXT NOT NULL,
    answer         TEXT NOT NULL,
    scores_json    TEXT NOT NULL,
    overall        REAL NOT NULL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      TEXT,
    agent_name      TEXT NOT NULL,
    model_used      TEXT NOT NULL,
    input_tokens    INTEGER,
    output_tokens   INTEGER,
    latency_ms      INTEGER,
    critic_approved BOOLEAN,
    retry_count     INTEGER,
    reject_reason   TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quiz_student_topic ON quiz_attempts (student_id, topic, attempted_at);
CREATE INDEX IF NOT EXISTS idx_turns_student ON interview_turns (student_id, created_at);
CREATE INDEX IF NOT EXISTS idx_qq_hash ON quiz_questions (question_hash);
