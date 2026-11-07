"""core/ai_router.py: circuit breaker, provider order and failover, health, and the Gemini and
Ollama wire formats (httpx MockTransport; nothing touches the network)."""

import json

import httpx
import pytest

from core import ai_router
from core.ai_router import AllProvidersDown, CircuitBreaker, Completion, InvalidJson, ProviderError
from piq.config import ROUTER_BROKEN_COOLDOWN_S, ConfigError, settings

MESSAGES = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


# --- circuit breaker --------------------------------------------------------------------------


def test_breaker_opens_after_threshold_and_half_opens_after_cooldown():
    clock = Clock()
    b = CircuitBreaker(threshold=2, cooldown=60, clock=clock)
    b.failure("boom")
    assert b.state == "closed" and b.allow()
    b.failure("boom")
    assert b.state == "open" and not b.allow() and b.retry_in() == 60
    clock.now += 60
    assert b.state == "half-open" and b.allow()
    b.failure("still down")  # the trial failed: open again at once
    assert b.state == "open"
    clock.now += 60
    b.success()
    assert b.state == "closed" and b.failures == 0 and b.reason == ""


def test_breaker_opens_at_once_for_a_rate_limit_and_honours_retry_after():
    clock = Clock()
    b = CircuitBreaker(threshold=5, cooldown=10, clock=clock)
    b.failure("429", retry_after=90, rate_limited=True)
    assert b.state == "open" and b.retry_in() == 90 and b.rate_limited


def test_breaker_cooldown_override_for_broken_config():
    clock = Clock()
    b = CircuitBreaker(threshold=5, cooldown=10, clock=clock)
    b.failure("model retired", cooldown=ROUTER_BROKEN_COOLDOWN_S)
    assert b.retry_in() == ROUTER_BROKEN_COOLDOWN_S


# --- routing with fake providers ------------------------------------------------------------


class Fake:
    def __init__(self, name: str, *replies, unavailable: str = "") -> None:
        self.name, self.replies, self.why, self.calls = name, list(replies), unavailable, 0

    def unavailable(self) -> str:
        return self.why

    def model(self, size: str) -> str:
        return f"{self.name}-model"

    def complete(self, messages, *, size, temperature, agent) -> Completion:
        self.calls += 1
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return Completion(reply, 1, 1, self.name, self.model(size))


@pytest.fixture
def fakes(monkeypatch):
    def install(**providers: Fake) -> dict[str, Fake]:
        monkeypatch.setattr(ai_router, "PROVIDERS", providers)
        monkeypatch.setenv("AI_PROVIDERS", ",".join(providers))
        monkeypatch.setenv("MOCK_MODE", "false")
        settings.cache_clear()
        return providers

    return install


def _complete() -> Completion:
    return ai_router.complete(MESSAGES, size="large", temperature=0.2, agent="planner")


def test_first_healthy_provider_answers(fakes):
    p = fakes(gemini=Fake("gemini", "g"), groq=Fake("groq", "q"), ollama=Fake("ollama", "o"))
    out = _complete()
    assert (out.text, out.label) == ("g", "gemini:gemini-model")
    assert (p["groq"].calls, p["ollama"].calls) == (0, 0)


def test_unconfigured_providers_are_skipped(fakes):
    fakes(
        gemini=Fake("gemini", unavailable="GEMINI_API_KEY is not set"),
        groq=Fake("groq", unavailable="GROQ_API_KEY is not set"),
        ollama=Fake("ollama", "local"),
    )
    assert _complete().provider == "ollama"


def test_a_failing_provider_fails_over_and_then_its_breaker_skips_it(fakes):
    p = fakes(
        gemini=Fake("gemini", ProviderError("down"), ProviderError("down")),
        groq=Fake("groq", "q1", "q2", "q3"),
    )
    assert _complete().provider == "groq"
    assert _complete().provider == "groq"  # second failure opens Gemini's breaker
    assert ai_router.breaker("gemini").state == "open"
    assert _complete().provider == "groq"
    assert p["gemini"].calls == 2  # the third request skipped Gemini entirely


