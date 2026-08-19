from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.runner.isolation import DisposableWorkspace, protected_delete_probe


class DisposableWorkspaceTests(unittest.TestCase):
    def test_publish_copies_additions_and_modifications_but_not_secrets(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "existing.txt").write_text("before\n", encoding="utf-8")
            (source / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"LUMEN_HOME": str(root / "lumon")}, clear=False):
                layer = DisposableWorkspace.create(source, "test")
                try:
                    self.assertFalse((layer.path / ".env").exists())
                    (layer.path / "existing.txt").write_text("after\n", encoding="utf-8")
                    (layer.path / "new.txt").write_text("new\n", encoding="utf-8")
                    receipt = layer.publish()
                finally:
                    layer.close()
            self.assertEqual(receipt.status, "succeeded")
            self.assertEqual((source / "existing.txt").read_text(encoding="utf-8"), "after\n")
            self.assertEqual((source / "new.txt").read_text(encoding="utf-8"), "new\n")
            self.assertEqual((source / ".env").read_text(encoding="utf-8"), "TOKEN=secret\n")

    def test_publish_blocks_irreversible_deletion(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "protected.txt").write_text("keep\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"LUMEN_HOME": str(root / "lumon")}, clear=False):
                layer = DisposableWorkspace.create(source, "test")
                try:
                    (layer.path / "protected.txt").unlink()
                    receipt = layer.publish()
                finally:
                    layer.close()
            self.assertEqual(receipt.status, "blocked")
            self.assertEqual(receipt.code, "DELETE_REQUIRES_EXPLICIT_CAPABILITY")
            self.assertTrue((source / "protected.txt").is_file())

    def test_git_clone_does_not_materialize_tracked_secret_files(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "README.md").write_text("visible\n", encoding="utf-8")
            (source / ".env").write_text("TOKEN=secret\n", encoding="utf-8")
            (source / "id_rsa").write_text("private\n", encoding="utf-8")
            import subprocess

            subprocess.run(["git", "-C", str(source), "init", "--quiet"], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(source), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(source), "add", "."], check=True)
            subprocess.run(["git", "-C", str(source), "commit", "--quiet", "-m", "fixture"], check=True)
            with mock.patch.dict(os.environ, {"LUMEN_HOME": str(root / "lumon")}, clear=False):
                layer = DisposableWorkspace.create(source, "test")
                try:
                    self.assertTrue((layer.path / "README.md").is_file())
                    self.assertFalse((layer.path / ".env").exists())
                    self.assertFalse((layer.path / "id_rsa").exists())
                finally:
                    layer.close()

    def test_delete_probe_is_side_effect_free_and_fails_closed(self) -> None:
        result = protected_delete_probe()
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["canonical_deleted"])


if __name__ == "__main__":
    unittest.main()
