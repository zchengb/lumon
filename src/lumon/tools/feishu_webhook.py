"""Send the smallest safe test message to a Feishu Webhook."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast
from urllib.parse import urlsplit

from lumon.errors import InvalidInputError, LumonError


class FeishuWebhookError(LumonError):
    """The Feishu Webhook rejected or could not receive a test message."""


class WebhookResponse(Protocol):
    """The small response surface needed by the Webhook sender."""

    status: int

    def read(self, amount: int = -1) -> bytes: ...

    def close(self) -> None: ...


WebhookOpener = Callable[..., WebhookResponse]


@dataclass(frozen=True, slots=True)
class WebhookTestResult:
    """The safe, non-sensitive outcome of a Webhook test."""

    success: bool
    detail: str


class FeishuWebhookSender:
    """Send Feishu test messages behind one small network seam."""

    def __init__(self, opener: WebhookOpener | None = None, timeout: float = 10.0) -> None:
        self._opener = opener or urllib.request.urlopen
        self._timeout = timeout

    def send_test(self, url: str) -> WebhookTestResult:
        """Send a harmless text message without exposing the URL in errors."""

        validate_webhook_url(url)
        payload = json.dumps(
            {
                "msg_type": "text",
                "content": {"text": "Lumon Webhook test"},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        response: WebhookResponse | None = None
        try:
            opened = self._opener(request, timeout=self._timeout)
            response = opened
            status = opened.status
            body = opened.read(16_384)
        except urllib.error.HTTPError as exc:
            raise FeishuWebhookError(
                f"Feishu Webhook test failed with HTTP status {exc.code}."
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise FeishuWebhookError("Unable to reach the Feishu Webhook.") from exc
        finally:
            if response is not None:
                response.close()

        if status < 200 or status >= 300:
            raise FeishuWebhookError(f"Feishu Webhook test failed with HTTP status {status}.")
        _validate_feishu_response(body)
        return WebhookTestResult(True, "Feishu Webhook test message sent.")


def validate_webhook_url(url: str) -> None:
    """Require an HTTPS URL without embedded credentials."""

    try:
        parsed = urlsplit(url.strip())
        hostname = parsed.hostname
    except ValueError as exc:
        raise InvalidInputError("Feishu Webhook URL must be a valid HTTPS URL.") from exc
    if parsed.scheme != "https" or not hostname:
        raise InvalidInputError("Feishu Webhook URL must be an HTTPS URL.")
    if parsed.username or parsed.password:
        raise InvalidInputError("Feishu Webhook URL must not contain credentials.")


def _validate_feishu_response(body: bytes) -> None:
    if not body:
        return
    try:
        raw_payload: object = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return
    if not isinstance(raw_payload, dict):
        return
    payload = cast(dict[str, object], raw_payload)
    code = payload.get("code")
    if isinstance(code, int) and code != 0:
        raise FeishuWebhookError("Feishu Webhook rejected the test message.")
