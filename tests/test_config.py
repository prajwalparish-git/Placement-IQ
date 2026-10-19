import pytest

from piq.config import ConfigError, settings


def test_defaults_to_mock_mode(monkeypatch):
    monkeypatch.delenv("MOCK_MODE")
    settings.cache_clear()
    assert settings().mock_mode is True


@pytest.mark.parametrize("raw", ["1", "YES", " true ", "True"])
def test_truthy_mock_flags(monkeypatch, raw):
    monkeypatch.setenv("MOCK_MODE", raw)
    settings.cache_clear()
    assert settings().mock_mode is True


def test_live_mode_requires_key_and_both_models(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    settings.cache_clear()
    with pytest.raises(ConfigError, match="GROQ_MODEL_LARGE, GROQ_MODEL_SMALL"):
        settings()

    monkeypatch.setenv("GROQ_MODEL_LARGE", "large-x")
    monkeypatch.setenv("GROQ_MODEL_SMALL", "small-y")
    settings.cache_clear()
    s = settings()
    assert (s.mock_mode, s.model_large, s.model_small) == (False, "large-x", "small-y")


def test_dotenv_file_is_read_without_overriding_real_env(tmp_path, monkeypatch):
    env = tmp_path / "custom.env"
    env.write_text("MAX_CRITIC_RETRIES=5\nMOCK_MODE=false\n", encoding="utf-8")
    monkeypatch.setenv("PIQ_DOTENV", str(env))
    monkeypatch.delenv("MAX_CRITIC_RETRIES")
    settings.cache_clear()
    s = settings()
    assert s.max_critic_retries == 5  # taken from the file
    assert s.mock_mode is True  # MOCK_MODE already set in the environment wins


def test_seed_demo_is_opt_in(monkeypatch):
    assert settings().seed_demo is False
    monkeypatch.setenv("SEED_DEMO", "true")
    settings.cache_clear()
    assert settings().seed_demo is True
