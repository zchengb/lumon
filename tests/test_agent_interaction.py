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
from agents.runtime.interaction import action_missing_fields, interaction_contract_prompt, normalize_clarification
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

    def test_action_requirements_detect_missing_target(self) -> None:
        self.assertEqual(["story"], action_missing_fields("delivery.start", arguments={}))
        self.assertEqual([], action_missing_fields("delivery.start", resource={"story": "MBPAS-1"}))
        self.assertEqual(["target_agent", "capability"], action_missing_fields("agent.job.create", arguments={}))

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

    def test_interaction_contract_distinguishes_grill_from_quick_change(self) -> None:
        prompt = interaction_contract_prompt(agent_id="mark")
        self.assertIn("[LUMEN GRILL PROTOCOL]", prompt)
        self.assertIn("Do not grill bounded quick changes", prompt)
        self.assertIn("question_budget", prompt)


if __name__ == "__main__":
    unittest.main()
