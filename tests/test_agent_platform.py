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

from agents.definitions import ensure_definitions_loaded, get_definition, list_definitions
from agents.runtime.reply_anchor import lookup_outbound, remember_outbound
from agents.runtime.session_store import SessionStore, conversation_scope_id, session_contract_current
from risk.store import GlobalAgentStore


class AgentPlatformTests(unittest.TestCase):
    def test_definitions_registered(self) -> None:
        ensure_definitions_loaded()
        ids = {d.id for d in list_definitions()}
        self.assertIn("dylan", ids)
        self.assertIn("mark", ids)
        self.assertIn("milchick", ids)
        dylan = get_definition("dylan")
        mark = get_definition("mark")
        milchick = get_definition("milchick")
        assert dylan is not None and mark is not None and milchick is not None
        self.assertEqual(dylan.role, "scan")
        self.assertEqual(mark.role, "delivery")
        self.assertEqual(milchick.role, "orchestrator")
        self.assertFalse(dylan.capabilities.direct_workspace_write)
        self.assertFalse(mark.capabilities.direct_workspace_write)
        self.assertEqual(dylan.capabilities.filesystem_mode, "workspace_read")
        self.assertEqual(mark.capabilities.filesystem_mode, "workspace_read")
        self.assertIn("risk.resolve", dylan.capabilities.actions)
        self.assertIn("delivery.start", mark.capabilities.actions)
        self.assertIn("delivery.quick_change", mark.capabilities.actions)
        self.assertIn("test_case.generate", mark.capabilities.actions)
        self.assertIn("agent.job.create", milchick.capabilities.actions)

    def test_unknown_agent_ignored(self) -> None:
        from agents.bridge import handle_agent_message

        result = handle_agent_message(agent_id="unknown", text="hi", meta={"chat_id": "oc1"})
        self.assertEqual(result.get("status"), "ignored")

    def test_session_scopes_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            store_path = Path(tmp) / "agent.sqlite3"
            gs = GlobalAgentStore(path=store_path)
            store = SessionStore(gs)
            dylan_scope = conversation_scope_id(agent_id="dylan", chat_id="oc1", thread_id="omt1")
            mark_scope = conversation_scope_id(agent_id="mark", chat_id="oc1", thread_id="omt1")
            self.assertNotEqual(dylan_scope, mark_scope)
            dylan = store.create(
                agent_id="dylan",
                chat_id="oc1",
                conversation_scope_id=dylan_scope,
                workspace_path=tmp,
                project_slug="mbpass",
                soul_version="5",
                protocol_version="5",
                provider_session_id="prov-dylan",
            )
            mark = store.create(
                agent_id="mark",
                chat_id="oc1",
                conversation_scope_id=mark_scope,
                workspace_path=tmp,
                project_slug="mbpass",
                soul_version="2",
                protocol_version="1",
                provider_session_id="prov-mark",
            )
            self.assertNotEqual(dylan["provider_session_id"], mark["provider_session_id"])
            self.assertEqual(
                store.get_active(agent_id="dylan", conversation_scope_id=dylan_scope)["session_id"],
                dylan["session_id"],
            )
            self.assertEqual(
                store.get_active(agent_id="mark", conversation_scope_id=mark_scope)["session_id"],
                mark["session_id"],
            )
            self.assertTrue(session_contract_current(dylan, soul_version="5", protocol_version="5"))
            self.assertFalse(session_contract_current(dylan, soul_version="1", protocol_version="1"))
            self.assertTrue(session_contract_current(mark, soul_version="2", protocol_version="1"))
            store.close()

    def test_group_roots_are_isolated_and_thread_replies_share_root(self) -> None:
        first_root = conversation_scope_id(
            agent_id="milchick",
            chat_id="oc1",
            chat_type="group",
            message_id="om_root_1",
            project_slug="mbpass",
        )
        first_reply = conversation_scope_id(
            agent_id="milchick",
            chat_id="oc1",
            chat_type="group",
            thread_id="omt_topic_1",
            root_id="om_root_1",
            message_id="om_reply_1",
            project_slug="mbpass",
        )
        second_root = conversation_scope_id(
            agent_id="milchick",
            chat_id="oc1",
            chat_type="group",
            message_id="om_root_2",
            project_slug="mbpass",
        )
        self.assertEqual(first_root, first_reply)
        self.assertNotEqual(first_root, second_root)

    def test_reply_anchors_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            remember_outbound(
                message_id="om_dylan",
                text="dylan outbound",
                chat_id="oc1",
                agent_id="dylan",
                thread_id="omt1",
            )
            remember_outbound(
                message_id="om_mark",
                text="mark outbound",
                chat_id="oc1",
                agent_id="mark",
                thread_id="omt1",
            )
            self.assertEqual(lookup_outbound("om_dylan", agent_id="dylan"), "dylan outbound")
            self.assertEqual(lookup_outbound("om_mark", agent_id="mark"), "mark outbound")
            self.assertEqual(lookup_outbound("om_dylan", agent_id="mark"), "")
            self.assertEqual(lookup_outbound("om_mark", agent_id="dylan"), "")


if __name__ == "__main__":
    unittest.main()
