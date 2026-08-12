#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from agents.dylan.session_bootstrap import build_bootstrap_prompt, build_resume_prompt
from agents.dylan.session_store import PROTOCOL_VERSION, SOUL_VERSION
from agents.dylan.workspace_contract import ensure_workspace_contract
from risk.dashboard_overlay import apply_risk_overlay, overlay_issue_with_finding
from risk.reconcile import reconcile_project
from risk.resolution import resolve_finding
from risk.status_display import display_status, evidence_summary
from risk.store import RiskStore, utc_now
from risk.verification import apply_verification_receipt
from risk.verification_runner import FakeVerificationAdapter, run_verification, verification_capability


def _seed_finding(
    store: RiskStore,
    finding_id: str = "FIND-7202570058a9",
    *,
    severity: str = "Medium",
    registry_issue_id: str = "ISSUE-cd6fa30c22",
    title: str = "Event dispatch FCM batch exceeds 500-token limit",
    repository: str = "mbpass-admin",
) -> str:
    now = utc_now()
    store.execute(
        """
        INSERT INTO finding(
            id, project_slug, canonical_fingerprint, registry_issue_id, repository, module,
            title, category, source_severity, effective_severity, status,
            first_seen_at, last_seen_at, resolved_at, reopened_count, recurrence_count,
            occurrence_count, consecutive_seen_count, verification_status, remediation_status,
            last_seen_scan_run_id, current_risk_score, current_risk_band
        ) VALUES (?, 'mbpass', 'fp-fcm-1', ?, ?, 'notify',
            ?, 'reliability', ?, ?, 'Open',
            ?, ?, NULL, 0, 0, 1, 1, 'observed', 'none',
            'scan-1', 70.0, 'medium')
        """,
        (finding_id, registry_issue_id, repository, title, severity, severity, now, now),
    )
    store.commit()
    return finding_id


