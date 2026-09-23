"""Typed, user-level configuration for one Lumon Workspace."""

from __future__ import annotations

import os
import re
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit
from uuid import UUID

from lumon.errors import InvalidInputError, PreflightError
from lumon.tools.feishu_webhook import validate_webhook_url
from lumon.workspace.registry import UserStateLayout

SETTINGS_SCHEMA_VERSION = 1
DEFAULT_AUTO_DELIVERY_HOOKS = ("jira.delivery_ready",)
DEFAULT_AUTO_DELIVERY_SCHEDULE = "*/5 * * * *"
DEFAULT_AUTO_SCAN_HOOKS: tuple[str, ...] = ()
DEFAULT_AUTO_SCAN_SCHEDULE = "0 12 * * 1-5"
DEFAULT_AUTO_SCAN_DESCRIPTION = (
    "Review recent repository changes for confirmed production-impacting bugs. "
    "Keep the review evidence-based and report-only."
)
_HOOK_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._:-]{0,63}\Z")
_CRON_FIELD_PATTERN = re.compile(
    r"(?:\*|\*/[1-9][0-9]*|[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*)\Z"
)


@dataclass(frozen=True, slots=True)
class FeishuWebhookSettings:
    """The v1 Feishu Webhook settings for one Workspace."""

    enabled: bool = False
    url: str | None = None


@dataclass(frozen=True, slots=True)
class AutoDeliverySettings:
    """Workspace permission for automated Story delivery."""

    enabled: bool = False
    trigger_hooks: tuple[str, ...] = DEFAULT_AUTO_DELIVERY_HOOKS
    schedule_expression: str = DEFAULT_AUTO_DELIVERY_SCHEDULE


@dataclass(frozen=True, slots=True)
class AutoScanSettings:
    """Workspace configuration for scheduled, review-only code scans."""

    enabled: bool = False
    lookback_days: int = 7
    trigger_hooks: tuple[str, ...] = DEFAULT_AUTO_SCAN_HOOKS
    schedule_expression: str = DEFAULT_AUTO_SCAN_SCHEDULE
    workflow_description: str = DEFAULT_AUTO_SCAN_DESCRIPTION


@dataclass(frozen=True, slots=True)
class WorkspaceSettings:
    """All typed, mutable settings owned by one Workspace profile."""

    workspace_id: UUID
    feishu_webhook: FeishuWebhookSettings = FeishuWebhookSettings()
    auto_delivery: AutoDeliverySettings = AutoDeliverySettings()
    auto_scan: AutoScanSettings = AutoScanSettings()


