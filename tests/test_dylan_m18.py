#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.dylan.autonomous import handle_autonomous_conversation
from agents.dylan.autonomous_runtime import AgentRunResult, CursorAgentRuntime
from agents.dylan.cursor_stream import parse_stream_json_text
from agents.dylan.schemas import ConversationFlags
from agents.dylan.session_store import SessionStore, conversation_scope_id
from agents.dylan.workspace_contract import ensure_workspace_contract
from risk.store import GlobalAgentStore


def _v4_common(provider: str = "cursor_cli") -> dict:
    return {
        "project": {"slug": "mbpass"},
        "agents": {
            "dylan": {
                "conversation_v4": {
                    "enabled": True,
                    "mode": "autonomous_workspace",
                    "provider": {"type": provider, "model": "fake-model"},
                    "session": {"scope": "thread_shared"},
                    "runtime": {"soft_timeout_seconds": 60, "hard_timeout_seconds": 180},
                    "reaction": {"enabled": True, "emoji_type": "Typing"},
                }
            }
        },
    }


class FakeRuntime(CursorAgentRuntime):
    def __init__(self, results: list[AgentRunResult]) -> None:
        super().__init__(model="fake")
        self.results = list(results)
        self.calls: list[dict] = []

    def run(self, *, workspace, prompt, provider_session_id=None, trace=None, obs=None):  # type: ignore[override]
        self.calls.append(
            {
                "workspace": str(workspace),
                "prompt": prompt,
                "provider_session_id": provider_session_id,
            }
        )
        if not self.results:
            return AgentRunResult(text="", provider_session_id="", status="failed", error="no fake result")
        return self.results.pop(0)


class StatelessFakeRuntime(FakeRuntime):
    supports_stateless = True
    supports_resume = False


class StreamJsonTests(unittest.TestCase):
    def test_parse_stream_json(self) -> None:
        text = "\n".join(
            [
                '{"type":"system","subtype":"init","session_id":"sess-abc"}',
                '{"type":"assistant","message":{"content":[{"type":"text","text":"Hello "}]}}',
                '{"type":"tool_call","subtype":"started","call_id":"c1","tool_call":{"shellToolCall":{"args":{"command":"lumen risk recent --json"}}}}',
                '{"type":"tool_call","subtype":"completed","call_id":"c1","tool_call":{"shellToolCall":{"args":{"command":"lumen risk recent --json"}}}}',
                '{"type":"result","subtype":"success","result":"Hello world","session_id":"sess-abc","duration_ms":1200,"request_id":"req-1"}',
            ]
        )
        parsed = parse_stream_json_text(text)
        self.assertEqual(parsed.status, "succeeded")
        self.assertEqual(parsed.text, "Hello world")
        self.assertEqual(parsed.provider_session_id, "sess-abc")
        self.assertEqual(parsed.request_id, "req-1")
        self.assertEqual(len(parsed.tool_events), 2)
        self.assertEqual(parsed.tool_events[0].command_base, "lumen")


class ConversationV4FlagsTests(unittest.TestCase):
    def test_autonomous_flag(self) -> None:
        flags = ConversationFlags.from_common(_v4_common())
        self.assertTrue(flags.v4_enabled)
        self.assertTrue(flags.autonomous)
        self.assertFalse(flags.agent_only)
        self.assertEqual(flags.model.model_name, "fake-model")
        self.assertEqual(flags.soft_timeout_seconds, 60)

    def test_default_hard_timeout_is_one_hour(self) -> None:
        common = _v4_common()
        common["agents"]["dylan"]["conversation_v4"].pop("runtime")
        flags = ConversationFlags.from_common(common)
        self.assertEqual(flags.hard_timeout_seconds, 3600)

    def test_global_execution_model_overrides_agent_model(self) -> None:
        common = _v4_common()
        common["execution"] = {"provider": "deepseek", "model": "deepseek-v4-flash", "api_key_env": "DEEPSEEK_API_KEY"}
        flags = ConversationFlags.from_common(common)
        self.assertEqual("deepseek", flags.model.provider)
        self.assertEqual("deepseek-v4-flash", flags.model.model_name)
        self.assertEqual("DEEPSEEK_API_KEY", flags.model.api_key_env)