def test_a_refused_request_does_not_trip_the_breaker(fakes):
    fakes(
        gemini=Fake("gemini", *[ProviderError("bad request", counts=False)] * 3),
        groq=Fake("groq", "a", "b", "c"),
    )
    for _ in range(3):
        _complete()
    assert ai_router.breaker("gemini").state == "closed"


def test_invalid_json_is_raised_for_repair_not_failed_over(fakes):
    p = fakes(gemini=Fake("gemini", InvalidJson("bad json")), groq=Fake("groq", "q"))
    with pytest.raises(InvalidJson):
        _complete()
    assert p["groq"].calls == 0 and ai_router.breaker("gemini").state == "closed"


def test_all_down_reports_each_reason(fakes):
    fakes(
        gemini=Fake("gemini", ProviderError("Gemini is unreachable (ConnectError)")),
        groq=Fake("groq", unavailable="GROQ_API_KEY is not set"),
        ollama=Fake("ollama", ProviderError("Ollama error 500: oops")),
    )
    with pytest.raises(AllProvidersDown) as exc:
        _complete()
    e = exc.value
    assert set(e.failures) == {"gemini", "ollama"} and set(e.skipped) == {"groq"}
    assert not e.rate_limited
    assert "Gemini: Gemini is unreachable" in str(e) and "Ollama (local): Ollama error" in str(e)


def test_all_rate_limited_is_reported_with_the_shortest_hint(fakes):
    fakes(
        gemini=Fake("gemini", ProviderError("429", rate_limited=True, retry_after=40)),
        groq=Fake("groq", ProviderError("429", rate_limited=True, retry_after=12)),
    )
    with pytest.raises(AllProvidersDown) as exc:
        _complete()
    assert exc.value.rate_limited and exc.value.retry_after == 12
    # Next request: both breakers are open on a rate limit; still reported as rate-limited.
    with pytest.raises(AllProvidersDown) as exc:
        _complete()
    assert exc.value.rate_limited and set(exc.value.failures) == {"gemini", "groq"}


def test_provider_order_follows_the_setting(fakes, monkeypatch):
    fakes(gemini=Fake("gemini", "g"), groq=Fake("groq", "q"))
    monkeypatch.setenv("AI_PROVIDERS", "groq,gemini")
    settings.cache_clear()
    assert _complete().provider == "groq"


def test_unknown_provider_name_is_a_config_error(monkeypatch):
    monkeypatch.setenv("AI_PROVIDERS", "gemini,openai")
    settings.cache_clear()
    with pytest.raises(ConfigError, match="openai"):
        settings()


