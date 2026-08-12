#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.runtime.cursor_runtime import _recent_cursor_provider_error
from agents.dylan.model_client import OpenAICompatibleDylanModelClient, get_model_client
from agents.dylan.schemas import ModelConfig
from agents.runtime.openai_compatible import OpenAICompatibleAgentRuntime, chat_completion


class _Response:
    def __init__(self, body: dict) -> None:
        self.body = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class OpenAICompatibleTests(unittest.TestCase):
    def test_deepseek_chat_completion_uses_openai_shape(self) -> None:
        with mock.patch.dict(os.environ, {"DEEPSEEK_API_KEY": "secret"}, clear=True), mock.patch(
            "urllib.request.urlopen",
            return_value=_Response({"id": "req-1", "choices": [{"message": {"content": json.dumps({"ok": True})}}]}),
        ) as urlopen:
            text, request_id = chat_completion(
                provider="deepseek",
                model="deepseek-v4-flash",
                prompt="return JSON",
                timeout=5,
                json_mode=True,
            )
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "https://api.deepseek.com/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(text, json.dumps({"ok": True}))
        self.assertEqual(request_id, "req-1")

    def test_missing_key_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"LUMON_HOME": tmp}, clear=True), mock.patch(
                "agents.runtime.openai_compatible._load_dotenv"
            ):
                with self.assertRaisesRegex(RuntimeError, "DEEPSEEK_API_KEY"):
                    chat_completion(provider="deepseek", model="deepseek-v4-flash", prompt="hi", timeout=5)

    def test_runtime_is_stateless(self) -> None:
        self.assertTrue(OpenAICompatibleAgentRuntime().supports_stateless)
        self.assertFalse(OpenAICompatibleAgentRuntime().supports_resume)

    def test_model_client_factory_accepts_deepseek(self) -> None:
        client = get_model_client(ModelConfig(provider="deepseek", model_name="deepseek-v4-flash"), require_real=True)
        self.assertIsInstance(client, OpenAICompatibleDylanModelClient)

    def test_cursor_quota_marker_is_normalized_without_log_leak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "cursor-agent-logs-session"
            log_dir.mkdir()
            log = log_dir / "session-1.log"
            log.write_text("secret prompt\nYou've reached your monthly usage limit\n", encoding="utf-8")
            error = _recent_cursor_provider_error({"TMPDIR": tmp}, 0)
        self.assertEqual(error, "Cursor monthly usage limit reached")
        self.assertNotIn("secret prompt", error)


if __name__ == "__main__":
    unittest.main()
