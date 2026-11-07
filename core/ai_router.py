"""Layer 3, self-healing AI router: send one chat request to the first healthy LLM provider.

Providers, tried in the order AI_PROVIDERS gives (default gemini, groq, ollama):
- gemini: Google's Gemini API over REST (generateContent with a JSON response type).
- groq: the Groq SDK in JSON mode, with its two-key lanes and 429 failover between the keys.
- ollama: a local Ollama server (OLLAMA_BASE_URL); no key, and it works with no internet.

A provider without its key, URL or model is skipped. Each one sits behind a circuit breaker:
errors that mean "this provider is down" (network, HTTP 5xx, a 429, a retired model, a refused
key) count as failures, and after ROUTER_FAILURE_THRESHOLD in a row (at once for a 429, a
retired model or a refused key) the breaker opens. An open breaker skips its provider until
the cooldown, or the server's retry-after, has passed; then one trial request closes it again
or reopens it. Ollama is health-checked (GET /api/tags, model pulled?) before use, and the
answer is cached for OLLAMA_HEALTH_TTL_S seconds.

The router moves text only. piq/llm.py builds the messages, validates the JSON against the
schema, repairs once and logs the call. When no provider answers, `complete` raises
AllProvidersDown with each provider's reason; piq/llm.py then serves the deterministic offline
tier (piq/mock.py, built from data/), and the agents/ package falls back to its own banks.
"""

import logging
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING, Literal, Protocol

import httpx

from piq.config import (
    CLOUD_TIMEOUT_S,
    OLLAMA_HEALTH_TTL_S,
    OLLAMA_PROBE_TIMEOUT_S,
    OLLAMA_TIMEOUT_S,
    ROUTER_BROKEN_COOLDOWN_S,
    ROUTER_COOLDOWN_S,
    ROUTER_FAILURE_THRESHOLD,
    settings,
)

if TYPE_CHECKING:
    from groq import Groq

Size = Literal["large", "small"]
Messages = list[dict[str, str]]
State = Literal["ready", "paused", "off"]
log = logging.getLogger("core.ai_router")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
LABELS = {"gemini": "Gemini", "groq": "Groq", "ollama": "Ollama (local)"}


@dataclass(frozen=True)
class Completion:
    text: str
    tokens_in: int
    tokens_out: int
    provider: str
    model: str

    @property
    def label(self) -> str:
        """What agent_logs.model_used records, e.g. 'groq:openai/gpt-oss-120b'."""
        return f"{self.provider}:{self.model}"


class ProviderError(Exception):
    """The provider could not answer this request.

    `counts`: it says the provider is unwell (False for a request it refused on its merits).
    `rate_limited` / `retry_after`: a 429 and the server's hint. `cooldown`: open the breaker
    for this long at once (a retired model or a refused key will not heal in a minute)."""

    def __init__(
        self,
        message: str,
        *,
        counts: bool = True,
        rate_limited: bool = False,
        retry_after: float | None = None,
        cooldown: float | None = None,
    ) -> None:
        super().__init__(message)
        self.counts, self.rate_limited = counts, rate_limited
        self.retry_after, self.cooldown = retry_after, cooldown


class InvalidJson(Exception):
    """The provider answered but refused the model's output as invalid JSON: repairable."""


class AllProvidersDown(Exception):
    """No provider could answer. `failures`: the reason for each provider that was tried or is
    paused; `skipped`: providers left out because they are not set up."""

    def __init__(
        self,
        failures: Mapping[str, str],
        skipped: Mapping[str, str],
        *,
        rate_limited: bool,
        retry_after: float | None,
    ) -> None:
        self.failures, self.skipped = dict(failures), dict(skipped)
        self.rate_limited, self.retry_after = rate_limited, retry_after
        if not failures:
            message = (
                "No AI provider is set up: add GEMINI_API_KEY, GROQ_API_KEY or "
                "OLLAMA_BASE_URL to .env."
            )
        elif len(failures) == 1:
            message = next(iter(failures.values()))
        else:
            message = "; ".join(f"{LABELS[k]}: {v}" for k, v in failures.items())
        super().__init__(message)


# --- circuit breaker --------------------------------------------------------------------------


