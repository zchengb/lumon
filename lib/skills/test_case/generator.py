from __future__ import annotations

import re
from typing import Any

from skills.test_case.models import StoryContext, TestCase

_AC_TITLE = re.compile(r"^(AC\s*\d+)\s*:\s*(.+)$", re.IGNORECASE | re.DOTALL)


def _normalize_language(value: str) -> str:
    raw = str(value or "").strip().lower().replace("_", "-")
    if raw in {"zh-hant", "zh-tw", "zh-hk", "zh-mo", "zh", "zh-cht", "traditional", "zh-traditional"}:
        return "zh-Hant"
    if raw in {"zh-hans", "zh-cn", "zh-sg", "simplified"}:
        return "zh-Hans"
    return "en"


def _steps(*lines: str) -> str:
    return "\n".join(f"{idx}. {line}" for idx, line in enumerate(lines, start=1) if str(line).strip())


def _ac_parts(ac: str) -> tuple[str, str]:
    text = str(ac or "").strip()
    match = _AC_TITLE.match(text)
    if match:
        return match.group(1).replace(" ", "").upper(), match.group(2).strip()
    return "", text


def _first_line(text: str, limit: int = 120) -> str:
    line = str(text or "").strip().splitlines()[0].strip() if str(text or "").strip() else ""
    return line[:limit]


def generate_test_cases(
    story: StoryContext,
    *,
    workspace_context: dict[str, Any] | None = None,
    language: str = "zh-Hant",
) -> list[TestCase]:
    lang = _normalize_language(language)
    criteria = list(story.acceptance_criteria or [])
    if not criteria:
        criteria = [story.summary or f"Validate {story.key}"]
    cases: list[TestCase] = []
    title = story.summary or story.key
    for index, ac in enumerate(criteria, start=1):
        ac_id, ac_body = _ac_parts(ac)
        label = ac_id or f"AC{index}"
        focus = _first_line(ac_body) or _first_line(ac) or title
        if lang in {"zh-Hant", "zh-Hans"}:
            cases.extend(
                [
                    TestCase(
                        title=f"{label} 正常路徑：{focus}",
                        steps=_steps(
                            f"依 Story「{title}」進入對應功能畫面／流程",
                            f"依驗收條件執行：{focus}",
                            "確認畫面狀態、資料與提示訊息符合預期",
                        ),
                        expected_result=f"滿足驗收條件：{focus}",
                        case_type="functional",
                        story_key=story.key,
                        story_title=title,
                    ),
                    TestCase(
                        title=f"{label} 負向路徑：{focus}",
                        steps=_steps(
                            f"準備不符合「{focus}」的無效、缺漏或未授權條件",
                            "以相同操作路徑再次嘗試",
                            "記錄系統阻擋方式與錯誤／空白態提示",
                        ),
                        expected_result="系統應阻擋或清楚提示失敗，且不破壞既有有效資料。",
                        case_type="validation",
                        story_key=story.key,
                        story_title=title,
                    ),
                    TestCase(
                        title=f"{label} 邊界路徑：{focus}",
                        steps=_steps(
                            f"找出與「{focus}」相關的邊界值（長度、數量、狀態、權限）",
                            "在允許範圍上下限各執行一次",
                            "若適用，再以超出範圍的值驗證拒絕行為",
                        ),
                        expected_result="範圍內應成功；超出範圍應安全拒絕並保留資料一致性。",
                        case_type="boundary",
                        story_key=story.key,
                        story_title=title,
                    ),
                ]
            )
        else:
            cases.extend(
                [
                    TestCase(
                        title=f"{label} happy path: {focus}",
                        steps=_steps(
                            f"Open the feature for {story.key}: {title}",
                            f"Perform the acceptance criterion: {focus}",
                            "Confirm UI/API state matches the expected outcome",
                        ),
                        expected_result=f"Acceptance criterion is satisfied: {focus}",
                        case_type="functional",
                        story_key=story.key,
                        story_title=title,
                    ),
                    TestCase(
                        title=f"{label} negative path: {focus}",
                        steps=_steps(
                            f"Prepare invalid or unauthorized input for: {focus}",
                            "Retry the same user action under the invalid condition",
                            "Capture the error or empty state shown to the user",
                        ),
                        expected_result="The system blocks or explains the failure without corrupting valid data.",
                        case_type="validation",
                        story_key=story.key,
                        story_title=title,
                    ),
                    TestCase(
                        title=f"{label} boundary: {focus}",
                        steps=_steps(
                            f"Identify edge values relevant to: {focus}",
                            "Execute the flow at the lower and upper allowed limits",
                            "Repeat once just outside the allowed limit when applicable",
                        ),
                        expected_result="In-bound values succeed; out-of-bound values are rejected safely.",
                        case_type="boundary",
                        story_key=story.key,
                        story_title=title,
                    ),
                ]
            )
    if story.attachments:
        names = ", ".join(att.get("name") or "attachment" for att in story.attachments[:5])
        if lang in {"zh-Hant", "zh-Hans"}:
            cases.append(
                TestCase(
                    title="附件對照檢查",
                    steps=_steps(
                        f"檢視相關附件：{names}",
                        "比對實際 UI／API 與附件規格或稿面",
                        "記錄與驗收條件不符之處",
                    ),
                    expected_result="實作應與附件規格一致（在需求允許範圍內）。",
                    case_type="functional",
                    story_key=story.key,
                    story_title=title,
                )
            )
        else:
            cases.append(
                TestCase(
                    title="attachment-informed UI check",
                    steps=_steps(
                        f"Review attached references: {names}",
                        "Compare the live UI/API against the referenced mock or specification",
                        "Note any mismatch against acceptance criteria",
                    ),
                    expected_result="Implementation matches the referenced attachment where requirements allow.",
                    case_type="functional",
                    story_key=story.key,
                    story_title=title,
                )
            )
    ctx = workspace_context or {}
    if str(ctx.get("technical_plan") or "").strip():
        if lang in {"zh-Hant", "zh-Hans"}:
            cases.append(
                TestCase(
                    title="技術方案對齊檢查",
                    steps=_steps(
                        "開啟本 Story 的 technical-plan.md",
                        "逐項比對計畫步驟與 Jira／Story 驗收條件",
                        "確認沒有計畫步驟與明確 AC 衝突",
                    ),
                    expected_result="技術方案步驟與驗收條件保持一致。",
                    case_type="functional",
                    story_key=story.key,
                    story_title=title,
                )
            )
        else:
            cases.append(
                TestCase(
                    title="technical-plan alignment",
                    steps=_steps(
                        "Open technical-plan.md for this story",
                        "Walk the planned user/system steps against the current acceptance criteria",
                        "Confirm no planned step contradicts an explicit AC",
                    ),
                    expected_result="Planned implementation steps remain consistent with Jira acceptance criteria.",
                    case_type="functional",
                    story_key=story.key,
                    story_title=title,
                )
            )
    for case in cases:
        if not str(case.feature_point or "").strip():
            case.feature_point = title
    return cases
