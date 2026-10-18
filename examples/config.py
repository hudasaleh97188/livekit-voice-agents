"""Central configuration; never print credentials or overwrite the user's .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def load_settings() -> None:
    load_dotenv(ROOT / ".env", override=False)
    for standard, legacy in (("MUNSIT_API_KEY", "key"),
                             ("OPENROUTER_API_KEY", "open_router")):
        if not os.getenv(standard) and os.getenv(legacy):
            os.environ[standard] = os.environ[legacy]


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("your_"):
        raise ValueError(f"Set {name} in .env before running this example.")
    return value


def free_model(value: str | None = None) -> str:
    model = (value if value is not None else
             os.getenv("OPENROUTER_MODEL", "openrouter/free")).strip()
    if model != "openrouter/free" and not model.endswith(":free"):
        raise ValueError("Only openrouter/free or an explicit :free model is allowed.")
    return model


def require_speech_opt_in() -> None:
    if os.getenv("ENABLE_MUNSIT_BILLING", "false").lower() != "true":
        raise ValueError("Munsit may consume credits. Check your plan, then set "
                         "ENABLE_MUNSIT_BILLING=true to enable speech requests.")


def require_livekit() -> None:
    for name in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"):
        required(name)

