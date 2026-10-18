"""llm.call in mock mode and, through a fake Groq client, every live-mode code path."""

import json
from types import SimpleNamespace

import groq
import httpx
import pytest

from piq import db, llm, mock
from piq.config import settings
from piq.schemas import InterviewTurn

VALID = {"question": "Tell me more?", "intent": "i", "is_followup": False, "is_final": False}


def _call(size: str = "large") -> tuple[InterviewTurn, int]:
    return llm.call(InterviewTurn, agent="interviewer", system="s", user="u", context={}, size=size)


def _rows() -> list[dict]:
    with db.tx() as c:
        return [dict(r) for r in c.execute("SELECT * FROM agent_logs ORDER BY id")]


def _status_error(cls, code: int, message: str):
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return cls(message, response=httpx.Response(code, request=req), body=None)


class FakeGroq:
    """Stands in for groq.Groq: replays canned contents or raises queued exceptions."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=reply))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        )


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL_LARGE", "large-model")
    monkeypatch.setenv("GROQ_MODEL_SMALL", "small-model")
    settings.cache_clear()

    def install(*replies) -> FakeGroq:
        fake = FakeGroq(*replies)
        monkeypatch.setattr(llm, "_client", lambda: fake)
        return fake

    return install


# --- mock mode -----------------------------------------------------------------


def test_mock_mode_repairs_invalid_output_once(monkeypatch):
    replies = iter([{"question": "x"}, VALID])
    monkeypatch.setattr(mock, "respond", lambda agent, ctx: next(replies))
    out, log_id = _call()
    assert out.question == "Tell me more?"
    [row] = _rows()
    assert (row["id"], row["agent_name"], row["model_used"]) == (log_id, "interviewer", "mock")


def test_mock_mode_raises_after_second_invalid_output(monkeypatch):
    monkeypatch.setattr(mock, "respond", lambda agent, ctx: {"question": "x"})
    with pytest.raises(llm.LLMError, match="failed validation twice"):
        _call()
    assert _rows() == []  # failed calls are not logged as successful generations


def test_model_for_maps_sizes(live):
    assert (llm.model_for("large"), llm.model_for("small")) == ("large-model", "small-model")


# --- live mode via fake client -------------------------------------------------


def test_live_request_shape_and_logging(live):
    fake = live(json.dumps(VALID))
    out, _ = _call(size="small")
    assert out == InterviewTurn(**VALID)
    [req] = fake.requests
    assert req["model"] == "small-model"
    assert req["response_format"] == {"type": "json_object"}
    assert "JSON Schema" in req["messages"][0]["content"]
    [row] = _rows()
    assert (row["model_used"], row["input_tokens"], row["output_tokens"]) == ("small-model", 10, 5)


def test_live_repair_feeds_validation_error_back_and_sums_tokens(live):
    fake = live("not json at all", json.dumps(VALID))
    _call()
    assert len(fake.requests) == 2
    repair = fake.requests[1]["messages"][-1]["content"]
    assert repair.startswith("That output failed validation")
    [row] = _rows()
    assert (row["input_tokens"], row["output_tokens"]) == (20, 10)


def test_live_json_validate_failed_is_repairable(live):
    err = _status_error(groq.BadRequestError, 400, "json_validate_failed: bad output")
    fake = live(err, json.dumps(VALID))
    out, _ = _call()
    assert out.question == "Tell me more?" and len(fake.requests) == 2


def test_live_other_bad_request_raises(live):
    live(_status_error(groq.BadRequestError, 400, "context_length_exceeded"))
    with pytest.raises(llm.LLMError, match="rejected the request"):
        _call()


def test_live_unknown_model_gives_actionable_error(live):
    live(_status_error(groq.NotFoundError, 404, "model not found"))
    with pytest.raises(llm.LLMError, match="GROQ_MODEL_LARGE"):
        _call()


def test_live_server_error_is_wrapped(live):
    live(_status_error(groq.InternalServerError, 500, "boom"))
    with pytest.raises(llm.LLMError, match="Groq API error"):
        _call()


def _rate_limit(headers: dict) -> groq.RateLimitError:
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    resp = httpx.Response(429, request=req, headers=headers)
    return groq.RateLimitError("rate limit reached", response=resp, body=None)


def test_live_rate_limit_carries_retry_after(live):
    live(_rate_limit({"retry-after": "7"}))
    with pytest.raises(llm.RateLimited, match="about 7 s") as exc:
        _call()
    assert exc.value.retry_after == 7.0
    assert isinstance(exc.value, llm.LLMError)  # the UI's existing error path still applies


def test_live_rate_limit_without_hint(live):
    live(_rate_limit({}))
    with pytest.raises(llm.RateLimited, match="Try again shortly") as exc:
        _call()
    assert exc.value.retry_after is None
