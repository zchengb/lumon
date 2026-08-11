#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.dylan.conversation import handle_conversation
from agents.dylan.model_client import FakeDylanModelClient
from agents.dylan.observability import Observability, TraceContext, new_trace_id
from agents.dylan.reaction import ReactionThinkingSession
from agents.dylan.schemas import AgentPlan, AgentTask, ConversationFlags, ToolCall
from risk.store import GlobalAgentStore, RiskStore


def _v3_common(provider: str = "fake") -> dict:
    return {
        "project": {"slug": "mbpass"},
        "agents": {
            "dylan": {
                "conversation_v3": {
                    "enabled": True,
                    "routing_mode": "agent_only",
                    "model": {"provider": provider, "model": "fake-model", "required": True},
                    "reaction": {"enabled": True, "emoji_type": "Typing"},
                    "agent_loop": {"allow_multi_task": True, "max_tool_calls": 8},
                },
                "risk_analyst": {"enabled": True, "conversation_v2": {"enabled": True, "grounding_guard_enabled": True}},
            }
        },
    }


class ConversationV3FlagsTests(unittest.TestCase):
    def test_agent_only_flag(self) -> None:
        flags = ConversationFlags.from_common(_v3_common())
        self.assertTrue(flags.v3_enabled)
        self.assertTrue(flags.agent_only)
        self.assertEqual(flags.reaction.emoji_type, "Typing")


class AgentOnlyPathTests(unittest.TestCase):
    def test_multi_intent_plan(self) -> None:
        plan = AgentPlan(
            language="en",
            confidence=0.95,
            tasks=[
                AgentTask(
                    task_id="task_1",
                    intent="conversation.agent_relationship",
                    tool_calls=[ToolCall(name="get_agent_relationship", arguments={"agent_id": "dylan", "other_id": "mark"})],
                ),
                AgentTask(
                    task_id="task_2",
                    intent="risk.unresolved",
                    tool_calls=[ToolCall(name="query_unresolved_findings", arguments={"project_slug": "mbpass", "limit": 5})],
                    project_slug="mbpass",
                ),
            ],
            source="fake",
        )
        client = FakeDylanModelClient(plan=plan, response_text="Mark and I collaborate. No unresolved findings in tool facts.")
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            try:
                GlobalAgentStore(Path(tmp) / "agents.sqlite3").close()
                with patch("agents.dylan.conversation._resolve_workspace", return_value=None), patch(
                    "agents.dylan.agent_controller.DylanAgentController._resolve_workspace", return_value=None
                ):
                    result = handle_conversation(
                        text="Do you know Mark? BTW any existing findings?",
                        meta={"chat_id": "oc_test", "message_id": "om_1", "user_id": "ou_1"},
                        common=_v3_common(),
                        known_slugs={"mbpass"},
                        model_client=client,
                    )
            finally:
                os.environ.pop("LUMEN_AGENTS_HOME", None)
        self.assertEqual(result["status"], "ok")
        self.assertIn("trace_id", result)
        self.assertTrue(result["flags"]["conversation_v3"])
        self.assertEqual(len(result["plan"]["tasks"]), 2)
        self.assertFalse(result.get("typing", {}).get("enabled", False))

    def test_agent_unavailable_no_heuristic(self) -> None:
        class BoomClient(FakeDylanModelClient):
            def plan(self, request):
                raise RuntimeError("planner boom")

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            try:
                result = handle_conversation(
                    text="What is the largest risk?",
                    meta={"chat_id": "oc_test", "message_id": "om_2"},
                    common=_v3_common(provider="fake"),
                    known_slugs={"mbpass"},
                    model_client=BoomClient(),
                )
            finally:
                os.environ.pop("LUMEN_AGENTS_HOME", None)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["action"], "agent.unavailable")
        self.assertIn("Trace ID:", result["text"])
        self.assertNotIn("largest risk", result["text"].lower())
        self.assertNotIn("Open / Reopened", result["text"])


