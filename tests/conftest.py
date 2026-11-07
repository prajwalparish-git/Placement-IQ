import csv

import pytest

from core import ai_router, speech_router
from database.connection import reset_manager
from piq import agents, db, question_bank, services
from piq.config import settings


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Every test: mock LLM, fresh SQLite file, default retry budget, never the developer's .env,
    and no question bank (tests never depend on the real bank's contents; those that need one
    use the small `bank` fixture below)."""
    monkeypatch.setenv("PIQ_DOTENV", str(tmp_path / "absent.env"))
    monkeypatch.setenv("MOCK_MODE", "true")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("MAX_CRITIC_RETRIES", "2")
    monkeypatch.setenv("TELEMETRY_DB_PATH", str(tmp_path / "telemetry.db"))
    for k in (
        "GROQ_API_KEY",
        "GROQ_API_KEY_1",
        "GROQ_API_KEY_2",
        "GROQ_MODEL_LARGE",
        "GROQ_MODEL_SMALL",
        "SEED_DEMO",
        "DATABASE_URL",
        "AI_PROVIDERS",
        "AI_OFFLINE_FALLBACK",
        "GEMINI_API_KEY",
        "GEMINI_MODEL",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "ELEVENLABS_API_KEY",
        "ELEVENLABS_VOICE_ID",
        "ELEVENLABS_MODEL",
    ):
        monkeypatch.delenv(k, raising=False)
    settings.cache_clear()
    ai_router.reset()  # breakers and health checks are process-wide: start each test closed
    speech_router.reset()
    reset_manager()
    db.init_db()
    agents.clear_verdict_cache()
    services.sample_resumes.cache_clear()
    monkeypatch.setattr(question_bank, "BANK", tmp_path / "absent_bank.csv")
    question_bank.clear_cache()
    yield
    reset_manager()
    settings.cache_clear()
    services.sample_resumes.cache_clear()
    question_bank.clear_cache()


# --- a small question bank for the tests that need one --------------------------------------

HEADER = [
    "category",
    "role_or_stream",
    "topic",
    "difficulty",
    "question",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct_option",
    "explanation",
    "bloom_level",
]


def _row(topic: str, difficulty: str, n: int, **changes) -> dict:
    row = {
        "category": "Computer Science",
        "role_or_stream": "Database Administrator (DBA)",
        "topic": topic,
        "difficulty": difficulty,
        "question": f"Bank question number {n} about {topic}?",
        "option_a": "first",
        "option_b": "second",
        "option_c": "third",
        "option_d": "fourth",
        "correct_option": "C",
        "explanation": "Because.",
        "bloom_level": "understand",
    }
    return row | changes


@pytest.fixture
def bank(tmp_path, monkeypatch):
    rows = [_row("SQL_Indexing", "easy", i) for i in range(6)]
    rows += [_row("Transactions_ACID", "medium", i + 10) for i in range(4)]
    rows += [
        _row("SQL_Indexing", "easy", 99, option_d="first"),  # repeated option
        _row("SQL_Indexing", "easy", 98, correct_option="E"),  # no such answer
        _row("SQL_Indexing", "easy", 0),  # same text as an earlier row
        _row("Flutter_Dart", "easy", 50),  # a topic no domain teaches
        _row("Not_In_The_Map", "easy", 51),
        _row("SQL_Indexing", "trivial", 52),  # not a difficulty
    ]
    path = tmp_path / "bank.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows)
    monkeypatch.setattr(question_bank, "BANK", path)
    question_bank.clear_cache()
    return path
