"""Provider compatibility and startup safeguards; all external traffic is mocked."""
import hashlib
import io
import json
import os
from pathlib import Path
import unittest
import uuid
from unittest.mock import MagicMock, patch
import zipfile

import requests

from . import launch
from .providers import ProviderError, failure_code
from .server import voice_runtime_status
from .service import SupportService


def response(payload=None, status=200):
    result = MagicMock()
    result.status_code = status
    result.ok = status < 400
    result.json.return_value = payload
    result.__enter__.return_value = result
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(response=result)
    return result


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.service = SupportService(None)
        self.articles = self.service.knowledge.search("return policy")
        self.valid = {"choices": [{"message": {"content": json.dumps({"answer": "Request within 14 days.", "source_ids": ["returns"]})}}]}
        self.env = patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-only", "OPENROUTER_MODEL": "openrouter/free"})
        self.env.start()
        self.addCleanup(self.env.stop)

    def generate(self):
        return self.service.generate("return policy", [], self.articles, "en")

    def test_json_compatibility_retry_stays_free(self):
        with patch("requests.post", side_effect=[response(status=400), response(self.valid)]) as post:
            self.assertEqual(self.generate()["mode"], "ai")
        self.assertEqual(post.call_count, 2)
        bodies = [call.kwargs["json"] for call in post.call_args_list]
        self.assertIn("response_format", bodies[0])
        self.assertNotIn("response_format", bodies[1])
        for body in bodies:
            self.assertEqual(body["model"], "openrouter/free")
            self.assertEqual(body["provider"]["max_price"], {"prompt": 0, "completion": 0})

    def test_fenced_json_is_validated(self):
        self.valid["choices"][0]["message"]["content"] = '```json\n' + self.valid["choices"][0]["message"]["content"] + '\n```'
        with patch("requests.post", return_value=response(self.valid)) as post:
            self.assertEqual(self.generate()["sources"][0]["id"], "returns")
        self.assertEqual(post.call_count, 1)

    def test_incomplete_or_invented_citations_are_not_accepted(self):
        for content, finish in (("{}", "length"), (json.dumps({"answer": "Made up", "source_ids": ["invented"]}), "stop")):
            bad = {"choices": [{"message": {"content": content}, "finish_reason": finish}]}
            with patch("requests.post", return_value=response(bad)) as post, self.assertRaises(ProviderError) as error:
                self.generate()
            self.assertEqual(error.exception.code, "format")
            self.assertEqual(post.call_count, 2)

    def test_quota_auth_network_never_replayed(self):
        for failure, code in ((response(status=401), "authentication"), (response(status=402), "credits"),
                              (response(status=429), "quota"), (requests.ProxyError if hasattr(requests, 'ProxyError') else requests.exceptions.ProxyError, "network")):
            kwargs = {"side_effect": failure("private proxy address")} if isinstance(failure, type) else {"return_value": failure}
            with patch("requests.post", **kwargs) as post, self.assertRaises(ProviderError) as error:
                self.generate()
            self.assertEqual(post.call_count, 1)
            self.assertEqual(error.exception.code, code)
            self.assertNotIn("private proxy", str(error.exception))

    def test_timeout_classification(self):
        self.assertEqual(failure_code(requests.Timeout("secret")), "timeout")

    def test_voice_tool_probe_rejects_plain_text(self):
        with patch.object(SupportService, "generate", return_value={"mode": "ai"}), patch("requests.post", return_value=response(self.valid)):
            with self.assertRaisesRegex(ValueError, "valid tool call"):
                launch.check_ai(voice=True)


class SetupTests(unittest.TestCase):
    def test_no_cloud_settings_overwritten(self):
        env = {"LIVEKIT_URL": "wss://test.livekit.cloud", "LIVEKIT_API_KEY": "test", "LIVEKIT_API_SECRET": "test"}
        with patch.dict(os.environ, env, clear=True), patch.object(launch, "save_setting") as save:
            self.assertFalse(launch.configure_local())
            save.assert_not_called()

    def test_partial_config_rejected(self):
        with patch.dict(os.environ, {"LIVEKIT_URL": "wss://test.livekit.cloud"}, clear=True), patch.object(launch, "save_setting") as save:
            with self.assertRaisesRegex(ValueError, "incomplete"):
                launch.configure_local()
            save.assert_not_called()

    def test_empty_config_gets_only_local_defaults(self):
        def save(name, value):
            os.environ[name] = value
        with patch.dict(os.environ, {}, clear=True), patch.object(launch, "save_setting", side_effect=save) as write:
            self.assertTrue(launch.configure_local())
            self.assertEqual(write.call_count, 3)
            self.assertEqual(os.environ["LIVEKIT_URL"], "ws://127.0.0.1:7880")

    def test_checksum_and_safe_binary_extraction(self):
        root = launch.RUNTIME / ("binary-test-" + uuid.uuid4().hex)
        target = root / "livekit-server.exe"
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("livekit-server.exe", b"test binary")
            archive.writestr("../../must-not-extract.txt", b"bad")
        data = data.getvalue()
        try:
            with self.assertRaisesRegex(ValueError, "checksum"):
                launch.install_binary(data, "0" * 64, target)
            self.assertFalse(target.exists())
            launch.install_binary(data, hashlib.sha256(data).hexdigest(), target)
            self.assertEqual(target.read_bytes(), b"test binary")
            self.assertEqual([p.name for p in root.iterdir()], ["livekit-server.exe"])
        finally:
            target.unlink(missing_ok=True)
            if root.exists():
                root.rmdir()

    def test_configured_but_dead_worker_is_not_ready(self):
        with patch("support_app.server.voice_status", return_value={"configured": True}), patch("requests.Session") as session:
            session.return_value.__enter__.return_value.get.side_effect = requests.ConnectionError()
            self.assertFalse(voice_runtime_status()["ready"])

    def test_wrong_worker_is_not_ready(self):
        with patch("support_app.server.voice_status", return_value={"configured": True}), patch("requests.Session") as session:
            session.return_value.__enter__.return_value.get.return_value = response({"agent_name": "different-agent"})
            self.assertFalse(voice_runtime_status()["ready"])

    def test_worker_health_and_name_checked(self):
        with patch("support_app.server.voice_status", return_value={"configured": True}), patch("requests.Session") as session:
            session.return_value.__enter__.return_value.get.return_value = response({"agent_name": "noura-support"})
            self.assertTrue(voice_runtime_status()["ready"])

    def test_supervisor_stops_only_owned_children(self):
        processes = launch.Processes()
        child, log = MagicMock(), MagicMock()
        child.poll.return_value = None
        processes.children.append((child, log, "owned"))
        processes.close()
        child.terminate.assert_called_once()
        child.wait.assert_called_once_with(timeout=8)
        log.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
