"""llm.call in mock mode and, through a fake Groq client behind core/ai_router.py, every
live-mode code path; plus the offline tier when no provider answers."""

import json
from types import SimpleNamespace

import groq
import httpx
import pytest

from core import ai_router
from piq import db, llm, mock, offline
from piq.config import KEY_COOLDOWN_S, settings
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
    # Errors surface as before; the offline tier has its own tests below.
    monkeypatch.setenv("AI_OFFLINE_FALLBACK", "false")
    settings.cache_clear()

    def install(*replies) -> FakeGroq:
        fake = FakeGroq(*replies)
        monkeypatch.setattr(ai_router, "_groq_client", lambda *_: fake)
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
    # Was "no row at all"; a failed call is now logged, marked failed, never as a success.
    [row] = _rows()
    assert row["reject_reason"].startswith("failed: interviewer: output failed validation")
    assert row["critic_approved"] is None and row["latency_ms"] >= 0


def test_groq_maps_sizes_to_models(live):
    groq_provider = ai_router.PROVIDERS["groq"]
    assert (groq_provider.model("large"), groq_provider.model("small")) == (
        "large-model",
        "small-model",
    )


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
    assert (row["model_used"], row["input_tokens"], row["output_tokens"]) == (
        "groq:small-model",
        10,
        5,
    )


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
    repair = fake.requests[1]["messages"][-1]["content"]
    assert "json_validate_failed: bad output" in repair  # Groq's own words reach the model


def test_live_failed_call_is_logged_with_its_tokens_and_latency(live):
    live("not json at all", _status_error(groq.InternalServerError, 500, "boom"))
    with pytest.raises(llm.LLMError, match="Groq API error"):
        _call()
    [row] = _rows()
    assert (row["input_tokens"], row["output_tokens"]) == (10, 5)  # the first reply's
    assert row["reject_reason"].startswith("failed: Groq API error")
    assert row["critic_approved"] is None and row["latency_ms"] >= 0


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


def test_live_rate_limit_without_hint_reports_the_key_cooldown(live):
    live(_rate_limit({}))
    with pytest.raises(llm.RateLimited, match=f"about {KEY_COOLDOWN_S} s") as exc:
        _call()
    assert exc.value.retry_after == pytest.approx(KEY_COOLDOWN_S, abs=1)  # the key's rest


# --- the key pool: round robin and failover ----------------------------------------------


@pytest.fixture
def pool(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    monkeypatch.setenv("GROQ_API_KEY_1", "key-one")
    monkeypatch.setenv("GROQ_API_KEY_2", "key-two")
    monkeypatch.setenv("GROQ_MODEL_LARGE", "large-model")
    monkeypatch.setenv("GROQ_MODEL_SMALL", "small-model")
    monkeypatch.setenv("AI_OFFLINE_FALLBACK", "false")
    settings.cache_clear()
    used: list[str] = []

    def install(*replies) -> FakeGroq:
        fake = FakeGroq(*replies)

        def client(key, timeout):
            used.append(key)
            return fake

        monkeypatch.setattr(ai_router, "_groq_client", client)
        return fake

    return install, used


def test_requests_take_the_keys_in_turn(pool):
    install, used = pool
    install(json.dumps(VALID), json.dumps(VALID), json.dumps(VALID))
    for _ in range(3):
        _call()
    assert used == ["key-one", "key-two", "key-one"]  # round robin
    assert settings().groq_api_key == "key-one"


def test_a_rate_limited_key_fails_over_to_the_other(pool):
    install, used = pool
    install(_status_error(groq.RateLimitError, 429, "limit"), json.dumps(VALID))
    out, _ = _call()
    assert out.question == "Tell me more?" and used == ["key-one", "key-two"]


def test_both_keys_rate_limited_raises_rate_limited(pool):
    install, used = pool
    install(
        _status_error(groq.RateLimitError, 429, "limit"),
        _status_error(groq.RateLimitError, 429, "limit"),
    )
    with pytest.raises(llm.RateLimited):
        _call()
    assert used == ["key-one", "key-two"]


def test_one_key_still_works_and_needs_no_numbered_keys(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "only")
    settings.cache_clear()
    assert settings().groq_api_keys == ("only",)
    assert ai_router.PROVIDERS["groq"].pool().order() == ["only"]


def test_comma_separated_pools_merge_with_single_keys_without_repeats(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEYS", " a , b,,c ")
    monkeypatch.setenv("GROQ_API_KEY", "b")
    monkeypatch.setenv("GROQ_API_KEY_1", "d")
    monkeypatch.setenv("GEMINI_API_KEYS", "g1,g2")
    monkeypatch.setenv("GEMINI_API_KEY", "g3")
    settings.cache_clear()
    s = settings()
    assert s.groq_api_keys == ("a", "b", "c", "d") and s.groq_api_key == "a"
    assert s.gemini_api_keys == ("g1", "g2", "g3") and s.gemini_api_key == "g1"


# --- the offline tier: no provider answers ---------------------------------------------------


def test_no_provider_set_up_is_served_by_the_offline_tier(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    settings.cache_clear()
    monkeypatch.setattr(offline, "respond", lambda agent, ctx: VALID)
    out, _ = _call()
    assert out == InterviewTurn(**VALID)  # the deterministic answer, validated like any other
    [row] = _rows()
    assert row["model_used"] == "offline" and row["reject_reason"] is None


def test_a_failing_provider_falls_back_to_the_offline_tier(live, monkeypatch):
    monkeypatch.setenv("AI_OFFLINE_FALLBACK", "true")
    settings.cache_clear()
    monkeypatch.setattr(offline, "respond", lambda agent, ctx: VALID)
    live(_status_error(groq.InternalServerError, 500, "boom"))
    out, _ = _call()
    assert out == InterviewTurn(**VALID) and _rows()[0]["model_used"] == "offline"


def test_rate_limited_names_the_provider(live):
    live(_rate_limit({"retry-after": "3"}))
    with pytest.raises(llm.RateLimited, match="^Groq free-tier rate limit reached"):
        _call()


def test_an_agent_without_an_offline_answer_raises_llm_error(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    settings.cache_clear()
    with pytest.raises(llm.LLMError, match="no offline answer"):
        llm.call(InterviewTurn, agent="no-such-agent", system="s", user="u", context={})


def test_offline_tier_off_and_nothing_set_up_names_the_keys(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    monkeypatch.setenv("AI_OFFLINE_FALLBACK", "false")
    settings.cache_clear()
    with pytest.raises(llm.LLMError, match="GROQ_API_KEYS, GEMINI_API_KEYS or OLLAMA_BASE_URL"):
        _call()
