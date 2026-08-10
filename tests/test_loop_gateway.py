#!/usr/bin/env python3
from __future__ import annotations

import os
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.definitions import ensure_definitions_loaded, get_definition
from agents.runtime.autonomous import handle_autonomous_conversation
from agents.runtime.cursor_runtime import AgentRunResult, CursorAgentRuntime
from agents.runtime.loop_intent import classify_loop_intent, loop_gateway_prompt
from agents.dylan.permission_policy import LOOP_PERMISSIONS
from agents.profiles import PROFILES
from feishu.client_registry import FeishuClientConfig
from feishu.handlers import should_handle


class FakeRuntime(CursorAgentRuntime):
    def __init__(self, results: list[AgentRunResult]) -> None:
        super().__init__(model="fake")
        self.results = list(results)
        self.calls: list[dict[str, str]] = []

    def run(self, *, workspace, prompt, provider_session_id=None, trace=None, obs=None):  # type: ignore[override]
        self.calls.append({"workspace": str(workspace), "prompt": prompt, "provider_session_id": provider_session_id or ""})
        return self.results.pop(0)


def _common() -> dict:
    return {
        "project": {"slug": "mbpass"},
        "agents": {
            "mark": {
                "conversation_v4": {
                    "enabled": True,
                    "mode": "autonomous_workspace",
                    "provider": {"type": "cursor_cli", "model": "fake-model"},
                    "session": {"scope": "thread_shared"},
                }
            }
        },
    }


class LoopGatewayTests(unittest.TestCase):
    def test_loop_permissions_only_open_planning_documents(self) -> None:
        allow = LOOP_PERMISSIONS["permissions"]["allow"]
        deny = LOOP_PERMISSIONS["permissions"]["deny"]
        self.assertIn("Write(topics/**)", allow)
        self.assertIn("Write(stories/**)", allow)
        self.assertIn("Write(repos/**)", deny)
        self.assertIn("Write(**/*.py)", deny)
        self.assertIn("Shell(git add)", deny)

    def test_classifies_natural_business_and_technical_entries(self) -> None:
        business = classify_loop_intent("把这段讨论整理成一个需求")
        technical = classify_loop_intent("Please turn this requirement into a technical plan")
        self.assertEqual(("business", "direct"), (business.loop, business.decision))
        self.assertEqual(("technical", "direct"), (technical.loop, technical.decision))

    def test_ambiguous_entry_needs_confirmation_but_explanation_does_not(self) -> None:
        ambiguous = classify_loop_intent("这个需求我们梳理一下")
        explanation = classify_loop_intent("什么是 Business Loop？")
        self.assertEqual(("business", "confirm"), (ambiguous.loop, ambiguous.decision))
        self.assertEqual("none", explanation.decision)
        self.assertIn("confirmation", loop_gateway_prompt(ambiguous).lower())

    def test_pending_loop_confirmation_resolves_number(self) -> None:
        pending = {"mode": "loop_confirmation", "loop": "business"}
        self.assertEqual("business", classify_loop_intent("1", pending=pending).loop)
        self.assertEqual("direct", classify_loop_intent("1", pending=pending).decision)
        self.assertEqual("decline", classify_loop_intent("2", pending=pending).decision)

    def test_mark_is_default_group_front_door_for_loop_entries(self) -> None:
        mark = FeishuClientConfig("mark", "cli_mark", "secret", PROFILES["mark"])
        dylan = FeishuClientConfig("dylan", "cli_dylan", "secret", PROFILES["dylan"])
        event = {
            "event": {
                "message": {
                    "chat_type": "group",
                    "mentions": [],
                    "content": '{"text":"把这个想法转换成一个需求"}',
                }
            }
        }
        self.assertTrue(should_handle(event, mark))
        self.assertFalse(should_handle(event, dylan))

    def test_agent_owns_loop_decision_and_continues_same_session(self) -> None:
        ensure_definitions_loaded()
        mark = get_definition("mark")
        assert mark is not None
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp)
            (docs / "stories").mkdir()
            previous = os.environ.get("LUMEN_AGENTS_HOME")
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            runtime = FakeRuntime(
                [
                    AgentRunResult(
                        text=(
                            '<CONVERSATION_DECISION>{"mode":"clarify","route":"business_loop",'
                            '"active_loop":"business","confidence":0.78}</CONVERSATION_DECISION>'
                            '<CLARIFICATION_REQUEST>{"action":"loop.start","mode":"grill",'
                            '"loop":"business","question":"要不要开始 Business Loop？",'
                            '"missing":["loop"],"choices":[{"value":"business","label":"开始 Business Loop"},'
                            '{"value":"decline","label":"先不启动"}]}</CLARIFICATION_REQUEST>'
                        ),
                        provider_session_id="provider-mark",
                        status="succeeded",
                    ),
                    AgentRunResult(
                        text=(
                            '<CONVERSATION_DECISION>{"mode":"continue_pending","route":"business_loop",'
                            '"active_loop":"business","confidence":1}</CONVERSATION_DECISION>'
                            '<FINAL_RESPONSE>Business Loop started.</FINAL_RESPONSE>'
                        ),
                        provider_session_id="provider-mark",
                        status="succeeded",
                    ),
                ]
            )
            definition = replace(
                mark,
                resolve_workspace=lambda project_slug, chat_id: ("mbpass", docs.resolve()),
                ensure_workspace_contract=lambda **kwargs: docs,
            )
            meta = {"chat_id": "oc1", "thread_id": "omt1", "user_id": "ou1", "message_id": "om1"}
            try:
                with mock.patch("agents.runtime.autonomous.resolve_project", return_value={"slug": "mbpass", "workspace": str(docs)}):
                    with mock.patch("agents.runtime.autonomous.known_project_slugs", return_value={"mbpass"}):
                        with mock.patch("agents.runtime.autonomous.load_chat_project_map", return_value={}):
                            first = handle_autonomous_conversation(
                                definition=definition,
                                text="这个需求我们梳理一下",
                                meta=meta,
                                common=_common(),
                                runtime=runtime,
                            )
                            second = handle_autonomous_conversation(
                                definition=definition,
                                text="1",
                                meta={**meta, "message_id": "om2"},
                                common=_common(),
                                runtime=runtime,
                            )
                self.assertEqual("autonomous.clarification", first["action"])
                self.assertEqual("business", first["pending_clarification"]["loop"])
                self.assertEqual(2, len(runtime.calls))
                self.assertEqual("ok", second["status"])
                self.assertEqual("provider-mark", runtime.calls[1]["provider_session_id"])
                self.assertIn("CONVERSATION_DECISION", runtime.calls[0]["prompt"])
                self.assertNotIn("[LUMEN LOOP GATEWAY]", runtime.calls[0]["prompt"])
                profile = json.loads((docs / ".cursor" / "cli.json").read_text(encoding="utf-8"))
                self.assertIn("Write(**)", profile["permissions"]["deny"])
                self.assertNotIn("Write(stories/**)", profile["permissions"]["allow"])
            finally:
                if previous is None:
                    os.environ.pop("LUMEN_AGENTS_HOME", None)
                else:
                    os.environ["LUMEN_AGENTS_HOME"] = previous


if __name__ == "__main__":
    unittest.main()
