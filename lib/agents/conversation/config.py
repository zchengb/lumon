from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ThreadNativeConfig:
    """Workspace-scoped controls for visible Agent collaboration.

    The migration flag deliberately defaults to disabled.  Existing workspaces
    therefore keep their current routing until ``common.json`` opts in.
    """

    enabled: bool = False
    max_relay_hops: int = 4
    context_max_chars: int = 24000


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


def thread_native_config(
    common: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> ThreadNativeConfig:
    raw_common = common if isinstance(common, dict) else {}
    raw = raw_common.get("agent_collaboration")
    data = raw if isinstance(raw, dict) else {}
    raw_meta = meta if isinstance(meta, dict) else {}

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
    )
