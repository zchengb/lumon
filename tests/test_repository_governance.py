from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


LIB_DIR = Path(__file__).resolve().parents[1] / "lib" / "scripts"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from dashboard_server import integration_value, save_repositories, update_env_value, workflow_model_config, workspace_payload  # noqa: E402
from delivery_workspace import repository_delivery_disabled_reasons  # noqa: E402
from auto_fix_sync import is_pr_candidate  # noqa: E402
from patch_runner import select_repository  # noqa: E402
from sync_workspace_repositories import scan_entry  # noqa: E402


class RepositoryGovernanceTests(unittest.TestCase):
    def make_workspace(self, root: Path) -> tuple[Path, Path]:
        workspace = root / "lumen"
        config = workspace / "config"
        repository = root / "repos" / "service"
        subprocess.run(["git", "init", "-b", "main", str(repository)], check=True, capture_output=True)
        (repository / ".nvmrc").write_text("20\n", encoding="utf-8")
        (repository / "build.gradle.kts").write_text("java { toolchain { languageVersion.set(JavaLanguageVersion.of(21)) } }", encoding="utf-8")
        (repository / "package.json").write_text(json.dumps({"scripts": {"lint": "eslint .", "test": "vitest"}}), encoding="utf-8")
        config.mkdir(parents=True)
        (config / "runtime-profiles.json").write_text(json.dumps({"local-java-review-only": {}}), encoding="utf-8")
        (config / "delivery.json").write_text(json.dumps({"verification": {"steps": {}}}), encoding="utf-8")
        (config / "repos.json").write_text(json.dumps({"repositories": [{
            "name": "service", "path": str(repository), "default_branch": "main", "runtime_profile": "local-java-review-only",
            "validation_commands": ["unused command"], "allow_auto_fix": True, "allow_pr": True,
            "runtime": {"visual_auth_credential": "secret", "node_version": "20"},
            "automation": {"delivery": {"enabled": False}, "patch": {"enabled": False}},
        }]}), encoding="utf-8")
        return workspace, repository

    def test_payload_detects_tooling_and_redacts_runtime_secret(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace, _ = self.make_workspace(Path(directory))
            repository = workspace_payload(workspace)["repositories"][0]
            self.assertNotIn("runtime", repository)
            self.assertTrue(repository["runtime_configured"])
            self.assertEqual("21", repository["health"]["java_version"])
            self.assertEqual("20", repository["health"]["node_version"])
            self.assertIn("Gradle", repository["health"]["build_tools"])
            self.assertFalse(repository["automation"]["delivery"]["enabled"])
            self.assertFalse(repository["automation"]["patch"]["enabled"])

    def test_payload_exposes_one_global_model_config_for_all_workflows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace, _ = self.make_workspace(Path(directory))
            (workspace / "config" / "common.json").write_text(json.dumps({"execution": {"provider": "deepseek", "model": "deepseek-v4-flash", "base_url": "https://api.deepseek.com", "api_key_env": "DEEPSEEK_API_KEY"}}), encoding="utf-8")
            payload = workspace_payload(workspace)
            self.assertEqual(payload["model_config"], payload["model_configs"]["scan"])
            self.assertEqual(payload["model_config"], payload["model_configs"]["delivery"])
            self.assertEqual(payload["model_config"], payload["model_configs"]["patch"])

    def test_codex_model_config_defaults_to_luna_xhigh_and_kuoyio(self) -> None:
        config = workflow_model_config({"provider": "codex"})
        self.assertEqual("codex", config["provider"])
        self.assertEqual("gpt-5.6-luna", config["model"])
        self.assertEqual("xhigh", config["reasoning_effort"])
        self.assertEqual("kuoyio0820@gmail.com", config["account_email"])

    def test_codex_ignores_legacy_api_endpoint_fields(self) -> None:
        config = workflow_model_config({"provider": "codex", "base_url": "https://old.example/v1", "api_key_env": "DEEPSEEK_API_KEY"})
        self.assertEqual("", config["base_url"])
        self.assertEqual("", config["api_key_env"])

    def test_workflow_model_config_normalizes_all_provider_aliases(self) -> None:
        self.assertEqual("cursor_cli", workflow_model_config({"provider": "cursor-cli"})["provider"])
        self.assertEqual("opencode", workflow_model_config({"provider": "deepseek_api"})["provider"])
        self.assertEqual("openai_compatible", workflow_model_config({"provider": "openai-compatible"})["provider"])
        self.assertEqual("deepseek-v4-flash", workflow_model_config({"provider": "opencode"})["model"])
        self.assertEqual("gpt-4o-mini", workflow_model_config({"provider": "openai"})["model"])

    def test_payload_exposes_and_updates_lumon_provider_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace, _ = self.make_workspace(Path(directory))
            lumen_home = Path(directory) / "lumon-home"
            lumen_home.mkdir()
            (lumen_home / ".env.local").write_text("DEEPSEEK_API_KEY=old-secret\n", encoding="utf-8")
            with patch.dict(os.environ, {"LUMON_HOME": str(lumen_home)}, clear=False):
                payload = workspace_payload(workspace)
                self.assertIn("DEEPSEEK_API_KEY", payload["configured_integrations"])
                self.assertEqual("lumon_local", payload["integration_sources"]["DEEPSEEK_API_KEY"])
                self.assertEqual("old-secret", integration_value(workspace, "DEEPSEEK_API_KEY"))
                update_env_value(workspace, "DEEPSEEK_API_KEY", "new-secret")
                self.assertEqual("new-secret", integration_value(workspace, "DEEPSEEK_API_KEY"))
                self.assertFalse((workspace / ".env.local").is_file())

    def test_missing_patch_permission_defaults_to_enabled_without_scan_pr_permission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace, _ = self.make_workspace(Path(directory))
            config_path = workspace / "config" / "repos.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["repositories"][0].pop("automation")
            config["repositories"][0].pop("allow_pr", None)
            config_path.write_text(json.dumps(config), encoding="utf-8")

            repository = workspace_payload(workspace)["repositories"][0]
            self.assertTrue(repository["automation"]["patch"]["enabled"])
            self.assertNotIn("allow_pr", repository)
            selected, _ = select_repository(workspace.parent, {"fields": {"labels": ["service"]}})
            self.assertEqual("service", selected["name"])
            finding = {"severity": "High", "auto_fix": {"status": "committed"}}
            self.assertTrue(is_pr_candidate(finding, {"automation": {"scan": {"allow_auto_fix": True, "allow_pr": False}}}))

    def test_save_removes_unused_validation_commands_and_preserves_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace, repository = self.make_workspace(Path(directory))
            save_repositories(workspace, [{
                "name": "service", "path": str(repository), "default_branch": "main", "runtime_profile": "local-java-review-only",
                "automation": {"scan": {"allow_auto_fix": False, "allow_pr": False}, "delivery": {"enabled": True}, "patch": {"enabled": True}},
                "delivery_commands": ["./gradlew test"],
            }])
            saved = json.loads((workspace / "config" / "repos.json").read_text(encoding="utf-8"))["repositories"][0]
            self.assertNotIn("validation_commands", saved)
            self.assertEqual("secret", saved["runtime"]["visual_auth_credential"])
            self.assertTrue(saved["automation"]["patch"]["enabled"])
            self.assertFalse(saved["allow_auto_fix"])
            self.assertEqual("custom", saved["verification"]["mode"])

    def test_save_persists_compile_only_verification_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace, repository = self.make_workspace(Path(directory))
            save_repositories(workspace, [{
                "name": "service", "path": str(repository), "default_branch": "main", "runtime_profile": "local-java-review-only",
                "verification": {"mode": "auto", "compile": True, "tests": False},
            }])
            saved = json.loads((workspace / "config" / "repos.json").read_text(encoding="utf-8"))["repositories"][0]
            self.assertEqual({"mode": "auto", "compile": True, "tests": False}, saved["verification"])
            self.assertNotIn("service", json.loads((workspace / "config" / "delivery.json").read_text(encoding="utf-8")).get("verification", {}).get("steps", {}))

    def test_save_persists_skip_verification_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace, repository = self.make_workspace(Path(directory))
            save_repositories(workspace, [{
                "name": "service", "path": str(repository), "default_branch": "main", "runtime_profile": "local-java-review-only",
                "verification": {"mode": "skip"},
            }])
            saved = json.loads((workspace / "config" / "repos.json").read_text(encoding="utf-8"))["repositories"][0]
            self.assertEqual({"mode": "skip", "compile": True, "tests": True}, saved["verification"])

    def test_save_persists_auto_patch_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace, repository = self.make_workspace(Path(directory))
            save_repositories(workspace, [{
                "name": "service", "path": str(repository), "default_branch": "main", "runtime_profile": "local-java-review-only",
                "automation": {"scan": {"allow_auto_fix": True}, "delivery": {"enabled": True}, "patch": {"enabled": False}},
            }])
            saved = json.loads((workspace / "config" / "repos.json").read_text(encoding="utf-8"))["repositories"][0]
            self.assertFalse(saved["automation"]["patch"]["enabled"])
            self.assertFalse(workspace_payload(workspace)["repositories"][0]["automation"]["patch"]["enabled"])
            selected, reason = select_repository(workspace.parent, {"fields": {"labels": ["service"]}})
            self.assertIsNone(selected)
            self.assertIn("Auto Patch is disabled", reason)

    def test_repository_sync_defaults_auto_patch_to_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace, repository = self.make_workspace(Path(directory))
            entry = scan_entry(
                {"name": "service", "path": str(repository), "default_branch": "main"},
                {"allow_auto_fix": False, "automation": {"delivery": {"enabled": False}}},
            )
            self.assertFalse(entry["automation"]["delivery"]["enabled"])
            self.assertTrue(entry["automation"]["patch"]["enabled"])

    def test_patch_and_delivery_respect_repository_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace, repository = self.make_workspace(Path(directory))
            item = {"fields": {"labels": ["service"]}}
            selected, reason = select_repository(workspace.parent, item)
            self.assertIsNone(selected)
            self.assertIn("Auto Patch is disabled", reason)
            context = SimpleNamespace(workspace_root=workspace.parent, repos=[SimpleNamespace(name="service")])
            self.assertEqual(["repository 'service' is not authorized for Auto Delivery"], repository_delivery_disabled_reasons(context))


if __name__ == "__main__":
    unittest.main()
