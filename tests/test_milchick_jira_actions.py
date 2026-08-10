#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.definitions import ensure_definitions_loaded, get_definition
from agents.security.access_policy import classify_authorization_intent
from agents.security.actions import JIRA_ACTIONS, ActionRequest
from agents.security.broker import CapabilityBroker, default_executors
from agents.security.policy import is_action_allowed_for_agent
from agents.runtime.final_response import prefer_action_summary


class JiraActionTests(unittest.TestCase):
    def test_intent_create_jira_card(self) -> None:
        self.assertEqual(
            classify_authorization_intent("Please create the jira card for this issue"),
            "mutate_explicit",
        )
        self.assertEqual(classify_authorization_intent("update jira MBPAS-1 summary"), "mutate_explicit")
        self.assertEqual(classify_authorization_intent("how's MBPAS-1491 going?"), "read")

    def test_all_agents_have_the_same_jira_action_surface(self) -> None:
        for agent_id in ("dylan", "mark", "milchick", "irving"):
            for action in JIRA_ACTIONS:
                self.assertTrue(is_action_allowed_for_agent(agent_id, action), (agent_id, action))
        executors = default_executors()
        for action in JIRA_ACTIONS:
            self.assertIn(action, executors)

    def test_definition_lists_jira_actions(self) -> None:
        ensure_definitions_loaded()
        milchick = get_definition("milchick")
        assert milchick is not None
        self.assertIn("jira.workitem.create", milchick.capabilities.actions)
        self.assertIn("jira.workitem.update", milchick.capabilities.allowed_mutations)

    def test_untested_report_uses_host_twg(self) -> None:
        from agents.security.adapters import jira as jira_adapter

        with mock.patch.object(jira_adapter, "_jira_config", return_value={"project_key": "MBPAS", "board_id": "42"}):
            with mock.patch("jira_sync.twg_ready", return_value=(True, "")):
                with mock.patch("jira_sync.resolve_active_sprint", return_value=("7", "Sprint 7")):
                    with mock.patch(
                        "jira_sync.run_twg",
                        return_value=(0, '{"data":{"issues":[{"key":"MBPAS-1","fields":{"summary":"QA","status":{"name":"Ready for QA"}}}]}}'),
                    ) as run:
                        with mock.patch("jira_sync.parse_twg_json", return_value={"data": {"issues": [{"key": "MBPAS-1", "fields": {"summary": "QA", "status": {"name": "Ready for QA"}}}]}}):
                            with mock.patch("jira_sync.site_args", return_value=[]):
                                result = jira_adapter.execute_jira_action(
                                    ActionRequest(
                                        agent_id="milchick",
                                        action="jira.sprint.untested.report",
                                        project_slug="mbpass",
                                        actor_user_id="ou_1",
                                        chat_id="oc_1",
                                        thread_id="",
                                        source_message_id="om_1",
                                        trace_id="tr_1",
                                        resource={"project_key": "MBPAS"},
                                        arguments={"standard": "1"},
                                    )
                                )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"][0]["issue_key"], "MBPAS-1")
        self.assertIn("jira", run.call_args.args[0])
        self.assertIn("Ready for QA", run.call_args.args[0][run.call_args.args[0].index("--jql") + 1])

    def test_format_sprint_report_summary(self) -> None:
        text = prefer_action_summary(
            "I will check the sprint.",
            [
                {
                    "action": "jira.sprint.untested.report",
                    "status": "succeeded",
                    "result": {
                        "status": "completed",
                        "sprint_name": "Sprint 7",
                        "count": 1,
                        "items": [{"issue_key": "MBPAS-1", "summary": "QA", "status": "Ready for QA"}],
                    },
                }
            ],
        )
        self.assertIn("Sprint 7", text)
        self.assertIn("MBPAS-1", text)

    def test_create_adapter_uses_twg(self) -> None:
        from agents.security.adapters import jira as jira_adapter

        with mock.patch.object(jira_adapter, "_jira_config", return_value={"project_key": "MBPAS", "issue_type": "Bug"}):
            with mock.patch("jira_sync.twg_ready", return_value=(True, "")):
                with mock.patch(
                    "jira_sync.run_twg",
                    return_value=(0, '{"key":"MBPAS-2001","self":"https://example.atlassian.net/browse/MBPAS-2001"}'),
                ) as run:
                    with mock.patch("jira_sync.parse_issue_key", return_value=("MBPAS-2001", "https://example.atlassian.net/browse/MBPAS-2001")):
                        with mock.patch("jira_sync.jira_browse_url_from_config", return_value="https://example.atlassian.net/browse/MBPAS-2001"):
                            with mock.patch("jira_sync.site_args", return_value=[]):
                                result = jira_adapter.execute_jira_action(
                                    ActionRequest(
                                        agent_id="milchick",
                                        action="jira.workitem.create",
                                        project_slug="mbpass",
                                        actor_user_id="ou_1",
                                        chat_id="oc_1",
                                        thread_id="",
                                        source_message_id="om_1",
                                        trace_id="tr_1",
                                        arguments={
                                            "summary": "Preview mismatch",
                                            "description": "Backend preview != APP",
                                            "target_version": "2.4.0",
                                        },
                                    )
                                )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["issue_key"], "MBPAS-2001")
        self.assertIn("https://", result["url"])
        cmd = run.call_args[0][0]
        self.assertEqual(cmd[:3], ["jira", "workitem", "create"])
        self.assertIn("--summary", cmd)
        self.assertIn("Preview mismatch", cmd)
        self.assertIn("Target version: 2.4.0", " ".join(cmd))
        self.assertEqual("2.4.0", result["target_version"])

    def test_update_adapter_requires_fields(self) -> None:
        from agents.security.adapters import jira as jira_adapter
        from agents.security.errors import ResourceDenied

        with self.assertRaises(ResourceDenied):
            jira_adapter.execute_jira_action(
                ActionRequest(
                    agent_id="milchick",
                    action="jira.workitem.update",
                    project_slug="mbpass",
                    actor_user_id="ou_1",
                    chat_id="oc_1",
                    thread_id="",
                    source_message_id="om_1",
                    trace_id="tr_1",
                    arguments={"issue_key": "MBPAS-1"},
                )
            )

    def test_prefer_summary_for_jira_create(self) -> None:
        receipts = [
            {
                "action": "jira.workitem.create",
                "status": "succeeded",
                "result": {
                    "status": "completed",
                    "issue_key": "MBPAS-2001",
                    "summary": "Preview mismatch",
                    "url": "https://example.atlassian.net/browse/MBPAS-2001",
                },
            }
        ]
        text = prefer_action_summary("I'll create the card now.", receipts)
        self.assertIn("Created MBPAS-2001: Preview mismatch", text)
        self.assertIn("https://example.atlassian.net/browse/MBPAS-2001", text)
        self.assertNotIn("I'll create", text)

    def test_jira_shortcut_parses_anchor_and_creates(self) -> None:
        from agents.milchick.jira_shortcut import summary_and_description, try_milchick_jira_create, wants_jira_create
        from agents.security.actions import ActionReceipt
        from agents.security.trusted import TrustedActionContext

        self.assertTrue(wants_jira_create("Please create the jira card for this issue"))
        anchored = (
            "[FEISHU REPLY ANCHOR]\nPrior message content:\n-----\n"
            + json.dumps(
                {
                    "title": "回覆：<問題反饋> 直視精選的後台預覽與前台完全不符合",
                    "elements": [[{"tag": "text", "text": "Backend preview is wrong."}]],
                },
                ensure_ascii=False,
            )
            + "\n-----\n\n[USER REPLY]\nPlease create the jira card for this issue\n"
        )
        summary, description = summary_and_description(
            user_text="Please create the jira card for this issue",
            anchored_text=anchored,
        )
        self.assertIn("直視精選", summary)
        self.assertIn("Backend preview", description)

        class FakeBroker:
            def execute(self, request):
                self.request = request
                return ActionReceipt(
                    receipt_id="act-1",
                    status="succeeded",
                    action=request.action,
                    agent_id=request.agent_id,
                    actor=request.actor_user_id,
                    resource=request.resource,
                    trace_id=request.trace_id,
                    executed_at="now",
                    result={
                        "status": "completed",
                        "issue_key": "MBPAS-2100",
                        "summary": request.arguments.get("summary"),
                        "url": "https://example.atlassian.net/browse/MBPAS-2100",
                    },
                )

        broker = FakeBroker()

        def fake_designer(prompt: str) -> str:
            self.assertIn("Investigate the workspace", prompt)
            return json.dumps(
                {
                    "summary": "Featured vertical preview mismatches APP crop",
                    "issue_type": "Bug",
                    "priority": "Medium",
                    "labels": ["feishu-feedback"],
                    "problem": "Admin featured preview does not match APP crop rules.",
                    "expected": "Preview reflects APP crop (24px sides, 228px text band).",
                    "actual": "Preview shows full image only.",
                    "steps_to_reproduce": ["Open admin featured editor", "Click preview"],
                    "acceptance_criteria": ["Preview matches APP crop guide"],
                    "workspace_findings": ["admin featured preview component"],
                    "suggested_fix": "Align preview overlay with APP crop constants.",
                },
                ensure_ascii=False,
            )

        out = try_milchick_jira_create(
            user_text="Please create the jira card for this issue",
            anchored_text=anchored,
            context=TrustedActionContext(
                agent_id="milchick",
                project_slug="mbpass",
                actor_user_id="ou_1",
                chat_id="oc_1",
                thread_id="omt_1",
                source_message_id="om_1",
                trace_id="tr_1",
                authorization_intent="mutate_explicit",
                explicit_authorization=True,
            ),
            broker=broker,
            workspace=Path("."),
            designer_runner=fake_designer,
        )
        assert out is not None
        self.assertEqual(out["status"], "ok")
        self.assertIn("MBPAS-2100", out["text"])
        self.assertEqual(broker.request.action, "jira.workitem.create")
        self.assertIn("## Problem", broker.request.arguments["description"])
        self.assertIn("Workspace findings", broker.request.arguments["description"])
        self.assertNotEqual(broker.request.arguments["description"], "Backend preview is wrong.")
        self.assertTrue(out["flags"]["jira_drafted"])
        self.assertEqual(broker.request.arguments["summary"], "Featured vertical preview mismatches APP crop")

    def test_format_issue_description_keeps_source(self) -> None:
        from agents.milchick.jira_designer import format_issue_description

        text = format_issue_description(
            {
                "problem": "Preview mismatch",
                "expected": "Match APP",
                "actual": "Full image",
                "steps_to_reproduce": ["Open preview"],
                "acceptance_criteria": ["Overlay matches crop"],
                "workspace_findings": ["featured-example.png guide"],
            },
            source_title="原邮件标题",
            source_body="raw email body",
        )
        self.assertIn("## Problem", text)
        self.assertIn("## Source feedback", text)
        self.assertIn("raw email body", text)

    def test_jira_retry_in_traditional_chinese_is_explicit_and_reports_result(self) -> None:
        from agents.milchick.jira_shortcut import try_milchick_jira_create, wants_jira_create
        from agents.security.actions import ActionReceipt
        from agents.security.trusted import TrustedActionContext

        user_text = (
            "jira.workitem.create was not executed: mutation denied for zone=RESTRICTED intent=read\n"
            "這個問題請再試試看是不是已修復\n"
            "另外版本號請基於既有的升級一個 minor 即可"
        )
        self.assertTrue(wants_jira_create(user_text))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "repos" / "digital-platform-admin" / "public"
            config.mkdir(parents=True)
            (config / "config.js").write_text("VERSION: '1.1.0'", encoding="utf-8")

            class FakeBroker:
                def execute(self, request):
                    self.request = request
                    return ActionReceipt(
                        receipt_id="act-retry",
                        status="succeeded",
                        action=request.action,
                        agent_id=request.agent_id,
                        actor=request.actor_user_id,
                        resource=request.resource,
                        trace_id=request.trace_id,
                        executed_at="now",
                        result={
                            "status": "completed",
                            "issue_key": "MBPAS-2200",
                            "summary": request.arguments["summary"],
                            "url": "https://example.atlassian.net/browse/MBPAS-2200",
                        },
                    )

            broker = FakeBroker()
            out = try_milchick_jira_create(
                user_text=user_text,
                anchored_text=user_text,
                context=TrustedActionContext(
                    agent_id="milchick",
                    project_slug="mbpass",
                    actor_user_id="ou_1",
                    chat_id="oc_1",
                    thread_id="omt_1",
                    source_message_id="om_1",
                    trace_id="tr_retry",
                    authorization_intent="read",
                ),
                broker=broker,
                workspace=root,
                designer_runner=lambda prompt: json.dumps(
                    {"summary": "Upgrade Admin Portal displayed version", "issue_type": "Task"}
                ),
            )

        assert out is not None
        self.assertEqual("ok", out["status"])
        self.assertIn("MBPAS-2200", out["text"])
        self.assertIn("https://example.atlassian.net/browse/MBPAS-2200", out["text"])
        self.assertTrue(broker.request.explicit_authorization)
        self.assertEqual("mutate_explicit", broker.request.arguments["_authorization_intent"])
        self.assertEqual("1.2.0", broker.request.arguments["target_version"])
        self.assertIn("Current displayed version: 1.1.0", broker.request.arguments["description"])

    def test_failed_jira_receipt_reports_reason(self) -> None:
        text = prefer_action_summary(
            "The Jira task is being created.",
            [
                {
                    "action": "jira.workitem.create",
                    "status": "failed",
                    "error": "twg CLI returned exit 1",
                    "error_code": "EXECUTOR_ERROR",
                }
            ],
        )
        self.assertIn("Action failed", text)
        self.assertIn("twg CLI returned exit 1", text)

    def test_broker_denies_dylan(self) -> None:
        receipt = CapabilityBroker(config={"access": {"mutation_allowed_user_ids": ["ou_owner"]}}).execute(
            ActionRequest(
                agent_id="dylan",
                action="jira.workitem.create",
                project_slug="mbpass",
                actor_user_id="ou_owner",
                chat_id="oc1",
                thread_id="",
                source_message_id="om1",
                trace_id="tr1",
                arguments={"summary": "x"},
                explicit_authorization=True,
            )
        )
        self.assertEqual(receipt.status, "denied")


if __name__ == "__main__":
    unittest.main()