class WorkspaceSettingsStore:
    """Read and atomically update per-Workspace TOML profiles."""

    def __init__(self, state_root: Path | None = None) -> None:
        self.layout = UserStateLayout.from_root(state_root)

    def path_for(self, workspace_id: UUID) -> Path:
        """Return the user-level configuration path for one Workspace."""

        return self.layout.profile(workspace_id)

    def load(self, workspace_id: UUID) -> WorkspaceSettings:
        """Load a profile, returning safe defaults when it has not been created."""

        path = self.path_for(workspace_id)
        if not path.exists():
            return WorkspaceSettings(workspace_id)
        try:
            payload = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise PreflightError(f"Unable to read Workspace settings: {path}") from exc
        return _parse_settings(payload, path, workspace_id)

    def ensure(self, workspace_id: UUID) -> WorkspaceSettings:
        """Create a default profile only when the Workspace has no profile yet."""

        path = self.path_for(workspace_id)
        if path.exists():
            _secure_file(path)
            return self.load(workspace_id)
        settings = WorkspaceSettings(workspace_id)
        self.save(settings)
        return settings

    def save(self, settings: WorkspaceSettings) -> None:
        """Validate and atomically write one profile with owner-only permissions."""

        if settings.feishu_webhook.url is not None:
            validate_webhook_url(settings.feishu_webhook.url)
        _validate_auto_delivery(settings.auto_delivery)
        _validate_auto_scan(settings.auto_scan)
        path = self.path_for(settings.workspace_id)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise PreflightError(
                f"Unable to create Lumon Workspace profile directory: {path.parent}"
            ) from exc
        _secure_directory(self.layout.root)
        _secure_directory(self.layout.profiles)
        _secure_directory(path.parent)
        _atomic_write(path, _render(settings).encode("utf-8"), mode=0o600)

    def remove(self, workspace_id: UUID) -> None:
        """Remove one user-level profile and any empty profile directories."""

        path = self.path_for(workspace_id)
        try:
            path.unlink(missing_ok=True)
            if path.parent.is_dir() and not any(path.parent.iterdir()):
                path.parent.rmdir()
            if self.layout.profiles.is_dir() and not any(self.layout.profiles.iterdir()):
                self.layout.profiles.rmdir()
        except OSError as exc:
            raise PreflightError(f"Unable to remove Workspace settings: {path}") from exc

    def raw_snapshot(self, workspace_id: UUID) -> bytes | None:
        """Capture one profile's exact bytes for a surrounding transaction."""

        path = self.path_for(workspace_id)
        if not path.exists():
            return None
        try:
            return path.read_bytes()
        except OSError as exc:
            raise PreflightError(f"Unable to snapshot Workspace settings: {path}") from exc

    def restore_raw(self, workspace_id: UUID, snapshot: bytes | None) -> None:
        """Restore or remove one profile after a failed transaction."""

        path = self.path_for(workspace_id)
        if snapshot is None:
            try:
                path.unlink(missing_ok=True)
            except OSError as exc:
                raise PreflightError(f"Unable to roll back Workspace settings: {path}") from exc
            return
        _atomic_write(path, snapshot, mode=0o600)


def masked_webhook_url(url: str | None) -> str | None:
    """Return a URL with the Webhook token's middle portion masked."""

    if not url:
        return None
    parsed = urlsplit(url)
    host = parsed.hostname or "configured"
    path = parsed.path or "/"
    last_slash = path.rfind("/")
    token = path[last_slash + 1 :]
    if token:
        path = f"{path[: last_slash + 1]}{_mask_middle(token)}"
    return f"{parsed.scheme}://{host}{path}"


def masked_secret(value: str | None) -> str | None:
    """Return a credential with only a short prefix and suffix visible."""

    return _mask_middle(value) if value else None


def _mask_middle(value: str) -> str:
    """Keep a short prefix and suffix while masking the value's middle."""

    if len(value) <= 2:
        return "*" * len(value)
    visible = 1 if len(value) <= 8 else 4
    middle_length = len(value) - (visible * 2)
    return f"{value[:visible]}{'*' * middle_length}{value[-visible:]}"