class CircuitBreaker:
    """Closed (requests go through) -> open (skipped until a deadline) -> half-open (one trial
    decides). Thread-safe: Streamlit serves each session from its own thread."""

    def __init__(
        self,
        threshold: int = ROUTER_FAILURE_THRESHOLD,
        cooldown: float = ROUTER_COOLDOWN_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.threshold, self.cooldown, self._clock = threshold, cooldown, clock
        self._lock = threading.Lock()
        self.failures = 0
        self.open_until = 0.0
        self.reason = ""
        self.rate_limited = False

    @property
    def state(self) -> Literal["closed", "open", "half-open"]:
        if not self.open_until:
            return "closed"
        return "open" if self._clock() < self.open_until else "half-open"

    def allow(self) -> bool:
        return self.state != "open"

    def retry_in(self) -> float:
        return max(0.0, self.open_until - self._clock()) if self.open_until else 0.0

    def success(self) -> None:
        with self._lock:
            self.failures, self.open_until, self.reason, self.rate_limited = 0, 0.0, "", False

    def failure(
        self,
        reason: str,
        *,
        retry_after: float | None = None,
        cooldown: float | None = None,
        rate_limited: bool = False,
    ) -> None:
        with self._lock:
            now = self._clock()
            half_open = bool(self.open_until) and now >= self.open_until
            self.failures += 1
            self.reason, self.rate_limited = reason, rate_limited
            if half_open or rate_limited or cooldown or self.failures >= self.threshold:
                wait = max(cooldown or self.cooldown, retry_after or 0.0)
                self.open_until = now + wait


# --- providers --------------------------------------------------------------------------------


class Provider(Protocol):
    name: str

    def unavailable(self) -> str:
        """Why this provider cannot take requests now ('' = it can)."""
        ...

    def model(self, size: Size) -> str: ...

    def complete(
        self, messages: Messages, *, size: Size, temperature: float, agent: str
    ) -> Completion: ...


@lru_cache
def _http() -> httpx.Client:
    """One pooled client for Gemini and Ollama (tests swap in a MockTransport)."""
    return httpx.Client()


def _retry_after(headers: Mapping[str, str]) -> float | None:
    try:
        return float(headers.get("retry-after"))
    except (TypeError, ValueError):
        return None


def _excerpt(r: httpx.Response) -> str:
    try:
        body = r.json()
        error = body.get("error") if isinstance(body, dict) else None
        text = error.get("message", "") if isinstance(error, dict) else str(error or body)
    except ValueError:
        text = r.text
    return " ".join(str(text).split())[:300]


class Gemini:
    name = "gemini"

    def unavailable(self) -> str:
        s = settings()
        return "" if s.gemini_api_key and s.gemini_model else "GEMINI_API_KEY is not set"

    def model(self, size: Size) -> str:
        return settings().gemini_model

    def complete(
        self, messages: Messages, *, size: Size, temperature: float, agent: str
    ) -> Completion:
        s = settings()
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        body: dict = {
            "contents": [
                {
                    "role": "model" if m["role"] == "assistant" else "user",
                    "parts": [{"text": m["content"]}],
                }
                for m in messages
                if m["role"] != "system"
            ],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        try:
            r = _http().post(
                GEMINI_URL.format(model=s.gemini_model),
                json=body,
                headers={"x-goog-api-key": s.gemini_api_key},
                timeout=CLOUD_TIMEOUT_S,
            )
        except httpx.HTTPError as e:
            raise ProviderError(f"Gemini is unreachable ({type(e).__name__})") from e
        if r.status_code == 429:
            raise ProviderError(
                "Gemini rate limit reached", rate_limited=True, retry_after=_retry_after(r.headers)
            )
        if r.status_code == 404:
            raise ProviderError(
                f"Gemini does not serve model {s.gemini_model!r}. Update GEMINI_MODEL in .env "
                "(see ai.google.dev/gemini-api/docs/models).",
                cooldown=ROUTER_BROKEN_COOLDOWN_S,
            )
        if r.status_code in (401, 403):
            raise ProviderError(
                f"Gemini refused the API key: {_excerpt(r)}", cooldown=ROUTER_BROKEN_COOLDOWN_S
            )
        if r.status_code == 400:
            raise ProviderError(f"Gemini rejected the request: {_excerpt(r)}", counts=False)
        if r.status_code >= 400:
            raise ProviderError(f"Gemini API error {r.status_code}: {_excerpt(r)}")
        data = r.json()
        candidates = data.get("candidates") or []
        if not candidates:  # blocked by a safety filter: the request, not the service
            blocked = (data.get("promptFeedback") or {}).get("blockReason", "no candidates")
            raise ProviderError(f"Gemini returned no answer ({blocked})", counts=False)
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        usage = data.get("usageMetadata") or {}
        return Completion(
            text,
            int(usage.get("promptTokenCount", 0)),
            int(usage.get("candidatesTokenCount", 0)),
            self.name,
            s.gemini_model,
        )


# Agents a student is waiting on: they take Groq's interactive lane (key 1).
INTERACTIVE_AGENTS = frozenset({"interviewer", "evaluator", "bullet"})


def keys_for(agent: str) -> list[str]:
    """Groq's keys in the order `agent` tries them: its lane's key, then the other."""
    pool = list(settings().groq_api_keys)
    if len(pool) < 2:
        return pool
    lane = 0 if agent in INTERACTIVE_AGENTS else 1
    return [pool[lane], pool[1 - lane]]


@lru_cache
def _groq_client(key: str) -> "Groq":
    from groq import Groq  # imported lazily so MOCK_MODE never needs network config

    # With a second key, fail over fast instead of backing off on an exhausted one.
    retries = 4 if len(settings().groq_api_keys) < 2 else 1
    return Groq(api_key=key, max_retries=retries, timeout=CLOUD_TIMEOUT_S)


class GroqProvider:
    """Keys form a pool of one or two (GROQ_API_KEY_1, GROQ_API_KEY_2). Agents a student waits
    on use key 1, background work key 2; a 429 on one key fails over to the other once. Groq
    limits quota per organisation, so a second key adds headroom only if it belongs to another
    one. With one key, 429 backoff is the SDK's own (max_retries)."""

    name = "groq"

    def unavailable(self) -> str:
        s = settings()
        if not s.groq_api_keys:
            return "GROQ_API_KEY is not set"
        return "" if s.model_large and s.model_small else "GROQ_MODEL_LARGE/SMALL are not set"

    def model(self, size: Size) -> str:
        s = settings()
        return s.model_large if size == "large" else s.model_small

    def complete(
        self, messages: Messages, *, size: Size, temperature: float, agent: str
    ) -> Completion:
        import groq

        model = self.model(size)
        keys = keys_for(agent)
        for n, key in enumerate(keys):
            try:
                r = _groq_client(key).chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                break
            except groq.RateLimitError as e:
                if n + 1 < len(keys):
                    log.warning("%s: Groq key %d rate-limited; trying key %d", agent, n + 1, n + 2)
                    continue
                raise ProviderError(
                    "Groq free-tier rate limit reached",
                    rate_limited=True,
                    retry_after=_retry_after(e.response.headers),
                ) from e
            except groq.NotFoundError as e:
                raise ProviderError(
                    f"Groq no longer serves model {model!r}. Update GROQ_MODEL_LARGE / "
                    "GROQ_MODEL_SMALL in .env (see console.groq.com/docs/models).",
                    cooldown=ROUTER_BROKEN_COOLDOWN_S,
                ) from e
            except groq.BadRequestError as e:
                # Groq rejects output that is not valid JSON in json_object mode: repairable.
                if "json_validate_failed" in str(e):
                    raise InvalidJson(str(e)) from e
                raise ProviderError(f"Groq rejected the request: {e}", counts=False) from e
            except groq.APIError as e:  # includes connection errors and timeouts
                raise ProviderError(f"Groq API error: {e}") from e
        u = r.usage
        return Completion(
            r.choices[0].message.content or "",
            u.prompt_tokens,
            u.completion_tokens,
            self.name,
            model,
        )


class Ollama:
    name = "ollama"

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._checked: tuple[float, str, str] | None = None  # (when, base_url, reason)

    def model(self, size: Size) -> str:
        return settings().ollama_model

    def forget(self) -> None:
        self._checked = None

    def unavailable(self) -> str:
        s = settings()
        if not (s.ollama_base_url and s.ollama_model):
            return "OLLAMA_BASE_URL is not set"
        now = self._clock()
        if (
            self._checked
            and self._checked[1] == s.ollama_base_url
            and now - self._checked[0] < OLLAMA_HEALTH_TTL_S
        ):
            return self._checked[2]
        reason = self._probe(s.ollama_base_url, s.ollama_model)
        self._checked = (now, s.ollama_base_url, reason)
        return reason

    @staticmethod
    def _probe(base: str, model: str) -> str:
        try:
            r = _http().get(f"{base}/api/tags", timeout=OLLAMA_PROBE_TIMEOUT_S)
            r.raise_for_status()
            names = {m.get("name", "") for m in r.json().get("models", [])}
        except (httpx.HTTPError, ValueError, AttributeError):
            return f"Ollama is not running at {base}"
        wanted = {model, f"{model}:latest"}
        if not (names & wanted or any(n.split(":")[0] == model for n in names)):
            return f"Ollama has not pulled {model!r} (run: ollama pull {model})"
        return ""

    def complete(
        self, messages: Messages, *, size: Size, temperature: float, agent: str
    ) -> Completion:
        s = settings()
        try:
            r = _http().post(
                f"{s.ollama_base_url}/api/chat",
                json={
                    "model": s.ollama_model,
                    "messages": messages,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": temperature},
                },
                timeout=OLLAMA_TIMEOUT_S,
            )
        except httpx.HTTPError as e:
            self.forget()  # the next request re-checks health instead of trusting the cache
            raise ProviderError(f"Ollama is unreachable ({type(e).__name__})") from e
        if r.status_code == 404:
            self.forget()
            raise ProviderError(
                f"Ollama has not pulled {s.ollama_model!r}", cooldown=ROUTER_COOLDOWN_S
            )
        if r.status_code >= 400:
            raise ProviderError(f"Ollama error {r.status_code}: {_excerpt(r)}")
        data = r.json()
        return Completion(
            (data.get("message") or {}).get("content", ""),
            int(data.get("prompt_eval_count", 0)),
            int(data.get("eval_count", 0)),
            self.name,
            s.ollama_model,
        )


PROVIDERS: dict[str, Provider] = {p.name: p for p in (Gemini(), GroqProvider(), Ollama())}
_breakers: dict[str, CircuitBreaker] = {}
_breakers_lock = threading.Lock()


def breaker(name: str) -> CircuitBreaker:
    with _breakers_lock:
        return _breakers.setdefault(name, CircuitBreaker())


def reset() -> None:
    """Close every breaker and forget health checks (tests; or after fixing .env)."""
    with _breakers_lock:
        _breakers.clear()
    ollama = PROVIDERS["ollama"]
    if isinstance(ollama, Ollama):
        ollama.forget()


# --- routing ----------------------------------------------------------------------------------


def complete(messages: Messages, *, size: Size, temperature: float, agent: str) -> Completion:
    """The first healthy provider's answer. Raises InvalidJson (repairable; the provider is up)
    or AllProvidersDown."""
    failures: dict[str, str] = {}
    skipped: dict[str, str] = {}
    hints: list[float | None] = []
    limited = 0
    for name in settings().ai_providers:
        provider = PROVIDERS[name]
        why = provider.unavailable()
        if why:
            skipped[name] = why
            continue
        b = breaker(name)
        if not b.allow():
            failures[name] = f"paused after errors ({b.reason})"
            if b.rate_limited:
                limited += 1
                hints.append(b.retry_in())
            continue
        try:
            out = provider.complete(messages, size=size, temperature=temperature, agent=agent)
        except InvalidJson:
            b.success()  # it answered; the output just needs repair
            raise
        except ProviderError as e:
            if e.counts:
                b.failure(
                    str(e),
                    retry_after=e.retry_after,
                    cooldown=e.cooldown,
                    rate_limited=e.rate_limited,
                )
            failures[name] = str(e)
            if e.rate_limited:
                limited += 1
                hints.append(e.retry_after)
            log.warning("%s: %s failed (%s); trying the next provider", agent, name, e)
            continue
        b.success()
        if failures:
            log.info("%s: answered by %s after %s failed", agent, name, ", ".join(failures))
        return out
    known = [h for h in hints if h]
    raise AllProvidersDown(
        failures,
        skipped,
        rate_limited=bool(failures) and limited == len(failures),
        retry_after=min(known) if known else None,
    )


@dataclass(frozen=True)
class ProviderStatus:
    name: str
    label: str
    state: State
    detail: str


def status() -> list[ProviderStatus]:
    """Every configured provider in routing order, for the sidebar and the faculty page."""
    out = []
    for name in settings().ai_providers:
        why = PROVIDERS[name].unavailable()
        b = breaker(name)
        if why:
            out.append(ProviderStatus(name, LABELS[name], "off", why))
        elif not b.allow():
            detail = f"Paused for {b.retry_in():.0f} s: {b.reason}"
            out.append(ProviderStatus(name, LABELS[name], "paused", detail))
        else:
            out.append(ProviderStatus(name, LABELS[name], "ready", "Ready"))
    return out


def active_provider() -> str:
    """Label of the provider the next request will try first, or 'Offline rules'."""
    if settings().mock_mode:
        return "Mock mode"
    ready = next((p for p in status() if p.state == "ready"), None)
    return ready.label if ready else "Offline rules"
