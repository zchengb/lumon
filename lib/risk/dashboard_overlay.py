from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from risk.store import RiskStore
from risk.status_display import dashboard_status, evidence_summary


def _norm_title(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def load_project_findings(workspace: Path, project_slug: str = "") -> list[dict[str, Any]]:
    store = RiskStore(workspace)
    try:
        slug = str(project_slug or "").strip()
        if not slug:
            common_path = Path(workspace) / "config" / "common.json"
            if common_path.is_file():
                import json

                common = json.loads(common_path.read_text(encoding="utf-8"))
                project = common.get("project") if isinstance(common.get("project"), dict) else {}
                slug = str(project.get("slug") or "").strip()
        if not slug:
            rows = store.fetchall("SELECT * FROM finding ORDER BY current_risk_score DESC")
        else:
            rows = store.list_findings(slug)
        return [dict(row) for row in rows]
    finally:
        store.close()


def match_finding_for_issue(issue: dict[str, Any], findings: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    issue_id = str(issue.get("id") or "").strip()
    if issue_id:
        for finding in findings:
            if str(finding.get("registry_issue_id") or "").strip() == issue_id:
                return finding
            if str(finding.get("id") or "").strip() == issue_id:
                return finding
    fingerprint = str(issue.get("canonical_fingerprint") or "").strip()
    if fingerprint:
        for finding in findings:
            if str(finding.get("canonical_fingerprint") or "").strip() == fingerprint:
                return finding
    repo = str(issue.get("repository") or "").strip().lower()
    title = _norm_title(str(issue.get("title") or ""))
    if repo and title:
        for finding in findings:
            if str(finding.get("repository") or "").strip().lower() != repo:
                continue
            if _norm_title(str(finding.get("title") or "")) == title:
                return finding
    return None


def overlay_issue_with_finding(issue: dict[str, Any], finding: Optional[dict[str, Any]]) -> dict[str, Any]:
    out = dict(issue)
    if finding is None:
        out["status_source"] = "issue_registry"
        out.setdefault("risk_finding_id", "")
        return out
    evidence = evidence_summary(finding)
    registry_status = str(out.get("status") or "").strip().lower()
    workspace_ignored = registry_status == "ignored"
    status = registry_status if workspace_ignored else dashboard_status(finding)
    out["status"] = status
    out["risk_finding_id"] = str(finding.get("id") or "")
    out["resolution_basis"] = str(finding.get("resolution_basis") or "")
    out["resolution_basis_label"] = evidence["resolution_basis"]
    out["verification_status"] = str(finding.get("verification_status") or "")
    out["verification_label"] = evidence["verification"]
    out["resolved_by"] = str(finding.get("resolved_by") or "")
    out["resolved_at"] = str(finding.get("resolved_at") or finding.get("owner_resolved_at") or out.get("resolved_at") or "")
    out["last_verified_at"] = str(finding.get("last_verified_at") or "")
    out["last_verification_run_id"] = str(finding.get("last_verification_run_id") or "")
    out["status_source"] = "issue_registry" if workspace_ignored else "risk_store"
    if not out.get("jira_key") and finding.get("registry_issue_id"):
        pass
    return out


def apply_risk_overlay(workspace: Path, issues: list[dict[str, Any]], project_slug: str = "") -> list[dict[str, Any]]:
    findings = load_project_findings(workspace, project_slug=project_slug)
    overlaid: list[dict[str, Any]] = []
    for issue in issues:
        finding = match_finding_for_issue(issue, findings)
        overlaid.append(overlay_issue_with_finding(issue, finding))
    return overlaid
