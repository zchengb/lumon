from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Optional

from risk.correlation import (
    canonical_fingerprint,
    category_from_finding,
    correlate_finding,
    evidence_hash,
    module_from_path,
    trigger_signature,
)
from risk.lifecycle import apply_seen, invalidate_ignore_if_needed, map_registry_status, resolve_missing
from risk.models import STATUS_OPEN, STATUS_REOPENED, RiskConfig
from risk.project_risk import persist_project_snapshot
from risk.retention import apply_retention
from risk.scoring import compute_effective_severity, score_finding
from risk.store import RiskStore, utc_now
from risk.verification import is_verification_scan

SEVERITY_RANK = {"Low": 1, "Medium": 2, "High": 3}


def _project_slug(workspace: Path, common: dict) -> str:
    project = common.get("project") if isinstance(common.get("project"), dict) else {}
    slug = str(project.get("slug") or "").strip()
    if slug:
        return slug
    name = str(project.get("display_name") or "").strip()
    if name:
        return name.lower().replace(" ", "-")
    parent = workspace.name
    if parent in {"lumon", "lumen", ".lumen"}:
        return workspace.parent.name.lower()
    return parent.lower()


def import_issue_registry(store: RiskStore, registry: dict, project_slug: str) -> int:
    imported = 0
    issues = registry.get("issues") if isinstance(registry.get("issues"), list) else []
    existing = {str(row["canonical_fingerprint"]) for row in store.list_findings(project_slug)}
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        finding_like = {
            "repository": issue.get("repository"),
            "file": issue.get("file"),
            "title": issue.get("title"),
            "root_cause": issue.get("root_cause"),
            "trigger": issue.get("trigger"),
        }
        fingerprint = canonical_fingerprint(finding_like)
        if fingerprint in existing:
            continue
        finding_id = f"FIND-{fingerprint[:12]}"
        status = map_registry_status(str(issue.get("status") or "open"))
        store.execute(
            """
            INSERT OR IGNORE INTO finding(
                id, project_slug, canonical_fingerprint, registry_issue_id, repository, module,
                title, category, source_severity, effective_severity, status,
                first_seen_at, last_seen_at, resolved_at, reopened_count, recurrence_count,
                occurrence_count, consecutive_seen_count, verification_status, remediation_status,
                current_risk_score, current_risk_band
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 'not_observed', 'none', 0, 'Low')
            """,
            (
                finding_id,
                project_slug,
                fingerprint,
                str(issue.get("id") or ""),
                str(issue.get("repository") or ""),
                module_from_path(str(issue.get("file") or "")),
                str(issue.get("title") or ""),
                category_from_finding(finding_like),
                str(issue.get("severity") or "Medium"),
                str(issue.get("severity") or "Medium"),
                status,
                issue.get("first_seen_at"),
                issue.get("last_seen_at"),
                issue.get("resolved_at"),
            ),
        )
        if issue.get("jira_key") or issue.get("jira_url"):
            store.execute(
                """
                INSERT INTO external_link(finding_id, type, external_id, url, status, last_synced_at)
                VALUES (?, 'jira', ?, ?, ?, ?)
                """,
                (
                    finding_id,
                    str(issue.get("jira_key") or ""),
                    str(issue.get("jira_url") or ""),
                    "unknown",
                    utc_now(),
                ),
            )
        if issue.get("pr_url"):
            store.execute(
                """
                INSERT INTO external_link(finding_id, type, external_id, url, status, last_synced_at)
                VALUES (?, 'pull_request', ?, ?, ?, ?)
                """,
                (finding_id, "", str(issue.get("pr_url") or ""), "unknown", utc_now()),
            )
        imported += 1
        existing.add(fingerprint)
    store.commit()
    return imported


def _upsert_links(store: RiskStore, finding_id: str, finding: dict, registry_issue: Optional[dict]) -> tuple[bool, bool]:
    has_jira = False
    has_pr = False
    jira_key = str((registry_issue or {}).get("jira_key") or finding.get("jira_key") or "").strip()
    jira_url = str((registry_issue or {}).get("jira_url") or finding.get("jira_url") or "").strip()
    pr_url = str((registry_issue or {}).get("pr_url") or finding.get("pr_url") or "").strip()
    if jira_key or jira_url:
        has_jira = True
        store.execute("DELETE FROM external_link WHERE finding_id = ? AND type = 'jira'", (finding_id,))
        store.execute(
            """
            INSERT INTO external_link(finding_id, type, external_id, url, status, last_synced_at)
            VALUES (?, 'jira', ?, ?, 'tracked', ?)
            """,
            (finding_id, jira_key, jira_url, utc_now()),
        )
    if pr_url:
        has_pr = True
        store.execute("DELETE FROM external_link WHERE finding_id = ? AND type = 'pull_request'", (finding_id,))
        store.execute(
            """
            INSERT INTO external_link(finding_id, type, external_id, url, status, last_synced_at)
            VALUES (?, 'pull_request', '', ?, 'tracked', ?)
            """,
            (finding_id, pr_url, utc_now()),
        )
    return has_jira, has_pr


