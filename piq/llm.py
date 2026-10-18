"""The only module that talks to an LLM.

`call()` = JSON mode + Pydantic validation + one repair retry + agent_logs row.
HTTP 429 backoff is handled by the Groq SDK itself (max_retries); a 429 that survives
it becomes `RateLimited` with the server's retry-after hint.
In MOCK_MODE the response comes from `piq.mock` and still goes through validation.
"""

import json
import logging
import time
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ValidationError

from piq import db, mock
from piq.config import settings

Size = Literal["large", "small"]
log = logging.getLogger("piq.llm")


class LLMError(RuntimeError):
    pass


class RateLimited(LLMError):
    """Groq's free-tier quota is exhausted even after the SDK's own retries."""

    def __init__(self, retry_after: float | None):
        self.retry_after = retry_after
        hint = f"Try again in about {retry_after:.0f} s." if retry_after else "Try again shortly."
        super().__init__(f"Groq free-tier rate limit reached. {hint}")


def _retry_after(headers) -> float | None:
    try:
        return float(headers.get("retry-after"))
    except (TypeError, ValueError):
        return None


@lru_cache
def _client():
    from groq import Groq  # imported lazily so MOCK_MODE never needs network config

    return Groq(api_key=settings().groq_api_key, max_retries=4, timeout=60)


def model_for(size: Size) -> str:
    s = settings()
    if s.mock_mode:
        return "mock"
    return s.model_large if size == "large" else s.model_small


def _complete(model: str, messages: list[dict], temperature: float) -> tuple[str, int, int]:
    import groq

    try:
        r = _client().chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
    except groq.NotFoundError as e:
        raise LLMError(
            f"Groq no longer serves model {model!r}. Update GROQ_MODEL_LARGE / "
            "GROQ_MODEL_SMALL in .env (see console.groq.com/docs/models)."
        ) from e
    except groq.RateLimitError as e:
        raise RateLimited(_retry_after(e.response.headers)) from e
    except groq.BadRequestError as e:
        # Groq rejects output that is not valid JSON in json_object mode; treat as repairable.
        if "json_validate_failed" in str(e):
            return "", 0, 0
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
    for attempt in range(2):
        if model == "mock":
            content, i, o = json.dumps(mock.respond(agent, context)), 0, 0
        else:
            content, i, o = _complete(model, messages, temperature)
        tok_in, tok_out = tok_in + i, tok_out + o
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
    latency = int((time.perf_counter() - t0) * 1000)
    log_id = db.log_call(agent, model, tok_in, tok_out, latency, student_id)
    return out, log_id
