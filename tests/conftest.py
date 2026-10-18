import pytest

from piq.config import settings


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Every test: mock LLM, default retry budget, never the developer's .env."""
    monkeypatch.setenv("PIQ_DOTENV", str(tmp_path / "absent.env"))
    monkeypatch.setenv("MOCK_MODE", "true")
    monkeypatch.setenv("MAX_CRITIC_RETRIES", "2")
    for k in ("GROQ_API_KEY", "GROQ_MODEL_LARGE", "GROQ_MODEL_SMALL"):
        monkeypatch.delenv(k, raising=False)
    settings.cache_clear()
    yield
    settings.cache_clear()
