"""Local teaching server: JSON API + static frontend, bound to loopback only."""
import argparse
import asyncio
from collections import defaultdict, deque
from datetime import timedelta
import hmac
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlsplit

from examples.config import load_settings
from .service import SupportService
from .store import Store, DEFAULT_DB, customer_orders

STATIC = Path(__file__).with_name("static")


def voice_status():
    required = ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET", "MUNSIT_API_KEY", "MUNSIT_VOICE_ID", "OPENROUTER_API_KEY")
    missing = [name for name in required if not os.getenv(name, "").strip()]
    enabled = os.getenv("ENABLE_MUNSIT_BILLING", "false").lower() == "true"
    return {"configured": not missing and enabled and os.getenv("MUNSIT_API_MODE", "current") == "current",
            "missing": missing, "speech_enabled": enabled}


def voice_runtime_status(offline=False):
    import requests
    status = voice_status() | {"ready": False}
    if offline:
        return status | {"configured": False, "reason": "offline"}
    if not status["configured"]:
        return status | {"reason": "configuration"}
    # The worker's management endpoint is bound to loopback, never a user URL.
    port = int(os.getenv("SUPPORT_WORKER_PORT", "8091"))
    with requests.Session() as client:
        client.trust_env = False
        try:
            base = f"http://127.0.0.1:{port}"
            health = client.get(base, timeout=0.6)
            worker = client.get(base + "/worker", timeout=0.6)
            status["ready"] = health.ok and worker.ok and worker.json().get("agent_name") == "noura-support"
        except (requests.RequestException, ValueError):
            pass
    return status | {"reason": "ready" if status["ready"] else "worker"}


def voice_token(session, language):
    from livekit import api
    metadata = json.dumps({"support_session": session["id"], "language": language})
    token = (api.AccessToken(os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"])
             .with_identity("customer-" + secrets.token_hex(6)).with_name("Noura demo customer")
             .with_ttl(timedelta(minutes=10))
             .with_grants(api.VideoGrants(room_join=True, room=session["room"], can_publish=True,
                                         can_publish_data=True, can_subscribe=True))
             .with_room_config(api.RoomConfiguration(agents=[api.RoomAgentDispatch(agent_name="noura-support", metadata=metadata)]))
             .to_jwt())
    return {"url": os.environ["LIVEKIT_URL"], "token": token}


async def close_voice_room(room):
    import aiohttp
    from livekit import api
    async with api.LiveKitAPI(timeout=aiohttp.ClientTimeout(total=10)) as client:
        await client.room.delete_room(api.DeleteRoomRequest(room=room))


class SupportHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store, offline=False):
        super().__init__(address, Handler)
        self.store, self.service, self.offline = store, SupportService(store, offline), offline
        self.locks = defaultdict(threading.Lock)
        self.rates = defaultdict(deque)
        self.rate_lock = threading.Lock()

    def permit(self, key, limit=12):
        with self.rate_lock:
            queue = self.rates[key]
            now = time.monotonic()
            while queue and now - queue[0] > 60:
                queue.popleft()
            if len(queue) >= limit:
                return False
            queue.append(now)
            return True


