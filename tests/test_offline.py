"""Offline checks for cost guards, request construction and response handling."""
import os
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from examples.config import free_model, load_settings, require_speech_opt_in
from examples.knowledge import search_faq
from examples.munsit_transcribe import main as transcribe, transcription_text
from examples.openrouter_chat import is_zero_price, main as chat


class OfflineTests(unittest.TestCase):
    def test_paid_and_automatic_routes_rejected(self):
        for model in ("openrouter/auto", "auto", "openai/gpt-4o", "", "x:free:online"):
            with self.subTest(model=model), self.assertRaises(ValueError):
                free_model(model)
        self.assertEqual(free_model("openrouter/free"), "openrouter/free")
        self.assertEqual(free_model("vendor/model:free"), "vendor/model:free")

    def test_unknown_pricing_is_not_free(self):
        self.assertFalse(is_zero_price({}))
        self.assertFalse(is_zero_price({"pricing": {"prompt": "0", "completion": ".1"}}))
        self.assertTrue(is_zero_price({"pricing": {"prompt": "0", "completion": "0.0"}}))

    def test_speech_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            require_speech_opt_in()

    def test_aliases_preserve_standard_key(self):
        with patch("examples.config.load_dotenv"), patch.dict(os.environ, {
            "key": "dummy-munsit", "open_router": "dummy-old",
            "OPENROUTER_API_KEY": "dummy-preferred",
        }, clear=True):
            load_settings()
            self.assertEqual(os.environ["MUNSIT_API_KEY"], "dummy-munsit")
            self.assertEqual(os.environ["OPENROUTER_API_KEY"], "dummy-preferred")

    def test_transcript_shapes_and_silence(self):
        self.assertEqual(transcription_text({"data": {"transcription": "مرحبا"}}), "مرحبا")
        self.assertEqual(transcription_text({"text": "hello"}), "hello")
        self.assertEqual(transcription_text({"data": {"transcription": ""}}), "")
        with self.assertRaises(RuntimeError):
            transcription_text({"data": {"unexpected": "value"}})

    def test_retrieval_unknown_and_arabic(self):
        self.assertTrue(search_faq("الدعم")["found"])
        self.assertFalse(search_faq("unmatchedxyz")["found"])
        self.assertFalse(search_faq("What is the password?")["found"])
        self.assertFalse(search_faq("x" * 501)["found"])

    def test_openrouter_request_never_uses_paid_route(self):
        response = MagicMock()
        response.ok = True
        response.json.return_value = {"choices": [{"message": {"content": "hello"}}]}
        with patch("examples.openrouter_chat.load_settings"), patch.dict(os.environ, {
            "OPENROUTER_API_KEY": "dummy", "OPENROUTER_MODEL": "openrouter/free"
        }, clear=True), patch.object(sys, "argv", ["chat", "hi"]), \
                patch("requests.post") as post, patch("builtins.print"):
            post.return_value.__enter__.return_value = response
            chat()
            self.assertEqual(post.call_args.args[0], "https://openrouter.ai/api/v1/chat/completions")
            body = post.call_args.kwargs["json"]
            self.assertEqual(body["model"], "openrouter/free")
            self.assertEqual(body["provider"]["max_price"], {"prompt": 0, "completion": 0})
            self.assertNotIn("plugins", body)
            self.assertNotIn("models", body)

    def test_current_and_legacy_munsit_auth(self):
        response = MagicMock()
        response.ok = True
        response.json.return_value = {"data": {"transcription": "test"}}
        with patch.object(Path, "is_file", return_value=True), \
                patch.object(Path, "stat", return_value=MagicMock(st_size=10)):
            audio = Path("sample.mp3")
            for mode in ("current", "legacy"):
                with self.subTest(mode=mode), patch("examples.munsit_transcribe.load_settings"), \
                        patch.dict(os.environ, {"MUNSIT_API_KEY": "dummy",
                                                "ENABLE_MUNSIT_BILLING": "true",
                                                "MUNSIT_API_MODE": mode}, clear=True), \
                        patch.object(sys, "argv", ["transcribe", str(audio)]), \
                        patch.object(Path, "open", return_value=io.BytesIO(b"fake audio")), \
                        patch("requests.post") as post, patch("builtins.print"):
                    post.return_value.__enter__.return_value = response
                    transcribe()
                    headers = post.call_args.kwargs["headers"]
                    expected = {"x-api-key": "dummy"} if mode == "current" else {"Authorization": "Bearer dummy"}
                    self.assertEqual(headers, expected)
                    self.assertTrue(post.call_args.kwargs["files"]["file"][1].closed)


if __name__ == "__main__":
    unittest.main()
