#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.security.actions import ActionRequest
from agents.security.adapters.feishu import execute_feishu_action
from agents.security.errors import ResourceDenied


def _request(workspace: Path, action: str, arguments: dict[str, object]) -> ActionRequest:
    return ActionRequest(
        agent_id="mark",
        action=action,
        project_slug="mbpass",
        actor_user_id="ou_owner",
        chat_id="oc_group",
        thread_id="omt_thread",
        source_message_id="om_source",
        trace_id="tr_action",
        arguments={"_workspace_path": str(workspace), "chat_type": "group", **arguments},
    )


class FeishuActionTests(unittest.TestCase):
    def test_progress_action_sends_to_current_thread(self) -> None:
        class FakeMessenger:
            def __init__(self, agent_id: str) -> None:
                self.agent_id = agent_id
                self.calls: list[tuple[object, ...]] = []

            def reply_markdown(self, *args: object, **kwargs: object) -> dict[str, object]:
                self.calls.append((*args, kwargs))
                return {"data": {"message_id": "om_progress"}}

        with patch("agents.security.adapters.feishu.FeishuMessenger", FakeMessenger):
            result = execute_feishu_action(
                _request(
                    Path("/tmp/workspace"),
                    "feishu.send_progress",
                    {"phase": "Evidence", "message": "已完成 Jira 核对，接下来检查输出文件。"},
                )
            )

        self.assertEqual("sent", result["status"])
        self.assertEqual("om_progress", result["message_id"])

    def test_file_action_uploads_and_cleans_generated_pdf(self) -> None:
        class FakeMessenger:
            upload_calls: list[Path] = []
            file_calls: list[tuple[object, ...]] = []

            def __init__(self, agent_id: str) -> None:
                self.agent_id = agent_id

            def upload_file(self, path: Path) -> str:
                self.upload_calls.append(path)
                return "file_v2_plan"

            def reply_markdown(self, *args: object, **kwargs: object) -> dict[str, object]:
                return {"data": {"message_id": "om_caption"}}

            def reply_file(self, *args: object, **kwargs: object) -> dict[str, object]:
                self.file_calls.append((*args, kwargs))
                return {"data": {"message_id": "om_file"}}

        with TemporaryDirectory() as directory:
            workspace = Path(directory)
            pdf = workspace / "output" / "pdf" / "plan.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"%PDF-demo")

            with patch("agents.security.adapters.feishu.FeishuMessenger", FakeMessenger):
                result = execute_feishu_action(
                    _request(
                        workspace,
                        "feishu.send_file",
                        {"path": "output/pdf/plan.pdf", "caption": "文件已准备好。"},
                    )
                )

            self.assertEqual("sent", result["status"])
            self.assertEqual("file_v2_plan", result["file_key"])
            self.assertEqual("om_file", result["message_id"])
            self.assertEqual("om_caption", result["caption_message_id"])
            self.assertEqual("output/pdf/plan.pdf", result["path"])
            self.assertTrue(result["cleaned_up"])
            self.assertFalse(pdf.exists())
            self.assertEqual([pdf.resolve()], FakeMessenger.upload_calls)
            self.assertEqual("om_source", FakeMessenger.file_calls[0][0])
            self.assertEqual("file_v2_plan", FakeMessenger.file_calls[0][1])
            self.assertEqual({"reply_in_thread": True}, FakeMessenger.file_calls[0][2])

    def test_file_action_rejects_outside_workspace_and_secrets(self) -> None:
        with TemporaryDirectory() as directory:
            workspace = Path(directory)
            outside = workspace.parent / "outside.pdf"
            outside.write_bytes(b"%PDF-outside")
            try:
                with self.assertRaises(ResourceDenied):
                    execute_feishu_action(
                        _request(workspace, "feishu.send_file", {"path": str(outside)})
                    )

                secret = workspace / ".env"
                secret.write_text("TOKEN=not-for-upload", encoding="utf-8")
                with self.assertRaises(ResourceDenied):
                    execute_feishu_action(
                        _request(workspace, "feishu.send_file", {"path": ".env", "cleanup": False})
                    )
            finally:
                outside.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
