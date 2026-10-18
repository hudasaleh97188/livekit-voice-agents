"""Transcribe a small audio file, or list current Munsit voices."""
import argparse
import json
import mimetypes
import os
from pathlib import Path

import requests
from dotenv import set_key

from .config import ROOT, load_settings, required, require_speech_opt_in
from .http_helpers import json_response, run_cli


def transcription_text(payload: dict) -> str:
    data = payload.get("data", payload)
    if not isinstance(data, dict):
        raise RuntimeError("Unexpected transcription response; expected an object.")
    for field in ("transcription", "text"):
        if isinstance(data.get(field), str):
            return data[field]
    raise RuntimeError("No transcription field in response; verify the account's API version.")


def find_voice(payload, name: str) -> dict:
    voices = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(voices, dict):
        voices = voices.get("voices")
    if not isinstance(voices, list):
        raise RuntimeError("Unexpected voice catalogue format; no settings changed.")
    names = {name.strip().casefold()}
    if "mansour" in names:
        names.add("منصور")
    matches = [voice for voice in voices if isinstance(voice, dict)
               and str(voice.get("name", "")).strip().casefold() in names
               and isinstance(voice.get("voice_id"), str) and voice["voice_id"].strip()]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one voice named {name}, found {len(matches)}. "
                           "Run --voices to inspect the catalogue; no settings changed.")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path, nargs="?")
    voice_options = parser.add_mutually_exclusive_group()
    voice_options.add_argument("--voices", action="store_true")
    voice_options.add_argument("--select-voice", metavar="NAME",
                               help="Find a voice by name and save its ID in .env; no synthesis")
    args = parser.parse_args()
    load_settings()
    key = required("MUNSIT_API_KEY")
    if args.voices or args.select_voice:
        with requests.get("https://api.munsit.com/api/v1/voices",
                          headers={"x-api-key": key}, timeout=(10, 30)) as response:
            catalogue = json_response(response)
        if args.select_voice:
            voice = find_voice(catalogue, args.select_voice)
            set_key(str(ROOT / ".env"), "MUNSIT_VOICE_ID", voice["voice_id"], encoding="utf-8")
            print(f"Selected {voice['name']}; saved MUNSIT_VOICE_ID in .env.")
            print("No speech was generated. Existing API keys were preserved.")
            if os.getenv("MUNSIT_VOICE_ID") and os.environ["MUNSIT_VOICE_ID"] != voice["voice_id"]:
                print("If MUNSIT_VOICE_ID is set in your shell, clear it before starting the agent.")
        else:
            print(json.dumps(catalogue, ensure_ascii=False, indent=2))
        return
    if not args.audio or not args.audio.is_file():
        raise ValueError("Pass an existing audio file, e.g. recordings/sample.mp3.")
    # Tutorial guard, not a claim about the provider's maximum upload size.
    if not 0 < args.audio.stat().st_size <= 20 * 1024 * 1024:
        raise ValueError("Use a non-empty file smaller than 20 MiB for this tutorial.")
    require_speech_opt_in()
    mode = os.getenv("MUNSIT_API_MODE", "current")
    if mode == "current":
        url = "https://api.munsit.com/api/v1/audio/transcribe"
        headers = {"x-api-key": key}
        model = os.getenv("MUNSIT_STT_MODEL", "munsit-en-ar")
    elif mode == "legacy":
        if args.audio.suffix.lower() != ".mp3":
            raise ValueError("The legacy example requires MP3, as in the legacy quickstart.")
        url = "https://api.cntxt.tools/audio/transcribe"
        headers = {"Authorization": f"Bearer {key}"}
        model = "munsit-1"
    else:
        raise ValueError("MUNSIT_API_MODE must be current or legacy.")
    mime = mimetypes.guess_type(args.audio.name)[0] or "application/octet-stream"
    with args.audio.open("rb") as audio:
        with requests.post(url, headers=headers, data={"model": model},
                           files={"file": (args.audio.name, audio, mime)},
                           timeout=(10, 120)) as response:
            result = json_response(response)
    print(transcription_text(result))


if __name__ == "__main__":
    run_cli(main)