def _parse_settings(
    payload: dict[str, object], source: Path, workspace_id: UUID
) -> WorkspaceSettings:
    schema_version = payload.get("schema_version")
    raw_id = payload.get("workspace_id")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != SETTINGS_SCHEMA_VERSION
    ):
        raise PreflightError(f"Unsupported Workspace settings schema: {source}")
    if not isinstance(raw_id, str) or raw_id != str(workspace_id):
        raise PreflightError(f"Workspace settings ID does not match its profile: {source}")

    raw_feishu = payload.get("feishu", {})
    if not isinstance(raw_feishu, dict):
        raise PreflightError(f"Invalid Feishu settings: {source}")
    raw_webhook = cast(dict[str, object], raw_feishu).get("webhook", {})
    if not isinstance(raw_webhook, dict):
        raise PreflightError(f"Invalid Feishu Webhook settings: {source}")
    webhook = cast(dict[str, object], raw_webhook)
    enabled = webhook.get("enabled", False)
    url = webhook.get("url")
    if not isinstance(enabled, bool):
        raise PreflightError(f"Invalid Feishu Webhook enabled value: {source}")
    if url is not None and (not isinstance(url, str) or not url.strip()):
        raise PreflightError(f"Invalid Feishu Webhook URL value: {source}")
    if isinstance(url, str):
        try:
            validate_webhook_url(url)
        except InvalidInputError as exc:
            raise PreflightError(f"Invalid Feishu Webhook URL value: {source}") from exc
    raw_auto_delivery = payload.get("auto_delivery", {})
    if not isinstance(raw_auto_delivery, dict):
        raise PreflightError(f"Invalid Auto Delivery settings: {source}")
    auto_delivery = cast(dict[str, object], raw_auto_delivery)
    auto_delivery_enabled = auto_delivery.get("enabled", False)
    if not isinstance(auto_delivery_enabled, bool):
        raise PreflightError(f"Invalid Auto Delivery enabled value: {source}")
    try:
        trigger_hooks = normalize_trigger_hooks(
            auto_delivery.get("trigger_hooks", DEFAULT_AUTO_DELIVERY_HOOKS)
        )
        schedule_expression = validate_schedule_expression(
            auto_delivery.get("schedule_expression", DEFAULT_AUTO_DELIVERY_SCHEDULE)
        )
    except InvalidInputError as exc:
        raise PreflightError(f"Invalid Auto Delivery settings: {source}") from exc
    raw_auto_scan = payload.get("auto_scan", {})
    if not isinstance(raw_auto_scan, dict):
        raise PreflightError(f"Invalid Auto Scan settings: {source}")
    auto_scan = cast(dict[str, object], raw_auto_scan)
    auto_scan_enabled = auto_scan.get("enabled", False)
    lookback_days = auto_scan.get("lookback_days", 7)
    workflow_description = auto_scan.get("workflow_description", DEFAULT_AUTO_SCAN_DESCRIPTION)
    if not isinstance(auto_scan_enabled, bool):
        raise PreflightError(f"Invalid Auto Scan enabled value: {source}")
    if (
        not isinstance(lookback_days, int)
        or isinstance(lookback_days, bool)
        or not 1 <= lookback_days <= 365
    ):
        raise PreflightError(f"Invalid Auto Scan lookback_days value: {source}")
    if not isinstance(workflow_description, str) or not workflow_description.strip():
        raise PreflightError(f"Invalid Auto Scan workflow_description value: {source}")
    if len(workflow_description.strip()) > 8_000:
        raise PreflightError(f"Auto Scan workflow_description is too long: {source}")
    try:
        scan_hooks = normalize_trigger_hooks(
            auto_scan.get("trigger_hooks", DEFAULT_AUTO_SCAN_HOOKS),
            allow_empty=True,
            label="Auto Scan",
        )
        scan_schedule = validate_schedule_expression(
            auto_scan.get("schedule_expression", DEFAULT_AUTO_SCAN_SCHEDULE),
            label="Auto Scan",
        )
    except InvalidInputError as exc:
        raise PreflightError(f"Invalid Auto Scan settings: {source}") from exc
    return WorkspaceSettings(
        workspace_id=workspace_id,
        feishu_webhook=FeishuWebhookSettings(enabled=enabled, url=url),
        auto_delivery=AutoDeliverySettings(
            enabled=auto_delivery_enabled,
            trigger_hooks=trigger_hooks,
            schedule_expression=schedule_expression,
        ),
        auto_scan=AutoScanSettings(
            enabled=auto_scan_enabled,
            lookback_days=lookback_days,
            trigger_hooks=scan_hooks,
            schedule_expression=scan_schedule,
            workflow_description=workflow_description.strip(),
        ),
    )


