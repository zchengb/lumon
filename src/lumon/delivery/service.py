"""Delivery lifecycle orchestration and Webhook notification handling."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from lumon.delivery.model import DeliveryEvent, DeliveryResult, DeliveryRun, DeliveryState
from lumon.delivery.notifications import build_delivery_card
from lumon.delivery.store import DeliveryRunStore
from lumon.errors import LumonError, PreflightError
from lumon.tools.feishu_webhook import FeishuWebhookError, FeishuWebhookSender
from lumon.workspace.settings import WorkspaceSettingsStore


@dataclass(frozen=True, slots=True)
class DeliveryNotification:
    """Safe result of one notification attempt."""

    event: DeliveryEvent
    sent: bool
    skipped: bool
    detail: str


class DeliveryService:
    """Persist lifecycle state and send at-most-once successful notifications."""

    def __init__(
        self,
        settings_store: WorkspaceSettingsStore | None = None,
        webhook_sender: FeishuWebhookSender | None = None,
        run_store: DeliveryRunStore | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.settings_store = settings_store or WorkspaceSettingsStore()
        self.webhook_sender = webhook_sender or FeishuWebhookSender()
        self.run_store = run_store or DeliveryRunStore()
        self.now = now or (lambda: datetime.now(UTC))

    def start(self, workspace: Path, workspace_id: UUID, run: DeliveryRun) -> DeliveryNotification:
        """Persist a claimed run and emit ``delivery.started``."""

        settings = self.settings_store.load(workspace_id)
        if not settings.auto_delivery.enabled:
            raise PreflightError("Auto Delivery is disabled for this Workspace.")
        self.run_store.save(workspace, run)
        return self.notify(workspace, workspace_id, run, DeliveryEvent.STARTED)

    def complete(
        self,
        workspace: Path,
        workspace_id: UUID,
        run: DeliveryRun,
        detail: str,
        *,
        phase: str = "publish",
        repository: str | None = None,
        branch: str | None = None,
        pull_request_url: str | None = None,
        verification_summary: str | None = None,
    ) -> tuple[DeliveryRun, DeliveryNotification]:
        """Persist a successful development result and emit ``delivery.dev_done``."""

        updated = run.with_result(
            DeliveryResult(
                DeliveryState.COMPLETED,
                phase,
                detail,
                published_url=pull_request_url,
                verification_summary=verification_summary,
            ),
            now=self.now(),
            repository=repository,
            branch=branch,
            pull_request_url=pull_request_url,
        )
        self.run_store.save(workspace, updated)
        return updated, self.notify(workspace, workspace_id, updated, DeliveryEvent.DEV_DONE)

    def fail(
        self,
        workspace: Path,
        workspace_id: UUID,
        run: DeliveryRun,
        reason: str,
        *,
        phase: str,
    ) -> tuple[DeliveryRun, DeliveryNotification]:
        """Persist an unexpected failure and emit ``delivery.failed``."""

        updated = run.with_result(
            DeliveryResult(DeliveryState.FAILED, phase, reason),
            now=self.now(),
        )
        self.run_store.save(workspace, updated)
        return updated, self.notify(workspace, workspace_id, updated, DeliveryEvent.FAILED)

    def block(
        self,
        workspace: Path,
        workspace_id: UUID,
        run: DeliveryRun,
        reason: str,
        *,
        phase: str,
    ) -> tuple[DeliveryRun, DeliveryNotification]:
        """Persist a known prerequisite/verification block and notify the user."""

        updated = run.with_result(
            DeliveryResult(DeliveryState.BLOCKED, phase, reason),
            now=self.now(),
        )
        self.run_store.save(workspace, updated)
        return updated, self.notify(workspace, workspace_id, updated, DeliveryEvent.BLOCKED)

    def notify(
        self,
        workspace: Path,
        workspace_id: UUID,
        run: DeliveryRun,
        event: DeliveryEvent | str,
    ) -> DeliveryNotification:
        """Send one event without allowing notification failure to alter run state."""

        event = DeliveryEvent(event)
        if self.run_store.notification_sent(workspace, run.run_id, event):
            return DeliveryNotification(event, sent=False, skipped=True, detail="Already sent.")
        settings = self.settings_store.load(workspace_id).feishu_webhook
        if not settings.enabled:
            return DeliveryNotification(event, sent=False, skipped=True, detail="Webhook disabled.")
        if not settings.url:
            return DeliveryNotification(
                event,
                sent=False,
                skipped=True,
                detail="Webhook URL is not configured.",
            )
        card = build_delivery_card(event, run)
        try:
            result = self.webhook_sender.send_card(settings.url, card)
        except (FeishuWebhookError, LumonError) as exc:
            return DeliveryNotification(event, sent=False, skipped=False, detail=str(exc))
        self.run_store.record_notification(workspace, run.run_id, event, result.detail, self.now())
        return DeliveryNotification(event, sent=True, skipped=False, detail=result.detail)
