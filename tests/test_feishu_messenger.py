#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from feishu.messenger import (
    FeishuMessenger,
    normalize_markdown_for_feishu,
    split_markdown_for_feishu,
)


class FeishuMessengerTests(unittest.TestCase):
    def test_outer_markdown_fence_is_removed_but_inner_fences_remain(self) -> None:
        rendered = normalize_markdown_for_feishu(
            "說明如下：\n\n```markdown\n# Technical Plan\n\n```mermaid\nflowchart TD\n```\n```"
        )
        self.assertEqual(
            "說明如下：\n\n# Technical Plan\n\n```mermaid\nflowchart TD\n```",
            rendered,
        )

    def test_long_markdown_is_split_for_feishu_cards(self) -> None:
        text = "\n\n".join(f"## Section {i}\ncontent" for i in range(1600))
        parts = split_markdown_for_feishu(text)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(part) <= 12000 for part in parts))
        self.assertEqual(text.replace("\n", ""), "".join(parts).replace("\n", ""))

    def test_safe_reply_renders_document_and_sends_long_plan_in_parts(self) -> None:
        text = "以下是 technical-plan.md：\n\n```markdown\n" + ("## Section\ncontent\n\n" * 900) + "```"
        messenger = FeishuMessenger("mark")
        responses: list[dict] = []

        def post(_url: str, _token: str, payload: dict) -> dict:
            responses.append(payload)
            return {"data": {"message_id": f"om_{len(responses)}"}}

        with patch.object(messenger, "tenant_token", return_value="tenant-token"), patch.object(
            messenger, "_post", side_effect=post
        ):
            sent = messenger.safe_reply_text("om_source", text, reply_in_thread=True)

        self.assertEqual(f"om_{len(responses)}", sent["data"]["message_id"])
        self.assertGreater(len(responses), 1)
        for payload in responses:
            self.assertEqual("interactive", payload["msg_type"])
            card = json.loads(payload["content"])
            content = card["body"]["elements"][0]["content"]
            self.assertNotIn("```markdown", content)
            self.assertLessEqual(len(content), 12000)

    def test_get_message_resource_downloads_image_bytes(self) -> None:
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b"fake-png"
        response.headers.get.return_value = "image/png"
        messenger = FeishuMessenger("milchick")
        with patch.object(messenger, "tenant_token", return_value="tenant-token"), patch(
            "feishu.messenger.urllib.request.urlopen", return_value=response
        ) as urlopen:
            body, content_type = messenger.get_message_resource("om_1", "img_1")

        self.assertEqual(b"fake-png", body)
        self.assertEqual("image/png", content_type)
        request = urlopen.call_args.args[0]
        self.assertIn("/messages/om_1/resources/img_1?type=image", request.full_url)
        self.assertEqual("Bearer tenant-token", request.headers["Authorization"])


if __name__ == "__main__":
    unittest.main()
