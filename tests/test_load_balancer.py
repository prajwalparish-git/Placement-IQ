"""Layer 3 speed: the round-robin key pool (core/key_pool.py), 429 cooldown and failover, the
instant skip to the next tier when every key rests, and the prompt cache (core/ai_cache.py)
answering repeats in under 2 ms. Fake clients and clocks only; nothing touches the network."""

import json
import threading
import time
from collections import Counter
from types import SimpleNamespace

import groq
import httpx
import pytest

from core import ai_router
from core.ai_cache import PromptCache, request_key
from core.key_pool import KeyPoolManager, mask
from piq import db, llm
from piq.config import KEY_COOLDOWN_S, ROUTER_BROKEN_COOLDOWN_S, settings
from piq.schemas import InterviewTurn

VALID = {"question": "Tell me more?", "intent": "i", "is_followup": False, "is_final": False}
MESSAGES = [{"role": "system", "content": "sys"}, {"role": "user", "content": "plan my week"}]


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


# --- the key pool -------------------------------------------------------------------------------


def test_round_robin_spreads_requests_over_every_key():
    pool = KeyPoolManager(["k1", "k2", "k3"])
    firsts = [pool.order()[0] for _ in range(6)]
    assert firsts == ["k1", "k2", "k3", "k1", "k2", "k3"]
    assert pool.order() == ["k1", "k2", "k3"]  # each request may fall through the whole ring


def test_a_rate_limited_key_rests_for_the_cooldown_and_comes_back():
    clock = Clock()
    pool = KeyPoolManager(["k1", "k2", "k3"], clock=clock)
    pool.rate_limited("k2")
    for _ in range(3):
        assert "k2" not in pool.order()
    assert pool.available_count() == 2 and pool.retry_in() == 0  # others are free now
    assert pool.status()[1].rests_for_s == KEY_COOLDOWN_S and pool.status()[1].rate_limits == 1
    clock.now += KEY_COOLDOWN_S
    assert "k2" in pool.order() and pool.available_count() == 3


def test_the_servers_retry_after_overrides_the_default_cooldown():
    clock = Clock()
    pool = KeyPoolManager(["k1"], clock=clock)
    pool.rate_limited("k1", retry_after=7)
    assert pool.order() == [] and pool.retry_in() == 7
    clock.now += 7
    assert pool.order() == ["k1"]


def test_a_refused_key_rests_for_an_hour():
    clock = Clock()
    pool = KeyPoolManager(["bad", "good"], clock=clock)
    pool.refused("bad")
    clock.now += KEY_COOLDOWN_S
    assert pool.order() == ["good"]
    clock.now += ROUTER_BROKEN_COOLDOWN_S
    assert "bad" in pool.order()


def test_latency_is_a_moving_average_and_keys_are_masked():
    pool = KeyPoolManager(["gsk_abcdefgh1234"])
    pool.success("gsk_abcdefgh1234", 0.100)
    pool.success("gsk_abcdefgh1234", 0.200)
    [s] = pool.status()
    assert s.latency_ms == 130 and s.successes == 2  # 0.7 x 100 + 0.3 x 200
    assert s.key == mask("gsk_abcdefgh1234") == "gsk_…1234"
    assert "abcdefgh" not in repr(pool.status())


def test_the_pool_is_thread_safe_and_even():
    pool = KeyPoolManager(["k1", "k2", "k3", "k4"])
    firsts: list[str] = []
    lock = threading.Lock()

    def worker() -> None:
        for _ in range(250):
            key = pool.order()[0]
            with lock:
                firsts.append(key)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert Counter(firsts) == {"k1": 500, "k2": 500, "k3": 500, "k4": 500}


# --- failover through the router ----------------------------------------------------------------


def _rate_limit() -> groq.RateLimitError:
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    return groq.RateLimitError("limit", response=httpx.Response(429, request=req), body=None)


class FakeGroq:
    """Answers per key: a queued exception or a valid reply."""

    def __init__(self, failing: set[str]) -> None:
        self.failing, self.used = failing, []

    def client(self, key: str, timeout: float):
        def create(**kwargs):
            self.used.append(key)
            if key in self.failing:
                raise _rate_limit()
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(VALID)))],
                usage=SimpleNamespace(prompt_tokens=3, completion_tokens=2),
            )

        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


