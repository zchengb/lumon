from __future__ import annotations

import re

from skills.test_case.localization import CANONICAL_CASE_TYPES, normalize_case_type
from skills.test_case.models import StoryContext, TestCase, TestCaseDraft, join_lines, join_numbered, normalize_title


class TestCaseDesignQualityError(ValueError):
    code = "TEST_CASE_DESIGN_QUALITY_FAILED"


_PLACEHOLDER_RE = re.compile(
    "|".join(
        re.escape(item)
        for item in (
            "依 Story 進入對應",
            "依 Story 进入对应",
            "依驗收條件執行",
            "依验收条件执行",
            "確認符合預期",
            "确认符合预期",
            "執行相關操作",
            "执行相关操作",
            "準備相關資料",
            "准备相关数据",
            "確保環境正確",
            "确保环境正确",
            "Prepare invalid input",
            "Identify edge values",
            "Confirm expected behavior",
            "Confirm UI/API state matches",
            "Retry the same user action",
            "Perform the acceptance criterion",
        )
    ),
    re.IGNORECASE,
)


def _blob(draft: TestCaseDraft) -> str:
    parts = [
        draft.title,
        draft.feature_point,
        *draft.preconditions,
        *draft.test_data,
        *draft.steps,
        *draft.expected_results,
    ]
    return "\n".join(str(part or "") for part in parts)


def validate_test_cases(
    drafts: list[TestCaseDraft],
    *,
    story: StoryContext,
    language: str = "zh-Hant",
) -> list[TestCase]:
    if not drafts:
        raise TestCaseDesignQualityError("designer returned no test cases")
    has_acs = bool(story.acceptance_criteria)
    seen_titles: set[str] = set()
    cases: list[TestCase] = []
    errors: list[str] = []
    for idx, draft in enumerate(drafts, start=1):
        title = str(draft.title or "").strip()
        if not title:
            errors.append(f"case {idx}: empty title")
            continue
        title_key = normalize_title(title)
        if title_key in seen_titles:
            errors.append(f"case {idx}: duplicated title {title!r}")
            continue
        seen_titles.add(title_key)
        steps = [str(item or "").strip() for item in draft.steps if str(item or "").strip()]
        expected = [str(item or "").strip() for item in draft.expected_results if str(item or "").strip()]
        if not steps:
            errors.append(f"case {idx}: steps required")
            continue
        if not expected:
            errors.append(f"case {idx}: expected_results required")
            continue
        case_type = normalize_case_type(draft.case_type)
        if case_type not in CANONICAL_CASE_TYPES:
            errors.append(f"case {idx}: unknown case_type {draft.case_type!r}")
            continue
        ac_refs = [str(item or "").strip().upper().replace(" ", "") for item in draft.ac_refs if str(item or "").strip()]
        if has_acs and not ac_refs:
            errors.append(f"case {idx}: ac_refs required")
            continue
        if _PLACEHOLDER_RE.search(_blob(draft)):
            errors.append(f"case {idx}: placeholder language rejected")
            continue
        cases.append(
            TestCase(
                title=title,
                steps=join_numbered(steps),
                expected_result=join_lines(expected),
                case_type=case_type,
                story_key=story.key,
                story_title=story.summary or story.key,
                ac_refs=ac_refs,
                preconditions=join_lines(list(draft.preconditions or [])),
                feature_point=str(draft.feature_point or "").strip(),
                test_data=join_lines(list(draft.test_data or [])),
            )
        )
    if errors:
        raise TestCaseDesignQualityError("; ".join(errors[:12]))
    if not cases:
        raise TestCaseDesignQualityError("no valid test cases after validation")
    return cases
