"""Output sanitization shared by Agent runners, persistence, and Feishu replies."""

from __future__ import annotations

import re


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
