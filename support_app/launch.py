"""Set up and supervise the complete local Noura demo from one terminal."""
import argparse
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import time
import uuid
import webbrowser
import zipfile

import requests
from dotenv import set_key

from examples.config import ROOT, free_model, load_settings, required
from examples.munsit_transcribe import find_voice
from .providers import ProviderError, failure_code, hint
from .service import SupportService

RUNTIME = ROOT / "support_app" / "runtime"
VERSION = "1.13.9"
# Official release asset digests, pinned with the release (see README sources).
DIGESTS = {
    "amd64": "d5b5e44c197f613fdd6bdb2ae53e9d086d848156d43f614c688c6b595cd3f25e",
    "arm64": "bc34c226ea047299d0bc08c9f6071b8d52c13f57be08dd5085f794c9095334a6",
}


def say(message):
    print(message, flush=True)


def save_setting(name, value):
    set_key(str(ROOT / ".env"), name, value, encoding="utf-8")
    os.environ[name] = value


def configure_local():
    names = ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")
    present = [bool(os.getenv(name, "").strip()) for name in names]
    if any(present) and not all(present):
        raise ValueError("LiveKit settings are incomplete. Set all three LIVEKIT settings, or remove all three to use the local server.")
    if not any(present):
        for name, value in zip(names, ("ws://127.0.0.1:7880", "devkey", "secret")):
            save_setting(name, value)
    return (os.environ["LIVEKIT_URL"] in ("ws://127.0.0.1:7880", "ws://localhost:7880")
            and os.environ["LIVEKIT_API_KEY"] == "devkey" and os.environ["LIVEKIT_API_SECRET"] == "secret")


def select_voice(name):
    say("Checking Munsit and selecting the voice (no speech is generated)...")
    with requests.get("https://api.munsit.com/api/v1/voices",
                      headers={"x-api-key": required("MUNSIT_API_KEY")}, timeout=(10, 30)) as response:
        if not response.ok:
            raise ValueError(f"Munsit voice catalogue returned HTTP {response.status_code}. Check the key and account access; no speech was generated.")
        payload = response.json()
    existing = os.getenv("MUNSIT_VOICE_ID", "").strip()
    if existing:
        voices = payload.get("data", payload) if isinstance(payload, dict) else payload
        if isinstance(voices, dict):
            voices = voices.get("voices")
        if not isinstance(voices, list) or not any(isinstance(v, dict) and v.get("voice_id") == existing for v in voices):
            raise ValueError("Your saved MUNSIT_VOICE_ID is not in the account's voice catalogue. Remove that setting to select Mansour automatically.")
    else:
        voice = find_voice(payload, name)
        save_setting("MUNSIT_VOICE_ID", voice["voice_id"])
    if os.getenv("MUNSIT_API_MODE", "current") != "current":
        raise ValueError("Voice requires MUNSIT_API_MODE=current and a current Munsit key.")
    for key, value in (("MUNSIT_API_MODE", "current"), ("MUNSIT_STT_MODEL", "munsit-en-ar"),
                       ("MUNSIT_TTS_MODEL", "faseeh-v1-preview")):
        if not os.getenv(key):
            save_setting(key, value)
    # This launcher is explicitly for speech setup. Actual speech starts only on
    # the app's Start voice button, which displays the Munsit credits notice.
    save_setting("ENABLE_MUNSIT_BILLING", "true")
    say("Munsit key and voice catalogue: OK. Voice calls use your Munsit allowance/credits.")


def ensure_dependencies():
    packages = ("livekit-agents", "livekit-api", "livekit-plugins-openai", "livekit-plugins-munsit", "livekit-plugins-silero")
    try:
        for name in packages:
            importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        say("Installing the project's voice dependencies into this Python environment...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements-livekit.txt")], check=True, cwd=ROOT)
    # Silero's ONNX model ships in the installed plugin; no Hugging Face token
    # or separate model download is required for this pipeline.
    from livekit.plugins import silero
    silero.VAD.load()
    say("Voice dependencies and local speech detector: OK.")


