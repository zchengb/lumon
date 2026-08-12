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

from agents.milchick.definition import MILCHICK_DEFINITION
from agents.runtime.autonomous import _serialize_repeated_actions, handle_autonomous_conversation
from agents.runtime.cursor_runtime import AgentRunResult, CursorAgentRuntime
from agents.security.actions import ActionReceipt


class FakeRuntime(CursorAgentRuntime):
    def __init__(self, results: list[AgentRunResult]) -> None:
        super().__init__(model="fake")
        self.results = list(results)
        self.calls: list[dict[str, object]] = []

    def run(self, *, workspace, prompt, provider_session_id=None, trace=None, obs=None):  # type: ignore[override]
        self.calls.append(
            {
                "workspace": str(workspace),
                "prompt": prompt,
                "provider_session_id": provider_session_id,
            }
        )
        return self.results.pop(0)


def _receipt(action: str, result: dict, *, resource: dict | None = None) -> ActionReceipt:
    return ActionReceipt(
        receipt_id=f"act-{action.replace('.', '-')}",
        status="succeeded",
        action=action,
        agent_id="milchick",
        actor="ou_owner",
        resource=dict(resource or {}),
        trace_id="tr_flow",
        executed_at="2026-08-11T00:00:00Z",
        result=result,
    )


def _common() -> dict:
    return {
        "project": {"slug": "mbpass"},
        "agents": {
            "milchick": {
                "conversation_v4": {
                    "enabled": True,
                    "mode": "autonomous_workspace",
                    "provider": {"type": "cursor_cli", "model": "fake-model"},
                    "session": {"scope": "thread_shared"},
                }
            }
        },
    }


