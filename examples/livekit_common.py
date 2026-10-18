"""Provider factories shared by the room examples."""
import os

# Plugins must register on the main thread, so import them here, not inside a job.
from livekit.plugins import munsit, openai, silero

try:  # openai SDK 3.x (livekit-agents >= 1.8.8) moved to the httpx2 fork.
    import httpx2 as httpx
except ImportError:
    import httpx

from .config import free_model, required, require_speech_opt_in

INSTRUCTIONS = (
    "You are a concise teaching assistant. Reply in the user's language. "
    "For Arabic, use clear Modern Standard Arabic. Keep spoken answers to two "
    "short sentences unless asked for detail. Do not invent facts or claim "
    "to have performed an action without a tool result."
)


def make_llm():
    return openai.LLM(
        api_key=required("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        model=free_model(),
        max_completion_tokens=2048,
        max_retries=1,
        timeout=httpx.Timeout(45.0, connect=10.0),
        # Some free models reject reasoning disabled (HTTP 400), so keep it low and
        # out of the reply text instead; non-reasoning models ignore this.
        extra_body={"provider": {"max_price": {"prompt": 0, "completion": 0}},
                    "reasoning": {"effort": "low", "exclude": True}},
    )


def speech_providers():
    require_speech_opt_in()
    if os.getenv("MUNSIT_API_MODE", "current") != "current":
        raise ValueError("The voice examples require the current Munsit API/plugin.")
    key = required("MUNSIT_API_KEY")
    voice = required("MUNSIT_VOICE_ID")
    return {
        "stt": munsit.STT(api_key=key, mode="streaming",
                          model=os.getenv("MUNSIT_STT_MODEL", "munsit-en-ar")),
        "tts": munsit.TTS(api_key=key, voice_id=voice,
                          model=os.getenv("MUNSIT_TTS_MODEL", "faseeh-v1-preview")),
        "vad": silero.VAD.load(),
    }

