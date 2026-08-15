#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
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
from feishu.pdf_renderer import is_plan_document, plan_pdf_filename, render_markdown_pdf


class FeishuMessengerTests(unittest.TestCase):
    def test_long_technical_or_story_plan_is_pdf_eligible(self) -> None:
        technical = "# Technical Plan: MBPAS-1503\n\n" + ("## Section\ncontent\n\n" * 80)
        story = "# Story Plan: MBPAS-1503\n\n" + ("## Section\ncontent\n\n" * 80)
        self.assertTrue(is_plan_document(technical))
        self.assertTrue(is_plan_document(story))
        self.assertEqual("MBPAS-1503-technical-plan.pdf", plan_pdf_filename(technical))
        self.assertEqual("MBPAS-1503-story-plan.pdf", plan_pdf_filename(story))

    def test_plan_reply_uploads_and_replies_with_pdf(self) -> None:
        text = "# Technical Plan: MBPAS-1503\n\n" + ("## Section\ncontent\n\n" * 80)
        messenger = FeishuMessenger("mark")
        with patch("feishu.messenger.render_markdown_pdf") as render, patch.object(
            messenger, "upload_file", return_value="file_v2_plan"
        ) as upload, patch.object(
            messenger, "reply_file", return_value={"data": {"message_id": "om_pdf"}}
        ) as reply_file:
            sent = messenger.safe_reply_text("om_source", text, reply_in_thread=True)

        self.assertEqual("om_pdf", sent["data"]["message_id"])
        render.assert_called_once()
        upload.assert_called_once()
        reply_file.assert_called_once_with("om_source", "file_v2_plan", reply_in_thread=True)

    def test_plan_pdf_renders_readable_document(self) -> None:
        text = """---
status: draft
jiraKey: MBPAS-1503
---

# Technical Plan: MBPAS-1503

## Goal

推薦資料含中文、`GET /articles:recommendations` 與表格。

| AC | Outcome |
|---|---|
| AC5 | Recommendation API |

```mermaid
flowchart TD
  A[文章] --> B[推薦 API]
```
"""
        with TemporaryDirectory() as directory:
            output = render_markdown_pdf(text, Path(directory) / "plan.pdf")
            self.assertTrue(output.is_file())
            self.assertEqual(b"%PDF-", output.read_bytes()[:5])

    def test_outer_markdown_fence_is_removed_but_inner_fences_remain(self) -> None:
        rendered = normalize_markdown_for_feishu(
            "說明如下：\n\n```markdown\n# Technical Plan\n\n```mermaid\nflowchart TD\n```\n```"
        )
        self.assertEqual(
            "說明如下：\n\n# Technical Plan\n\n```mermaid\nflowchart TD\n```",
            rendered,
        )

    def test_metadata_and_tables_are_card_safe(self) -> None:
        rendered = normalize_markdown_for_feishu(
            """---
status: \"draft\"
jiraKey: \"MBPAS-1503\"
featureBranch: \"feature/MBPAS-1503\"
---

## Acceptance Criteria

| Criterion | Outcome |
|---|---|
| AC5 | Recommendation API |
| AC6 | Dealer isolation |
"""
        )
        self.assertIn("### Document metadata", rendered)
        self.assertIn("- **Jira Key:** `MBPAS-1503`", rendered)
        self.assertIn("- **Criterion:** AC5 · **Outcome:** Recommendation API", rendered)
        self.assertNotIn("|---|---|", rendered)

    def test_long_markdown_is_split_for_feishu_cards(self) -> None:
        text = "\n\n".join(f"## Section {i}\ncontent" for i in range(1600))
        parts = split_markdown_for_feishu(text)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(part) <= 12000 for part in parts))
        self.assertEqual(text.replace("\n", ""), "".join(parts).replace("\n", ""))

    def test_safe_reply_renders_document_and_sends_long_plan_in_parts(self) -> None:
        text = "以下是 document.md：\n\n```markdown\n" + ("## Section\ncontent\n\n" * 900) + "```"
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
