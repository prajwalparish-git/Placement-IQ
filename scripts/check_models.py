"""Pre-demo check of the configured Groq models: still served, JSON mode works, quota left.

    python -m scripts.check_models

Makes one tiny request per configured model. Never prints the API key.
Exit code: 0 = all good, 1 = a model failed, 2 = configuration error.
"""

import json
import sys

from piq.config import ConfigError, settings

# Served by Groq but not chat models: speech-to-text, text-to-speech, safety classifiers.
NON_CHAT = ("whisper", "orpheus", "prompt-guard", "safeguard")
PROBE = [{"role": "user", "content": 'Return exactly this JSON object: {"ok": true}'}]


def main() -> int:
    try:
        s = settings()
    except ConfigError as e:
        print(f"config error: {e}")
        return 2
    if s.mock_mode:
        print("MOCK_MODE=true: no models in use. Set MOCK_MODE=false in .env to check them.")
        return 0

    import groq

    client = groq.Groq(api_key=s.groq_api_key, max_retries=1, timeout=30)
    served = {m.id for m in client.models.list().data}
    chat = sorted(m for m in served if not any(k in m for k in NON_CHAT))
    print(f"chat models served: {', '.join(chat)}")

    ok = True
    for var, model in (("GROQ_MODEL_LARGE", s.model_large), ("GROQ_MODEL_SMALL", s.model_small)):
        if model not in served:
            print(f"FAIL {var}={model}: not served by Groq; pick one of the chat models above")
            ok = False
            continue
        try:
            raw = client.chat.completions.with_raw_response.create(
                model=model,
                messages=PROBE,
                response_format={"type": "json_object"},
                max_completion_tokens=300,
            )
            reply = json.loads(raw.parse().choices[0].message.content or "")
        except (groq.APIError, ValueError) as e:
            print(f"FAIL {var}={model}: JSON-mode request failed: {e}")
            ok = False
            continue
        h = raw.headers
        print(
            f"OK   {var}={model}: JSON mode works ({reply}); "
            f"requests left today {h.get('x-ratelimit-remaining-requests')}"
            f"/{h.get('x-ratelimit-limit-requests')}, "
            f"tokens left this minute {h.get('x-ratelimit-remaining-tokens')}"
            f"/{h.get('x-ratelimit-limit-tokens')}"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
