from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.dylan.schemas import ConversationFlags  # noqa: E402
from agents.runtime.codex_runtime import (  # noqa: E402
    CodexAgentRuntime,
    codex_account_email,
    parse_codex_json_lines,
)
from agents.runtime.cursor_runtime import CursorAgentRuntime, canonical_agent_provider, create_agent_runtime  # noqa: E402
from agents.runtime.openai_compatible import OpenAICompatibleAgentRuntime  # noqa: E402
from agents.runtime.opencode_runtime import OpenCodeAgentRuntime  # noqa: E402


def _jwt(payload: dict[str, str]) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"header.{encoded}.signature"


class CodexRuntimeTests(unittest.TestCase):
    def test_parser_collects_thread_final_message_and_tools(self) -> None:
        events = [
            {"type": "thread.started", "thread_id": "thread-1"},
            {"type": "item.completed", "item": {"id": "cmd-1", "type": "command_execution", "status": "completed"}},
            {"type": "item.completed", "item": {"id": "msg-1", "type": "agent_message", "text": "Connected."}},
            {"type": "turn.completed", "turn_id": "turn-1"},
        ]
        result = parse_codex_json_lines(json.dumps(event) for event in events)
        self.assertEqual("thread-1", result.provider_session_id)
        self.assertEqual("turn-1", result.request_id)
        self.assertEqual("Connected.", result.text)
        self.assertEqual("succeeded", result.status)
        self.assertEqual("command_execution", result.tool_events[0].tool_type)

    def test_factory_routes_codex_to_codex_runtime(self) -> None:
        runtime = create_agent_runtime(provider="codex", model="gpt-5.6-luna", reasoning_effort="xhigh", account_email="kuoyio0820@gmail.com")
        self.assertIsInstance(runtime, CodexAgentRuntime)
        self.assertEqual("xhigh", runtime.reasoning_effort)
        self.assertEqual("kuoyio0820@gmail.com", runtime.account_email)

    def test_codex_command_pins_model_and_reasoning_effort(self) -> None:
        runtime = CodexAgentRuntime(model="gpt-5.6-luna", reasoning_effort="xhigh", account_email="kuoyio0820@gmail.com")
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            with patch.object(runtime, "_agent_bin", return_value="codex"):
                command = runtime._command(workspace, "hello", None)
        self.assertIn("gpt-5.6-luna", command)
        self.assertIn('model_reasoning_effort="xhigh"', command)
        self.assertIn("workspace-write", command)
        self.assertIn("never", command)

    def test_codex_command_can_request_structured_output(self) -> None:
        runtime = CodexAgentRuntime(
            model="gpt-5.6-luna",
            reasoning_effort="xhigh",
            account_email="kuoyio0820@gmail.com",
            output_schema=Path("/tmp/test-case-output-schema.json"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(runtime, "_agent_bin", return_value="codex"):
                command = runtime._command(Path(tmp), "generate", None)
        self.assertIn("--output-schema", command)
        self.assertIn(str(Path("/tmp/test-case-output-schema.json").resolve()), command)

    def test_codex_resume_command_uses_the_saved_thread_id(self) -> None:
        runtime = CodexAgentRuntime(model="gpt-5.6-luna", reasoning_effort="xhigh", account_email="kuoyio0820@gmail.com")
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(runtime, "_agent_bin", return_value="codex"):
                command = runtime._command(Path(tmp), "continue", "thread-from-first-turn")
        self.assertEqual("resume", command[4])
        self.assertEqual("thread-from-first-turn", command[5])
        self.assertIn("--json", command)
        self.assertIn("gpt-5.6-luna", command)
        self.assertIn('model_reasoning_effort="xhigh"', command)
        self.assertNotIn("--cd", command)

    def test_account_email_is_read_without_exposing_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "auth.json").write_text(
                json.dumps({"tokens": {"id_token": _jwt({"email": "kuoyio0820@gmail.com"}), "access_token": "secret"}}),
                encoding="utf-8",
            )
            self.assertEqual("kuoyio0820@gmail.com", codex_account_email(home))

    def test_conversation_flags_apply_codex_defaults(self) -> None:
        flags = ConversationFlags.from_common({"execution": {"provider": "codex"}})
        self.assertEqual("codex", flags.model.provider)
        self.assertEqual("gpt-5.6-luna", flags.model.model_name)
        self.assertEqual("xhigh", flags.model.reasoning_effort)
        self.assertEqual("kuoyio0820@gmail.com", flags.model.account_email)

    def test_conversation_flags_apply_non_codex_provider_defaults(self) -> None:
        opencode = ConversationFlags.from_common({"execution": {"provider": "deepseek_api"}})
        api = ConversationFlags.from_common({"execution": {"provider": "openai-compatible"}})
        self.assertEqual("deepseek-v4-flash", opencode.model.model_name)
        self.assertEqual("gpt-4o-mini", api.model.model_name)

    def test_provider_aliases_and_session_capabilities_are_consistent(self) -> None:
        self.assertEqual("cursor_cli", canonical_agent_provider("cursor-cli"))
        self.assertEqual("openai_compatible", canonical_agent_provider("openai-compatible"))
        runtimes = {
            "cursor": create_agent_runtime(provider="cursor-cli", model="cursor-grok-4.5-medium"),
            "opencode": create_agent_runtime(provider="deepseek_api", model="deepseek-v4-flash"),
            "codex": create_agent_runtime(provider="codex-cli", model="gpt-5.6-luna"),
            "api": create_agent_runtime(provider="openai-compatible", model="gpt-4o-mini"),
        }
        self.assertIsInstance(runtimes["cursor"], CursorAgentRuntime)
        self.assertIsInstance(runtimes["opencode"], OpenCodeAgentRuntime)
        self.assertIsInstance(runtimes["codex"], CodexAgentRuntime)
        self.assertIsInstance(runtimes["api"], OpenAICompatibleAgentRuntime)
        for name in ("cursor", "opencode", "codex"):
            self.assertTrue(runtimes[name].supports_resume, name)
            self.assertFalse(runtimes[name].supports_stateless, name)
        self.assertFalse(runtimes["api"].supports_resume)
        self.assertTrue(runtimes["api"].supports_stateless)


if __name__ == "__main__":
    unittest.main()