def _write_registry(workspace: Path, issue_id: str = "ISSUE-cd6fa30c22", status: str = "open") -> None:
    (workspace / "state").mkdir(parents=True, exist_ok=True)
    (workspace / "state" / "issue-registry.json").write_text(
        json.dumps(
            {
                "issues": [
                    {
                        "id": issue_id,
                        "status": status,
                        "repository": "mbpass-admin",
                        "title": "Event dispatch FCM batch exceeds 500-token limit",
                        "jira_key": "MBPAS-1559",
                        "severity": "Medium",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


class ContractM21Tests(unittest.TestCase):
    def test_protocol_bump(self) -> None:
        self.assertEqual(SOUL_VERSION, "5")
        self.assertEqual(PROTOCOL_VERSION, "5")

    def test_bootstrap_no_auto_verify_ask(self) -> None:
        prompt = build_bootstrap_prompt(project_slug="mbpass", workspace_path="/tmp", user_message="hi")
        self.assertIn("do not auto-ask verification", prompt.lower())
        self.assertIn("Open / Resolved / Reopened / Ignored", prompt)
        self.assertIn("Prefer Jira keys", prompt)
        self.assertIn("Do not ask Want me to run a Verification Scan after ordinary resolve.", prompt)

    def test_resume_no_verify_ask(self) -> None:
        prompt = build_resume_prompt(user_message="Mark it resolved.")
        self.assertIn("do not ask for Verification", prompt)

    def test_workspace_managed_v5(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ensure_workspace_contract(workspace=root, project_slug="mbpass")
            text = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("version=5", text)
            self.assertIn("do not auto-ask Verification", text)
            self.assertIn("risk reconcile", text)


class StatusVocabularyTests(unittest.TestCase):
    def test_primary_status_only(self) -> None:
        self.assertEqual(
            display_status(
                {
                    "status": "Resolved",
                    "resolution_basis": "user_confirmed",
                    "verification_status": "pending_verification",
                }
            ),
            "Resolved",
        )
        self.assertEqual(
            display_status({"status": "Resolved", "verification_status": "verified_clean"}),
            "Resolved",
        )
        self.assertEqual(
            display_status({"status": "Reopened", "verification_status": "verification_failed"}),
            "Reopened",
        )
        evidence = evidence_summary(
            {
                "status": "Resolved",
                "resolution_basis": "user_confirmed",
                "verification_status": "pending_verification",
            }
        )
        self.assertEqual(evidence["resolution_basis"], "User confirmed")
        self.assertEqual(evidence["verification"], "Not run")


class DashboardOverlayTests(unittest.TestCase):
    def test_risk_resolved_overrides_registry_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config").mkdir()
            (workspace / "config" / "common.json").write_text(
                json.dumps({"project": {"slug": "mbpass"}}),
                encoding="utf-8",
            )
            _write_registry(workspace, status="open")
            store = RiskStore(workspace)
            finding_id = _seed_finding(store)
            resolve_finding(
                store,
                finding_id,
                actor="u1",
                reason="fixed",
                source_message_id="om_1",
                trace_id="tr_1",
            )
            store.close()
            issues = apply_risk_overlay(
                workspace,
                [
                    {
                        "id": "ISSUE-cd6fa30c22",
                        "status": "open",
                        "repository": "mbpass-admin",
                        "title": "Event dispatch FCM batch exceeds 500-token limit",
                        "jira_key": "MBPAS-1559",
                    }
                ],
                project_slug="mbpass",
            )
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0]["status"], "resolved")
            self.assertEqual(issues[0]["status_source"], "risk_store")
            self.assertEqual(issues[0]["risk_finding_id"], finding_id)
            self.assertEqual(issues[0]["resolution_basis"], "user_confirmed")

    def test_fallback_without_risk(self) -> None:
        issue = overlay_issue_with_finding({"id": "ISSUE-1", "status": "open"}, None)
        self.assertEqual(issue["status"], "open")
        self.assertEqual(issue["status_source"], "issue_registry")

    def test_build_payload_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config").mkdir()
            (workspace / "config" / "common.json").write_text(
                json.dumps({"project": {"slug": "mbpass", "display_name": "MBPass"}}),
                encoding="utf-8",
            )
            (workspace / "config" / "repos.json").write_text(
                json.dumps({"repositories": []}),
                encoding="utf-8",
            )
            for name in ("results", "reports", "logs", "state"):
                (workspace / name).mkdir()
            _write_registry(workspace, status="open")
            store = RiskStore(workspace)
            finding_id = _seed_finding(store)
            resolve_finding(
                store,
                finding_id,
                actor="u1",
                reason="fixed",
                source_message_id="om_payload",
                trace_id="tr_payload",
            )
            store.close()
            path = ROOT / "lib" / "scripts" / "render-dashboard.py"
            spec = importlib.util.spec_from_file_location("render_dashboard_m21", path)
            assert spec is not None and spec.loader is not None
            renderer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(renderer)
            payload = renderer.build_payload(workspace)
            issue = next(item for item in payload["issues"] if item["id"] == "ISSUE-cd6fa30c22")
            self.assertEqual(issue["status"], "resolved")
            self.assertEqual(issue["status_source"], "risk_store")
            self.assertEqual(payload["issue_counts"]["open_total"], 0)

    def test_build_payload_ignores_incomplete_scan_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config").mkdir()
            (workspace / "config" / "common.json").write_text("{}\n", encoding="utf-8")
            (workspace / "config" / "repos.json").write_text('{"repositories":[]}\n', encoding="utf-8")
            (workspace / "results").mkdir()
            (workspace / "reports").mkdir()
            (workspace / "logs").mkdir()
            (workspace / "state").mkdir()
            (workspace / "results" / "scan-result-tmp-test.json").write_text(
                json.dumps({"scan_status": "completed_with_findings"}),
                encoding="utf-8",
            )
            (workspace / "results" / "scan-result-20260810-040000.json").write_text(
                json.dumps({
                    "started_at": "2026-08-10T04:00:00Z",
                    "finished_at": "2026-08-10T04:01:00Z",
                    "scan_status": "completed",
                    "findings": [],
                }),
                encoding="utf-8",
            )

            path = ROOT / "lib" / "scripts" / "render-dashboard.py"
            spec = importlib.util.spec_from_file_location("render_dashboard_incomplete_test", path)
            assert spec is not None and spec.loader is not None
            renderer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(renderer)

            payload = renderer.build_payload(workspace)

            self.assertEqual(["scan-result-20260810-040000"], [run["id"] for run in payload["runs"]])

    def test_build_payload_includes_current_scan_result_in_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config").mkdir()
            (workspace / "config" / "common.json").write_text("{}\n", encoding="utf-8")
            (workspace / "config" / "repos.json").write_text('{"repositories":[]}\n', encoding="utf-8")
            for name in ("results", "reports", "logs", "state"):
                (workspace / name).mkdir()
            (workspace / "results" / "scan-result.json").write_text(
                json.dumps({
                    "started_at": "2026-08-12T05:52:00Z",
                    "finished_at": "2026-08-12T06:03:20Z",
                    "scan_status": "completed",
                    "repositories_scanned": 13,
                    "findings": [{"severity": "Medium"}],
                }),
                encoding="utf-8",
            )
            path = ROOT / "lib" / "scripts" / "render-dashboard.py"
            spec = importlib.util.spec_from_file_location("render_dashboard_current_test", path)
            assert spec is not None and spec.loader is not None
            renderer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(renderer)
            payload = renderer.build_payload(workspace)
            self.assertEqual("scan-result", payload["runs"][0]["id"])
            self.assertEqual("scan-result", payload["latest_run"]["id"])


class ReconcileTests(unittest.TestCase):
    def test_dry_run_and_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config").mkdir()
            (workspace / "config" / "common.json").write_text(
                json.dumps({"project": {"slug": "mbpass"}}),
                encoding="utf-8",
            )
            _write_registry(workspace, status="open")
            store = RiskStore(workspace)
            finding_id = _seed_finding(store)
            store.execute(
                "UPDATE finding SET status = 'Resolved', resolution_basis = 'user_confirmed', "
                "verification_status = 'pending_verification', resolved_by = 'u1' WHERE id = ?",
                (finding_id,),
            )
            store.commit()
            store.close()
            dry = reconcile_project(workspace, project_slug="mbpass", repair=False)
            self.assertEqual(dry["mismatched"], 1)
            self.assertEqual(dry["repaired"], 0)
            repaired = reconcile_project(workspace, project_slug="mbpass", repair=True)
            self.assertEqual(repaired["repaired"], 1)
            registry = json.loads((workspace / "state" / "issue-registry.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["issues"][0]["status"], "resolved")
            self.assertEqual(registry["issues"][0]["risk_finding_id"], finding_id)


class VerificationGuardTests(unittest.TestCase):
    def test_production_blocks_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config").mkdir()
            store = RiskStore(workspace)
            finding_id = _seed_finding(store)
            resolve_finding(
                store,
                finding_id,
                actor="u1",
                reason="fixed",
                source_message_id="om_v1",
                trace_id="tr_v1",
            )
            before = dict(store.get_finding(finding_id))
            out = run_verification(store, workspace, finding_id, actor="u1", source_message_id="om_v2", trace_id="tr_v2")
            self.assertEqual(out["code"], "REAL_VERIFICATION_NOT_AVAILABLE")
            after = dict(store.get_finding(finding_id))
            self.assertEqual(after["status"], before["status"])
            self.assertEqual(after["verification_status"], before["verification_status"])
            store.close()

    def test_fake_adapter_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config").mkdir()
            store = RiskStore(workspace)
            finding_id = _seed_finding(store)
            resolve_finding(
                store,
                finding_id,
                actor="u1",
                reason="fixed",
                source_message_id="om_v3",
                trace_id="tr_v3",
            )
            out = run_verification(
                store,
                workspace,
                finding_id,
                actor="u1",
                source_message_id="om_v4",
                trace_id="tr_v4",
                scan_adapter=FakeVerificationAdapter(observed=False),
            )
            self.assertEqual(out["status"], "verified_clean")
            self.assertEqual(out["display_status"], "Resolved")
            failed = apply_verification_receipt(
                store,
                finding_id,
                result="verification_failed",
                observed=True,
                scan_run_id="verify-fail-1",
            )
            self.assertEqual(failed["display_status"], "Reopened")
            store.close()

    def test_capability_default_unavailable(self) -> None:
        cap = verification_capability(common={})
        self.assertFalse(cap["available"])
        self.assertEqual(cap["mode"], "none")


class ResolveCliDisplayTests(unittest.TestCase):
    def test_resolve_returns_primary_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config").mkdir()
            _write_registry(workspace)
            store = RiskStore(workspace)
            finding_id = _seed_finding(store)
            out = resolve_finding(
                store,
                finding_id,
                actor="u1",
                reason="Owner confirmed repair",
                source_message_id="om_r",
                trace_id="tr_r",
            )
            self.assertEqual(out["status"], "ok")
            self.assertEqual(out["display_status"], "Resolved")
            self.assertEqual(out["registry_mirror"]["status"], "synced")
            store.close()


class VerificationStatusCliTests(unittest.TestCase):
    def test_verification_status_includes_availability(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "run_agent_json_cli_m21",
            ROOT / "lib" / "scripts" / "run-agent-json-cli.py",
        )
        assert spec is not None and spec.loader is not None
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "config").mkdir()
            (workspace / "config" / "common.json").write_text(
                json.dumps({"project": {"slug": "mbpass"}}),
                encoding="utf-8",
            )
            store = RiskStore(workspace)
            finding_id = _seed_finding(store)
            store.close()
            code = cli.main(
                [
                    "risk",
                    "finding",
                    "verification-status",
                    finding_id,
                    "--workspace",
                    str(workspace),
                    "--project",
                    "mbpass",
                    "--json",
                ]
            )
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
