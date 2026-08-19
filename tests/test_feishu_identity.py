#!/usr/bin/env python3
from __future__ import annotations

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

from feishu.handlers import extract_message_meta, remember_message_identities
from feishu.identity import (
    discover_feishu_group_chats,
    enrich_feishu_identities,
    is_feishu_open_chat_id,
    is_feishu_open_user_id,
)
from risk.store import GlobalAgentStore

ALICE = "ou_4f1d9b4d016ca1a31a17f4efa6473ffd"
BOB = "ou_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
CHAT = "oc_5434c33a98e60c3872c966f22b75fd84"


class FeishuIdentityTests(unittest.TestCase):
    def test_open_id_shape(self) -> None:
        self.assertTrue(is_feishu_open_user_id(ALICE))
        self.assertFalse(is_feishu_open_user_id("ou_alice"))
        self.assertTrue(is_feishu_open_chat_id(CHAT))
        self.assertFalse(is_feishu_open_chat_id("oc_mbpass"))

    def test_remember_mentions_and_enrich(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            store = GlobalAgentStore()
            try:
                event = {
                    "header": {"app_id": "cli_x"},
                    "event": {
                        "sender": {
                            "sender_id": {
                                "open_id": ALICE,
                                "union_id": "on_4bf919cda0978cc8aad2abaf6535af87",
                            }
                        },
                        "message": {
                            "message_id": "om_1",
                            "chat_id": CHAT,
                            "chat_type": "group",
                            "mentions": [
                                {"id": {"open_id": ALICE}, "name": "Alice"},
                                {"id": {"open_id": BOB}, "name": "Bob"},
                            ],
                        },
                    },
                }
                meta = extract_message_meta(event)
                self.assertEqual(meta["user_id"], ALICE)
                self.assertEqual(meta["user_name"], "Alice")
                self.assertEqual(meta["union_id"], "on_4bf919cda0978cc8aad2abaf6535af87")
                with mock.patch("feishu.identity._messenger_for", return_value=None):
                    remember_message_identities(event, meta)
                self.assertEqual([CHAT], store.list_recent_feishu_group_chat_ids())
                self.assertEqual("group", store.get_feishu_chat_context(CHAT))
                self.assertEqual(store.get_feishu_display_name(ALICE), "Alice")
                self.assertEqual(store.get_feishu_union_id(ALICE), "on_4bf919cda0978cc8aad2abaf6535af87")
                self.assertEqual(store.get_feishu_display_name(BOB), "Bob")
                with mock.patch("feishu.identity._messenger_for", return_value=None):
                    enriched = enrich_feishu_identities(
                        user_ids=[ALICE, "ou_missingmissingmissingmissing"],
                        chat_ids=[CHAT, "oc_mbpass"],
                        store=store,
                    )
                self.assertEqual(enriched["names"][ALICE], "Alice")
                self.assertEqual(enriched["users"][0]["name"], "Alice")
                self.assertEqual(len(enriched["users"]), 1)
                milchick = "ou_12309d90c1d05b757ef1d002b59fc91b"
                store.upsert_feishu_identity(
                    identity_id=milchick,
                    identity_type="user",
                    display_name="Alice",
                    union_id="on_4bf919cda0978cc8aad2abaf6535af87",
                )
                linked = store.expand_feishu_open_ids([ALICE])
                self.assertIn(ALICE, linked)
                self.assertIn(milchick, linked)
                cached = enrich_feishu_identities(
                    user_ids=[ALICE],
                    chat_ids=[CHAT],
                    store=store,
                    network=False,
                )
                self.assertEqual(cached["names"][ALICE], "Alice")
                self.assertEqual(cached["chats"][0]["name"], "")
                self.assertNotEqual(cached["chats"][0]["name"], "mbpass")
            finally:
                store.close()

    def test_unknown_sender_is_kept_as_pending_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            store = GlobalAgentStore()
            try:
                with mock.patch("feishu.identity._messenger_for", return_value=None):
                    from feishu.identity import remember_user_identity

                    remember_user_identity(
                        store=store,
                        open_id=BOB,
                        union_id="on_pending_user",
                        agent_id="mark",
                    )
                self.assertEqual(store.get_feishu_display_name(BOB), "")
                self.assertEqual(store.get_feishu_union_id(BOB), "on_pending_user")
                recent = store.list_recent_feishu_ids()
                self.assertIn(BOB, recent["user_ids"])
                enriched = enrich_feishu_identities(
                    user_ids=[BOB],
                    chat_ids=[],
                    store=store,
                    network=False,
                )
                self.assertTrue(enriched["users"][0]["pending"])
                self.assertEqual(enriched["users"][0]["union_id"], "on_pending_user")
            finally:
                store.close()

    def test_recent_private_contacts_exclude_group_only_senders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            store = GlobalAgentStore()
            try:
                store.record_feishu_user_context(user_id="ou_dm", chat_id="oc_dm", chat_type="p2p")
                store.record_feishu_user_context(user_id="ou_group", chat_id="oc_group", chat_type="group")
                self.assertEqual(["ou_dm"], store.list_recent_feishu_dm_user_ids())
            finally:
                store.close()

    def test_chat_context_separates_group_and_direct_message_candidates(self) -> None:
        group_chat = "oc_abcdef0123456789abcdef0123456789"
        direct_chat = "oc_0123456789abcdef0123456789abcdef"
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            store = GlobalAgentStore()
            try:
                store.record_feishu_chat_context(chat_id=group_chat, chat_type="group")
                store.record_feishu_chat_context(chat_id=direct_chat, chat_type="p2p")
                self.assertEqual([group_chat], store.list_recent_feishu_group_chat_ids())
                self.assertEqual([direct_chat], store.list_recent_feishu_dm_chat_ids())
                self.assertEqual("group", store.get_feishu_chat_context(group_chat))
                self.assertEqual("dm", store.get_feishu_chat_context(direct_chat))
            finally:
                store.close()

    def test_group_discovery_merges_membership_across_agent_apps(self) -> None:
        shared = "oc_abcdef0123456789abcdef0123456789"
        mark_only = "oc_0123456789abcdef0123456789abcdef"

        class FakeMessenger:
            def __init__(self, chats: list[dict[str, str]]) -> None:
                self.chats = chats

            def safe_list_group_chats(self) -> list[dict[str, str]]:
                return self.chats

        messengers = {
            "dylan": FakeMessenger([{"id": shared, "name": "Shared Delivery"}]),
            "mark": FakeMessenger(
                [
                    {"id": shared, "name": "Shared Delivery"},
                    {"id": mark_only, "name": "Mark Only"},
                ]
            ),
        }

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            store = GlobalAgentStore()
            try:
                with mock.patch(
                    "feishu.identity._messenger_for",
                    side_effect=lambda agent_id: messengers.get(agent_id),
                ):
                    chats = discover_feishu_group_chats(store=store)
                self.assertEqual([mark_only, shared], [item["id"] for item in chats])
                self.assertEqual([mark_only, shared], sorted(store.list_recent_feishu_group_chat_ids()))
                shared_item = next(item for item in chats if item["id"] == shared)
                self.assertEqual(["dylan", "mark"], shared_item["agents"])
                self.assertEqual("Shared Delivery", store.get_feishu_display_name(shared))
            finally:
                store.close()

    def test_agent_mentions_are_not_human_identities(self) -> None:
        bot_id = "ou_cccccccccccccccccccccccccccccccc"
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["LUMEN_AGENTS_HOME"] = tmp
            store = GlobalAgentStore()
            try:
                event = {
                    "event": {
                        "message": {
                            "chat_id": CHAT,
                            "chat_type": "group",
                            "mentions": [
                                {
                                    "id": {"open_id": bot_id},
                                    "name": "Mr. Milchick",
                                    "mentioned_type": "bot",
                                }
                            ],
                        }
                    }
                }
                remember_message_identities(event, {"user_id": "", "chat_id": CHAT, "chat_type": "group"})
                self.assertNotIn(bot_id, store.list_recent_feishu_ids()["user_ids"])
                store.upsert_feishu_identity(
                    identity_id=bot_id,
                    identity_type="user",
                    display_name="Mr. Milchick",
                    union_id="on_agent",
                )
                enriched = enrich_feishu_identities(
                    user_ids=[bot_id],
                    chat_ids=[],
                    store=store,
                    network=False,
                )
                self.assertEqual(enriched["users"], [])
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