def test_a_half_configured_provider_is_a_config_error(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    settings.cache_clear()
    with pytest.raises(ConfigError, match="GEMINI_MODEL"):
        settings()


def test_status_and_active_provider(fakes):
    fakes(
        gemini=Fake("gemini", unavailable="GEMINI_API_KEY is not set"),
        groq=Fake("groq"),
        ollama=Fake("ollama"),
    )
    ai_router.breaker("groq").failure("x", rate_limited=True, retry_after=30)
    states = {s.name: s.state for s in ai_router.status()}
    assert states == {"gemini": "off", "groq": "paused", "ollama": "ready"}
    assert ai_router.active_provider() == "Ollama (local)"


def test_active_provider_in_mock_mode_and_with_nothing_set_up(monkeypatch):
    assert ai_router.active_provider() == "Mock mode"
    monkeypatch.setenv("MOCK_MODE", "false")
    settings.cache_clear()
    assert ai_router.active_provider() == "Offline rules"


# --- Gemini and Ollama over HTTP --------------------------------------------------------------


@pytest.fixture
def http(monkeypatch):
    seen: list[httpx.Request] = []

    def install(handler) -> list[httpx.Request]:
        def record(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        client = httpx.Client(transport=httpx.MockTransport(record))
        monkeypatch.setattr(ai_router, "_http", lambda: client)
        return seen

    return install


@pytest.fixture
def gemini_env(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    monkeypatch.setenv("AI_PROVIDERS", "gemini")
    settings.cache_clear()


def test_gemini_request_and_response_shape(gemini_env, http):
    answer = {
        "candidates": [
            {"content": {"parts": [{"text": "thinking", "thought": True}, {"text": '{"a": 1}'}]}}
        ],
        "usageMetadata": {"promptTokenCount": 7, "candidatesTokenCount": 3},
    }
    seen = http(lambda r: httpx.Response(200, json=answer))
    messages = [*MESSAGES, {"role": "assistant", "content": "x"}, {"role": "user", "content": "y"}]
    out = ai_router.complete(messages, size="small", temperature=0.3, agent="planner")
    assert (out.text, out.tokens_in, out.tokens_out, out.label) == (
        '{"a": 1}',
        7,
        3,
        "gemini:gemini-test",
    )
    [req] = seen
    assert req.url.path.endswith("/models/gemini-test:generateContent")
    assert req.headers["x-goog-api-key"] == "g-key"
    body = json.loads(req.content)
    assert body["systemInstruction"] == {"parts": [{"text": "sys"}]}
    assert [c["role"] for c in body["contents"]] == ["user", "model", "user"]
    assert body["generationConfig"] == {"temperature": 0.3, "responseMimeType": "application/json"}


@pytest.mark.parametrize(
    ("code", "headers", "match", "state"),
    [
        (429, {"retry-after": "9"}, "rate limit", "open"),
        (404, {}, "GEMINI_MODEL", "open"),
        (403, {}, "refused the API key", "open"),
        (400, {}, "rejected the request", "closed"),
        (503, {}, "Gemini API error 503", "closed"),  # one failure; the threshold is two
    ],
)
def test_gemini_errors(gemini_env, http, code, headers, match, state):
    http(lambda r: httpx.Response(code, headers=headers, json={"error": {"message": "nope"}}))
    with pytest.raises(AllProvidersDown, match=match):
        _complete()
    assert ai_router.breaker("gemini").state == state


def test_gemini_unreachable_is_a_provider_failure(gemini_env, http):
    def refuse(request):
        raise httpx.ConnectError("no route", request=request)

    http(refuse)
    with pytest.raises(AllProvidersDown, match="unreachable"):
        _complete()


@pytest.fixture
def ollama_env(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test:11434/")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3")
    monkeypatch.setenv("AI_PROVIDERS", "ollama")
    settings.cache_clear()


def _ollama(tags: list[str], status: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(status, json={"models": [{"name": t} for t in tags]})
        body = json.loads(request.content)
        assert body["format"] == "json" and body["stream"] is False
        return httpx.Response(
            200,
            json={"message": {"content": '{"ok": true}'}, "prompt_eval_count": 4, "eval_count": 2},
        )

    return handler


def test_ollama_health_check_then_chat(ollama_env, http):
    seen = http(_ollama(["llama3:latest", "mistral:7b"]))
    out = _complete()
    assert (out.text, out.label, out.tokens_in) == ('{"ok": true}', "ollama:llama3", 4)
    assert [r.url.path for r in seen] == ["/api/tags", "/api/chat"]
    _complete()  # the health answer is cached: no second probe
    assert [r.url.path for r in seen] == ["/api/tags", "/api/chat", "/api/chat"]


def test_ollama_without_the_model_pulled_is_skipped_with_the_command(ollama_env, http):
    http(_ollama(["mistral:7b"]))
    with pytest.raises(AllProvidersDown) as exc:
        _complete()
    assert "ollama pull llama3" in exc.value.skipped["ollama"]


def test_ollama_not_running_is_skipped(ollama_env, http):
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    http(refuse)
    with pytest.raises(AllProvidersDown) as exc:
        _complete()
    assert "not running" in exc.value.skipped["ollama"]