class Handler(BaseHTTPRequestHandler):
    server_version = "NouraLocal/1.0"

    def log_message(self, fmt, *args):
        # No cookies, tokens, user messages or response bodies in server logs.
        pass

    def headers_common(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self' https: wss: ws:; worker-src blob:; frame-ancestors 'none'")

    def respond(self, status, payload, cookie=None):
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.headers_common()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        if cookie:
            self.send_header("Set-Cookie", f"noura_session={cookie}; Path=/; HttpOnly; SameSite=Strict; Max-Age=604800")
        self.end_headers()
        self.wfile.write(data)

    def local_request(self):
        port = self.server.server_port
        return self.headers.get("Host") in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def session(self):
        try:
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            token = cookies["noura_session"].value if "noura_session" in cookies else ""
            return self.server.store.session(token)
        except Exception:
            return None

    def do_GET(self):
        if not self.local_request():
            return self.respond(403, {"error": "Use the localhost address printed by the server."})
        path = urlsplit(self.path).path
        if path == "/api/bootstrap":
            cookie = None
            session = self.session()
            if not session:
                cookie, session = self.server.store.new_session()
            return self.respond(200, {"csrf": session["csrf"], "messages": self.server.store.messages(session["id"]),
                "orders": customer_orders(session["customer"]), "tickets": self.server.store.tickets(session["id"]),
                "articles": self.server.service.knowledge.articles, "voice": voice_runtime_status(self.server.offline),
                "ai_available": bool(os.getenv("OPENROUTER_API_KEY")) and not self.server.offline,
                "demo": True}, cookie)
        if path == "/api/health":
            return self.respond(200, {"status": "ok", "mode": "local-demo"})
        if path == "/api/voice/status":
            return self.respond(200, voice_runtime_status(self.server.offline))
        if path in ("/api/messages", "/api/tickets"):
            session = self.session()
            if not session:
                return self.respond(401, {"error": "Session expired. Refresh the page."})
            payload = self.server.store.messages(session["id"]) if path.endswith("messages") else self.server.store.tickets(session["id"])
            return self.respond(200, {"items": payload})
        files = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}
        if path not in files:
            return self.respond(404, {"error": "Not found"})
        data = (STATIC / files[path]).read_bytes()
        self.send_response(200)
        self.headers_common()
        self.send_header("Content-Type", (mimetypes.guess_type(files[path])[0] or "application/octet-stream") + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        try:
            self.handle_post()
        except (ValueError, json.JSONDecodeError) as exc:
            self.respond(400, {"error": str(exc)})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.respond(500, {"error": "The request could not be completed. Try again; no external action was confirmed."})

    def handle_post(self):
        if not self.local_request():
            return self.respond(403, {"error": "Invalid host."})
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
            return self.respond(403, {"error": "Cross-origin requests are not allowed."})
        session = self.session()
        if not session:
            return self.respond(401, {"error": "Session expired. Refresh the page."})
        if not hmac.compare_digest(self.headers.get("X-CSRF-Token", ""), session["csrf"]):
            return self.respond(403, {"error": "Invalid session request. Refresh the page."})
        if self.headers.get_content_type() != "application/json":
            return self.respond(415, {"error": "Send JSON."})
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= 20000:
            return self.respond(413, {"error": "Request is too large or empty."})
        self.connection.settimeout(10)
        body = json.loads(self.rfile.read(length))
        if not isinstance(body, dict):
            raise ValueError("Expected a JSON object.")
        sid, path = session["id"], urlsplit(self.path).path
        if not self.server.permit(sid):
            return self.respond(429, {"error": "Please wait a minute before trying again."})
        with self.server.locks[sid]:
            if path == "/api/chat":
                text = field(body, "message", 1, 2000)
                mode, language = body.get("mode", "ai"), body.get("language", "en")
                if mode not in ("ai", "knowledge") or language not in ("en", "ar"):
                    raise ValueError("Invalid chat mode or language.")
                result = self.server.service.answer(session, text, mode, language)
                return self.respond(200, result)
            if path == "/api/conversation/clear":
                self.server.store.clear(sid)
                return self.respond(200, {"ok": True})
            if path == "/api/tickets":
                subject, description = field(body, "subject", 4, 120), field(body, "description", 10, 3000)
                category = body.get("category")
                if category not in ("Order", "Return", "Product", "Other") or not isinstance(body.get("attach", False), bool):
                    raise ValueError("Invalid ticket category or transcript setting.")
                request_id = field(body, "request_id", 16, 80)
                ticket = self.server.store.create_ticket(sid, request_id, subject, category, description, body.get("attach", False))
                return self.respond(201, {"id": ticket, "tickets": self.server.store.tickets(sid)})
            if path == "/api/voice/token":
                status = voice_runtime_status(self.server.offline)
                if not status["ready"]:
                    return self.respond(409, {"error": "Voice is not running. Stop the old web server and run: python -m support_app.launch", "reason": status["reason"]})
                language = body.get("language", "en")
                if language not in ("en", "ar"):
                    raise ValueError("Invalid language.")
                return self.respond(200, voice_token(session, language))
            if path == "/api/voice/end":
                if voice_status()["configured"] and not self.server.offline:
                    try:
                        asyncio.run(close_voice_room(session["room"]))
                    except Exception:
                        return self.respond(502, {"error": "Browser disconnected, but server room cleanup could not be confirmed. Check the agent terminal."})
                return self.respond(200, {"ok": True})
        return self.respond(404, {"error": "Not found"})


def field(body, key, minimum, maximum):
    value = body.get(key)
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(f"{key} must be between {minimum} and {maximum} characters.")
    return value.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--offline", action="store_true", help="Use only local knowledge; no model or voice calls")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    load_settings()
    server = SupportHTTPServer(("127.0.0.1", args.port), Store(args.db), args.offline)
    print(f"Noura Care is ready at http://127.0.0.1:{args.port}", flush=True)
    print("Local fictional demo. Ctrl+C stops the server.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