class SessionStoreTests(unittest.TestCase):
    def test_create_resume_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            store = SessionStore(GlobalAgentStore(Path(tmp) / "agents.sqlite3"))
            scope = conversation_scope_id(chat_id="oc1", thread_id="om_root", project_slug="mbpass")
            created = store.create(
                chat_id="oc1",
                conversation_scope_id=scope,
                workspace_path=tmp,
                project_slug="mbpass",
            )
            active = store.get_active(conversation_scope_id=scope)
            self.assertIsNotNone(active)
            assert active is not None
            self.assertEqual(active["session_id"], created["session_id"])
            store.update(created["session_id"], provider_session_id="cursor-123")
            again = store.get_active(conversation_scope_id=scope)
            assert again is not None
            self.assertEqual(again["provider_session_id"], "cursor-123")
            store.close()


class AutonomousRuntimeTests(unittest.TestCase):
    def test_bootstrap_then_resume(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            (workspace / "config").mkdir()
            (workspace / "config" / "common.json").write_text(
                '{"project":{"slug":"mbpass"}}',
                encoding="utf-8",
            )
            ensure_workspace_contract(workspace=workspace, project_slug="mbpass")
            self.assertTrue((workspace / "AGENTS.md").is_file())
            self.assertTrue((workspace / ".cursor" / "cli.json").is_file())

            GlobalAgentStore(Path(tmp) / "agents.sqlite3").close()

            # Stub project resolver by pointing mapping via env workspace path is hard;
            # exercise handle_autonomous with monkeypatched resolve by writing registry-like layout.
            from unittest.mock import patch

            fake = FakeRuntime(
                [
                    AgentRunResult(
                        text="first answer",
                        provider_session_id="prov-1",
                        status="succeeded",
                        duration_ms=100,
                    ),
                    AgentRunResult(
                        text="second answer",
                        provider_session_id="prov-1",
                        status="succeeded",
                        duration_ms=80,
                    ),
                ]
            )
            project = {"slug": "mbpass", "workspace": str(workspace)}
            with patch("agents.dylan.autonomous.resolve_project", return_value=project), patch(
                "agents.dylan.autonomous.known_project_slugs", return_value={"mbpass"}
            ), patch("agents.dylan.autonomous.load_chat_project_map", return_value={}):
                first = handle_autonomous_conversation(
                    text="summarize risks",
                    meta={"chat_id": "oc1", "chat_type": "p2p", "thread_id": "t1", "user_id": "u1", "message_id": "m1"},
                    common=_v4_common(),
                    runtime=fake,
                )
                self.assertEqual(first["status"], "ok")
                self.assertTrue(first.get("bootstrap"))
                self.assertIn("BOOTSTRAP", fake.calls[0]["prompt"])
                self.assertIsNone(fake.calls[0]["provider_session_id"])

                second = handle_autonomous_conversation(
                    text="and the top one?",
                    meta={"chat_id": "oc1", "chat_type": "p2p", "thread_id": "t1", "user_id": "u1", "message_id": "m2"},
                    common=_v4_common(),
                    runtime=fake,
                )
                self.assertEqual(second["status"], "ok")
                self.assertFalse(second.get("bootstrap"))
                self.assertEqual(fake.calls[1]["provider_session_id"], "prov-1")
                self.assertIn("LUMEN MESSAGE", fake.calls[1]["prompt"])
                self.assertIn("Remain Dylan", fake.calls[1]["prompt"])

    def test_resume_stream_failure_bootstraps_again(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            (workspace / "config").mkdir()
            (workspace / "config" / "common.json").write_text('{"project":{"slug":"mbpass"}}', encoding="utf-8")
            GlobalAgentStore(Path(tmp) / "agents.sqlite3").close()
            from unittest.mock import patch

            fake = FakeRuntime(
                [
                    AgentRunResult(text="ok", provider_session_id="prov-1", status="succeeded", duration_ms=50),
                    AgentRunResult(text="", provider_session_id="", status="failed", error="no result event in stream-json"),
                    AgentRunResult(text="recovered dylan voice", provider_session_id="prov-2", status="succeeded", duration_ms=60),
                ]
            )
            project = {"slug": "mbpass", "workspace": str(workspace)}
            with patch("agents.dylan.autonomous.resolve_project", return_value=project), patch(
                "agents.dylan.autonomous.known_project_slugs", return_value={"mbpass"}
            ), patch("agents.dylan.autonomous.load_chat_project_map", return_value={}):
                handle_autonomous_conversation(
                    text="hi",
                    meta={"chat_id": "oc1", "chat_type": "p2p", "user_id": "u1", "message_id": "m1"},
                    common=_v4_common(),
                    runtime=fake,
                )
                recovered = handle_autonomous_conversation(
                    text="Are you happy in Lumon?",
                    meta={"chat_id": "oc1", "chat_type": "p2p", "user_id": "u1", "message_id": "m2"},
                    common=_v4_common(),
                    runtime=fake,
                )
                self.assertEqual(recovered["status"], "ok")
                self.assertIn("recovered", recovered["text"])
                self.assertIsNone(fake.calls[2]["provider_session_id"])
                self.assertIn("BOOTSTRAP", fake.calls[2]["prompt"])
                self.assertIn("Soul notes", fake.calls[2]["prompt"])

    def test_provider_switch_starts_a_native_session_with_a_logical_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            (workspace / "config").mkdir()
            (workspace / "config" / "common.json").write_text('{"project":{"slug":"mbpass"}}', encoding="utf-8")
            cursor = FakeRuntime([
                AgentRunResult(text="cursor answer", provider_session_id="cursor-session", status="succeeded", duration_ms=50),
            ])
            codex = FakeRuntime([
                AgentRunResult(text="codex answer", provider_session_id="codex-thread-1", status="succeeded", duration_ms=50),
                AgentRunResult(text="codex continuation", provider_session_id="codex-thread-2", status="succeeded", duration_ms=50),
            ])
            project = {"slug": "mbpass", "workspace": str(workspace)}
            from unittest.mock import patch

            with patch("agents.dylan.autonomous.resolve_project", return_value=project), patch(
                "agents.dylan.autonomous.known_project_slugs", return_value={"mbpass"}
            ), patch("agents.dylan.autonomous.load_chat_project_map", return_value={}):
                first = handle_autonomous_conversation(
                    text="continue the risk review",
                    meta={"chat_id": "oc1", "chat_type": "p2p", "thread_id": "t1", "user_id": "u1", "message_id": "m1"},
                    common=_v4_common("cursor_cli"),
                    runtime=cursor,
                )
                switched = handle_autonomous_conversation(
                    text="continue with the latest evidence",
                    meta={"chat_id": "oc1", "chat_type": "p2p", "thread_id": "t1", "user_id": "u1", "message_id": "m2"},
                    common=_v4_common("codex"),
                    runtime=codex,
                )
                resumed = handle_autonomous_conversation(
                    text="now summarize the conclusion",
                    meta={"chat_id": "oc1", "chat_type": "p2p", "thread_id": "t1", "user_id": "u1", "message_id": "m3"},
                    common=_v4_common("codex"),
                    runtime=codex,
                )

            self.assertEqual("ok", first["status"])
            self.assertEqual("ok", switched["status"])
            self.assertEqual("ok", resumed["status"])
            self.assertIsNone(cursor.calls[0]["provider_session_id"])
            self.assertIsNone(codex.calls[0]["provider_session_id"])
            self.assertIn("LUMON PROVIDER SWITCH HANDOFF", codex.calls[0]["prompt"])
            self.assertIn("cursor answer", codex.calls[0]["prompt"])
            self.assertEqual("codex-thread-1", codex.calls[1]["provider_session_id"])
            self.assertEqual("codex-thread-2", resumed["provider_session_id"])

            store = SessionStore(GlobalAgentStore(Path(tmp) / "agents.sqlite3"))
            scope = conversation_scope_id(chat_id="oc1", thread_id="t1", project_slug="mbpass")
            active = store.get_active(agent_id="dylan", conversation_scope_id=scope)
            self.assertIsNotNone(active)
            assert active is not None
            self.assertEqual("codex", active["provider"])
            self.assertEqual("codex-thread-2", active["provider_session_id"])
            self.assertEqual(2, len(store.list_sessions(agent_id="dylan")))
            store.close()

    def test_stateless_provider_keeps_a_checkpoint_for_the_next_turn(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            (workspace / "config").mkdir()
            (workspace / "config" / "common.json").write_text('{"project":{"slug":"mbpass"}}', encoding="utf-8")
            fake = StatelessFakeRuntime([
                AgentRunResult(text="first stateless answer", provider_session_id="", status="succeeded", duration_ms=50),
                AgentRunResult(text="second stateless answer", provider_session_id="", status="succeeded", duration_ms=50),
            ])
            project = {"slug": "mbpass", "workspace": str(workspace)}
            from unittest.mock import patch

            with patch("agents.dylan.autonomous.resolve_project", return_value=project), patch(
                "agents.dylan.autonomous.known_project_slugs", return_value={"mbpass"}
            ), patch("agents.dylan.autonomous.load_chat_project_map", return_value={}):
                handle_autonomous_conversation(
                    text="remember this result",
                    meta={"chat_id": "oc2", "chat_type": "p2p", "thread_id": "t2", "user_id": "u1", "message_id": "m1"},
                    common=_v4_common("openai-compatible"),
                    runtime=fake,
                )
                handle_autonomous_conversation(
                    text="continue from that result",
                    meta={"chat_id": "oc2", "chat_type": "p2p", "thread_id": "t2", "user_id": "u1", "message_id": "m2"},
                    common=_v4_common("openai-compatible"),
                    runtime=fake,
                )

            self.assertIsNone(fake.calls[1]["provider_session_id"])
            self.assertIn("LUMON SESSION CHECKPOINT", fake.calls[1]["prompt"])
            self.assertIn("first stateless answer", fake.calls[1]["prompt"])


class UserFacingErrorTests(unittest.TestCase):
    def test_hides_raw_stream_error(self) -> None:
        from agents.dylan.autonomous import _user_facing_agent_error

        text = _user_facing_agent_error("no result event in stream-json", "tr_abc")
        self.assertNotIn("stream-json", text)
        self.assertIn("tr_abc", text)

    def test_cursor_api_error(self) -> None:
        from agents.dylan.autonomous import _user_facing_agent_error

        text = _user_facing_agent_error("Failed to reach the Cursor API", "tr_x")
        self.assertIn("Cursor Agent service", text)

    def test_model_quota_error_is_actionable(self) -> None:
        from agents.dylan.autonomous import _user_facing_agent_error

        text = _user_facing_agent_error("Cursor monthly usage limit reached", "tr_quota")
        self.assertIn("usage quota", text)
        self.assertIn("Nothing was sent to Jira", text)
        self.assertNotIn("/new", text)

    def test_missing_model_key_is_actionable(self) -> None:
        from agents.dylan.autonomous import _user_facing_agent_error

        text = _user_facing_agent_error("deepseek API key is not configured (DEEPSEEK_API_KEY)", "tr_key")
        self.assertIn("DEEPSEEK_API_KEY", text)
        self.assertIn("~/.lumon/.env.local", text)


class ReplyAnchorTests(unittest.TestCase):
    def test_format_anchor_overrides_latest_topic(self) -> None:
        from agents.dylan.reply_anchor import format_anchored_user_message, extract_content_text, remember_outbound, lookup_outbound
        import tempfile
        from unittest.mock import patch

        text = format_anchored_user_message(
            user_message="按你的建議來",
            parent_id="om_a",
            anchor_text="建議：保持 MBPAS-1559 Open，等下次 scan 驗證。",
        )
        self.assertIn("FEISHU REPLY ANCHOR", text)
        self.assertIn("MBPAS-1559", text)
        self.assertIn("按你的建議來", text)
        self.assertIn("PRIOR message", text)

        card = {
            "schema": "2.0",
            "body": {"elements": [{"tag": "markdown", "content": "## 決定\n保持 Open"}]},
        }
        extracted = extract_content_text("interactive", json.dumps(card, ensure_ascii=False))
        self.assertIn("保持 Open", extracted)

        with tempfile.TemporaryDirectory() as tmp:
            with patch("agents.dylan.reply_anchor.agents_home", return_value=Path(tmp)):
                remember_outbound(
                    message_id="om_x",
                    text="suggestion A about webhook",
                    reply_to="om_user",
                    thread_id="omt_1",
                )
                self.assertEqual(lookup_outbound("om_x"), "suggestion A about webhook")
                from agents.dylan.reply_anchor import is_dylan_thread_context

                self.assertTrue(is_dylan_thread_context(parent_id="om_x"))
                self.assertTrue(is_dylan_thread_context(root_id="om_user"))
                self.assertTrue(is_dylan_thread_context(thread_id="omt_1"))
                self.assertFalse(is_dylan_thread_context(parent_id="om_other"))


if __name__ == "__main__":
    unittest.main()