class MilchickTestCaseFlowTests(unittest.TestCase):
    def test_repeated_test_case_actions_are_serialized(self) -> None:
        requests = [
            {"action": "test_case.generate", "arguments": {"issue_key": "MBPAS-1"}},
            {"action": "test_case.generate", "arguments": {"issue_key": "MBPAS-2"}},
            {"action": "test_case.generate", "arguments": {"issue_key": "MBPAS-3"}},
        ]
        self.assertEqual([requests[0]], _serialize_repeated_actions(requests))

    def test_jira_results_return_to_milchick_for_per_item_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "stories").mkdir()
            previous_home = os.environ.get("LUMEN_AGENTS_HOME")
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            items = [
                {"issue_key": key, "summary": f"Story {key}", "status": "Ready for QA"}
                for key in ("MBPAS-1497", "MBPAS-1550", "MBPAS-1276", "MBPAS-1491")
            ]
            query = _receipt(
                "jira.sprint.untested.report",
                {"status": "completed", "count": 4, "items": items},
            )
            generated = [
                _receipt(
                    "test_case.generate",
                    {"status": "completed", "summary": f"Generated test cases for {item['issue_key']}"},
                    resource={"issue_key": item["issue_key"]},
                )
                for item in items
            ]
            action_turns = []
            for item in items:
                action_turns.append(
                    AgentRunResult(
                        text=(
                            '<CONVERSATION_DECISION>{"mode":"normal","route":"test_case_generation",'
                            '"completion_criteria":"one terminal result per eligible issue"}</CONVERSATION_DECISION>'
                            f'<FINAL_RESPONSE>正在处理 {item["issue_key"]}。</FINAL_RESPONSE>'
                            "<ACTION_REQUEST>"
                            + json.dumps(
                                {"action": "test_case.generate", "arguments": {"issue_key": item["issue_key"]}},
                                ensure_ascii=False,
                            )
                            + "</ACTION_REQUEST>"
                        ),
                        provider_session_id="sess-milchick",
                        status="succeeded",
                    )
                )
            runtime = FakeRuntime(
                [
                    AgentRunResult(
                        text=(
                            '<CONVERSATION_DECISION>{"mode":"normal","route":"test_case_generation",'
                            '"confidence":0.98}</CONVERSATION_DECISION>'
                            '<FINAL_RESPONSE>我先读取 Ready for QA 的 Story。</FINAL_RESPONSE>'
                            '<ACTION_REQUEST>{"action":"jira.sprint.untested.report",'
                            '"arguments":{"standard":"A"}}</ACTION_REQUEST>'
                        ),
                        provider_session_id="sess-milchick",
                        status="succeeded",
                    ),
                    *action_turns,
                    AgentRunResult(
                        text=(
                            '<CONVERSATION_DECISION>{"mode":"normal","route":"test_case_generation",'
                            '"completion_criteria":"one terminal result per eligible issue"}</CONVERSATION_DECISION>'
                            "<FINAL_RESPONSE>已为 4 张 Story 逐张生成测试用例。</FINAL_RESPONSE>"
                        ),
                        provider_session_id="sess-milchick",
                        status="succeeded",
                    ),
                ]
            )
            definition = replace(
                MILCHICK_DEFINITION,
                resolve_workspace=lambda project_slug, chat_id: ("mbpass", workspace),
                ensure_workspace_contract=lambda **kwargs: workspace,
            )
            calls = [[query], *[[item] for item in generated]]
            try:
                with mock.patch(
                    "agents.runtime.autonomous.resolve_project",
                    return_value={"slug": "mbpass", "workspace": str(workspace)},
                ):
                    with mock.patch("agents.runtime.autonomous.known_project_slugs", return_value={"mbpass"}):
                        with mock.patch("agents.runtime.autonomous.load_chat_project_map", return_value={}):
                            with mock.patch(
                                "agents.runtime.autonomous.execute_trusted_actions",
                                side_effect=calls,
                            ) as execute:
                                result = handle_autonomous_conversation(
                                    definition=definition,
                                    text="把 Jira 板子的 Ready For QA 对应的 Story 卡都生成测试用例",
                                    meta={
                                        "chat_id": "oc1",
                                        "chat_type": "group",
                                        "thread_id": "omt1",
                                        "user_id": "ou_owner",
                                        "message_id": "om1",
                                    },
                                    common=_common(),
                                    agents_config={
                                        "access": {
                                            "default_policy": "legacy_allow",
                                            "allowed_chat_ids": ["oc1"],
                                            "allowed_user_ids": ["ou_owner"],
                                            "mutation_allowed_user_ids": ["ou_owner"],
                                        }
                                    },
                                    runtime=runtime,
                                )
            finally:
                if previous_home is None:
                    os.environ.pop("LUMEN_AGENTS_HOME", None)
                else:
                    os.environ["LUMEN_AGENTS_HOME"] = previous_home

            self.assertEqual("ok", result["status"])
            self.assertEqual(5, execute.call_count)
            self.assertEqual(6, len(runtime.calls))
            self.assertIn("[LUMEN HOST ACTION RESULTS]", str(runtime.calls[1]["prompt"]))
            for index, item in enumerate(items, start=1):
                requests = execute.call_args_list[index].kwargs["requests"]
                self.assertEqual(1, len(requests))
                self.assertEqual(item["issue_key"], requests[0]["arguments"]["issue_key"])
            self.assertIn("MBPAS-1497", result["text"])
            self.assertIn("Generated test cases for MBPAS-1491", result["text"])

    def test_scoped_request_is_terminal_after_one_batch_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "stories").mkdir()
            previous_home = os.environ.get("LUMEN_AGENTS_HOME")
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            items = [
                {"issue_key": key, "summary": f"Story {key}", "status": "Ready for QA"}
                for key in ("MBPAS-1276",)
            ]
            generated = _receipt(
                "test_case.generate",
                {
                    "status": "completed",
                    "scope": "ready_for_qa",
                    "batch": True,
                    "summary": "Generated test cases for 1/1 Ready for QA Stories.\n- MBPAS-1276: completed",
                    "items": [{"issue_key": "MBPAS-1276", "status": "completed"}],
                },
            )
            runtime = FakeRuntime(
                [
                    AgentRunResult(
                        text=(
                            '<CONVERSATION_DECISION>{"mode":"normal","route":"test_case_generation",'
                            '"required_actions":["test_case.generate"]}</CONVERSATION_DECISION>'
                            '<ACTION_REQUEST>'
                            '{"action":"test_case.generate","arguments":{"scope":"ready_for_qa"}}'
                            '</ACTION_REQUEST>'
                        ),
                        provider_session_id="sess-milchick",
                        status="succeeded",
                    ),
                ]
            )
            definition = replace(
                MILCHICK_DEFINITION,
                resolve_workspace=lambda project_slug, chat_id: ("mbpass", workspace),
                ensure_workspace_contract=lambda **kwargs: workspace,
            )
            try:
                with mock.patch(
                    "agents.runtime.autonomous.resolve_project",
                    return_value={"slug": "mbpass", "workspace": str(workspace)},
                ):
                    with mock.patch("agents.runtime.autonomous.known_project_slugs", return_value={"mbpass"}):
                        with mock.patch("agents.runtime.autonomous.load_chat_project_map", return_value={}):
                            with mock.patch(
                                "agents.runtime.autonomous.execute_trusted_actions",
                                side_effect=[[generated]],
                            ) as execute:
                                result = handle_autonomous_conversation(
                                    definition=definition,
                                    text="把 Jira 板子的 Ready For QA 对应的 Story 卡都生成测试用例",
                                    meta={
                                        "chat_id": "oc1",
                                        "chat_type": "group",
                                        "thread_id": "omt1",
                                        "user_id": "ou_owner",
                                        "message_id": "om1",
                                    },
                                    common=_common(),
                                    agents_config={
                                        "access": {
                                            "default_policy": "legacy_allow",
                                            "allowed_chat_ids": ["oc1"],
                                            "allowed_user_ids": ["ou_owner"],
                                            "mutation_allowed_user_ids": ["ou_owner"],
                                        }
                                    },
                                    runtime=runtime,
                                )
            finally:
                if previous_home is None:
                    os.environ.pop("LUMEN_AGENTS_HOME", None)
                else:
                    os.environ["LUMEN_AGENTS_HOME"] = previous_home

            self.assertEqual("ok", result["status"])
            self.assertEqual(1, execute.call_count)
            self.assertEqual(1, len(runtime.calls))
            request = execute.call_args_list[0].kwargs["requests"][0]
            self.assertEqual("test_case.generate", request["action"])
            self.assertEqual("ready_for_qa", request["arguments"]["scope"])
            self.assertIn("Generated test cases for 1/1", result["text"])


if __name__ == "__main__":
    unittest.main()