def livekit_executable():
    installed = shutil.which("livekit-server")
    if installed:
        return Path(installed)
    if sys.platform != "win32":
        raise ValueError("Install livekit-server on this OS, or configure a LiveKit Cloud project in .env.")
    arch = "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "amd64"
    directory = RUNTIME / "bin" / f"livekit-{VERSION}-{arch}"
    executable = directory / "livekit-server.exe"
    if executable.is_file():
        return executable
    name = f"livekit_{VERSION}_windows_{arch}.zip"
    say(f"Downloading LiveKit {VERSION} for Windows (once; no Docker or Cloud account needed)...")
    with requests.get(f"https://github.com/livekit/livekit/releases/download/v{VERSION}/{name}", timeout=(10, 90)) as response:
        response.raise_for_status()
        data = response.content
    install_binary(data, DIGESTS[arch], executable)
    return executable


def install_binary(data, digest, target):
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("LiveKit download checksum failed. Nothing was installed.")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        # Copy one named file; never extract arbitrary paths from an archive.
        names = [name for name in archive.namelist() if Path(name).name == "livekit-server.exe"]
        if len(names) != 1:
            raise ValueError("The LiveKit archive does not contain exactly one server executable.")
        binary = archive.read(names[0])
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".download")
    temporary.write_bytes(binary)
    temporary.replace(target)


def check_ai(voice=True):
    required("OPENROUTER_API_KEY")
    free_model()
    say("Checking a real grounded answer with OpenRouter (free models only)...")
    service = SupportService(None)
    answer = service.generate("What is your return policy?", [], service.knowledge.search("return policy"), "en")
    say("Grounded AI answer with validated citations: OK.")
    if not voice:
        return
    say("Checking free-model tool calling for the voice agent...")
    body = {
        "model": free_model(), "max_tokens": 2048, "reasoning": {"effort": "low", "exclude": True},
        "provider": {"max_price": {"prompt": 0, "completion": 0}},
        "messages": [{"role": "user", "content": "Call support_probe with the question return policy. Do not answer directly."}],
        "tools": [{"type": "function", "function": {"name": "support_probe", "description": "Read the support guide.",
                   "parameters": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}}}],
        "tool_choice": "required",
    }
    with requests.post("https://openrouter.ai/api/v1/chat/completions",
                       headers={"Authorization": f"Bearer {required('OPENROUTER_API_KEY')}"},
                       json=body, timeout=(10, 55)) as response:
        response.raise_for_status()
        result = response.json()
    try:
        calls = result["choices"][0]["message"].get("tool_calls", [])
        valid = any(c["function"]["name"] == "support_probe" and
                    isinstance(json.loads(c["function"]["arguments"]).get("question"), str) for c in calls)
    except (KeyError, TypeError, ValueError, IndexError):
        valid = False
    if not valid:
        raise ValueError("The free model did not return a valid tool call. Retry, or select another tool-capable :free OPENROUTER_MODEL.")
    say("Voice tool calling: OK. Free-model availability can change between requests.")


def port_available(port):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


