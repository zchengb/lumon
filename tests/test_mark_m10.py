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

from agents.definitions import ensure_definitions_loaded, get_definition
from agents.mark.delivery_adapter import DeliveryActionAdapter
from agents.mark.session_bootstrap import build_bootstrap_prompt, build_resume_prompt
from agents.mark.workspace_contract import ensure_workspace_contract
from agents.runtime.autonomous import handle_autonomous_conversation
from agents.runtime.cursor_runtime import AgentRunResult, CursorAgentRuntime


def _v4_common() -> dict:
    return {
        "project": {"slug": "mbpass"},
        "agents": {
            "mark": {
                "conversation_v4": {
                    "enabled": True,
                    "mode": "autonomous_workspace",
                    "provider": {"type": "cursor_cli", "model": "fake-model"},
                    "session": {"scope": "thread_shared"},
                    "runtime": {"soft_timeout_seconds": 60, "hard_timeout_seconds": 180},
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
        self.calls.append({"workspace": str(workspace), "prompt": prompt, "provider_session_id": provider_session_id})
        if not self.results:
            return AgentRunResult(text="", provider_session_id="", status="failed", error="no fake result")
        return self.results.pop(0)


class MarkM10Tests(unittest.TestCase):
    def test_soul_and_bootstrap(self) -> None:
        ensure_definitions_loaded()
        mark = get_definition("mark")
        assert mark is not None
        prompt = build_bootstrap_prompt(
            project_slug="mbpass",
            workspace_path="/tmp/docs",
            user_message="MBPAS-1601 现在怎么样？",
        )
        self.assertIn("Mark", prompt)
        self.assertIn("Delivery Lead", prompt)
        self.assertIn("lumen delivery", prompt)
        self.assertIn("Never modify business source code", prompt)
        self.assertIn("Lumen Grill protocol", prompt)
        self.assertIn("Do not turn a bounded quick change into a Story", prompt)
        resume = build_resume_prompt(user_message="继续", project_slug="mbpass")
        self.assertIn("Remain Mark", resume)
        self.assertIn("Relationship — Dylan", prompt)
        self.assertIn("Soul Version: **3**", prompt)
        self.assertTrue(prompt.startswith("[MARK SESSION BOOTSTRAP]"))

    def test_workspace_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ensure_workspace_contract(workspace=root, project_slug="mbpass")
            text = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("LUMEN MARK MANAGED START", text)
            self.assertIn("Delivery Lead", text)
            self.assertIn("Do not modify business source", text)

    def test_readiness_matrix(self) -> None:
        adapter = DeliveryActionAdapter()
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp)
            stories = docs / "stories" / "MBPAS-1601"
            stories.mkdir(parents=True)
            self.assertEqual(adapter.readiness(workspace=docs, story="MBPAS-1601")["code"], "METADATA_MISSING")
            (stories / "metadata.json").write_text(
                json.dumps(
                    {
                        "jiraKey": "MBPAS-1601",
                        "businessStatus": "ready",
                        "technicalStatus": "draft",
                        "linkedRepos": ["repo-a"],
                    }
                ),
                encoding="utf-8",
            )
            (stories / "story.md").write_text("# story\n", encoding="utf-8")
            self.assertEqual(
                adapter.readiness(workspace=docs, story="MBPAS-1601")["code"],
                "TECHNICAL_PLAN_MISSING",
            )
            (stories / "technical-plan.md").write_text("# plan\n", encoding="utf-8")
            self.assertEqual(
                adapter.readiness(workspace=docs, story="MBPAS-1601")["code"],
                "TECHNICAL_PLAN_NOT_APPROVED",
            )
            (stories / "metadata.json").write_text(
                json.dumps(
                    {
                        "jiraKey": "MBPAS-1601",
                        "businessStatus": "ready",
                        "technicalStatus": "approved",
                        "linkedRepos": ["repo-a"],
                    }
                ),
                encoding="utf-8",
            )
            ready = adapter.readiness(workspace=docs, story="MBPAS-1601")
            self.assertEqual(ready["status"], "ready")
            self.assertEqual(ready["code"], "READY")

    def test_explicit_start_returns_run_id_without_waiting(self) -> None:
        adapter = DeliveryActionAdapter()
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp)
            stories = docs / "stories" / "MBPAS-1601"
            stories.mkdir(parents=True)
            (stories / "metadata.json").write_text(
                json.dumps(
                    {
                        "jiraKey": "MBPAS-1601",
                        "businessStatus": "ready",
                        "technicalStatus": "approved",
                        "linkedRepos": ["repo-a"],
                    }
                ),
                encoding="utf-8",
            )
            (stories / "story.md").write_text("# story\n", encoding="utf-8")
            (stories / "technical-plan.md").write_text("# plan\n", encoding="utf-8")
            with mock.patch("agents.mark.delivery_adapter.threading.Thread") as thread_mock:
                thread_mock.side_effect = lambda *a, **k: mock.Mock(start=lambda: None)
                started = adapter.start(
                    workspace=docs,
                    story="MBPAS-1601",
                    actor="ou_user",
                    source_message_id="om1",
                    trace_id="tr1",
                    dry_run=True,
                )
            self.assertEqual(started["status"], "started")
            self.assertTrue(str(started.get("run_id") or "").startswith("delivery-"))
            self.assertEqual(started["actor"], "ou_user")
            self.assertEqual(started["source_message_id"], "om1")
            self.assertEqual(started["trace_id"], "tr1")
            blocked = adapter.start(workspace=docs, story="missing-story")
            self.assertEqual(blocked["status"], "blocked")

    def test_cancel_stops_active_delivery_process(self) -> None:
        adapter = DeliveryActionAdapter()
        with tempfile.TemporaryDirectory() as tmp, mock.patch(
            "agents.mark.delivery_adapter._terminate_process_tree"
        ) as terminate:
            docs = Path(tmp)
            lock = docs / "locks" / "delivery-run"
            lock.mkdir(parents=True)
            (lock / "pid").write_text("1234\n", encoding="utf-8")
            result = adapter.cancel(workspace=docs, run_id="", actor="ou_user")
        self.assertEqual("cancelled", result["status"])
        self.assertEqual(1234, result["pid"])
        terminate.assert_called_once_with(1234)

    def test_quick_change_clarification_keeps_explicit_intent(self) -> None:
        from dataclasses import replace

        ensure_definitions_loaded()
        mark = get_definition("mark")
        assert mark is not None
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp)
            (docs / "stories").mkdir()
            (docs / "admin-portal").mkdir()
            (docs / "admin-portal" / "package.json").write_text('{"version":"1.2.3"}\n', encoding="utf-8")
            previous = os.environ.get("LUMEN_AGENTS_HOME")
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            runtime = FakeRuntime(
                [
                    AgentRunResult(
                        text=(
                            '<FINAL_RESPONSE>Which version should I use?</FINAL_RESPONSE>'
                            '<ACTION_REQUEST>{"action":"delivery.quick_change","arguments":'
                            '{"repository":"admin-portal","target_files":["package.json"],'
                            '"request":"upgrade the version","change_type":"version_bump"}}</ACTION_REQUEST>'
                        ),
                        provider_session_id="sess-mark",
                        status="succeeded",
                    ),
                    AgentRunResult(
                        text=(
                            '<FINAL_RESPONSE>Starting the bounded change.</FINAL_RESPONSE>'
                            '<ACTION_REQUEST>{"action":"delivery.quick_change","arguments":'
                            '{"repository":"admin-portal","target_files":["package.json"],'
                            '"request":"upgrade the version","change_type":"version_bump",'
                            '"target_version":"1.2.3"}}</ACTION_REQUEST>'
                        ),
                        provider_session_id="sess-mark",
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
                                text="Please upgrade the version",
                                meta=meta,
                                common=_v4_common(),
                                runtime=runtime,
                            )
                            with mock.patch("agents.runtime.autonomous.execute_trusted_actions", return_value=[]) as execute:
                                second = handle_autonomous_conversation(
                                    definition=definition,
                                    text="1.2.3",
                                    meta={**meta, "message_id": "om2"},
                                    common=_v4_common(),
                                    runtime=runtime,
                                )
                self.assertEqual("autonomous.clarification", first.get("action"))
                self.assertIsNotNone(first.get("pending_clarification"))
                self.assertIn("1.2.4", first.get("text", ""))
                self.assertEqual("ok", second.get("status"))
                execute.assert_called_once()
                self.assertFalse(execute.call_args.kwargs["context"].explicit_authorization)
            finally:
                if previous is None:
                    os.environ.pop("LUMEN_AGENTS_HOME", None)
                else:
                    os.environ["LUMEN_AGENTS_HOME"] = previous

    def test_mark_autonomous_reply_no_delivery_side_effect(self) -> None:
        from dataclasses import replace

        ensure_definitions_loaded()
        mark = get_definition("mark")
        assert mark is not None
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp)
            (docs / "stories").mkdir()
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            runtime = FakeRuntime(
                [
                    AgentRunResult(
                        text="<FINAL_RESPONSE>Story is blocked on plan approval.</FINAL_RESPONSE>",
                        provider_session_id="sess-mark",
                        status="succeeded",
                        duration_ms=12,
                    )
                ]
            )
            definition = replace(
                mark,
                resolve_workspace=lambda project_slug, chat_id: ("mbpass", docs),
                ensure_workspace_contract=lambda **kwargs: docs,
            )
            with mock.patch("agents.runtime.autonomous.resolve_project", return_value={"slug": "mbpass", "workspace": str(docs)}):
                with mock.patch("agents.runtime.autonomous.known_project_slugs", return_value={"mbpass"}):
                    with mock.patch("agents.runtime.autonomous.load_chat_project_map", return_value={}):
                        with mock.patch.object(DeliveryActionAdapter, "start") as start_mock:
                            result = handle_autonomous_conversation(
                                definition=definition,
                                text="MBPAS-1601 现在怎么样？",
                                meta={
                                    "chat_id": "oc1",
                                    "thread_id": "omt1",
                                    "user_id": "ou1",
                                    "message_id": "om1",
                                },
                                common=_v4_common(),
                                runtime=runtime,
                            )
            self.assertEqual(result.get("status"), "ok")
            self.assertEqual(result.get("agent_id"), "mark")
            self.assertIn("blocked", str(result.get("text") or "").lower())
            start_mock.assert_not_called()
            self.assertIn("Never modify business source code", runtime.calls[0]["prompt"])


if __name__ == "__main__":
    unittest.main()
