import pytest

from piq import db
from piq.config import settings


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Every test: mock LLM, fresh SQLite file, default retry budget, never the developer's .env."""
    monkeypatch.setenv("PIQ_DOTENV", str(tmp_path / "absent.env"))
    monkeypatch.setenv("MOCK_MODE", "true")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("MAX_CRITIC_RETRIES", "2")
    for k in ("GROQ_API_KEY", "GROQ_MODEL_LARGE", "GROQ_MODEL_SMALL"):
        monkeypatch.delenv(k, raising=False)
    settings.cache_clear()
    db.init_db()
    yield
    settings.cache_clear()
