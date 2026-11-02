"""The only module that talks to an LLM.

`call()` = JSON mode + Pydantic validation + one repair retry + agent_logs row.

Keys form a pool of one or two (GROQ_API_KEY_1, GROQ_API_KEY_2). Agents a student waits on
(interviewer, evaluator, bullet polish) use key 1; background work (profile, planner, quiz,
critic, evaluation) uses key 2. A 429 on one key fails over to the other once. Groq limits
quota per organisation, so a second key adds headroom only if it belongs to another one.
With one key, HTTP 429 backoff is the SDK's own (max_retries); a 429 that survives every
key becomes `RateLimited` with the server's retry-after hint.
In MOCK_MODE the response comes from `piq.mock` and still goes through validation.
"""

import json
import logging
import time
from collections.abc import Mapping
from functools import lru_cache
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ValidationError

from piq import db, mock
from piq.config import settings

if TYPE_CHECKING:
    from groq import Groq

Size = Literal["large", "small"]
log = logging.getLogger("piq.llm")


class LLMError(RuntimeError):
    pass


class RateLimited(LLMError):
    """Groq's free-tier quota is exhausted even after the SDK's own retries."""

    def __init__(self, retry_after: float | None) -> None:
        self.retry_after = retry_after
        hint = f"Try again in about {retry_after:.0f} s." if retry_after else "Try again shortly."
        super().__init__(f"Groq free-tier rate limit reached. {hint}")


class _InvalidJson(Exception):
    """Groq refused the model's output as invalid JSON (json_validate_failed): repairable."""


def _retry_after(headers: Mapping[str, str]) -> float | None:
    try:
        return float(headers.get("retry-after"))
    except (TypeError, ValueError):
        return None


# Agents a student is waiting on: they take the interactive lane (key 1).
INTERACTIVE_AGENTS = frozenset({"interviewer", "evaluator", "bullet"})


def keys_for(agent: str) -> list[str]:
    """The pool's keys in the order `agent` tries them: its lane's key, then the other."""
    pool = list(settings().groq_api_keys)
    if len(pool) < 2:
        return pool
    lane = 0 if agent in INTERACTIVE_AGENTS else 1
    return [pool[lane], pool[1 - lane]]


@lru_cache
def _client(key: str) -> "Groq":
    from groq import Groq  # imported lazily so MOCK_MODE never needs network config

    # With a second key, fail over fast instead of backing off on an exhausted one.
    retries = 4 if len(settings().groq_api_keys) < 2 else 1
    return Groq(api_key=key, max_retries=retries, timeout=60)


def model_for(size: Size) -> str:
    s = settings()
    if s.mock_mode:
        return "mock"
    return s.model_large if size == "large" else s.model_small


def _complete(
    model: str, messages: list[dict], temperature: float, agent: str = ""
) -> tuple[str, int, int]:
    import groq

    keys = keys_for(agent) or [""]
    for n, key in enumerate(keys):
        try:
            r = _client(key).chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            break
        except groq.RateLimitError as e:
            if n + 1 < len(keys):
                log.warning("%s: key %d rate-limited; failing over to key %d", agent, n + 1, n + 2)
                continue
            raise RateLimited(_retry_after(e.response.headers)) from e
        except groq.NotFoundError as e:
            raise LLMError(
                f"Groq no longer serves model {model!r}. Update GROQ_MODEL_LARGE / "
                "GROQ_MODEL_SMALL in .env (see console.groq.com/docs/models)."
            ) from e
        except groq.BadRequestError as e:
            # Groq rejects output that is not valid JSON in json_object mode: repairable.
            if "json_validate_failed" in str(e):
                raise _InvalidJson(str(e)) from e
            raise LLMError(f"Groq rejected the request: {e}") from e
        except groq.APIError as e:
            raise LLMError(f"Groq API error: {e}") from e
    u = r.usage
    return r.choices[0].message.content or "", u.prompt_tokens, u.completion_tokens


def call[T: BaseModel](
    schema: type[T],
    *,
    agent: str,
    system: str,
    user: str,
    context: dict,
    size: Size = "large",
    temperature: float = 0.4,
    student_id: str | None = None,
) -> tuple[T, int]:
    """Return (validated output, agent_logs row id). `context` feeds MOCK_MODE only."""
    model = model_for(size)
    messages = [
        {
            "role": "system",
            "content": f"{system}\n\nRespond with one JSON object matching this JSON Schema:\n"
            f"{json.dumps(schema.model_json_schema())}",
        },
        {"role": "user", "content": user},
    ]
    t0 = time.perf_counter()
    tok_in = tok_out = 0
    error = ""
    try:
        for attempt in range(2):
            content = ""
            if model == "mock":
                content, i, o = json.dumps(mock.respond(agent, context)), 0, 0
            else:
                try:
                    content, i, o = _complete(model, messages, temperature, agent)
                except _InvalidJson as e:  # Groq's words tell the model what to fix
                    i = o = 0
                    error = f"Groq rejected the output as invalid JSON: {e}"
            tok_in, tok_out = tok_in + i, tok_out + o
            if content:
                try:
                    out = schema.model_validate_json(content)
                    break
                except ValidationError as e:
                    error = str(e)
            log.warning("%s: invalid output (attempt %d): %s", agent, attempt + 1, error[:300])
            messages += [
                {"role": "assistant", "content": content or "(invalid JSON)"},
                {
                    "role": "user",
                    "content": f"That output failed validation:\n{error}\n"
                    "Return the corrected JSON object only.",
                },
            ]
        else:
            raise LLMError(f"{agent}: output failed validation twice: {error[:500]}")
    except LLMError as e:  # a failed call still cost time and tokens: log it, marked failed
        latency = int((time.perf_counter() - t0) * 1000)
        db.log_call(agent, model, tok_in, tok_out, latency, student_id, failed=str(e))
        raise
    latency = int((time.perf_counter() - t0) * 1000)
    log_id = db.log_call(agent, model, tok_in, tok_out, latency, student_id)
    return out, log_id