def ingest_scan_risk(
    *,
    workspace: Path,
    scan: dict[str, Any],
    registry: dict[str, Any],
    common: dict[str, Any],
    result_path: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    config = RiskConfig.from_common(common)
    if not config.enabled:
        return {"status": "disabled"}
    if dry_run:
        return {"status": "dry_run_skipped"}

    store = RiskStore(workspace)
    project_slug = _project_slug(workspace, common)
    imported = import_issue_registry(store, registry, project_slug)

    findings = scan.get("findings") if isinstance(scan.get("findings"), list) else []
    high_count = sum(1 for item in findings if isinstance(item, dict) and str(item.get("severity")) == "High")
    run_id = f"scan-{utc_now().replace(':', '').replace('-', '')}-{uuid.uuid4().hex[:6]}"
    store.upsert_scan_run(
        {
            "id": run_id,
            "project_slug": project_slug,
            "source": "auto_scan",
            "started_at": scan.get("started_at"),
            "completed_at": scan.get("finished_at") or utc_now(),
            "status": str(scan.get("scan_status") or "completed"),
            "window_days": (common.get("execution") or {}).get("scan_window_days") if isinstance(common.get("execution"), dict) else 7,
            "result_path": str(result_path),
            "finding_count": len(findings),
            "high_count": high_count,
            "data_freshness": "fresh",
        }
    )

    registry_by_id = {
        str(issue.get("id")): issue
        for issue in (registry.get("issues") if isinstance(registry.get("issues"), list) else [])
        if isinstance(issue, dict) and issue.get("id")
    }
    existing_rows = store.list_findings(project_slug)
    seen_ids: set[str] = set()
    events: list[dict[str, Any]] = []
    completed_at = str(scan.get("finished_at") or utc_now())

    for finding in findings:
        if not isinstance(finding, dict):
            continue
        outcome, matched, _confidence = correlate_finding(finding, existing_rows)
        if outcome == "ambiguous":
            # M1: treat ambiguous as new; record review event after insert
            outcome = "new_finding"
            matched = None
        fingerprint = canonical_fingerprint(finding)
        module = module_from_path(str(finding.get("file") or ""))
        category = category_from_finding(finding)
        source_severity = str(finding.get("severity") or "Medium")
        registry_issue = registry_by_id.get(str(finding.get("issue_id") or ""))

        reopened = False
        if matched is not None:
            finding_id = str(matched["id"])
            previous = str(matched["status"])
            new_status = apply_seen(
                store,
                finding_id,
                previous,
                completed_at,
                scan_run_id=run_id,
            )
            reopened = new_status == STATUS_REOPENED and previous != STATUS_REOPENED
            if reopened:
                events.append({"type": "reopened", "finding_id": finding_id})
        else:
            finding_id = f"FIND-{fingerprint[:12]}"
            store.execute(
                """
                INSERT INTO finding(
                    id, project_slug, canonical_fingerprint, registry_issue_id, repository, module,
                    title, category, source_severity, effective_severity, status,
                    first_seen_at, last_seen_at, resolved_at, reopened_count, recurrence_count,
                    occurrence_count, consecutive_seen_count, verification_status, remediation_status,
                    last_seen_scan_run_id, current_risk_score, current_risk_band
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 0, 0, 1, 1, 'observed', 'none', ?, 0, 'Low')
                """,
                (
                    finding_id,
                    project_slug,
                    fingerprint,
                    str(finding.get("issue_id") or ""),
                    str(finding.get("repository") or ""),
                    module,
                    str(finding.get("title") or ""),
                    category,
                    source_severity,
                    source_severity,
                    STATUS_OPEN,
                    completed_at,
                    completed_at,
                    run_id,
                ),
            )
            store.insert_event(
                finding_id,
                "opened",
                previous_status=None,
                new_status=STATUS_OPEN,
                reason="new finding from scan",
                occurred_at=completed_at,
            )
            events.append({"type": "new_finding", "finding_id": finding_id, "severity": source_severity})
            existing_rows = store.list_findings(project_slug)

        seen_ids.add(finding_id)
        store.execute(
            """
            INSERT INTO finding_occurrence(
                id, finding_id, scan_run_id, file, line_range, trigger_signature,
                evidence_hash, commit_sha, detected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"occ-{uuid.uuid4().hex[:12]}",
                finding_id,
                run_id,
                str(finding.get("file") or ""),
                str(finding.get("line_range") or ""),
                trigger_signature(finding.get("trigger")),
                evidence_hash(finding),
                "",
                completed_at,
            ),
        )

        row = store.get_finding(finding_id)
        recurrence = int(row["recurrence_count"] or 0) if row else 0
        reopened_count = int(row["reopened_count"] or 0) if row else 0
        first_seen = str(row["first_seen_at"] or completed_at) if row else completed_at
        effective, upgrade_reasons = compute_effective_severity(
            source_severity,
            recurrence_count=recurrence,
            reopened_count=reopened_count,
            module=module,
            critical_modules=config.critical_modules,
            category=category,
            title=str(finding.get("title") or ""),
        )
        previous_effective = str(row["effective_severity"] or source_severity) if row else source_severity
        severity_upgraded = (
            effective != previous_effective
            and SEVERITY_RANK.get(effective, 0) > SEVERITY_RANK.get(previous_effective, 0)
        )
        if severity_upgraded:
            store.execute(
                """
                INSERT INTO severity_adjustment(
                    finding_id, source_severity, effective_severity, direction,
                    reason_codes, rule_version, adjusted_at, confirmed_by
                ) VALUES (?, ?, ?, 'upgrade', ?, '1.0', ?, 'rule-engine')
                """,
                (finding_id, source_severity, effective, json.dumps(upgrade_reasons), completed_at),
            )
            events.append({"type": "severity_upgraded", "finding_id": finding_id, "from": previous_effective, "to": effective})

        has_jira, has_pr = _upsert_links(store, finding_id, finding, registry_issue)
        previous_score = float(row["current_risk_score"] or 0) if row else 0.0
        previous_module = str(row["module"] or "") if row else ""
        breakdown = score_finding(
            effective_severity=effective,
            recurrence_count=recurrence,
            reopened_count=reopened_count,
            module=module,
            first_seen_at=first_seen,
            has_jira=has_jira,
            has_pr=has_pr,
            config=config,
            category=category,
        )
        store.execute(
            """
            UPDATE finding SET source_severity = ?, effective_severity = ?,
                current_risk_score = ?, current_risk_band = ?, title = ?, category = ?,
                repository = ?, module = ?, registry_issue_id = ?
            WHERE id = ?
            """,
            (
                source_severity,
                effective,
                breakdown.total,
                breakdown.band,
                str(finding.get("title") or ""),
                category,
                str(finding.get("repository") or ""),
                module,
                str(finding.get("issue_id") or ""),
                finding_id,
            ),
        )
        score_delta = breakdown.total - previous_score if previous_score else 0.0
        if previous_score and score_delta >= config.score_alert_delta:
            events.append(
                {
                    "type": "score_increased",
                    "finding_id": finding_id,
                    "from": previous_score,
                    "to": breakdown.total,
                }
            )
        if breakdown.band == "High" and (not row or str(row["current_risk_band"]) != "High"):
            events.append({"type": "band_high", "finding_id": finding_id})
        critical_hit = bool(module and module.lower() in set(config.critical_modules) and previous_module.lower() not in set(config.critical_modules))
        if invalidate_ignore_if_needed(
            store,
            finding_id,
            severity_upgraded=severity_upgraded,
            score_delta=score_delta,
            reopened=reopened,
            score_threshold=config.score_alert_delta,
            critical_module_hit=critical_hit,
            blast_radius_expanded=False,
        ):
            events.append({"type": "ignore_invalidated", "finding_id": finding_id})

    resolve_missing(
        store,
        project_slug,
        seen_ids,
        completed_at,
        scan_run_id=run_id,
        verification_scan=is_verification_scan(scan),
    )
    project_snapshot = persist_project_snapshot(store, project_slug, run_id, config)
    retention = apply_retention(store, keep_days=90)
    store.commit()

    sidecar = {
        "status": "updated",
        "project_slug": project_slug,
        "scan_run_id": run_id,
        "imported_registry": imported,
        "finding_count": len(findings),
        "events": events,
        "project_risk": project_snapshot,
        "retention": retention,
    }
    sidecar_path = workspace / "state" / "risk-analysis.json"
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    store.close()
    return sidecar
