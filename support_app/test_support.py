"""Offline API integration tests; no model, speech or hosting charges."""
import base64
import json
import os
from pathlib import Path
import threading
import unittest
import uuid
from unittest.mock import patch, MagicMock

import requests

from .knowledge import KnowledgeBase
from .server import SupportHTTPServer, voice_token
from .service import SupportService
from .store import Store, customer_orders, lookup_order


class SupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parent / "runtime"
        root.mkdir(parents=True, exist_ok=True)
        cls.path = root / ("test-" + uuid.uuid4().hex + ".sqlite3")
        cls.store = Store(cls.path)
        cls.server = SupportHTTPServer(("127.0.0.1", 0), cls.store, offline=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.path.unlink(missing_ok=True)

    def setUp(self):
        self.client = requests.Session()
        self.client.trust_env = False  # Local loopback test, never external traffic.
        response = self.client.get(self.url + "/api/bootstrap", timeout=5)
        self.data = response.json()
        self.client.headers["X-CSRF-Token"] = self.data["csrf"]

    def tearDown(self):
        self.client.close()

    def post(self, path, body):
        return self.client.post(self.url + path, json=body, timeout=5)

    def ticket(self):
        return {"subject": "Headphones will not pair", "description": "I tried the steps for my demo Noura Air and need help.",
                "category": "Product", "attach": False, "request_id": str(uuid.uuid4())}

    def test_static_and_configuration(self):
        self.assertEqual(len(self.data["articles"]), 10)
        self.assertFalse(self.data["ai_available"])
        self.assertFalse(self.data["voice"]["configured"])
        page = self.client.get(self.url, timeout=5)
        self.assertEqual(page.status_code, 200)
        self.assertIn("Noura Care", page.text)
        self.assertEqual(page.headers["X-Frame-Options"], "DENY")
        self.assertEqual(self.client.get(self.url + "/.env", timeout=5).status_code, 404)

    def test_csrf_and_cross_origin_rejected(self):
        self.client.headers.pop("X-CSRF-Token")
        self.assertEqual(self.post("/api/tickets", self.ticket()).status_code, 403)
        self.client.headers["X-CSRF-Token"] = self.data["csrf"]
        self.client.headers["Origin"] = "https://evil.example"
        self.assertEqual(self.post("/api/tickets", self.ticket()).status_code, 403)

    def test_known_question_and_persistence(self):
        answer = self.post("/api/chat", {"message": "What is your return policy?", "mode": "knowledge"}).json()
        self.assertIn("14 calendar days", answer["text"])
        self.assertEqual(answer["sources"][0]["id"], "returns")
        messages = self.client.get(self.url + "/api/messages", timeout=5).json()["items"]
        self.assertEqual(len(messages), 2)

    def test_arabic_retrieval(self):
        answer = self.post("/api/chat", {"message": "ما سياسة الإرجاع؟", "mode": "knowledge"}).json()
        self.assertEqual(answer["language"], "ar")
        self.assertIn("14", answer["text"])
        self.assertEqual(answer["sources"][0]["id"], "returns")
        sources = KnowledgeBase().search("كيف أقوم بإقران سماعات Noura Air؟")
        self.assertEqual([s["id"] for s in sources], ["pairing"])

    def test_unknown_question_does_not_call_model(self):
        with patch("requests.post", side_effect=AssertionError("Provider must not be called")):
            service = SupportService(self.store)
            _, session = self.store.new_session()
            answer = service.answer(session, "Who won the lunar chess tournament?", "ai", "en")
        self.assertTrue(answer["needs_support"])
        self.assertEqual(answer["sources"], [])

    def test_order_lookup_is_customer_scoped(self):
        answer = self.post("/api/chat", {"message": "Where is NR-1042?"}).json()
        self.assertEqual(answer["order"]["status"], "Shipped")
        self.assertIsNone(lookup_order("different-customer", "NR-1042"))
        self.assertEqual(customer_orders("different-customer"), [])
        self.assertNotIn("order", self.post("/api/chat", {"message": "Where is NR-9999?"}).json())

    def test_policy_question_with_order(self):
        answer = self.post("/api/chat", {"message": "Can I cancel NR-1042?"}).json()
        self.assertEqual(answer["order"]["status"], "Shipped")
        self.assertIn("cancel", [s["id"] for s in answer["sources"]])
        self.assertIn("cannot", answer["text"])

    def test_ticket_idempotency_and_isolation(self):
        payload = self.ticket()
        first = self.post("/api/tickets", payload)
        second = self.post("/api/tickets", payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["id"], second.json()["id"])
        self.assertEqual(len(second.json()["tickets"]), 1)
        with requests.Session() as other:
            other.trust_env = False
            bootstrap = other.get(self.url + "/api/bootstrap", timeout=5).json()
            self.assertEqual(bootstrap["tickets"], [])
        with self.store.connect() as db:
            row = db.execute("SELECT transcript FROM tickets WHERE id=?", (first.json()["id"],)).fetchone()
            self.assertEqual(json.loads(row["transcript"]), [])

    def test_ticket_validation(self):
        payload = self.ticket()
        payload["category"] = "Execute command"
        self.assertEqual(self.post("/api/tickets", payload).status_code, 400)
        self.assertEqual(self.post("/api/chat", {"message": "x" * 2001}).status_code, 400)

    def test_clear_keeps_tickets(self):
        self.post("/api/chat", {"message": "hello"})
        self.post("/api/tickets", self.ticket())
        self.assertEqual(self.post("/api/conversation/clear", {}).status_code, 200)
        self.assertEqual(self.client.get(self.url + "/api/messages", timeout=5).json()["items"], [])
        self.assertEqual(len(self.client.get(self.url + "/api/tickets", timeout=5).json()["items"]), 1)

    def test_rate_limit(self):
        for _ in range(12):
            self.assertEqual(self.post("/api/conversation/clear", {}).status_code, 200)
        self.assertEqual(self.post("/api/conversation/clear", {}).status_code, 429)

    def test_voice_not_configured(self):
        self.assertEqual(self.post("/api/voice/token", {}).status_code, 409)

    def test_voice_token_room_and_dispatch(self):
        _, session = self.store.new_session()
        with patch.dict(os.environ, {"LIVEKIT_API_KEY": "dummy", "LIVEKIT_API_SECRET": "x" * 32, "LIVEKIT_URL": "ws://localhost:7880"}):
            token = voice_token(session, "ar")["token"]
        encoded = token.split(".")[1]
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        self.assertEqual(payload["video"]["room"], session["room"])
        self.assertFalse(payload["video"].get("roomAdmin", False))
        self.assertEqual(payload["roomConfig"]["agents"][0]["agentName"], "noura-support")

    def test_invalid_model_output_falls_back(self):
        _, session = self.store.new_session()
        service = SupportService(self.store)
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "dummy"}), patch.object(service, "generate", side_effect=ValueError("invalid citation")):
            answer = service.answer(session, "How long do refunds take?", "ai", "en")
        self.assertEqual(answer["mode"], "knowledge")
        self.assertEqual(answer["error_code"], "format")
        self.assertIn("invalid source", answer["notice"])

    def test_model_request_and_citation_validation(self):
        service = SupportService(self.store)
        articles = service.knowledge.search("return policy")
        response = MagicMock()
        post = MagicMock()
        post.return_value.__enter__.return_value = response
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "dummy", "OPENROUTER_MODEL": "openrouter/free"}), patch("support_app.service.requests.post", post):
            response.json.return_value = {"choices": [{"message": {"content": json.dumps({"answer": "Request within 14 calendar days.", "source_ids": ["returns"]})}}]}
            result = service.generate("return policy", [], articles, "en")
            self.assertEqual(result["mode"], "ai")
            self.assertEqual(post.call_args.kwargs["json"]["provider"]["max_price"], {"prompt": 0, "completion": 0})
            for invalid in (["wrong type"], {"answer": "Invented", "source_ids": ["not-retrieved"]}):
                response.json.return_value = {"choices": [{"message": {"content": json.dumps(invalid)}}]}
                with self.assertRaises(ValueError):
                    service.generate("return policy", [], articles, "en")


if __name__ == "__main__":
    unittest.main()
