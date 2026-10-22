"""Output sanitization shared by tools and external communication channels."""

from __future__ import annotations

import re
from urllib.parse import urlsplit


def sanitize_command(command: str) -> str:
    """Keep a bounded command preview, without common credentials or prompt arguments."""

    redacted = re.sub(
        r"-----BEGIN [A-Z0-9 ]+-----.*?(?:-----END [A-Z0-9 ]+-----|$)",
        "[REDACTED]",
        command,
        flags=re.DOTALL | re.IGNORECASE,
    )
    argument = r"""(?:"(?:\\.|[^"\\])*"|'[^']*'|[^\s,;&]+)"""
    redacted = re.sub(
        r"""(?ix)((?:--|\b)[\w-]*(?:token|secret|password|passwd|api[_-]?key|"""
        r"""credential|webhook|prompt|instructions)[\w-]*["']?\s*(?:[:=]\s*|\s+))""" + argument,
        r"\1[REDACTED]",
        redacted,
    )
    redacted = re.sub(r"(?i)(Bearer\s+)[\w.~+/=-]+", r"\1[REDACTED]", redacted)
    redacted = re.sub(
        r"(?i)((?:^|\s)(?:-u|--user|-p|-d|--data(?:-raw|-binary)?|-H|--header|-c)\s+)" + argument,
        r"\1[REDACTED]",
        redacted,
    )
    redacted = re.sub(r"(https?://)[^/\s:@]+:[^@\s/]+@", r"\1[REDACTED]@", redacted)
    # Script bodies can contain whole prompts or private documents, not just commands.
    redacted = re.sub(r"(?s)(<<[^\n]*\n).*", r"\1[script body omitted]", redacted)
    redacted = sanitize_output(redacted).strip()
    encoded = redacted.encode("utf-8")
    return encoded[:1024].decode("utf-8", errors="ignore").rstrip() + (
        " … [truncated]" if len(encoded) > 1024 else ""
    )


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
