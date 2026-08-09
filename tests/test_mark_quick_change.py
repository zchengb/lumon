#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
SCRIPTS = LIB / "scripts"
for path in (LIB, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agents.mark.delivery_adapter import DeliveryActionAdapter
from agents.runtime.interaction import action_missing_fields, clarification_question
from agents.security.access_policy import classify_authorization_intent
from quick_change_runner import configured_publish_mode, normalize_target_files, run


class MarkQuickChangeTests(unittest.TestCase):
    def test_small_change_requirements_are_real_fields(self) -> None:
        self.assertEqual(
            ["target_files", "target_version"],
            action_missing_fields(
                "delivery.quick_change",
                arguments={"repository": "admin", "target_files": [], "request": "upgrade the version"},
            ),
        )
        self.assertEqual([], action_missing_fields(
            "delivery.quick_change",
            arguments={
                "repository": "admin",
                "target_files": ["package.json"],
                "request": "upgrade the version",
                "target_version": "1.2.3",
            },
        ))
        self.assertEqual("Which version should I upgrade it to?", clarification_question("delivery.quick_change", ["target_version"]))
        self.assertEqual("mutate_explicit", classify_authorization_intent("Please upgrade the version number"))

    def test_target_file_and_publish_policy_helpers(self) -> None:
        self.assertEqual(["package.json", "src/version.ts"], normalize_target_files("package.json, src/version.ts"))
        with self.assertRaises(ValueError):
            normalize_target_files(["../package.json"])
        self.assertEqual("merge", configured_publish_mode({"publish": {"mode": "merge"}}))
        self.assertEqual("direct", configured_publish_mode({"publish": {"quick_change": {"mode": "direct"}}}))

    def test_dry_run_uses_isolated_worktree_without_story(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            repo = docs / "admin-portal"
            (docs / "stories").mkdir(parents=True)
            (docs / "lumen" / "config").mkdir(parents=True)
            (docs / "lumen" / "config" / "workspace.json").write_text(
                json.dumps({"layout": "sibling", "workspace_root": str(docs)}) + "\n", encoding="utf-8"
            )
            (docs / "lumen" / "config" / "repos.json").write_text(
                json.dumps({"repositories": [{"name": "admin-portal", "default_branch": "master"}]}) + "\n",
                encoding="utf-8",
            )
            (docs / "lumen" / "config" / "delivery.json").write_text(
                json.dumps({"publish": {"mode": "none"}}) + "\n", encoding="utf-8"
            )
            repo.mkdir()
            (repo / "package.json").write_text('{"version":"1.0.0"}\n', encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "branch", "-M", "master"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(repo), "add", "package.json"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)

            args = Namespace(
                docs_dir=str(docs),
                run_id="quick-test-1",
                repository="admin-portal",
                request="upgrade the version number",
                change_type="version_bump",
                target_version="1.1.0",
                target_file=["package.json"],
                dry_run=True,
            )
            fake_agent = Path(tmp) / "fake-agent"
            fake_agent.write_text(
                "#!/usr/bin/env python3\n"
                "from pathlib import Path\n"
                "Path('package.json').write_text('{\"version\":\"1.1.0\"}\\n', encoding='utf-8')\n",
                encoding="utf-8",
            )
            fake_agent.chmod(0o755)
            with mock.patch.dict(os.environ, {"LUMEN_AGENT_BIN": str(fake_agent), "CURSOR_AGENT_SANDBOX": "enabled"}):
                self.assertEqual(0, run(args))
            result = json.loads(
                (docs / "lumen" / "results" / "quick-changes" / "quick-test-1.json").read_text(encoding="utf-8")
            )
            self.assertEqual("dry_run", result["status"])
            self.assertFalse((docs / "lumen" / "worktrees" / "quick" / "quick-test-1" / "admin-portal").exists())

    def test_status_reads_quick_change_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp)
            result_path = docs / "lumen" / "results" / "quick-changes" / "quick-1.json"
            result_path.parent.mkdir(parents=True)
            result_path.write_text(json.dumps({"run_id": "quick-1", "status": "completed", "repository": "admin"}), encoding="utf-8")
            status = DeliveryActionAdapter().status(workspace=docs, run_id="quick-1")
            self.assertEqual("quick-1", status["run_id"])
            self.assertEqual("completed", status["delivery_status"])


if __name__ == "__main__":
    unittest.main()