@pytest.fixture
def groq_pool(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    monkeypatch.setenv("GROQ_API_KEYS", "k1,k2,k3")
    monkeypatch.setenv("GROQ_MODEL_LARGE", "large")
    monkeypatch.setenv("GROQ_MODEL_SMALL", "small")
    monkeypatch.setenv("AI_PROVIDERS", "groq")
    settings.cache_clear()

    def install(failing: set[str]) -> FakeGroq:
        fake = FakeGroq(failing)
        monkeypatch.setattr(ai_router, "_groq_client", fake.client)
        return fake

    return install


def _ask(agent: str = "interviewer") -> ai_router.Completion:
    return ai_router.complete(MESSAGES, size="small", temperature=0.2, agent=agent)


def test_a_429_switches_to_the_next_key_within_the_same_request(groq_pool):
    fake = groq_pool({"k1"})
    t0 = time.perf_counter()
    out = _ask()
    switch = time.perf_counter() - t0
    assert out.provider == "groq" and fake.used == ["k1", "k2"]
    assert switch < 0.05  # the switch itself is in memory: well under 50 ms
    pool = ai_router.PROVIDERS["groq"].pool()
    assert pool.available_count() == 2  # k1 rests
    fake.used.clear()
    for _ in range(4):
        _ask()
    assert "k1" not in fake.used and set(fake.used) == {"k2", "k3"}


def test_when_every_key_rests_the_tier_is_skipped_without_a_call(groq_pool):
    fake = groq_pool({"k1", "k2", "k3"})
    with pytest.raises(ai_router.AllProvidersDown) as exc:
        _ask()
    assert exc.value.rate_limited and fake.used == ["k1", "k2", "k3"]
    fake.used.clear()
    t0 = time.perf_counter()
    with pytest.raises(ai_router.AllProvidersDown):
        _ask()
    assert fake.used == [] and time.perf_counter() - t0 < 0.05  # instant, no request
    [groq_status] = ai_router.status()
    assert groq_status.state == "paused" and "resting" in groq_status.detail


def test_all_keys_resting_falls_through_to_the_offline_tier_silently(groq_pool, monkeypatch):
    groq_pool({"k1", "k2", "k3"})
    from piq import offline

    monkeypatch.setattr(offline, "respond", lambda agent, ctx: VALID)
    out, _ = llm.call(InterviewTurn, agent="interviewer", system="s", user="u", context={})
    assert out == InterviewTurn(**VALID)


def test_gemini_keys_rotate_on_429(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "false")
    monkeypatch.setenv("GEMINI_API_KEYS", "g1,g2")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    monkeypatch.setenv("AI_PROVIDERS", "gemini")
    settings.cache_clear()
    used: list[str] = []
    answer = {"candidates": [{"content": {"parts": [{"text": '{"ok": 1}'}]}}]}

    def handler(request: httpx.Request) -> httpx.Response:
        key = request.headers["x-goog-api-key"]
        used.append(key)
        return httpx.Response(429 if key == "g1" else 200, json=answer)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(ai_router, "_http", lambda: client)
    assert _ask().text == '{"ok": 1}' and used == ["g1", "g2"]


def test_timeouts_are_configurable(monkeypatch):
    monkeypatch.setenv("GROQ_TIMEOUT_S", "2.5")
    monkeypatch.setenv("GEMINI_TIMEOUT_S", "6")
    settings.cache_clear()
    assert (settings().groq_timeout_s, settings().gemini_timeout_s) == (2.5, 6.0)
    monkeypatch.setenv("GROQ_TIMEOUT_S", "0")
    settings.cache_clear()
    from piq.config import ConfigError

    with pytest.raises(ConfigError, match="GROQ_TIMEOUT_S"):
        settings()


def test_supabase_url_is_the_telemetry_database_unless_database_url_is_set(monkeypatch):
    monkeypatch.setenv("SUPABASE_DB_URL", "postgresql://u:p@db.example.supabase.co:5432/postgres")
    settings.cache_clear()
    assert settings().database_url.startswith("postgresql://u:p@db.example.supabase.co")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/x")
    settings.cache_clear()
    assert settings().database_url == "postgresql://u:p@localhost/x"


# --- the prompt cache ---------------------------------------------------------------------------


def test_cache_hits_return_in_under_2_ms(tmp_path):
    cache = PromptCache(tmp_path / "c.json")
    key = request_key(MESSAGES, "small", 0.2, "planner")
    cache.put(key, '{"plan": 1}', "groq:small")
    timings = []
    for _ in range(20):
        t0 = time.perf_counter()
        entry = cache.get(request_key(MESSAGES, "small", 0.2, "planner"))
        timings.append(time.perf_counter() - t0)
    assert entry.text == '{"plan": 1}' and entry.label == "groq:small"
    assert min(timings) < 0.002 and sorted(timings)[len(timings) // 2] < 0.002


def test_the_key_covers_the_whole_request():
    base = request_key(MESSAGES, "small", 0.2, "planner")
    other = [MESSAGES[0], {"role": "user", "content": "plan my month"}]
    assert base != request_key(other, "small", 0.2, "planner")
    assert base != request_key(MESSAGES, "large", 0.2, "planner")
    assert base != request_key(MESSAGES, "small", 0.3, "planner")
    assert base != request_key(MESSAGES, "small", 0.2, "critic")


def test_cache_survives_a_restart_expires_and_drops_least_recently_used(tmp_path):
    clock = Clock()
    path = tmp_path / "c.json"
    PromptCache(path, clock=clock).put("a", "A", "groq:x")
    reloaded = PromptCache(path, clock=clock)
    assert reloaded.get("a").text == "A"
    clock.now += 10_000_000  # past the TTL
    assert reloaded.get("a") is None
    small = PromptCache(tmp_path / "s.json", max_entries=2, clock=clock)
    small.put("1", "one", "l")
    small.put("2", "two", "l")
    small.get("1")  # 1 is now the most recently used
    small.put("3", "three", "l")
    assert small.get("2") is None and small.get("1").text == "one" and len(small) == 2


def test_a_damaged_cache_file_starts_empty(tmp_path):
    path = tmp_path / "c.json"
    path.write_text("{not json", encoding="utf-8")
    cache = PromptCache(path)
    assert cache.get("x") is None
    cache.put("x", "X", "l")
    assert json.loads(path.read_text(encoding="utf-8"))["x"]["text"] == "X"


@pytest.fixture
def live_planner(groq_pool):
    return groq_pool(set())


def _rows() -> list[dict]:
    with db.tx() as c:
        return [dict(r) for r in c.execute("SELECT * FROM agent_logs ORDER BY id")]


def _plan_call():
    return llm.call(
        InterviewTurn, agent="planner", system="sys", user="same input", context={}, size="small"
    )


def test_a_repeated_plan_is_served_from_the_cache_without_a_call(live_planner):
    first, _ = _plan_call()
    t0 = time.perf_counter()
    again, _ = _plan_call()
    assert time.perf_counter() - t0 < 0.05  # validation and logging included
    assert again == first and len(live_planner.used) == 1
    assert [r["model_used"] for r in _rows()] == ["groq:small", "cache:groq:small"]
    assert settings().ai_cache_path.is_file()  # written through to disk


def test_quiz_and_interview_answers_are_never_cached(live_planner):
    for _ in range(2):
        llm.call(InterviewTurn, agent="interviewer", system="s", user="u", context={})
    assert len(live_planner.used) == 2


def test_the_cache_can_be_turned_off(live_planner, monkeypatch):
    monkeypatch.setenv("AI_CACHE", "false")
    settings.cache_clear()
    _plan_call()
    _plan_call()
    assert len(live_planner.used) == 2


def test_an_answer_that_failed_validation_is_never_cached(groq_pool, monkeypatch):
    replies = iter(['{"question": "x"}', '{"question": "x"}'])  # invalid twice

    def client(key: str, timeout: float):
        def create(**kwargs):
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=next(replies)))],
                usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
            )

        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

    monkeypatch.setenv("AI_OFFLINE_FALLBACK", "false")
    settings.cache_clear()
    monkeypatch.setattr(ai_router, "_groq_client", client)
    with pytest.raises(llm.LLMError):
        _plan_call()
    assert len(ai_router.prompt_cache()) == 0
