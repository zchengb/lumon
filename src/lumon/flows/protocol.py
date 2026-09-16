"""Small control markers exchanged between Mark and the Codex runner."""

from __future__ import annotations

import json
import re
from typing import cast

_FLOW_MARKER_RE = re.compile(
    r"<lumon-flow>\s*(?P<payload>\{.*?\})\s*</lumon-flow>",
    re.IGNORECASE | re.DOTALL,
)
_FLOW_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def extract_flow_selection(text: str | None) -> tuple[str | None, str | None, str]:
    """Remove a control marker and return its safe selected flow ID."""

    value = str(text or "")
    match = _FLOW_MARKER_RE.search(value)
    if match is None:
        return None, None, value
    cleaned = (value[: match.start()] + value[match.end() :]).strip()
    try:
        payload = json.loads(match.group("payload"))
    except json.JSONDecodeError:
        return None, None, cleaned
    if not isinstance(payload, dict):
        return None, None, cleaned
    payload_dict = cast(dict[str, object], payload)
    flow_id = payload_dict.get("flow_id")
    status = payload_dict.get("status")
    if (
        not isinstance(flow_id, str)
        or _FLOW_ID_RE.fullmatch(flow_id.strip()) is None
        or status != "selected"
    ):
        return None, str(status) if isinstance(status, str) else None, cleaned
    return flow_id.strip(), "selected", cleaned
