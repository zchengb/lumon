#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from skills.test_case.designer import _extract_json_object, design_test_cases, drafts_from_payload
from skills.test_case.localization import (
    localize_test_case_type,
    localize_verify_status_options,
    normalize_case_type,
)
from skills.test_case.models import StoryContext
from skills.test_case.validator import TestCaseDesignQualityError, validate_test_cases

FIXTURES = ROOT / "tests" / "fixtures" / "test_case"


class LocalizationTests(unittest.TestCase):
    def test_filter_labels(self) -> None:
        self.assertEqual(localize_test_case_type("filter", "zh-Hant"), "篩選")
        self.assertEqual(localize_test_case_type("filter", "zh-Hans"), "筛选")
        self.assertEqual(localize_test_case_type("filter", "en"), "Filter")

    def test_unknown_type_fails(self) -> None:
        with self.assertRaises(ValueError):
            localize_test_case_type("not-a-type", "en")

    def test_verify_status_options(self) -> None:
        self.assertEqual(localize_verify_status_options("zh-Hant"), ("待驗證", "驗證成功", "驗證失敗", "忽略"))
        self.assertEqual(localize_verify_status_options("zh-Hans"), ("待验证", "验证成功", "验证失败", "忽略"))
        self.assertEqual(localize_verify_status_options("en"), ("Pending", "Passed", "Failed", "Ignored"))

    def test_normalize_legacy(self) -> None:
        self.assertEqual(normalize_case_type("Negative"), "validation")
        self.assertEqual(normalize_case_type("導航"), "navigation")


class JsonExtractionTests(unittest.TestCase):
    def test_extracts_json_with_fence_and_trailing_text(self) -> None:
        payload = _extract_json_object(
            'Here is the payload:\n```json\n{"test_cases":[{"title":"登入"}]}\n```\nDone.'
        )
        self.assertEqual(payload["test_cases"][0]["title"], "登入")


class ProviderRoutingTests(unittest.TestCase):
    def test_codex_provider_routes_to_codex_designer_with_account_contract(self) -> None:
        story = StoryContext(
            key="MBPAS-1505",
            type="Story",
            summary="Generate test cases",
            description="desc",
            acceptance_criteria=["AC1: generate executable cases"],
        )
        payload = {
            "test_cases": [
                {
                    "ac_refs": ["AC1"],
                    "title": "產生可執行測試案例",
                    "preconditions": ["已取得需求內容"],
                    "steps": ["執行測試案例生成"],
                    "expected_results": ["產生可執行的測試案例"],
                    "case_type": "functional",
                    "feature_point": "測試案例生成",
                    "rationale": "驗證需求指定功能",
                }
            ]
        }
        with patch(
            "skills.test_case.designer._run_codex_agent",
            return_value=json.dumps(payload, ensure_ascii=False),
        ) as runner:
            drafts = design_test_cases(
                story,
                agents_config={
                    "execution": {
                        "provider": "codex",
                        "model": "gpt-5.6-luna",
                        "reasoning_effort": "xhigh",
                        "account_email": "kuoyio0820@gmail.com",
                    }
                },
            )

        self.assertEqual(1, len(drafts))
        self.assertEqual("gpt-5.6-luna", runner.call_args.kwargs["model"])
        self.assertEqual("xhigh", runner.call_args.kwargs["reasoning_effort"])
        self.assertEqual("kuoyio0820@gmail.com", runner.call_args.kwargs["account_email"])
        self.assertEqual("測試案例生成", drafts[0].feature_point)

    def test_repairs_structural_model_json_errors(self) -> None:
        payload = _extract_json_object('{"test_cases":[{title: "登入", "steps": ["1."],},],}')
        self.assertEqual(payload["test_cases"][0]["title"], "登入")

    def test_accepts_python_style_single_quoted_payload(self) -> None:
        payload = _extract_json_object("{'test_cases': [{'title': '登入'}]}")
        self.assertEqual(payload["test_cases"][0]["title"], "登入")

    def test_wraps_top_level_case_array(self) -> None:
        payload = _extract_json_object('[{"title":"登入"},{"title":"登出"}]')
        self.assertEqual([item["title"] for item in payload["test_cases"]], ["登入", "登出"])

    def test_wraps_array_with_surrounding_text(self) -> None:
        payload = _extract_json_object('Result:\n[{"title":"登入"}]\nDone.')
        self.assertEqual(payload["test_cases"][0]["title"], "登入")


class ValidatorTests(unittest.TestCase):
    def _story(self) -> StoryContext:
        return StoryContext(
            key="MBPAS-1",
            type="Story",
            summary="Banner",
            description="",
            acceptance_criteria=["AC1: menu"],
        )

    def test_accepts_navigation_fixture(self) -> None:
        data = json.loads((FIXTURES / "navigation_only.json").read_text(encoding="utf-8"))
        drafts = drafts_from_payload(data)
        cases = validate_test_cases(drafts, story=self._story(), language="zh-Hant")
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].case_type, "navigation")
        self.assertEqual(cases[0].ac_refs, ["AC1"])
        self.assertIn("1.", cases[0].steps)

    def test_rejects_placeholder_language(self) -> None:
        data = json.loads((FIXTURES / "bad_placeholder.json").read_text(encoding="utf-8"))
        drafts = drafts_from_payload(data)
        with self.assertRaises(TestCaseDesignQualityError):
            validate_test_cases(drafts, story=self._story(), language="zh-Hant")

    def test_no_mechanical_boundary_required_for_navigation(self) -> None:
        data = json.loads((FIXTURES / "navigation_only.json").read_text(encoding="utf-8"))
        drafts = drafts_from_payload(data)
        cases = validate_test_cases(drafts, story=self._story(), language="zh-Hant")
        self.assertTrue(all(c.case_type != "boundary" for c in cases))

    def test_real_boundary_fixture(self) -> None:
        data = json.loads((FIXTURES / "boundary_ac.json").read_text(encoding="utf-8"))
        drafts = drafts_from_payload(data)
        cases = validate_test_cases(drafts, story=self._story(), language="zh-Hant")
        self.assertEqual(cases[0].case_type, "boundary")


if __name__ == "__main__":
    unittest.main()