class ReactionSessionTests(unittest.TestCase):
    def test_add_and_remove(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            try:
                obs = Observability()
                trace = TraceContext(trace_id=new_trace_id(), message_id="om_x")
                messenger = MagicMock()
                messenger.safe_add_reaction.return_value = {"data": {"reaction_id": "r_1"}}
                messenger.safe_delete_reaction.return_value = {"ok": True}
                session = ReactionThinkingSession(
                    messenger=messenger,
                    source_message_id="om_x",
                    emoji_type="OnIt",
                    trace=trace,
                    obs=obs,
                )
                session.start()
                self.assertEqual(session.reaction_id, "r_1")
                session.finish(success=True)
                messenger.safe_delete_reaction.assert_called_once_with("om_x", "r_1")
                events = [e["event"] for e in obs.events_for_trace(trace.trace_id)]
                self.assertIn("reaction.add.succeeded", events)
                self.assertIn("reaction.remove.succeeded", events)
                obs.close()
            finally:
                os.environ.pop("LUMEN_AGENTS_HOME", None)


class ObservabilityTests(unittest.TestCase):
    def test_jsonl_and_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            try:
                obs = Observability()
                trace = TraceContext(trace_id=new_trace_id(), message_id="om_y", project_slug="mbpass")
                obs.upsert_trace(trace, state="planning")
                obs.emit(trace, "agent.planner.started", provider="fake")
                obs.upsert_trace(trace, state="completed", latency_ms=12)
                row = obs.get_trace(trace.trace_id)
                self.assertEqual(row["state"], "completed")
                self.assertTrue((Path(tmp) / "dylan.jsonl").is_file())
                obs.close()
            finally:
                os.environ.pop("LUMEN_AGENTS_HOME", None)


class RecentFindingsTests(unittest.TestCase):
    def test_recent_window_includes_open(self) -> None:
        from risk.queries import recent_findings

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config").mkdir()
            (workspace / "state").mkdir()
            common = {"project": {"slug": "demo"}, "agents": {"dylan": {"risk_analyst": {"enabled": True}}}}
            finding = {
                "title": "Windowed bug",
                "severity": "High",
                "repository": "app",
                "file": "a.py",
                "trigger": "x",
                "root_cause": "y",
            }
            from risk.ingestion import ingest_scan_risk

            ingest_scan_risk(
                workspace=workspace,
                scan={"scan_status": "completed", "finished_at": "2026-08-05T00:00:00Z", "findings": [finding]},
                registry={"issues": []},
                common=common,
                result_path=workspace / "results" / "a.json",
            )
            store = RiskStore(workspace)
            data = recent_findings(store, "demo", window_days=30)
            self.assertGreaterEqual(data["total"], 1)
            store.close()

    def test_validate_plan_autofills_tools(self) -> None:
        from agents.dylan.agent_controller import DylanAgentController
        from agents.dylan.observability import Observability, TraceContext, new_trace_id
        from agents.dylan.schemas import AgentPlan, AgentTask, ConversationFlags

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            try:
                obs = Observability()
                ctrl = DylanAgentController(
                    flags=ConversationFlags(v3_enabled=True, routing_mode="agent_only"),
                    obs=obs,
                    trace=TraceContext(trace_id=new_trace_id()),
                )
                plan = AgentPlan(
                    language="en",
                    confidence=0.9,
                    tasks=[AgentTask(task_id="task_1", intent="risk.recent", tool_calls=[], params={"window_days": 7})],
                )
                validated = ctrl._validate_plan(plan)
                names = [c.name for c in validated.tasks[0].tool_calls]
                self.assertIn("query_recent_findings", names)
                obs.close()
            finally:
                os.environ.pop("LUMEN_AGENTS_HOME", None)
    def test_run_conversation_job_observability_same_thread(self) -> None:
        from concurrent.futures import ThreadPoolExecutor

        from agents.dylan.runtime import run_conversation_job

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            try:

                def worker() -> dict:
                    obs = Observability()
                    try:
                        trace = TraceContext(trace_id=new_trace_id(), message_id="om_inline")
                        obs.emit(trace, "message.received")
                        obs.upsert_trace(trace, state="completed", latency_ms=1)
                        return {"status": "ok", "action": "test", "trace_id": trace.trace_id}
                    finally:
                        obs.close()

                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(
                        run_conversation_job,
                        message_id="om_inline",
                        chat_id="oc_1",
                        thread_id="",
                        user_id="ou_1",
                        worker=worker,
                    )
                    out = future.result(timeout=5)
                self.assertEqual(out["status"], "completed")
                self.assertEqual(out["result"]["status"], "ok")
                obs = Observability()
                row = obs.get_trace(out["result"]["trace_id"])
                self.assertIsNotNone(row)
                obs.close()
            finally:
                os.environ.pop("LUMEN_AGENTS_HOME", None)
