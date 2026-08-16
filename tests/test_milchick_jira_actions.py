#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.definitions import ensure_definitions_loaded, get_definition
from agents.security.actions import JIRA_ACTIONS, ActionRequest
from agents.security.broker import CapabilityBroker, default_executors
from agents.security.policy import is_action_allowed_for_agent
from agents.runtime.final_response import prefer_action_summary


class JiraActionTests(unittest.TestCase):
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

    def test_get_workitem_accepts_twg_data_list(self) -> None:
        from agents.security.adapters import jira as jira_adapter

        twg_output = (
            '{"apiVersion":"v2","command":"jira.workitem.get","request":{"issueIdOrKey":"MBPAS-1503"},'
            '"data":[{"key":"MBPAS-1503","fields":{"summary":"【文章】新增「猜你喜歡」推薦模塊",'
            '"status":{"name":"To Do"},"issuetype":{"name":"Story"}}}]}'
        )
        with mock.patch.object(jira_adapter, "_jira_config", return_value={"project_key": "MBPAS"}):
            with mock.patch("jira_sync.twg_ready", return_value=(True, "")):
                with mock.patch("jira_sync.run_twg", return_value=(0, twg_output)):
                    with mock.patch("jira_sync.site_args", return_value=[]):
                        result = jira_adapter.execute_jira_action(
                            ActionRequest(
                                agent_id="milchick",
                                action="jira.workitem.get",
                                project_slug="mbpass",
                                actor_user_id="ou_1",
                                chat_id="oc_1",
                                thread_id="",
                                source_message_id="om_1",
                                trace_id="tr_1",
                                resource={},
                                arguments={"issue_key": "MBPAS-1503"},
                            )
                        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["issue_key"], "MBPAS-1503")
        self.assertEqual(result["issue_status"], "To Do")
        self.assertIn("猜你喜歡", result["summary"])

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

    def test_create_adapter_assigns_new_issue_to_active_sprint_by_workspace_default(self) -> None:
        from agents.security.adapters import jira as jira_adapter

        with mock.patch.object(
            jira_adapter,
            "_jira_config",
            return_value={
                "project_key": "MBPAS",
                "issue_type": "Task",
                "board_id": "42",
                "assign_to_active_sprint": True,
            },
        ):
            with mock.patch("jira_sync.twg_ready", return_value=(True, "")):
                with mock.patch("jira_sync.resolve_active_sprint", return_value=("7", "Sprint 7")):
                    with mock.patch("jira_sync.assign_workitem_to_sprint") as assign:
                        with mock.patch(
                            "jira_sync.run_twg",
                            return_value=(0, '{"key":"MBPAS-2002"}'),
                        ) as run:
                            with mock.patch(
                                "jira_sync.parse_issue_key",
                                return_value=("MBPAS-2002", "https://example.atlassian.net/browse/MBPAS-2002"),
                            ):
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
                                            trace_id="tr_2",
                                            arguments={"summary": "Sprint task"},
                                        )
                                    )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["sprint_id"], "7")
        self.assertEqual(result["sprint_name"], "Sprint 7")
        assign.assert_called_once_with("MBPAS-2002", "7", mock.ANY)
        self.assertEqual(run.call_args.args[0][:3], ["jira", "workitem", "create"])

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

    def test_structured_jira_mutation_is_open_for_all_agents(self) -> None:
        config = {
            "access": {
                "allowed_user_ids": ["ou_owner"],
                "allowed_chat_ids": ["oc1"],
                "mutation_allowed_user_ids": ["ou_owner"],
                "agents": {agent_id: {} for agent_id in ("dylan", "mark", "milchick", "irving")},
            }
        }
        broker = CapabilityBroker(
            config=config,
            executors={"jira.workitem.create": lambda request: {"status": "completed"}},
        )
        for agent_id in ("dylan", "mark", "milchick", "irving"):
            receipt = broker.execute(
                ActionRequest(
                    agent_id=agent_id,
                    action="jira.workitem.create",
                    project_slug="mbpass",
                    actor_user_id="ou_owner",
                    chat_id="oc1",
                    thread_id="omt1",
                    source_message_id="om1",
                    trace_id=f"tr_{agent_id}",
                    arguments={"chat_type": "group", "summary": "Version bump"},
                )
            )
            self.assertEqual("succeeded", receipt.status, agent_id)

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
