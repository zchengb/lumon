"""Send Feishu messages through the current Workspace's saved Webhook."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, cast
from uuid import UUID

import typer

from lumon.errors import LumonError, PreflightError
from lumon.tools.feishu_webhook import FeishuWebhookSender
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import load_manifest
from lumon.workspace.settings import WorkspaceSettingsStore

webhook_app = typer.Typer(
    name="webhook",
    help="Send messages through a Workspace's configured Feishu Webhook.",
    no_args_is_help=True,
    add_completion=False,
)
_MAX_PAYLOAD_BYTES = 256_000


@webhook_app.command("send")
def send(
    payload_file: Annotated[
        Path,
        typer.Option("--payload-file", help="Workspace-relative Feishu JSON payload file."),
    ],
    workspace: Annotated[Path, typer.Option("--workspace", dir_okay=True)] = Path("."),
) -> None:
    """Send a Feishu-supported JSON message using the saved Workspace Webhook."""

    try:
        root, workspace_id = _workspace_identity(workspace)
        payload = _load_payload(root, payload_file)
        webhook = WorkspaceSettingsStore().load(workspace_id).feishu_webhook
        if not webhook.enabled:
            raise PreflightError("Feishu Webhook is disabled for this Workspace.")
        if not webhook.url:
            raise PreflightError("Feishu Webhook is not configured for this Workspace.")

        result = FeishuWebhookSender().send_message(webhook.url, payload)
        typer.echo(result.detail)
    except LumonError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc


def _workspace_identity(workspace: Path) -> tuple[Path, UUID]:
    root = workspace.expanduser().resolve()
    manifest = load_manifest(WorkspaceLayout.from_root(root).manifest)
    return root, manifest.workspace_id


def _load_payload(workspace: Path, payload_file: Path) -> dict[str, object]:
    candidate = payload_file.expanduser()
    if not candidate.is_absolute():
        candidate = workspace / candidate
    if candidate.is_symlink():
        raise PreflightError("Webhook payload file must not be a symbolic link.")
    try:
        path = candidate.resolve(strict=True)
        path.relative_to(workspace)
        raw_payload = path.read_bytes()
    except (OSError, ValueError) as exc:
        raise PreflightError("Webhook payload file must be inside the Workspace.") from exc
    if len(raw_payload) > _MAX_PAYLOAD_BYTES:
        raise PreflightError("Webhook payload exceeds the 256 KB limit.")
    try:
        parsed: object = json.loads(raw_payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreflightError("Webhook payload must contain valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise PreflightError("Webhook payload must be a JSON object.")
    payload = cast(dict[str, object], parsed)
    message_type = payload.get("msg_type")
    if not isinstance(message_type, str) or not message_type.strip():
        raise PreflightError("Webhook payload must include a non-empty msg_type.")
    return payload
