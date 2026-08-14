#!/usr/bin/env python3
from __future__ import annotations

import sys
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.parser import parse_dylan_text
from agents.jobs.broker import AgentJobBroker
from agents.jobs.store import AgentJobStore
from agents.runtime.autonomous import _prepare_feishu_image_context
from feishu.dedup import MessageDeduper
from feishu.handlers import extract_message_meta, extract_text, handle_message_event, should_handle
from feishu.client_registry import FeishuClientConfig
from agents.profiles import PROFILES


class AgentBridgeScanTests(unittest.TestCase):
    def test_parse_scan_run_with_days_and_project(self) -> None:
        action = parse_dylan_text("扫描一下 mbpass 最近七天的代码", known_slugs={"mbpass"})
        self.assertEqual(action.name, "scan.run")
        self.assertEqual(action.params.get("project"), "mbpass")
        self.assertEqual(action.params.get("window_days"), 7)

    def test_parse_status(self) -> None:
        action = parse_dylan_text("刚才的 Scan 完成了吗？")
        self.assertEqual(action.name, "scan.status")

    def test_parse_cancel(self) -> None:
        action = parse_dylan_text("取消刚才的 Scan")
        self.assertEqual(action.name, "scan.cancel")

    def test_dedup_claim_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            deduper = MessageDeduper(Path(tmp) / "dedup.sqlite3")
            self.assertTrue(deduper.claim("msg-1"))
            self.assertFalse(deduper.claim("msg-1"))
            self.assertTrue(deduper.seen("msg-1"))

    def test_extract_text_from_json_content(self) -> None:
        event = {
            "event": {
                "message": {
                    "content": '{"text":"@Dylan 扫描 mbpass"}',
                    "chat_type": "group",
                    "mentions": [{"id": "bot"}],
                }
            }
        }
        self.assertIn("扫描", extract_text(event))

    def test_extract_text_from_feishu_post_content(self) -> None:
        event = {
            "event": {
                "message": {
                    "message_id": "om_image_1",
                    "msg_type": "post",
                    "content": '{"zh_cn":{"title":"Admin Portal","content":[[{"tag":"text","text":"Wording 輪播圖改成多圖"},{"tag":"img","image_key":"img_1"}]]}}',
                }
            }
        }
        text = extract_text(event)
        self.assertIn("Wording 輪播圖改成多圖", text)
        self.assertIn("[Image attachment]", text)
        self.assertEqual('["img_1"]', extract_message_meta(event)["image_keys"])

    def test_image_context_downloads_to_temporary_agent_directory(self) -> None:
        class Messenger:
            def safe_get_message_resource(self, message_id, file_key, *, resource_type):
                self.request = (message_id, file_key, resource_type)
                return b"fake-png", "image/png"

        messenger = Messenger()
        context, directory = _prepare_feishu_image_context(
            meta={"message_id": "om_image_1", "image_keys": '["img_1"]'},
            messenger=messenger,
        )
        try:
            self.assertIn("Open and inspect", context)
            self.assertEqual(("om_image_1", "img_1", "image"), messenger.request)
            self.assertIsNotNone(directory)
            assert directory is not None
            self.assertEqual(b"fake-png", (directory / "image-1.png").read_bytes())
        finally:
            if directory is not None:
                shutil.rmtree(directory, ignore_errors=True)

    def test_extract_text_from_image_message_is_not_empty(self) -> None:
        event = {
            "event": {
                "message": {
                    "msg_type": "image",
                    "content": '{"image_key":"img_1"}',
                }
            }
        }
        self.assertEqual("[Image attachment]", extract_text(event))

    def test_extract_text_from_image_message_with_separate_caption(self) -> None:
        event = {
            "event": {
                "message": {
                    "msg_type": "image",
                    "content": '{"image_key":"img_1"}',
                    "text": "Admin Portal 中的 Wording「輪播圖」改成「多圖」",
                }
            }
        }
        text = extract_text(event)
        self.assertIn("[Image attachment]", text)
        self.assertIn("Wording「輪播圖」改成「多圖」", text)

    def test_extract_text_from_message_read_response_body(self) -> None:
        event = {
            "event": {
                "message": {
                    "msg_type": "post",
                    "body": {
                        "content": '{"content":[[{"tag":"text","text":"Wording 輪播圖改成多圖"}]]}'
                    },
                }
            }
        }
        self.assertIn("Wording 輪播圖改成多圖", extract_text(event))

    def test_handler_recovers_post_text_omitted_from_websocket_image_event(self) -> None:
        from unittest.mock import patch

        client = FeishuClientConfig(
            agent_id="milchick",
            app_id="cli_mil",
            app_secret="secret",
            profile=PROFILES["milchick"],
        )
        event = {
            "event": {
                "sender": {"sender_type": "user"},
                "message": {
                    "message_id": "om_image_1",
                    "msg_type": "image",
                    "chat_type": "group",
                    "mentions": [{"name": "Milchick"}],
                    "content": '{"image_key":"img_1"}',
                },
            }
        }
        response = {
            "data": {
                "items": [
                    {
                        "msg_type": "post",
                        "body": {
                            "content": '{"content":[[{"tag":"text","text":"Admin Portal Wording 輪播圖改成多圖"}]]}'
                        },
                    }
                ]
            }
        }
        with (
            patch("feishu.handlers.FeishuMessenger.safe_get_message", return_value=response),
            patch("feishu.handlers.remember_message_identities"),
            patch("feishu.handlers.handle_agent_message", return_value={}) as handle,
        ):
            handle_message_event(event, client)
        self.assertIn("Wording 輪播圖改成多圖", handle.call_args.kwargs["text"])

    def test_should_handle_requires_mention_in_group(self) -> None:
        client = FeishuClientConfig(
            agent_id="dylan",
            app_id="cli_x",
            app_secret="secret",
            profile=PROFILES["dylan"],
        )
        bare = {"event": {"message": {"chat_type": "group", "mentions": []}}}
        self.assertFalse(should_handle(bare, client))
        mentioned = {"event": {"message": {"chat_type": "group", "mentions": [{"name": "Dylan"}]}}}
        self.assertTrue(should_handle(mentioned, client))

    def test_should_handle_only_mentioned_agent(self) -> None:
        dylan = FeishuClientConfig(
            agent_id="dylan",
            app_id="cli_d",
            app_secret="secret",
            profile=PROFILES["dylan"],
        )
        mark = FeishuClientConfig(
            agent_id="mark",
            app_id="cli_m",
            app_secret="secret",
            profile=PROFILES["mark"],
        )
        only_mark = {"event": {"message": {"chat_type": "group", "mentions": [{"name": "Mark"}]}}}
        self.assertFalse(should_handle(only_mark, dylan))
        self.assertTrue(should_handle(only_mark, mark))

    def test_should_handle_ignores_bot_senders(self) -> None:
        milchick = FeishuClientConfig(
            agent_id="milchick",
            app_id="cli_mil",
            app_secret="secret",
            profile=PROFILES["milchick"],
        )
        bot_in_thread = {
            "event": {
                "sender": {"sender_type": "bot", "sender_id": {"open_id": "ou_mark_bot"}},
                "message": {
                    "chat_type": "group",
                    "mentions": [],
                    "parent_id": "om_user_1",
                    "root_id": "om_user_1",
                    "content": '{"text":"Generated 27 test cases"}',
                },
            }
        }
        self.assertFalse(should_handle(bot_in_thread, milchick))
        app_dm = {
            "event": {
                "sender": {"sender_type": "app", "sender_id": {"open_id": "ou_mark_bot"}},
                "message": {"chat_type": "p2p", "mentions": [], "content": '{"text":"hi"}'},
            }
        }
        self.assertFalse(should_handle(app_dm, milchick))

    def test_should_handle_dylan_thread_reply_without_mention(self) -> None:
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from agents.dylan.reply_anchor import remember_outbound
        from feishu.handlers import extract_message_meta

        dylan = FeishuClientConfig(
            agent_id="dylan",
            app_id="cli_x",
            app_secret="secret",
            profile=PROFILES["dylan"],
        )
        mark = FeishuClientConfig(
            agent_id="mark",
            app_id="cli_m",
            app_secret="secret",
            profile=PROFILES["mark"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"LUMEN_AGENTS_HOME": tmp}):
                remember_outbound(
                    message_id="om_dylan_1",
                    text="Want me to verify?",
                    reply_to="om_user_1",
                    agent_id="dylan",
                )
                reply = {
                    "event": {
                        "message": {
                            "chat_type": "group",
                            "mentions": [],
                            "parent_id": "om_dylan_1",
                            "root_id": "om_user_1",
                            "content": '{"text":"可以，跑一下"}',
                        }
                    }
                }
                self.assertTrue(should_handle(reply, dylan))
                self.assertFalse(should_handle(reply, mark))
                meta = extract_message_meta(
                    {
                        "event": {
                            "message": {
                                "thread_id": "omt_topic_1",
                                "root_id": "om_root",
                                "parent_id": "om_parent",
                            }
                        }
                    }
                )
                self.assertEqual(meta["thread_id"], "omt_topic_1")
                self.assertEqual(meta["root_id"], "om_root")
                meta_no_thread = extract_message_meta(
                    {"event": {"message": {"root_id": "om_root", "parent_id": "om_parent"}}}
                )
                self.assertEqual(meta_no_thread["thread_id"], "")
                self.assertEqual(meta_no_thread["root_id"], "om_root")

    def test_waiting_loop_reply_routes_to_child_owner_without_mention(self) -> None:
        mark = FeishuClientConfig(
            agent_id="mark",
            app_id="cli_m",
            app_secret="secret",
            profile=PROFILES["mark"],
        )
        milchick = FeishuClientConfig(
            agent_id="milchick",
            app_id="cli_mil",
            app_secret="secret",
            profile=PROFILES["milchick"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {"LUMEN_AGENTS_HOME": tmp}):
                store = AgentJobStore(Path(tmp) / "agent_jobs.sqlite3")
                try:
                    broker = AgentJobBroker(store)
                    parent = broker.create_parent(
                        project="mbpass",
                        requested_by="ou_owner",
                        delegated_by="milchick",
                        source_message_id="om-root",
                        chat_id="oc1",
                        thread_id="",
                        trace_id="tr1",
                    )
                    child = broker.create_child(
                        parent=parent,
                        target_agent="mark",
                        capability="loop.technical",
                        input_data={"issue_key": "MBPAS-1503"},
                    )
                    child.status = "waiting_user"
                    child.result = {"question_message_id": "om-question"}
                    store.save(child)
                finally:
                    store.close()
                reply = {
                    "event": {
                        "message": {
                            "chat_id": "oc1",
                            "chat_type": "group",
                            "mentions": [],
                            "parent_id": "om-question",
                            "root_id": "om-root",
                            "content": '{"text":"D：完成 API 層 Technical Plan"}',
                        }
                    }
                }
                self.assertTrue(should_handle(reply, mark))
                self.assertFalse(should_handle(reply, milchick))

    def test_should_reply_in_thread_for_group_mentions(self) -> None:
        from feishu.messenger import should_reply_in_thread

        self.assertTrue(should_reply_in_thread({"chat_type": "group", "thread_id": ""}))
        self.assertFalse(should_reply_in_thread({"chat_type": "p2p", "thread_id": ""}))
        self.assertTrue(should_reply_in_thread({"chat_type": "p2p", "thread_id": "omt_1"}))


if __name__ == "__main__":
    unittest.main()
