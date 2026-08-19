from __future__ import annotations

import re
from typing import Any


# These are product-surface hints, not a project-specific enum.  A project may
# use a different surface name; the model-provided feature point is preserved
# when the evidence does not match one of these generic hints.
_SURFACE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Admin Portal",
        (
            "admin portal",
            "adminportal",
            "backoffice",
            "back office",
            "後台",
            "后台",
            "營運",
            "运营",
            "管理系統",
            "管理系统",
            "cms",
            "dashboard",
        ),
    ),
    (
        "Mobile App",
        (
            "mobile app",
            "ios",
            "android",
            "mobile",
            "行動端",
            "移动端",
            "手機",
            "手机",
        ),
    ),
    (
        "App",
        (
            "app",
            "client",
            "客戶端",
            "客户端",
            "前端",
            "頁面",
            "页面",
            "詳情頁",
            "详情页",
            "首頁",
            "首页",
        ),
    ),
    (
        "API/Backend",
        (
            "api",
            "backend",
            "後端",
            "后端",
            "service",
            "endpoint",
            "webhook",
        ),
    ),
    (
        "Web",
        (
            "web",
            "browser",
            "website",
            "網頁",
            "网页",
        ),
    ),
    (
        "Desktop",
        (
            "desktop",
            "windows",
            "macos",
        ),
    ),
)


def _text(value: Any) -> str:
    if isinstance(value, (list, tuple, set)):
        return "\n".join(str(item or "").strip() for item in value if str(item or "").strip())
    return str(value or "").strip()


def infer_common_surface(*evidence: Any) -> str:
    """Infer a generic product surface from story-local evidence.

    The order intentionally prefers an explicit admin surface over a generic
    page/app hint, and a mobile-specific label over the broader App label.
    It does not inspect a project key or any mbpass-specific brand name.
    """
    text = "\n".join(_text(item) for item in evidence if _text(item)).casefold()
    if not text:
        return ""
    for label, patterns in _SURFACE_PATTERNS:
        for pattern in patterns:
            if re.search(rf"(?<![a-z0-9]){re.escape(pattern)}(?![a-z0-9])", text):
                return label
    return ""


def normalize_feature_point(value: Any, *fallback_evidence: Any) -> str:
    """Return a common C-column value without inventing project terminology."""
    raw = _text(value)
    surface = infer_common_surface(raw, *fallback_evidence)
    if surface:
        return surface
    if raw:
        return raw
    return infer_common_surface(*fallback_evidence) or "Other"
