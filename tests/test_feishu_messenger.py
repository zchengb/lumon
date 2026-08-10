#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from feishu.messenger import FeishuMessenger


class FeishuMessengerTests(unittest.TestCase):
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
