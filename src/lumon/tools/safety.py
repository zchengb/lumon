"""Output sanitization shared by tools and external communication channels."""

from __future__ import annotations

import re
from urllib.parse import urlsplit


def safe_trace_url(url: object) -> str | None:
    """Accept credential-free Langfuse trace links, including self-hosted instances."""

    if not isinstance(url, str) or len(url) > 2048 or re.search(r"\s", url):
        return None
    try:
        parsed = urlsplit(url)
        _ = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        return None
    if not re.search(r"/project/[A-Za-z0-9_-]+/traces/[0-9a-f]{32}$", parsed.path):
        return None
    return url


def sanitize_output(value: str) -> str:
    """Redact common credential-shaped values before they cross a boundary."""

    result = re.sub(
        r"(?i)(https?://open\.feishu\.(?:cn|com)/[^\s]*?/hook/)[A-Za-z0-9_-]+",
        r"\1[REDACTED]",
        value,
    )
    credential_pattern = (
        r"(?i)((?:app[_ -]?secret|access[_ -]?token|refresh[_ -]?token|"
        r"api[_ -]?key|password|private[_ -]?key|webhook(?:\s+url)?|token)"
        r"\s*[:=]\s*)[^\s,;]+"
    )
    return re.sub(credential_pattern, r"\1[REDACTED]", result)
