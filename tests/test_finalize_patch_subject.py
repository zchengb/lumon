import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib" / "scripts"))

from finalize_patch import subject_for  # noqa: E402


class FinalizePatchSubjectTests(unittest.TestCase):
    def test_normalizes_conventional_subject(self):
        result = {"repos_touched": [{"name": "service", "commit_subject": "fix(MBPAS-1548): handle fuel type"}]}
        self.assertEqual(
            "[lumon] #MBPAS-1548 fix: handle fuel type",
            subject_for(result, "service", "MBPAS-1548"),
        )

    def test_replaces_human_prefix_and_keeps_allowed_kind(self):
        result = {"repos_touched": [{"name": "service", "commit_subject": "[xiaobin] #MBPAS-1548 refactor: simplify filter"}]}
        self.assertEqual(
            "[lumon] #MBPAS-1548 refactor: simplify filter",
            subject_for(result, "service", "MBPAS-1548"),
        )

    def test_supplies_canonical_default(self):
        self.assertEqual(
            "[lumon] #MBPAS-1548 fix: apply Auto Patch correction",
            subject_for({}, "service", "MBPAS-1548"),
        )


if __name__ == "__main__":
    unittest.main()
