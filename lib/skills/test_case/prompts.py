from __future__ import annotations

import json
from typing import Any

from skills.test_case.localization import CANONICAL_CASE_TYPES
from skills.test_case.models import StoryContext


DESIGN_SYSTEM_PROMPT = """You are designing executable manual test cases for Lumen's Milchick-owned test-case workflow.

This prompt is the test-case generation standard. Treat the Jira card and the supplied workspace/repository evidence as the source of truth; do not replace them with generic templates.

Do not mechanically generate positive, negative, and boundary cases for every AC.

For each requirement:
1. Understand the user-visible behavior.
2. Split it into independently verifiable rules.
3. Generate only scenarios justified by explicit requirement, known business rule, implementation evidence, or strongly implied standard behavior.
4. Do not invent arbitrary permissions, limits, validation, errors, or edge values.
5. Each case must be executable without rereading Jira.
6. One case should verify one primary behavior.
7. Preconditions must identify required account/data/state.
8. Steps must be concrete actions.
9. Expected results must be observable and pass/fail decidable.
10. Return canonical test type keys only.

Negative scenarios only when failure behavior, permission, validation, empty state, or an explicit error path is justified.
Boundary scenarios only when a real boundary dimension exists (length, count, date, size, pagination, frequency, etc.).

Return ONLY compact JSON with this shape:
{"test_cases":[{"ac_refs":["AC1"],"title":"...","preconditions":["..."],"steps":["..."],"expected_results":["..."],"case_type":"navigation","rationale":"..."}]}
"""


def build_design_prompt(
    story: StoryContext,
    *,
    workspace_context: dict[str, Any] | None,
    language: str,
) -> str:
    ctx = workspace_context if isinstance(workspace_context, dict) else {}
    attachments = []
    for item in story.attachments[:8]:
        if isinstance(item, dict):
            attachments.append(str(item.get("name") or "attachment"))
    comments = []
    for item in story.comments[:5]:
        if isinstance(item, dict):
            body = str(item.get("body") or "").strip()
            if body:
                comments.append(body[:240])
    payload = {
        "story_key": story.key,
        "summary": story.summary,
        "description": (story.description or "")[:6000],
        "acceptance_criteria": list(story.acceptance_criteria or [])[:40],
        "comments": comments,
        "attachments": attachments,
        "technical_plan": str(ctx.get("technical_plan") or "")[:4000],
        "language": language,
        "allowed_case_types": list(CANONICAL_CASE_TYPES),
        "output_language": language,
    }
    return (
        DESIGN_SYSTEM_PROMPT
        + "\n\nWrite titles, preconditions, steps, and expected results in the output_language.\n"
        + "Input:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )
