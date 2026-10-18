"""Offline configuration checks. Prints presence only, never secret values."""
import argparse
import os

from .config import free_model, load_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", action="store_true")
    parser.add_argument("--room", action="store_true")
    args = parser.parse_args()
    load_settings()
    names = ["OPENROUTER_API_KEY"]
    if args.voice:
        names += ["MUNSIT_API_KEY", "MUNSIT_VOICE_ID"]
    if args.room:
        names += ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"]
    missing = False
    for name in names:
        present = bool(os.getenv(name, "").strip())
        print(f"{name}: {'present' if present else 'missing'}")
        missing |= not present
    try:
        free_model()
        print("OpenRouter free-only model policy: OK")
    except ValueError as exc:
        print(str(exc))
        missing = True
    if args.voice and os.getenv("ENABLE_MUNSIT_BILLING", "false").lower() != "true":
        print("Speech requests disabled until ENABLE_MUNSIT_BILLING=true.")
        missing = True
    raise SystemExit(1 if missing else 0)


if __name__ == "__main__":
    main()
