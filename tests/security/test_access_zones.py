#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.security.access_policy import (
    authorize_agent_interaction,
    load_agent_access_policy,
    resolve_trust_zone,
    interaction_context_from_meta,
)
from agents.security.actions import ActionRequest
from agents.security.broker import CapabilityBroker
from agents.security.adapters.host_read import execute_host_read_action


OWNER = "ou_owner"
DEV = "ou_dev"
STRANGER = "ou_stranger"
DYLAN_DM = "oc_dylan_dm"
MARK_CHAT = "oc_mbpass_delivery"
SHARED = "oc_shared"


def _config() -> dict:
    return {
        "access": {
            "default_policy": "deny",
            "owners": [OWNER],
            "admins": [OWNER],
            "agents": {
                "dylan": {
                    "exposure_mode": "owner_private",
                    "allowed_user_ids": [OWNER],
                    "allowed_chat_ids": [],
                    "dm_only": True,
                    "host_read": "selected",
                    "host_read_capabilities": ["host.disk.summary", "host.runtime.summary"],
                    "mutation_allowed_user_ids": [OWNER],
                },
                "mark": {
                    "exposure_mode": "restricted_team",
                    "allowed_user_ids": [OWNER, DEV],
                    "allowed_chat_ids": [MARK_CHAT],
                    "dm_only": False,
                    "host_read": "deny",
                    "mutation_allowed_user_ids": [OWNER],
                },
                "milchick": {
                    "exposure_mode": "admin_private",
                    "allowed_user_ids": [OWNER],
                    "allowed_chat_ids": [],
                    "dm_only": True,
                    "host_read": "system_only",
                    "host_read_capabilities": ["lumen.system.health", "lumen.agent.status"],
                    "mutation_allowed_user_ids": [OWNER],
                },
            },
        }
    }


