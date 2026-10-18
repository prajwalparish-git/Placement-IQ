from types import SimpleNamespace

import groq
import pytest

from piq.config import settings
from scripts import check_models

HEADERS = {
    "x-ratelimit-remaining-requests": "990",
    "x-ratelimit-limit-requests": "1000",
    "x-ratelimit-remaining-tokens": "7800",
    "x-ratelimit-limit-tokens": "8000",
}


class FakeGroq:
    served = ["big-model", "small-model", "whisper-large-v3"]
    reply = '{"ok": true}'

    def __init__(self, **kwargs):
        self.models = SimpleNamespace(
            list=lambda: SimpleNamespace(data=[SimpleNamespace(id=m) for m in self.served])
        )
        raw = SimpleNamespace(
            headers=HEADERS,
            parse=lambda: SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=self.reply))]
            ),
        )
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(with_raw_response=SimpleNamespace(create=lambda **kw: raw))
        )


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL_LARGE", "big-model")
    monkeypatch.setenv("GROQ_MODEL_SMALL", "small-model")
    settings.cache_clear()
    monkeypatch.setattr(groq, "Groq", FakeGroq)


def test_mock_mode_has_nothing_to_check(capsys):
    assert check_models.main() == 0
    assert "MOCK_MODE=true" in capsys.readouterr().out


def test_missing_configuration_exits_2(monkeypatch, capsys):
    monkeypatch.setenv("MOCK_MODE", "false")
    settings.cache_clear()
    assert check_models.main() == 2
    assert "config error" in capsys.readouterr().out


def test_served_models_pass_and_report_quota(live, capsys):
    assert check_models.main() == 0
    out = capsys.readouterr().out
    assert "chat models served: big-model, small-model" in out  # whisper filtered out
    assert "OK   GROQ_MODEL_LARGE=big-model" in out
    assert "requests left today 990/1000, tokens left this minute 7800/8000" in out


def test_retired_model_fails(live, monkeypatch, capsys):
    monkeypatch.setenv("GROQ_MODEL_SMALL", "llama3-8b-8192")
    settings.cache_clear()
    assert check_models.main() == 1
    assert "FAIL GROQ_MODEL_SMALL=llama3-8b-8192: not served" in capsys.readouterr().out


def test_non_json_reply_fails(live, monkeypatch, capsys):
    monkeypatch.setattr(FakeGroq, "reply", "sure, here you go")
    assert check_models.main() == 1
    assert "JSON-mode request failed" in capsys.readouterr().out
