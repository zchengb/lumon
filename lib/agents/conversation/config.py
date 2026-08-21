from __future__ import annotations

from dataclasses import dataclass
from typing import Any


NATIVE_PROVIDER_NAMES = frozenset({"cursor", "cursor_cli", "opencode", "codex"})


@dataclass(frozen=True)
class ThreadNativeConfig:
    """Workspace-scoped controls for visible Agent collaboration.

    The migration flag deliberately defaults to disabled.  Existing workspaces
    therefore keep their current routing until ``common.json`` opts in.
    """

    enabled: bool = False
    max_relay_hops: int = 4
    context_max_chars: int = 24000
    # Native providers use the Harness event/tool surface first.  Legacy
    # envelope parsing remains an explicit migration fallback so existing
    # workspaces can be upgraded without losing an in-flight conversation.
    native_first: bool = True
    legacy_compatibility: bool = True
    visible_workstream: bool = True
    native_tools: bool = True
    native_questions: bool = True
    minimum_event_interval_seconds: int = 3
    dedupe_window_seconds: int = 10


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().casefold() in {"1", "true", "yes", "on", "enabled"}


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def native_provider_contract(provider: str, config: ThreadNativeConfig) -> bool:
    """Whether a configured provider should use the native 3.0 contract."""

    normalized = str(provider or "").strip().casefold().replace("-", "_")
    if normalized in {"deepseek", "deepseek_api", "opencode_deepseek"}:
        normalized = "opencode"
    return bool(config.native_first and normalized in NATIVE_PROVIDER_NAMES)


def thread_native_config(
    common: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> ThreadNativeConfig:
    raw_common = common if isinstance(common, dict) else {}
    raw = raw_common.get("agent_collaboration")
    data = raw if isinstance(raw, dict) else {}
    raw_meta = meta if isinstance(meta, dict) else {}
    # ``conversation`` is the 3.0 public config name.  Accept the earlier
    # implementation spelling as a migration alias for already-installed
    # workspaces.
    runtime = raw_common.get("conversation")
    if not isinstance(runtime, dict):
        runtime = raw_common.get("conversation_runtime")
    runtime_data = runtime if isinstance(runtime, dict) else {}

    # Internal test/relay callers may pass an explicit decision.  A message
    # cannot silently enable collaboration; the workspace flag remains the
    # normal production switch.
    enabled = _bool(data.get("thread_native_handoff"), False)
    if "_thread_native_handoff" in raw_meta:
        enabled = _bool(raw_meta.get("_thread_native_handoff"), enabled)
    return ThreadNativeConfig(
        enabled=enabled,
        max_relay_hops=_bounded_int(
            data.get("max_relay_hops"), default=4, minimum=1, maximum=12
        ),
        context_max_chars=_bounded_int(
            data.get("context_max_chars"), default=24000, minimum=4000, maximum=100000
        ),
        native_first=_bool(runtime_data.get("native_first", True), True),
        legacy_compatibility=_bool(runtime_data.get("legacy_compatibility", True), True),
        visible_workstream=_bool(
            runtime_data.get("visible_workstream", data.get("visible_workstream", True)), True
        ),
        native_tools=_bool(runtime_data.get("native_tools", True), True),
        native_questions=_bool(runtime_data.get("native_questions", True), True),
        minimum_event_interval_seconds=_bounded_int(
            runtime_data.get("minimum_event_interval_seconds"), default=3, minimum=0, maximum=60
        ),
        dedupe_window_seconds=_bounded_int(
            runtime_data.get("dedupe_window_seconds"), default=10, minimum=0, maximum=300
        ),
    )
