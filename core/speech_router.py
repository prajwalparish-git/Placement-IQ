"""Layer 3, speech router: speak a text with the best voice available, never raising.

1. ElevenLabs (ELEVENLABS_API_KEY; ELEVENLABS_VOICE_ID and ELEVENLABS_MODEL optional) returns
   MP3 bytes the page plays with st.audio.
2. Otherwise the browser's own voice (Web Speech API): `browser_speech_html` builds a button
   that reads the text aloud in the student's browser. Nothing leaves the machine, so it also
   works offline.

pyttsx3 is deliberately not used: it speaks through the server's sound card, which in a web
app is not the student's, and it would add a dependency.

ElevenLabs sits behind the same kind of circuit breaker as the AI providers: an outage, a 429
or a refused key pauses it, and the browser voice answers in the meantime.
"""

import html
import json
import logging
from dataclasses import dataclass
from typing import Literal

import httpx

from core.ai_router import CircuitBreaker, _http, _retry_after
from piq.config import (
    BRAND_COLOR,
    BROWSER_VOICE_LANG,
    ELEVENLABS_DEFAULT_VOICE,
    PALETTE,
    ROUTER_BROKEN_COOLDOWN_S,
    TTS_MAX_CHARS,
    TTS_TIMEOUT_S,
    settings,
)

log = logging.getLogger("core.speech_router")
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice}"
Source = Literal["elevenlabs", "browser"]
_breaker = CircuitBreaker()


@dataclass(frozen=True)
class Speech:
    text: str  # what is spoken (cut to TTS_MAX_CHARS)
    source: Source
    audio: bytes | None = None  # MP3 when source is "elevenlabs"
    detail: str = ""  # why the browser voice is used


def reset() -> None:
    """Close the ElevenLabs breaker (tests; or after fixing .env)."""
    _breaker.success()


def clip(text: str) -> str:
    """Whitespace collapsed, and cut at the last full sentence within TTS_MAX_CHARS."""
    text = " ".join(text.split())
    if len(text) <= TTS_MAX_CHARS:
        return text
    cut = text[:TTS_MAX_CHARS]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return cut[: end + 1] if end > 0 else cut


def elevenlabs_unavailable() -> str:
    """Why ElevenLabs cannot speak now ('' = it can)."""
    if not settings().elevenlabs_api_key:
        return "ELEVENLABS_API_KEY is not set"
    if not _breaker.allow():
        return f"ElevenLabs paused for {_breaker.retry_in():.0f} s: {_breaker.reason}"
    return ""


def _elevenlabs(text: str) -> bytes:
    s = settings()
    body: dict = {"text": text, "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    if s.elevenlabs_model:  # unset: ElevenLabs uses its default model
        body["model_id"] = s.elevenlabs_model
    try:
        r = _http().post(
            ELEVENLABS_URL.format(voice=s.elevenlabs_voice_id or ELEVENLABS_DEFAULT_VOICE),
            json=body,
            headers={"xi-api-key": s.elevenlabs_api_key, "Accept": "audio/mpeg"},
            timeout=TTS_TIMEOUT_S,
        )
    except httpx.HTTPError as e:
        _breaker.failure(f"unreachable ({type(e).__name__})")
        raise
    if r.status_code == 429:
        _breaker.failure("rate limit", retry_after=_retry_after(r.headers), rate_limited=True)
    elif r.status_code in (401, 403):  # a bad key or used-up quota will not heal in a minute
        _breaker.failure(f"refused (HTTP {r.status_code})", cooldown=ROUTER_BROKEN_COOLDOWN_S)
    elif r.status_code >= 400:
        _breaker.failure(f"HTTP {r.status_code}")
    elif not r.content:
        _breaker.failure("empty audio")
    else:
        _breaker.success()
        return r.content
    raise RuntimeError(f"ElevenLabs answered HTTP {r.status_code}")


def synthesize(text: str) -> Speech:
    """ElevenLabs audio when it can, else a Speech the page renders with the browser voice."""
    spoken = clip(text)
    why = elevenlabs_unavailable()
    if not why and spoken:
        try:
            return Speech(spoken, "elevenlabs", _elevenlabs(spoken))
        except Exception as e:  # the student still hears the question
            log.warning("ElevenLabs failed (%s); the browser voice takes over", e)
            why = f"ElevenLabs failed: {e}"
    return Speech(spoken, "browser", None, why)


def active_voice() -> str:
    return "ElevenLabs" if not elevenlabs_unavailable() else "Browser voice"


def _js_string(text: str) -> str:
    """A JavaScript string literal that cannot end the <script> element or the attribute."""
    return json.dumps(text).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def browser_speech_html(text: str, label: str = "Read the question aloud") -> str:
    """A self-contained page (for st.components.v1.html) with one button that speaks `text`
    through the Web Speech API, and says so in words when the browser has no voice."""
    light, dark = PALETTE["light"], PALETTE["dark"]
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
  /* An iframe cannot read the Streamlit theme: the same tokens, picked by the OS scheme. */
  :root {{ color-scheme: light dark; }}
  body {{ margin: 0; font: 16px system-ui, sans-serif; color: {light["text"]}; }}
  button {{ background: {light["primary"]}; color: #fff; border: 0; border-radius: 8px;
           padding: 8px 16px; font: inherit; font-weight: 600; cursor: pointer; }}
  button:focus-visible {{ outline: 3px solid {BRAND_COLOR}; outline-offset: 2px; }}
  #note {{ margin-left: 12px; }}
  @media (prefers-color-scheme: dark) {{
    body {{ color: {dark["text"]}; }}
    button {{ background: {dark["primary"]}; }}
  }}
</style></head><body>
<button type="button" id="speak" aria-describedby="note">{html.escape(label)}</button>
<span id="note" role="status"></span>
<script>
  const text = {_js_string(text)};
  const note = document.getElementById("note");
  document.getElementById("speak").addEventListener("click", () => {{
    if (!("speechSynthesis" in window)) {{
      note.textContent = "This browser cannot speak; read the question below.";
      return;
    }}
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "{BROWSER_VOICE_LANG}";
    u.onstart = () => {{ note.textContent = "Speaking"; }};
    u.onend = () => {{ note.textContent = ""; }};
    window.speechSynthesis.speak(u);
  }});
</script></body></html>"""
