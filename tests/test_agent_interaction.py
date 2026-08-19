#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.runtime.final_response import extract_final_response
from agents.runtime.interaction import (
    action_missing_fields,
    clarification_choice_hint,
    clarification_has_rendered_choices,
    format_clarification_reply,
    interaction_contract_prompt,
    normalize_clarification,
    normalize_conversation_decision,
    version_upgrade_choices,
)
from agents.security.trusted import TrustedActionContext, bind_action_request, execute_trusted_actions
from agents.runtime.session_store import SessionStore, conversation_scope_id
from risk.store import GlobalAgentStore


class AgentInteractionTests(unittest.TestCase):
    def test_clarification_envelope_becomes_user_facing_question(self) -> None:
        parsed = extract_final_response(
            '<CLARIFICATION_REQUEST>{"action":"delivery.start","question":"Which Story should I start?","missing":["story"]}</CLARIFICATION_REQUEST>'
        )
        self.assertEqual("Which Story should I start?", parsed.text)
        self.assertEqual("delivery.start", parsed.clarification_request["action"])
        self.assertEqual([], parsed.action_requests)

    def test_conversation_decision_is_internal_metadata(self) -> None:
        parsed = extract_final_response(
            '<CONVERSATION_DECISION>{"mode":"new_request","route":"quick_change",'
            '"confidence":0.96,"supersede_pending":true}</CONVERSATION_DECISION>'
            '<FINAL_RESPONSE>我会处理这个小改动。</FINAL_RESPONSE>'
        )
        self.assertEqual("我会处理这个小改动。", parsed.text)
        self.assertEqual("new_request", parsed.conversation_decision["mode"])
        self.assertEqual("quick_change", parsed.conversation_decision["route"])
        decision = normalize_conversation_decision(
            {
                **parsed.conversation_decision,
                "required_actions": ["delivery.quick_change"],
                "completion_criteria": "a verified delivery result",
            },
            pending={"action": "jira.sprint.untested.report"},
        )
        assert decision is not None
        self.assertTrue(decision["supersede_pending"])
        self.assertAlmostEqual(0.96, decision["confidence"])
        self.assertEqual(["delivery.quick_change"], decision["required_actions"])
        self.assertEqual("a verified delivery result", decision["completion_criteria"])

    def test_unclosed_final_response_drops_internal_preamble_and_marker(self) -> None:
        parsed = extract_final_response(
            "User answered: 2A. Let me record these decisions in story.md.\n"
            "Decisions recorded in story.md.\n"
            "<FINAL_RESPONSE>已记录你的决定：后端推荐 API；UI 由你手动完成。"
        )
        self.assertEqual("已记录你的决定：后端推荐 API；UI 由你手动完成。", parsed.text)
        self.assertEqual("final_response_unclosed", parsed.mode)
        self.assertEqual("UNCLOSED_FINAL_RESPONSE", parsed.error_code)
        self.assertFalse(parsed.valid)

    def test_legacy_response_drops_compact_approval_progress_prefix(self) -> None:
        parsed = extract_final_response(
            "User approved (A). Let me update metadata.json and the plan's front matter."
            "**技術計畫已批准 ✅**（technicalStatus: approved）"
        )
        self.assertEqual("**技術計畫已批准 ✅**（technicalStatus: approved）", parsed.text)

    def test_dsml_protocol_markers_never_reach_feishu(self) -> None:
        parsed = extract_final_response(
            "執行失敗，請先修正表格。\n"
            "</| | DSML | | parameter>\n"
            "</| | DSML | | invoke>\n"
            "</| | DSML | | tool_calls>"
        )
        self.assertEqual("執行失敗，請先修正表格。", parsed.text)

    def test_action_requirements_detect_missing_target(self) -> None:
        self.assertEqual(["story"], action_missing_fields("delivery.start", arguments={}))
        self.assertEqual([], action_missing_fields("delivery.start", resource={"story": "MBPAS-1"}))
        self.assertEqual(["target_agent", "capability"], action_missing_fields("agent.job.create", arguments={}))
        self.assertEqual([], action_missing_fields("test_case.generate", arguments={"scope": "ready_for_qa"}))

    def test_legacy_action_alias_is_canonicalized(self) -> None:
        from agents.runtime.final_response import extract_action_requests

        parsed = extract_action_requests(
            '<ACTION_REQUEST>{"action":"create_job","arguments":{"target_agent":"mark","capability":"loop.technical"}}</ACTION_REQUEST>'
        )
        self.assertEqual("agent.job.create", parsed[0]["action"])

        legacy = extract_action_requests(
            '<ACTION_REQUEST>{"action":"jira.testcase.generate","arguments":{"scope":"ready_for_qa"}}</ACTION_REQUEST>'
        )
        self.assertEqual("test_case.generate", legacy[0]["action"])

    def test_action_catalog_is_referenced_instead_of_inlined(self) -> None:
        from agents.runtime.interaction import interaction_contract_prompt
        from agents.security.actions import ALL_ACTIONS

        prompt = interaction_contract_prompt(agent_id="milchick")
        self.assertIn("action-catalog.md", prompt)
        self.assertIn("exact canonical action names", prompt)
        self.assertIn("arguments shape", prompt)
        catalog = (ROOT / "lib" / "agents" / "action-catalog.md").read_text(encoding="utf-8")
        self.assertIn("`agent.job.create`", catalog)
        self.assertIn("`create_job`", catalog)
        self.assertIn('"target_agent":"mark"', catalog)
        self.assertIn("Put every model-selected input in `arguments`", catalog)
        self.assertIn("`target_files` is a JSON array", catalog)
        self.assertIn("twg jira workitem get", catalog)
        self.assertIn("twg jira workitem query", catalog)
        self.assertTrue(all(f"`{action}`" in catalog for action in ALL_ACTIONS))

    def test_pending_clarification_survives_session_reload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.environ.get("LUMEN_AGENTS_HOME")
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            store = GlobalAgentStore(Path(tmp) / "agents.sqlite3")
            try:
                sessions = SessionStore(store)
                scope = conversation_scope_id(agent_id="mark", chat_id="oc1", thread_id="omt1")
                session = sessions.create(
                    agent_id="mark",
                    chat_id="oc1",
                    conversation_scope_id=scope,
                    workspace_path=tmp,
                    project_slug="mbpass",
                )
                pending = normalize_clarification(
                    {"action": "delivery.start", "question": "Which Story?", "missing": ["story"]},
                    agent_id="mark",
                    source_message_id="om1",
                )
                assert pending is not None
                sessions.save_pending(session["session_id"], pending)
                loaded = sessions.get_pending(sessions.get(session["session_id"]))
                self.assertEqual("Which Story?", loaded["question"])
                sessions.clear_pending(session["session_id"])
                self.assertIsNone(sessions.get_pending(sessions.get(session["session_id"])))
            finally:
                store.close()
                if previous is None:
                    os.environ.pop("LUMEN_AGENTS_HOME", None)
                else:
                    os.environ["LUMEN_AGENTS_HOME"] = previous

    def test_grill_clarification_preserves_decision_context(self) -> None:
        pending = normalize_clarification(
            {
                "mode": "grill",
                "loop": "technical",
                "question": "Should this update be synchronous or queued?",
                "impact": "This changes timeout and retry behavior.",
                "why": "The existing endpoint is synchronous.",
                "recommended": "Keep it synchronous for the current volume.",
                "assumptions": ["No material increase in request volume."],
                "stop_condition": "Stop when execution mode and retry behavior are confirmed.",
                "question_number": 2,
                "question_budget": 3,
            },
            agent_id="mark",
        )
        assert pending is not None
        self.assertEqual("grill", pending["mode"])
        self.assertEqual("technical", pending["loop"])
        self.assertEqual(2, pending["question_number"])
        self.assertEqual(3, pending["question_budget"])
        self.assertEqual("Keep it synchronous for the current volume.", pending["recommended"])
        self.assertEqual(["No material increase in request volume."], pending["assumptions"])

    def test_version_choices_render_and_resolve_numeric_answers(self) -> None:
        choices = version_upgrade_choices("1.2.3")
        self.assertEqual(["1.2.4", "1.3.0", "2.0.0"], [item["value"] for item in choices])
        reply = format_clarification_reply("Which version should I use?", choices, "1.2.3")
        self.assertIn("Current version: 1.2.3", reply)
        self.assertIn("1.2.4", reply)
        self.assertIn("Recommended", reply)
        hint = clarification_choice_hint(
            "1",
            {"missing": ["target_version"], "choices": choices},
        )
        self.assertIn("value=1.2.4", hint)
        self.assertIn("target_version", hint)

    def test_version_choices_still_render_when_full_question_differs(self) -> None:
        choices = version_upgrade_choices("1.2.3")
        reply = format_clarification_reply(
            "Which version should I use?",
            choices,
            "1.2.3",
            full_question="Which version should I upgrade it to?",
        )
        self.assertIn("Which version should I use?", reply)
        self.assertIn("1.2.4", reply)

    def test_clarification_does_not_duplicate_agent_rendered_choices(self) -> None:
        choices = [
            {"value": "bug", "label": "A", "description": "Create Bug"},
            {"value": "story", "label": "B", "description": "Create Story"},
            {"value": "investigate", "label": "C", "description": "Investigate first"},
            {"value": "other", "label": "D", "description": "Other"},
        ]
        agent_text = "A. Create Bug\nB. Create Story\nC. Investigate first\nD. Other"
        self.assertTrue(clarification_has_rendered_choices(agent_text, choices))
        self.assertEqual(agent_text, format_clarification_reply(agent_text, choices))
        self.assertIn("自訂答案", format_clarification_reply("What should I do?", choices))

    def test_structured_clarification_preserves_grouped_choices(self) -> None:
        choices = [
            {"id": "1A", "label": "獨立收件人模型"},
            {"id": "1B", "label": "重用 event_tickets"},
            {"id": "2A", "label": "沿用現有容量假設"},
            {"id": "2B", "label": "提供明確容量要求"},
        ]
        answer_summary = "Evidence 已完成。請回复 `1A, 2A`。"
        full_question = (
            "Technical Loop 需要確認兩個決定：\n\n"
            "1. 參加名單如何建模？\n"
            "A. 建立獨立收件人資料\n"
            "B. 重用 event_tickets\n\n"
            "2. 名單規模是否有額外要求？\n"
            "A. 沿用現有容量假設\n"
            "B. 提供明確容量要求"
        )

        reply = format_clarification_reply(
            answer_summary,
            choices,
            full_question=full_question,
        )

        self.assertIn(answer_summary, reply)
        self.assertIn(full_question, reply)
        self.assertNotIn("建議選項（可回覆代號或完整值）：", reply)
        self.assertNotIn("You can also reply", reply)

    def test_compound_choice_reference_does_not_trigger_flat_options(self) -> None:
        choices = [
            {"id": "1A", "label": "獨立收件人模型"},
            {"id": "1B", "label": "重用 event_tickets"},
            {"id": "2A", "label": "沿用現有容量假設"},
            {"id": "2B", "label": "提供明確容量要求"},
        ]
        self.assertTrue(clarification_has_rendered_choices("請回复 `1A, 2A`。", choices))

    def test_agent_decision_keeps_pending_context_explicit(self) -> None:
        pending = normalize_clarification(
            {"action": "jira.sprint.untested.report", "question": "Which standard?", "missing": ["standard"]},
            agent_id="milchick",
        )
        assert pending is not None
        decision = normalize_conversation_decision(
            {"mode": "new_request", "route": "quick_change", "reason": "latest message is a wording change"},
            pending=pending,
        )
        assert decision is not None
        self.assertTrue(decision["supersede_pending"])
        self.assertEqual("quick_change", decision["route"])

    def test_trusted_context_does_not_infer_authorization_from_text(self) -> None:
        request = bind_action_request(
            context=TrustedActionContext(
                agent_id="milchick",
                project_slug="mbpass",
                actor_user_id="ou_owner",
                chat_id="oc1",
                thread_id="omt1",
                source_message_id="om1",
                trace_id="tr1",
                explicit_authorization=True,
            ),
            action="jira.workitem.create",
            arguments={"summary": "Version bump"},
        )
        self.assertNotIn("_authorization_intent", request.arguments)
        self.assertTrue(request.explicit_authorization)

    def test_job_handoff_injects_original_message_and_images(self) -> None:
        captured: dict[str, object] = {}

        class FakeBroker:
            def execute(self, request: object) -> object:
                captured["request"] = request
                return object()

        execute_trusted_actions(
            context=TrustedActionContext(
                agent_id="milchick",
                project_slug="mbpass",
                actor_user_id="ou_owner",
                chat_id="oc1",
                thread_id="omt1",
                source_message_id="om1",
                trace_id="tr1",
                user_message="Admin Portal 中的 Wording 改成多圖",
                image_keys='["img_v3"]',
            ),
            requests=[
                {
                    "action": "agent.job.create",
                    "arguments": {
                        "target_agent": "mark",
                        "capability": "delivery.quick_change",
                        "user_message": "wrong intermediate summary",
                    },
                }
            ],
            broker=FakeBroker(),
        )
        request = captured["request"]
        self.assertEqual("Admin Portal 中的 Wording 改成多圖", request.arguments["user_message"])
        self.assertEqual('["img_v3"]', request.arguments["image_keys"])

    def test_test_case_handoff_injects_original_message(self) -> None:
        captured: dict[str, object] = {}

        class FakeBroker:
            def execute(self, request: object) -> object:
                captured["request"] = request
                return object()

        execute_trusted_actions(
            context=TrustedActionContext(
                agent_id="milchick",
                project_slug="mbpass",
                actor_user_id="ou_owner",
                chat_id="oc1",
                thread_id="omt1",
                source_message_id="om1",
                trace_id="tr1",
                user_message="請生成測試用例",
            ),
            requests=[
                {
                    "action": "test_case.generate",
                    "arguments": {"scope": "ready_for_qa", "user_message": "wrong summary"},
                }
            ],
            broker=FakeBroker(),
        )
        request = captured["request"]
        self.assertEqual("請生成測試用例", request.arguments["user_message"])

    def test_interaction_contract_distinguishes_grill_from_quick_change(self) -> None:
        prompt = interaction_contract_prompt(agent_id="mark")
        self.assertIn("[LUMON INTERACTION CONTRACT]", prompt)
        self.assertIn("READ the interaction protocol", prompt)
        self.assertIn("CONVERSATION_DECISION", prompt)
        self.assertIn("ACTION_REQUEST", prompt)
        self.assertIn("Never claim work was delegated", prompt)
        self.assertIn("common blacklist", prompt)
        self.assertIn("twg jira workitem get/query", prompt)

    def test_grill_protocol_lives_in_readable_file(self) -> None:
        protocol = (ROOT / "lib" / "agents" / "protocol.md").read_text(encoding="utf-8")
        self.assertIn("Do not grill bounded quick changes", protocol)
        self.assertIn("question_budget", protocol)
        self.assertIn("Jira is a tool, not the default workflow", protocol)
        self.assertIn("<ACTION_REQUEST>", protocol)

    def test_all_agents_receive_agent_owned_turn_decision_contract(self) -> None:
        for agent_id in ("dylan", "mark", "milchick", "irving"):
            prompt = interaction_contract_prompt(agent_id=agent_id)
            self.assertIn("CONVERSATION_DECISION", prompt)
            self.assertIn("pending clarification is context, not a lock", prompt)


if __name__ == "__main__":
    unittest.main()
