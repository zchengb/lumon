from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agents.conversation.config import (
    ThreadNativeConfig,
    normalize_reply_language,
    thread_native_config,
)
from agents.conversation.event_bus import EventBus
from agents.conversation.output import ConversationOutput
from agents.conversation.thread_store import ThreadTranscriptStore
from agents.dylan.schemas import ConversationFlags
from agents.runtime.autonomous import _session_protocol_version
from agents.runtime.connected_tools import ConnectedToolExecutor, ConnectedToolRegistry
from agents.runtime.native_prompt import build_native_bootstrap_prompt
from agents.security.access_policy import AccessDecision, InteractionContext
from agents.security.trusted import TrustedActionContext
from feishu.handlers import extract_message_meta


class _Messenger:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def reply_agent_text(self, message_id: str, text: str, **kwargs: object) -> dict[str, object]:
        self.calls.append(text)
        return {"data": {"message_id": f"reply-{len(self.calls)}"}}


class ConversationQualityM09Tests(unittest.TestCase):
    def test_golden_conversation_fixture_covers_the_m09_judgment_surface(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "conversation_quality_m09.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.assertEqual("3.3", fixture["contract"])
        self.assertEqual(
            {
                "A-alert-email-only",
                "B-human-explicit-language",
                "C-quiet-investigation",
                "D-dm-mark",
                "E-group-consult",
                "F-transfer",
                "G-live-environment",
                "H-new-human-evidence",
                "I-layered-root-cause",
                "J-proactive-completion",
            },
            {str(item["id"]) for item in fixture["cases"]},
        )
        definition = SimpleNamespace(
            id="mark",
            display_name="Mark",
            role="delivery",
            soul_path=Path("/does/not/exist"),
        )
        prompt = build_native_bootstrap_prompt(
            definition=definition,
            project_slug="mbpass",
            workspace_path="/tmp/mbpass",
            user_message="Run the golden conversation cases.",
            default_language="en",
        )
        for phrase in (
            "Ordinary work is quiet by default",
            "Typing reaction",
            "Conversation default reply language: en",
            "feishu.context",
            "Consult for one bounded contribution",
            "Transfer only when the peer owns",
            "live runtime/infrastructure",
            "Re-plan immediately",
            "Confirmed, Likely, and Unknown",
            "materially different paths",
        ):
            self.assertIn(phrase, prompt)

    def test_language_and_native_session_contract_are_dynamic(self) -> None:
        self.assertEqual("en", normalize_reply_language("english"))
        config = thread_native_config(
            {
                "conversation": {"version": "3.3", "default_language": "en"},
                "agent_collaboration": {"thread_native_handoff": True},
            }
        )
        self.assertEqual("3.3", config.version)
        self.assertEqual("en", config.default_language)
        definition = SimpleNamespace(protocol_version="5")
        self.assertEqual("5:native-3.3", _session_protocol_version(definition, True, config.version))
        flags = ConversationFlags.from_common(
            {"conversation": {"default_language": "zh-Hant"}},
            {"conversation": {"default_language": "en"}},
        )
        self.assertEqual("en", flags.default_language)

    def test_prompt_describes_senior_coworker_conversation_quality(self) -> None:
        definition = SimpleNamespace(
            id="mark",
            display_name="Mark",
            role="delivery",
            soul_path=Path("/does/not/exist"),
        )
        prompt = build_native_bootstrap_prompt(
            definition=definition,
            project_slug="mbpass",
            workspace_path="/tmp/mbpass",
            user_message="Investigate the current failure.",
            default_language="en",
        )
        self.assertIn("Conversation default reply language: en", prompt)
        self.assertIn("Ordinary work is quiet by default", prompt)
        self.assertIn("Consult for one bounded contribution", prompt)
        self.assertIn("Confirmed, Likely, and Unknown", prompt)
        self.assertIn("feishu.context", prompt)

    def test_quality_metrics_are_observational_and_count_visible_events(self) -> None:
        with tempfile.TemporaryDirectory(prefix="lumon-m09-quality-") as tmp:
            store = ThreadTranscriptStore(Path(tmp) / "thread.sqlite3")
            bus = EventBus(store=store)
            messenger = _Messenger()
            output = ConversationOutput(
                agent_id="mark",
                meta={"message_id": "human-1", "chat_id": "chat-1", "root_id": "human-1"},
                messenger=messenger,
                event_bus=bus,
                config=ThreadNativeConfig(minimum_event_interval_seconds=0, default_language="en"),
            )
            output.message("I found the current failure.")
            output.progress("I am checking the deployed configuration.")
            output.handoff("Consulting Irving for one bounded check.", collaboration_kind="consult")
            output.question("Should I apply the reversible fix or wait for approval?")
            output.mark_conclusion()
            summary = output.quality_summary()
            self.assertEqual(4, summary["public_message_count"])
            self.assertEqual(1, summary["progress_message_count"])
            self.assertEqual(1, summary["consult_count"])
            self.assertEqual(1, summary["handoff_count"])
            self.assertEqual("en", summary["language_used"])
            self.assertIsNotNone(summary["time_to_first_useful_message"])
            self.assertIsNotNone(summary["time_to_conclusion"])
            self.assertFalse(summary["question_after_conclusion"])
            self.assertEqual(4, len(messenger.calls))
            output.close()
            bus.close()
            store.close()

    def test_feishu_context_is_read_only_host_bound_information(self) -> None:
        access_context = InteractionContext(
            agent_id="mark",
            user_id="ou-user",
            chat_id="oc-chat",
            chat_type="group",
            thread_id="omt-thread",
            message_id="om-message",
            is_dm=False,
            trust_zone="RESTRICTED",
            chat_name="MBPass 2026",
            root_id="om-root",
            participants=("ou-user", "ou-other"),
            available_agents=("mark", "irving"),
        )
        decision = AccessDecision(
            allowed=True,
            reason_code="ENTRY_GATE",
            trust_zone="RESTRICTED",
            host_read_allowed=False,
            mutation_allowed=False,
            effective_capabilities=frozenset(),
            context=access_context,
        )
        context = TrustedActionContext(
            agent_id="mark",
            project_slug="mbpass",
            actor_user_id="ou-user",
            chat_id="oc-chat",
            thread_id="omt-thread",
            source_message_id="om-message",
            trace_id="tr-m09",
            access_decision=decision,
        )
        calls: list[str] = []
        executor = ConnectedToolExecutor(
            registry=ConnectedToolRegistry(include_legacy=False),
            native_executor=lambda name, arguments, bound: calls.append(name) or {"unexpected": True},
        )
        with patch("feishu.client_registry.configured_agents", return_value=[]):
            snapshot = executor.execute("feishu.context", {}, context=context)
        self.assertEqual("thread", snapshot["context_type"])
        self.assertEqual("MBPass 2026", snapshot["chat_name"])
        self.assertEqual(["mark", "irving"], snapshot["available_agents"])
        self.assertFalse(snapshot["available_agents_verified"])
        self.assertEqual([], calls)

    def test_feishu_message_meta_keeps_mentions_as_observed_context(self) -> None:
        meta = extract_message_meta(
            {
                "event": {
                    "sender": {"sender_id": {"open_id": "ou-human"}},
                    "message": {
                        "message_id": "om-message",
                        "chat_id": "oc-group",
                        "chat_type": "group",
                        "mentions": [
                            {"id": {"open_id": "ou-mark"}, "name": "Mark S."},
                            {"id": {"open_id": "ou-person"}, "name": "A human"},
                        ],
                    },
                }
            }
        )
        self.assertEqual(["ou-human", "ou-mark", "ou-person"], json.loads(meta["participants"]))
        self.assertEqual(["mark"], json.loads(meta["available_agents"]))
        self.assertNotIn("available_agents_verified", meta)


if __name__ == "__main__":
    unittest.main()