class AccessZoneTests(unittest.TestCase):
    def test_unknown_user_denied(self) -> None:
        decision = authorize_agent_interaction(
            agent_id="dylan",
            meta={"user_id": STRANGER, "chat_id": DYLAN_DM, "chat_type": "p2p", "message_id": "om1"},
            config=_config(),
        )
        self.assertFalse(decision.allowed)

    def test_owner_dylan_dm_private(self) -> None:
        decision = authorize_agent_interaction(
            agent_id="dylan",
            meta={"user_id": OWNER, "chat_id": DYLAN_DM, "chat_type": "p2p", "message_id": "om1"},
            config=_config(),
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.trust_zone, "PRIVATE")
        self.assertTrue(decision.host_read_allowed)
        self.assertIn("host.disk.summary", decision.effective_capabilities)
        self.assertTrue(decision.mutation_allowed)

    def test_owner_dylan_group_denied_dm_only(self) -> None:
        decision = authorize_agent_interaction(
            agent_id="dylan",
            meta={"user_id": OWNER, "chat_id": SHARED, "chat_type": "group", "message_id": "om1"},
            config=_config(),
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason_code, "DM_ONLY")

    def test_dylan_shared_host_denied_when_group_allowed(self) -> None:
        cfg = _config()
        cfg["access"]["agents"]["dylan"]["dm_only"] = False
        cfg["access"]["agents"]["dylan"]["allowed_chat_ids"] = [SHARED]
        decision = authorize_agent_interaction(
            agent_id="dylan",
            meta={"user_id": OWNER, "chat_id": SHARED, "chat_type": "group", "message_id": "om1"},
            config=cfg,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.trust_zone, "SHARED")
        self.assertFalse(decision.host_read_allowed)
        self.assertNotIn("host.disk.summary", decision.effective_capabilities)
        self.assertFalse(decision.mutation_allowed)

    def test_mark_team_chat_restricted(self) -> None:
        decision = authorize_agent_interaction(
            agent_id="mark",
            meta={"user_id": DEV, "chat_id": MARK_CHAT, "chat_type": "group", "message_id": "om1"},
            config=_config(),
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.trust_zone, "RESTRICTED")
        self.assertIn("delivery.readiness", decision.effective_capabilities)
        self.assertNotIn("delivery.start", decision.effective_capabilities)

    def test_allowed_group_authorizes_a_user_not_in_private_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"LUMEN_AGENTS_HOME": tmp}):
            decision = authorize_agent_interaction(
                agent_id="mark",
                meta={"user_id": STRANGER, "chat_id": MARK_CHAT, "chat_type": "group", "message_id": "om1"},
                config=_config(),
            )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.trust_zone, "RESTRICTED")

    def test_private_chat_still_requires_one_to_one_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"LUMEN_AGENTS_HOME": tmp}):
            decision = authorize_agent_interaction(
                agent_id="mark",
                meta={"user_id": STRANGER, "chat_id": "oc_mark_dm", "chat_type": "p2p", "message_id": "om1"},
                config=_config(),
            )
        self.assertFalse(decision.allowed)

    def test_global_group_acl_works_without_per_agent_override(self) -> None:
        config = {"access": {"default_policy": "deny", "allowed_chat_ids": [SHARED]}}
        decision = authorize_agent_interaction(
            agent_id="mark",
            meta={"user_id": STRANGER, "chat_id": SHARED, "chat_type": "group", "message_id": "om1"},
            config=config,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.trust_zone, "RESTRICTED")

    def test_mark_other_chat_denied(self) -> None:
        decision = authorize_agent_interaction(
            agent_id="mark",
            meta={"user_id": DEV, "chat_id": SHARED, "chat_type": "group", "message_id": "om1"},
            config=_config(),
        )
        self.assertFalse(decision.allowed)

    def test_mark_mutation_owner_only(self) -> None:
        decision = authorize_agent_interaction(
            agent_id="mark",
            meta={"user_id": OWNER, "chat_id": MARK_CHAT, "chat_type": "group", "message_id": "om1"},
            config=_config(),
        )
        self.assertTrue(decision.mutation_allowed)
        self.assertIn("delivery.start", decision.effective_capabilities)

    def test_milchick_admin_dm(self) -> None:
        decision = authorize_agent_interaction(
            agent_id="milchick",
            meta={"user_id": OWNER, "chat_id": "oc_m", "chat_type": "p2p", "message_id": "om1"},
            config=_config(),
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.trust_zone, "PRIVATE")
        self.assertIn("lumen.system.health", decision.effective_capabilities)

    def test_cross_app_open_id_linked_by_union(self) -> None:
        import os
        import tempfile

        from risk.store import GlobalAgentStore

        dylan_ou = "ou_4f1d9b4d016ca1a31a17f4efa6473ffd"
        milchick_ou = "ou_12309d90c1d05b757ef1d002b59fc91b"
        union = "on_4bf919cda0978cc8aad2abaf6535af87"
        cfg = _config()
        cfg["access"]["owners"] = [dylan_ou]
        cfg["access"]["admins"] = [dylan_ou]
        cfg["access"]["agents"]["milchick"]["allowed_user_ids"] = [dylan_ou]
        cfg["access"]["agents"]["milchick"]["mutation_allowed_user_ids"] = [dylan_ou]
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            store = GlobalAgentStore()
            try:
                store.upsert_feishu_identity(
                    identity_id=dylan_ou,
                    identity_type="user",
                    display_name="Zheng",
                    union_id=union,
                )
                store.upsert_feishu_identity(
                    identity_id=milchick_ou,
                    identity_type="user",
                    display_name="Zheng",
                    union_id=union,
                )
                denied = authorize_agent_interaction(
                    agent_id="milchick",
                    meta={"user_id": milchick_ou, "chat_id": "oc_m", "chat_type": "p2p", "message_id": "om1"},
                    config=cfg,
                    store=store,
                )
                self.assertTrue(denied.allowed)
                self.assertEqual(denied.trust_zone, "PRIVATE")
                self.assertTrue(denied.mutation_allowed)
            finally:
                store.close()

    def test_milchick_group_denied(self) -> None:
        decision = authorize_agent_interaction(
            agent_id="milchick",
            meta={"user_id": OWNER, "chat_id": SHARED, "chat_type": "group", "message_id": "om1"},
            config=_config(),
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason_code, "DM_ONLY")

    def test_milchick_whitelisted_group_allowed(self) -> None:
        cfg = _config()
        cfg["access"]["agents"]["milchick"]["allowed_chat_ids"] = [SHARED]
        decision = authorize_agent_interaction(
            agent_id="milchick",
            meta={"user_id": OWNER, "chat_id": SHARED, "chat_type": "group", "message_id": "om1"},
            config=cfg,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.trust_zone, "RESTRICTED")
        self.assertTrue(decision.mutation_allowed)
        self.assertNotIn("lumen.system.health", decision.effective_capabilities)

    def test_milchick_global_chat_whitelist(self) -> None:
        cfg = _config()
        cfg["access"]["allowed_chat_ids"] = [SHARED]
        decision = authorize_agent_interaction(
            agent_id="milchick",
            meta={"user_id": OWNER, "chat_id": SHARED, "chat_type": "group", "message_id": "om1"},
            config=cfg,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.trust_zone, "RESTRICTED")

    def test_unconfigured_agent_denied(self) -> None:
        decision = authorize_agent_interaction(
            agent_id="dylan",
            meta={"user_id": OWNER, "chat_id": DYLAN_DM, "chat_type": "p2p", "message_id": "om1"},
            config={"access": {"default_policy": "deny", "owners": [OWNER], "agents": {}}},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason_code, "AGENT_ACCESS_UNCONFIGURED")

    def test_host_disk_summary_brokered(self) -> None:
        result = execute_host_read_action(
            ActionRequest(
                agent_id="dylan",
                action="host.disk.summary",
                project_slug="mbpass",
                actor_user_id=OWNER,
                chat_id=DYLAN_DM,
                thread_id="",
                source_message_id="om1",
                trace_id="tr1",
                arguments={
                    "_access_decision": {
                        "host_read_allowed": True,
                        "effective_capabilities": ["host.disk.summary"],
                    }
                },
            )
        )
        self.assertIn("free_gb", result)
        self.assertIn("total_gb", result)

    def test_host_summary_denied_in_shared(self) -> None:
        cfg = _config()
        cfg["access"]["agents"]["dylan"]["dm_only"] = False
        cfg["access"]["agents"]["dylan"]["allowed_chat_ids"] = [SHARED]
        receipt = CapabilityBroker(config=cfg).execute(
            ActionRequest(
                agent_id="dylan",
                action="host.disk.summary",
                project_slug="mbpass",
                actor_user_id=OWNER,
                chat_id=SHARED,
                thread_id="",
                source_message_id="om1",
                trace_id="tr1",
                arguments={"chat_type": "group"},
                explicit_authorization=True,
            )
        )
        self.assertEqual(receipt.status, "denied")


if __name__ == "__main__":
    unittest.main()