class Processes:
    def __init__(self):
        self.children = []

    def start(self, args, label):
        log = (RUNTIME / f"{label}.log").open("w", encoding="utf-8")
        try:
            child = subprocess.Popen(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except BaseException:
            log.close()
            raise
        self.children.append((child, log, label))
        return child

    def check(self):
        for child, _, label in self.children:
            if child.poll() is not None:
                raise ValueError(f"{label} stopped. See support_app/runtime/{label}.log for details.")

    def wait_for(self, predicate, seconds, description):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.check()
            if predicate():
                return
            time.sleep(0.3)
        raise ValueError(f"Timed out waiting for {description}. Check support_app/runtime/*.log.")

    def close(self):
        for child, log, _ in reversed(self.children):
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
            log.close()


def local_health(url):
    # Only these explicit loopback probes bypass proxy lookup; external calls
    # keep normal requests proxy/TLS settings.
    with requests.Session() as client:
        client.trust_env = False
        try:
            return client.get(url, timeout=1).status_code == 200
        except requests.RequestException:
            return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--text-only", action="store_true", help="Check and start AI chat without speech setup")
    parser.add_argument("--check-only", action="store_true", help="Check providers and prepare voice, then exit")
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--voice-name", default="Mansour")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535 or args.port in (7880, 7881, 8091):
        parser.error("Choose an app port from 1024 to 65535, except 7880, 7881 and 8091.")
    load_settings()
    RUNTIME.mkdir(parents=True, exist_ok=True)
    processes = Processes()
    marker = RUNTIME / ("worker-" + uuid.uuid4().hex + ".ready")
    stage = "configuration"
    try:
        if not args.check_only and not port_available(args.port):
            raise ValueError(f"Port {args.port} is in use. Stop your previous web server with Ctrl+C, or add --port 8082. No existing process was stopped.")
        stage = "OpenRouter"
        check_ai(voice=not args.text_only)
        if not args.text_only:
            stage = "voice dependencies"
            ensure_dependencies()
            stage = "Munsit"
            select_voice(args.voice_name)
            stage = "LiveKit"
            local = configure_local()
            binary = livekit_executable() if local else None
            if args.check_only:
                say("Provider checks and voice preparation passed. Run without --check-only to start the servers.")
                return 0
            if local:
                if not port_available(7880):
                    raise ValueError("Port 7880 is in use. Stop the previous local LiveKit process before launching. No existing process was stopped.")
                processes.start([str(binary), "--dev", "--bind", "127.0.0.1"], "livekit")
                processes.wait_for(lambda: local_health("http://127.0.0.1:7880"), 30, "LiveKit")
            if not port_available(8091):
                raise ValueError("Port 8091 is in use. Stop the previous Noura voice worker before launching.")
            os.environ["SUPPORT_WORKER_READY_FILE"] = str(marker)
            os.environ["SUPPORT_WORKER_PORT"] = "8091"
            os.environ["SUPPORT_DB"] = str(RUNTIME / "support.sqlite3")
            processes.start([sys.executable, "-m", "support_app.voice_agent", "dev", "--no-reload", "--log-level", "info"], "voice-worker")
            processes.wait_for(marker.is_file, 60, "voice worker registration")
            say("LiveKit voice worker registered: OK.")
        elif args.check_only:
            say("AI checks passed.")
            return 0
        stage = "web server"
        processes.start([sys.executable, "-m", "support_app", "--port", str(args.port)], "web")
        url = f"http://127.0.0.1:{args.port}"
        processes.wait_for(lambda: local_health(url + "/api/health"), 15, "web server")
        say(f"\nNoura Care is ready: {url}")
        say("Allow microphone access after clicking Start a voice chat. Munsit speech uses your plan's credits." if not args.text_only else "AI text support is ready. Voice was not started.")
        say("Keep this terminal open. Ctrl+C stops only the processes started by this launcher.")
        if not args.no_browser:
            webbrowser.open(url)
        while True:
            processes.check()
            time.sleep(1)
    except KeyboardInterrupt:
        say("\nStopping Noura Care...")
        return 0
    except (requests.RequestException, ProviderError) as exc:
        if stage == "OpenRouter":
            message = hint(failure_code(exc))
        else:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            message = f"HTTP {status}; check account access or download availability." if status else "Network request failed. Check the network/proxy in this terminal."
        say(f"\n{stage} check failed: {message}")
        say("Setup did not finish. Fix this check and run the same command again; API keys were not printed.")
        return 1
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        say(f"\n{stage}: {exc}")
        return 1
    finally:
        processes.close()
        marker.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
