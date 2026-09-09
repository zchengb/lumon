"""Contract tests for the concrete Feishu Webhook integration."""

from __future__ import annotations

import urllib.error
from urllib.request import Request

import pytest

from lumon.errors import InvalidInputError
from lumon.tools.feishu_webhook import (
    FeishuWebhookError,
    FeishuWebhookSender,
    validate_webhook_url,
)


class _Response:
    def __init__(self, body: bytes = b'{"code": 0}', status: int = 200) -> None:
        self.body = body
        self.status = status

    def read(self, amount: int = -1) -> bytes:
        del amount
        return self.body

    def close(self) -> None:
        pass


def _success_opener(request: Request, timeout: float) -> _Response:
    del request, timeout
    return _Response()


def test_sender_posts_a_safe_test_message() -> None:
    sender = FeishuWebhookSender(opener=_success_opener)

    result = sender.send_test("https://open.feishu.cn/open-apis/bot/v2/hook/token")

    assert result.success is True


def test_sender_rejects_nonzero_feishu_response_code() -> None:
    def opener(request: Request, timeout: float) -> _Response:
        del request, timeout
        return _Response(b'{"code": 19001}')

    with pytest.raises(FeishuWebhookError, match="rejected"):
        FeishuWebhookSender(opener=opener).send_test(
            "https://open.feishu.cn/open-apis/bot/v2/hook/token"
        )


def test_sender_hides_transport_details_and_webhook_url() -> None:
    url = "https://open.feishu.cn/open-apis/bot/v2/hook/private-token"

    def opener(request: Request, timeout: float) -> _Response:
        del request, timeout
        raise urllib.error.URLError("network failure")

    with pytest.raises(FeishuWebhookError, match="Unable to reach") as error:
        FeishuWebhookSender(opener=opener).send_test(url)
    assert url not in str(error.value)


def test_webhook_url_requires_https_without_embedded_credentials() -> None:
    with pytest.raises(InvalidInputError, match="HTTPS"):
        validate_webhook_url("http://example.test/hook")
    with pytest.raises(InvalidInputError, match="credentials"):
        validate_webhook_url("https://user:password@example.test/hook")
