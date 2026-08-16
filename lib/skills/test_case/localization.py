from __future__ import annotations

from skills.test_case.config import normalize_test_case_language

CANONICAL_CASE_TYPES = (
    "functional",
    "navigation",
    "filter",
    "permission",
    "validation",
    "state_transition",
    "boundary",
    "empty_state",
    "ui",
    "compatibility",
)

TYPE_LABELS = {
    "zh-Hant": {
        "functional": "功能",
        "navigation": "導航",
        "filter": "篩選",
        "permission": "權限",
        "validation": "驗證",
        "state_transition": "狀態轉換",
        "boundary": "邊界",
        "empty_state": "空狀態",
        "ui": "介面",
        "compatibility": "相容性",
    },
    "zh-Hans": {
        "functional": "功能",
        "navigation": "导航",
        "filter": "筛选",
        "permission": "权限",
        "validation": "校验",
        "state_transition": "状态转换",
        "boundary": "边界",
        "empty_state": "空状态",
        "ui": "界面",
        "compatibility": "兼容性",
    },
    "en": {
        "functional": "Functional",
        "navigation": "Navigation",
        "filter": "Filter",
        "permission": "Permission",
        "validation": "Validation",
        "state_transition": "State Transition",
        "boundary": "Boundary",
        "empty_state": "Empty State",
        "ui": "UI",
        "compatibility": "Compatibility",
    },
}

VERIFY_STATUS_KEYS = ("pending", "passed", "failed", "ignored")

VERIFY_STATUS_LABELS = {
    "zh-Hant": {"pending": "待驗證", "passed": "驗證成功", "failed": "驗證失敗", "ignored": "忽略"},
    "zh-Hans": {"pending": "待验证", "passed": "验证成功", "failed": "验证失败", "ignored": "忽略"},
    "en": {"pending": "Pending", "passed": "Passed", "failed": "Failed", "ignored": "Ignored"},
}

_LEGACY_TYPE_MAP = {
    "functional": "functional",
    "negative": "validation",
    "boundary": "boundary",
    "功能": "functional",
    "導航": "navigation",
    "导航": "navigation",
    "篩選": "filter",
    "筛选": "filter",
    "權限": "permission",
    "权限": "permission",
    "驗證": "validation",
    "校验": "validation",
    "狀態轉換": "state_transition",
    "状态转换": "state_transition",
    "邊界": "boundary",
    "边界": "boundary",
    "空狀態": "empty_state",
    "空状态": "empty_state",
    "介面": "ui",
    "界面": "ui",
    "相容性": "compatibility",
    "兼容性": "compatibility",
    "navigation": "navigation",
    "filter": "filter",
    "permission": "permission",
    "validation": "validation",
    "state_transition": "state_transition",
    "state transition": "state_transition",
    "empty_state": "empty_state",
    "empty state": "empty_state",
    "ui": "ui",
    "compatibility": "compatibility",
}


def normalize_case_type(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    key = raw.lower().replace("-", "_").replace(" ", "_")
    if key in CANONICAL_CASE_TYPES:
        return key
    mapped = _LEGACY_TYPE_MAP.get(raw) or _LEGACY_TYPE_MAP.get(key) or _LEGACY_TYPE_MAP.get(raw.lower())
    return mapped or ""


def localize_test_case_type(case_type: str, language: str) -> str:
    lang = normalize_test_case_language(language)
    key = normalize_case_type(case_type)
    if not key:
        raise ValueError(f"unknown test case type: {case_type!r}")
    labels = TYPE_LABELS.get(lang) or TYPE_LABELS["en"]
    label = labels.get(key)
    if not label:
        raise ValueError(f"unknown test case type: {case_type!r}")
    return label


def localize_verify_status(status_key: str, language: str) -> str:
    lang = normalize_test_case_language(language)
    key = str(status_key or "").strip().lower()
    if key in {"succeed", "success", "pass", "passed"}:
        key = "passed"
    elif key in {"fail", "failed", "failure"}:
        key = "failed"
    elif key in {"pending", "todo", "to_verify", "待驗證", "待验证"}:
        key = "pending"
    elif key in {"ignore", "ignored", "skip", "skipped", "忽略"}:
        key = "ignored"
    labels = VERIFY_STATUS_LABELS.get(lang) or VERIFY_STATUS_LABELS["en"]
    label = labels.get(key)
    if not label:
        raise ValueError(f"unknown verify status: {status_key!r}")
    return label


def localize_verify_status_options(language: str) -> tuple[str, ...]:
    return tuple(localize_verify_status(key, language) for key in VERIFY_STATUS_KEYS)
