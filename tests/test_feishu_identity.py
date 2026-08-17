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
from feishu.identity import enrich_feishu_identities, is_feishu_open_chat_id, is_feishu_open_user_id
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


if __name__ == "__main__":
    unittest.main()