def _render(settings: WorkspaceSettings) -> str:
    lines = [
        f"schema_version = {SETTINGS_SCHEMA_VERSION}",
        f"workspace_id = {_toml_string(str(settings.workspace_id))}",
        "",
        "[feishu.webhook]",
        f"enabled = {'true' if settings.feishu_webhook.enabled else 'false'}",
    ]
    if settings.feishu_webhook.url:
        lines.append(f"url = {_toml_string(settings.feishu_webhook.url)}")
    lines.extend(
        [
            "",
            "[auto_delivery]",
            f"enabled = {'true' if settings.auto_delivery.enabled else 'false'}",
            f"trigger_hooks = {_toml_array(settings.auto_delivery.trigger_hooks)}",
            f"schedule_expression = {_toml_string(settings.auto_delivery.schedule_expression)}",
            "",
            "[auto_scan]",
            f"enabled = {'true' if settings.auto_scan.enabled else 'false'}",
            f"lookback_days = {settings.auto_scan.lookback_days}",
            f"trigger_hooks = {_toml_array(settings.auto_scan.trigger_hooks)}",
            f"schedule_expression = {_toml_string(settings.auto_scan.schedule_expression)}",
            f"workflow_description = {_toml_string(settings.auto_scan.workflow_description)}",
        ]
    )
    return "\n".join(lines) + "\n"


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"


def normalize_trigger_hooks(
    values: object,
    *,
    allow_empty: bool = False,
    label: str = "Auto Delivery",
) -> tuple[str, ...]:
    """Normalize declarative trigger IDs without accepting executable input."""

    candidates: tuple[object, ...]
    if isinstance(values, str):
        candidates = tuple(values.splitlines())
    elif isinstance(values, list):
        candidates = tuple(cast(list[object], values))
    elif isinstance(values, tuple):
        candidates = tuple(cast(tuple[object, ...], values))
    else:
        raise InvalidInputError(f"{label} trigger_hooks must be a list of IDs.")

    normalized: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, str):
            raise InvalidInputError(f"{label} trigger hooks must be strings.")
        hook = candidate.strip()
        if not hook:
            continue
        if not _HOOK_ID_PATTERN.fullmatch(hook):
            raise InvalidInputError(f"Invalid {label} trigger hook ID: {hook!r}.")
        if hook not in normalized:
            normalized.append(hook)
    if not normalized and not allow_empty:
        raise InvalidInputError(f"{label} requires at least one trigger hook.")
    return tuple(normalized)


def validate_schedule_expression(value: object, *, label: str = "Auto Delivery") -> str:
    """Validate the supported five-field numeric cron expression."""

    if not isinstance(value, str):
        raise InvalidInputError(f"{label} schedule_expression must be a string.")
    expression = value.strip()
    fields = expression.split()
    if len(fields) != 5 or any(not _CRON_FIELD_PATTERN.fullmatch(field) for field in fields):
        raise InvalidInputError(
            f"{label} schedule_expression must contain five numeric cron fields."
        )
    return expression


def _validate_auto_delivery(settings: AutoDeliverySettings) -> None:
    """Validate all values that control a scheduled Auto Delivery poll."""

    normalize_trigger_hooks(settings.trigger_hooks)
    validate_schedule_expression(settings.schedule_expression)


def _validate_auto_scan(settings: AutoScanSettings) -> None:
    """Validate all values that control a scheduled Auto Scan poll."""

    if not 1 <= settings.lookback_days <= 365:
        raise InvalidInputError("Auto Scan lookback_days must be between 1 and 365.")
    if not settings.workflow_description.strip():
        raise InvalidInputError("Auto Scan workflow_description must not be empty.")
    if len(settings.workflow_description) > 8_000:
        raise InvalidInputError("Auto Scan workflow_description is too long.")
    normalize_trigger_hooks(
        settings.trigger_hooks,
        allow_empty=True,
        label="Auto Scan",
    )
    validate_schedule_expression(settings.schedule_expression, label="Auto Scan")


def _secure_directory(path: Path) -> None:
    try:
        path.chmod(0o700)
    except OSError as exc:
        raise PreflightError(f"Unable to secure Lumon user directory: {path}") from exc


def _secure_file(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError as exc:
        raise PreflightError(f"Unable to secure Workspace settings: {path}") from exc


def _atomic_write(path: Path, content: bytes, mode: int) -> None:
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(temporary_name)
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        path.chmod(mode)
    except OSError as exc:
        raise PreflightError(f"Unable to write Workspace settings: {path}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
