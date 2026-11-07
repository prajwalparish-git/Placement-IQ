"""core/speech_router.py: ElevenLabs first, the browser voice otherwise; never raises."""

import json

import httpx
import pytest

from core import ai_router, speech_router
from piq.config import TTS_MAX_CHARS, settings


@pytest.fixture
def eleven(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "el-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice-1")
    settings.cache_clear()
    seen: list[httpx.Request] = []

    def install(handler) -> list[httpx.Request]:
        def record(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        client = httpx.Client(transport=httpx.MockTransport(record))
        monkeypatch.setattr(speech_router, "_http", lambda: client)
        return seen

    return install


def test_without_a_key_the_browser_voice_is_used():
    speech = speech_router.synthesize("Tell me about yourself.")
    assert (speech.source, speech.audio) == ("browser", None)
    assert "ELEVENLABS_API_KEY" in speech.detail
    assert speech_router.active_voice() == "Browser voice"


def test_elevenlabs_audio_and_request_shape(eleven):
    seen = eleven(lambda r: httpx.Response(200, content=b"ID3mp3"))
    speech = speech_router.synthesize("Tell   me\nabout yourself.")
    assert (speech.source, speech.audio, speech.text) == (
        "elevenlabs",
        b"ID3mp3",
        "Tell me about yourself.",
    )
    [req] = seen
    assert req.url.path == "/v1/text-to-speech/voice-1"
    assert req.headers["xi-api-key"] == "el-key"
    assert "model_id" not in json.loads(req.content)  # unset: ElevenLabs' default model


@pytest.mark.parametrize("code", [401, 429, 500])
def test_elevenlabs_errors_fall_back_to_the_browser(eleven, code):
    eleven(lambda r: httpx.Response(code))
    speech = speech_router.synthesize("Question?")
    assert speech.source == "browser" and "ElevenLabs failed" in speech.detail


def test_a_refused_key_pauses_elevenlabs(eleven):
    seen = eleven(lambda r: httpx.Response(401))
    speech_router.synthesize("One?")
    speech = speech_router.synthesize("Two?")
    assert len(seen) == 1 and "paused" in speech.detail  # no second request


def test_network_error_falls_back(eleven):
    def refuse(request):
        raise httpx.ConnectError("offline", request=request)

    eleven(refuse)
    assert speech_router.synthesize("Question?").source == "browser"


def test_clip_cuts_at_a_sentence():
    text = ("This is one sentence. " * 200).strip()
    clipped = speech_router.clip(text)
    assert len(clipped) <= TTS_MAX_CHARS and clipped.endswith(".")


def test_browser_html_cannot_be_broken_out_of():
    page = speech_router.browser_speech_html('</script><img src=x onerror=alert(1)> "q" & \\')
    assert "</script><img" not in page and "<img" not in page
    assert page.count("</script>") == 1
    assert "speechSynthesis" in page and "Read the question aloud" in page


def test_speech_router_shares_the_ai_routers_breaker_type():
    assert isinstance(speech_router._breaker, ai_router.CircuitBreaker)


def test_audio_is_cached_so_a_question_is_synthesised_once(eleven):
    seen = eleven(lambda r: httpx.Response(200, content=b"ID3mp3"))
    first = speech_router.synthesize("Why this role?")
    second = speech_router.synthesize("Why  this role?")  # same words after clipping
    assert first.audio == second.audio == b"ID3mp3" and len(seen) == 1
    path = speech_router.audio_path("Why this role?")
    assert path.read_bytes() == b"ID3mp3" and path.suffix == ".mp3"
    assert path.parent == settings().audio_cache_dir


def test_cached_audio_plays_even_while_elevenlabs_is_paused(eleven):
    eleven(lambda r: httpx.Response(200, content=b"ID3mp3"))
    speech_router.synthesize("Tell me about a project.")
    speech_router._breaker.failure("down", cooldown=3600)
    again = speech_router.synthesize("Tell me about a project.")
    assert again.source == "elevenlabs" and again.audio == b"ID3mp3"


def test_without_a_key_nothing_is_cached_or_asked():
    speech = speech_router.synthesize("Hello there, candidate.")
    assert speech.source == "browser" and not settings().audio_cache_dir.exists()
