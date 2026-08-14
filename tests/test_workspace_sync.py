from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "lib" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from workspace_sync import is_lumen_owned_path, sync  # noqa: E402
from workspace_sync_launchd import interval_minutes_from_cron  # noqa: E402


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def init_workspace(root: Path) -> tuple[Path, Path]:
    remote = root / "remote.git"
    docs = root / "docs"
    subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "init", "-b", "main", str(docs)], check=True, capture_output=True)
    git(docs, "config", "user.name", "Lumen Test")
    git(docs, "config", "user.email", "lumen@example.test")
    (docs / "stories" / "DEMO-1").mkdir(parents=True)
    (docs / "stories" / "DEMO-1" / "story.md").write_text("story\n", encoding="utf-8")
    git(docs, "add", ".")
    git(docs, "commit", "-m", "initial")
    git(docs, "remote", "add", "origin", str(remote))
    git(docs, "push", "-u", "origin", "main")
    return remote, docs


class WorkspaceSyncTests(unittest.TestCase):
    def test_sync_commits_only_lumen_owned_paths_and_pushes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            _, docs = init_workspace(Path(temp))
            plan = docs / "stories" / "DEMO-1" / "technical-plan.md"
            plan.write_text("plan\n", encoding="utf-8")

            result = sync(docs)

            self.assertEqual("ok", result["status"])
            self.assertEqual(["stories/DEMO-1/technical-plan.md"], result["committed_paths"])
            self.assertEqual("pushed", result["remote_sync"])
            self.assertEqual("", git(docs, "status", "--porcelain"))
            self.assertEqual(git(docs, "rev-parse", "HEAD"), git(docs, "rev-parse", "origin/main"))

    def test_sync_pulls_clean_workspace_and_blocks_foreign_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            remote, docs = init_workspace(Path(temp))
            other = Path(temp) / "other"
            subprocess.run(["git", "clone", "-b", "main", str(remote), str(other)], check=True, capture_output=True)
            git(other, "config", "user.name", "Remote Test")
            git(other, "config", "user.email", "remote@example.test")
            (other / "stories" / "DEMO-1" / "remote-note.md").write_text("remote\n", encoding="utf-8")
            git(other, "add", ".")
            git(other, "commit", "-m", "remote update")
            git(other, "push", "origin", "main")

            pulled = sync(docs)
            self.assertEqual("pulled", pulled["remote_sync"])
            self.assertTrue((docs / "stories" / "DEMO-1" / "remote-note.md").is_file())

            (docs / "notes.md").write_text("local user edit\n", encoding="utf-8")
            blocked = sync(docs)
            self.assertEqual("blocked_dirty", blocked["status"])
            self.assertIn("notes.md", blocked["foreign_paths"])

    def test_owned_path_policy_excludes_secrets_and_unknown_files(self) -> None:
        self.assertTrue(is_lumen_owned_path("stories/DEMO-1/story.md"))
        self.assertTrue(is_lumen_owned_path("lumen/config/delivery.json"))
        self.assertFalse(is_lumen_owned_path("notes.md"))
        self.assertFalse(is_lumen_owned_path("lumen/.env.local"))
        self.assertFalse(is_lumen_owned_path("stories/DEMO-1/token.pem"))
        self.assertEqual(5, interval_minutes_from_cron("*/5 * * * *"))
        self.assertIsNone(interval_minutes_from_cron("0 9 * * *"))


if __name__ == "__main__":
    unittest.main()
