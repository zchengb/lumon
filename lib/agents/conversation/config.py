from __future__ import annotations

from dataclasses import dataclass
from typing import Any


NATIVE_PROVIDER_NAMES = frozenset({"cursor", "cursor_cli", "opencode", "codex"})
SUPPORTED_REPLY_LANGUAGES = frozenset({"en", "zh-Hans", "zh-Hant"})
DEFAULT_REPLY_LANGUAGE = "zh-Hant"


@dataclass(frozen=True)
class ThreadNativeConfig:
    """Workspace-scoped controls for visible Agent collaboration.

    Native-first is the default for new workspaces. Existing sessions are
    migrated by the runtime contract version and may opt into compatibility.
    """

    enabled: bool = False
    version: str = "3.3"
    default_language: str = DEFAULT_REPLY_LANGUAGE
    max_relay_hops: int = 4
    context_max_chars: int = 24000
    # Native providers use the Harness event/tool surface first.  Legacy
    # envelope parsing remains an explicit migration fallback so existing
    # workspaces can be upgraded without losing an in-flight conversation.
    native_first: bool = True
    legacy_compatibility: bool = False
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


def normalize_reply_language(value: Any, default: str = DEFAULT_REPLY_LANGUAGE) -> str:
    """Normalize the small, provider-neutral reply-language vocabulary."""

    raw = str(value or "").strip()
    aliases = {
        "english": "en",
        "en-us": "en",
        "en-gb": "en",
        "简体中文": "zh-Hans",
        "simplified chinese": "zh-Hans",
        "zh-cn": "zh-Hans",
        "zh-sg": "zh-Hans",
        "繁體中文": "zh-Hant",
        "traditional chinese": "zh-Hant",
        "zh-tw": "zh-Hant",
        "zh-hk": "zh-Hant",
        "zh-mo": "zh-Hant",
    }
    normalized = aliases.get(raw.casefold(), raw)
    if normalized in SUPPORTED_REPLY_LANGUAGES:
        return normalized
    fallback = aliases.get(str(default or "").strip().casefold(), str(default or "").strip())
    return fallback if fallback in SUPPORTED_REPLY_LANGUAGES else DEFAULT_REPLY_LANGUAGE


def conversation_runtime_version(common: dict[str, Any] | None = None, default: str = "3.3") -> str:
    """Return the configured conversation contract version without inventing one."""

    data = common if isinstance(common, dict) else {}
    runtime = data.get("conversation")
    if not isinstance(runtime, dict):
        runtime = data.get("conversation_runtime")
    runtime = runtime if isinstance(runtime, dict) else {}
    value = str(runtime.get("version") or default).strip()
    return value or default


def native_provider_contract(provider: str, config: ThreadNativeConfig) -> bool:
    """Whether a configured provider should use the configured native contract."""

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
    configured_language = runtime_data.get("default_language", DEFAULT_REPLY_LANGUAGE)
    if "_default_language" in raw_meta:
        configured_language = raw_meta.get("_default_language")
    configured_version = conversation_runtime_version(raw_common)
    if "_conversation_version" in raw_meta:
        candidate_version = str(raw_meta.get("_conversation_version") or "").strip()
        if candidate_version:
            configured_version = candidate_version
    return ThreadNativeConfig(
        enabled=enabled,
        version=configured_version,
        default_language=normalize_reply_language(configured_language),
        max_relay_hops=_bounded_int(
            data.get("max_relay_hops"), default=4, minimum=1, maximum=12
        ),
        context_max_chars=_bounded_int(
            data.get("context_max_chars"), default=24000, minimum=4000, maximum=100000
        ),
        native_first=_bool(runtime_data.get("native_first", True), True),
        legacy_compatibility=_bool(runtime_data.get("legacy_compatibility", False), False),
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
