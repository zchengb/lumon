#!/usr/bin/env python3
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple


def load_json(path: Path, default):
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def normalize_title(text) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower())
    return value.strip("-")


def issue_file_path(issue: dict) -> str:
    if issue.get("file"):
        return issue["file"]
    fingerprint = issue.get("fingerprint") or ""
    if fingerprint and not re.fullmatch(r"[a-f0-9]{64}", fingerprint):
        parts = fingerprint.split(":")
        if len(parts) >= 2:
            return parts[1]
    return ""


def issue_match_key(issue: dict) -> str:
    repo = issue.get("repository") or ""
    file_path = issue_file_path(issue)
    if repo and file_path:
        return f"{repo}|{file_path}"
    title = normalize_title(issue.get("title"))
    if repo and title:
        return f"{repo}|{title}"
    return issue.get("id") or ""


def deduplicate_issues(issues: list) -> list:
    groups = {}
    for issue in issues:
        key = issue_match_key(issue)
        groups.setdefault(key, []).append(issue)

    merged = []
    for group in groups.values():
        if len(group) == 1:
            merged.append(group[0])
            continue
        best = sorted(
            group,
            key=lambda item: (
                1 if str(item.get("id", "")).startswith("ISSUE-") else 0,
                str(item.get("last_seen_at") or ""),
            ),
            reverse=True,
        )[0]
        merged.append(best)
    return merged


def issue_status_group(status) -> int:
    value = str(status or "").strip().lower()
    if value in {"open", "in_progress", "pr_open"}:
        return 0
    if value in {"ignored", "resolved", "accepted_risk", "false_positive"}:
        return 2
    return 1


def sort_dashboard_issues(issues: list) -> list:
    ordered = sorted(
        issues,
        key=lambda item: str(item.get("first_seen_at") or item.get("last_seen_at") or ""),
        reverse=True,
    )
    ordered.sort(key=lambda item: issue_status_group(item.get("status")))
    return ordered


def severity_counts(findings):
    counts = {"High": 0, "Medium": 0, "Low": 0}
    for finding in findings or []:
        severity = finding.get("severity", "Low")
        counts[severity] = counts.get(severity, 0) + 1
    return counts


def rel(root: Path, path) -> str:
    if not path:
        return ""
    try:
        return str(Path(path).resolve().relative_to(root.resolve()))
    except Exception:
        value = str(path)
        if value.startswith("http://") or value.startswith("https://"):
            return value
        return value


def existing_rel(root: Path, path) -> str:
    if not path:
        return ""
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
    if candidate.is_file():
        return rel(root, candidate)
    return ""


def run_stamp_from_path(path: Path) -> str:
    stem = path.stem
    if stem.startswith("scan-result-"):
        return stem.replace("scan-result-", "", 1)
    return ""


def date_stamp_from_scan(data: dict) -> str:
    for value in (data.get("finished_at"), data.get("started_at")):
        if value and len(str(value)) >= 10:
            return str(value)[:10]
    return ""


def resolve_report_artifacts(
    root: Path,
    reports_dir: Path,
    result_path: Path,
    data: dict,
) -> Tuple[str, str, str]:
    report = data.get("report") if isinstance(data.get("report"), dict) else {}

    html = existing_rel(root, report.get("html_path"))
    pdf = existing_rel(root, report.get("pdf_path"))

    stamps: list[str] = []
    run_stamp = run_stamp_from_path(result_path)
    if run_stamp:
        stamps.append(run_stamp)
    date_stamp = date_stamp_from_scan(data)
    if date_stamp:
        stamps.append(date_stamp)

    for stamp in stamps:
        if not html:
            html = existing_rel(root, reports_dir / f"code-quality-security-scan-{stamp}.html")
        if not pdf:
            pdf = existing_rel(root, reports_dir / f"code-quality-security-scan-{stamp}.pdf")

    report_status = str(report.get("status", "")).strip()
    if not report_status:
        if html and pdf:
            report_status = "generated"
        elif html:
            report_status = "html_only"
        else:
            report_status = "not_generated"

    return html, pdf, report_status


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def process_alive(pid_text: str) -> bool:
    pid_text = str(pid_text or "").strip()
    if not pid_text.isdigit():
        return False
    pid = int(pid_text)
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def parse_iso_timestamp(value: str):
    if not value:
        return None
    try:
        normalized = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def format_duration(seconds: int) -> str:
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return "< 1m"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    remaining = minutes % 60
    if remaining:
        return f"{hours}h {remaining}m"
    return f"{hours}h"


def duration_between(start_value: str, end_value: str) -> str:
    start = parse_iso_timestamp(start_value)
    end = parse_iso_timestamp(end_value)
    if not start or not end:
        return "—"
    return format_duration(int((end - start).total_seconds()))


def infer_phase_from_log(log_path: Path) -> str:
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-400:]
    except OSError:
        return "Running"

    text = "\n".join(lines).lower()
    if "dashboard:" in text and "generated" in text:
        return "Finishing"
    if "generating report and sending feishu" in text:
        return "Report & notify"
    if "lumen scan agent finished" in text:
        return "Report & notify"
    if "scan status:" in text or "writing scan-result" in text or "write results" in text:
        return "Write results"
    if "auto-fix pr" in text or "creating an auto-fix" in text or "auto-fix/" in text:
        return "Auto-fix PR"
    if "fetching recent commits" in text or "scan window" in text or "scanning recent" in text:
        return "Scan repositories"
    if "starting lumen scan agent" in text:
        return "Scan agent"
    if "setup" in text or "worktree" in text:
        return "Setup"
    return "Scan agent"


def read_active_run(root: Path, state_dir: Path, logs_dir: Path) -> Optional[dict]:
    lock_dir = state_dir / "run.lock"
    if not lock_dir.is_dir():
        return None

    pid = read_text(lock_dir / "pid")
    started_at = read_text(lock_dir / "started_at")
    if not pid or not process_alive(pid):
        return None

    latest_log = None
    if logs_dir.is_dir():
        logs = sorted(logs_dir.glob("run-*.log"), key=lambda item: item.stat().st_mtime, reverse=True)
        if logs:
            latest_log = logs[0]

    started = parse_iso_timestamp(started_at)
    elapsed = format_duration(int((datetime.now(timezone.utc) - started).total_seconds())) if started else "—"

    return {
        "status": "running",
        "pid": pid,
        "started_at": started_at,
        "elapsed": elapsed,
        "phase": infer_phase_from_log(latest_log) if latest_log else "Running",
        "log": rel(root, latest_log) if latest_log else "",
    }


def run_outcome(status: str) -> str:
    if status == "failed":
        return "failed"
    if status in {"completed", "completed_clean", "completed_with_findings"}:
        return "success"
    return "other"


def compute_run_stats(runs: list) -> dict:
    now = datetime.now(timezone.utc)
    windows = {
        "24h": now - timedelta(hours=24),
        "7d": now - timedelta(days=7),
    }
    stats = {
        "success_24h": 0,
        "failed_24h": 0,
        "success_7d": 0,
        "failed_7d": 0,
    }
    for run in runs:
        finished = parse_iso_timestamp(run.get("finished_at") or run.get("started_at") or "")
        if not finished:
            continue
        outcome = run_outcome(str(run.get("status", "")))
        if outcome == "other":
            continue
        for key, window_start in windows.items():
            if finished < window_start:
                continue
            if outcome == "success":
                stats[f"success_{key}"] += 1
            elif outcome == "failed":
                stats[f"failed_{key}"] += 1
    return stats


def scan_code_snippets(scan_results: list[dict]) -> tuple[dict[str, str], dict[str, str]]:
    """Index stored scan snippets so older registry records remain readable."""
    by_issue_id: dict[str, str] = {}
    by_match_key: dict[str, str] = {}
    for scan in scan_results:
        for finding in scan.get("findings", []) or []:
            if not isinstance(finding, dict):
                continue
            snippet = str(finding.get("code_snippet") or "").strip()
            if not snippet:
                continue
            issue_id = str(finding.get("issue_id") or "").strip()
            if issue_id:
                by_issue_id.setdefault(issue_id, snippet)
            match_key = issue_match_key(finding)
            if match_key:
                by_match_key.setdefault(match_key, snippet)
    return by_issue_id, by_match_key


def code_excerpt(
    issue: dict,
    repository_paths: dict[str, Path],
    scan_snippets_by_id: dict[str, str],
    scan_snippets_by_match: dict[str, str],
) -> str:
    """Return a small local source excerpt for legacy registry entries without code evidence."""
    existing = str(issue.get("code_snippet") or "").strip()
    if existing:
        return existing
    stored = scan_snippets_by_id.get(str(issue.get("id") or "")) or scan_snippets_by_match.get(issue_match_key(issue))
    if stored:
        return stored
    repository = str(issue.get("repository") or "")
    relative_file = issue_file_path(issue)
    repository_root = repository_paths.get(repository)
    if not repository_root or not relative_file:
        return ""
    try:
        candidate = (repository_root / relative_file).resolve()
        if not candidate.is_relative_to(repository_root.resolve()) or not candidate.is_file():
            return ""
        match = re.match(r"(\d+)", str(issue.get("line_range") or ""))
        line_number = int(match.group(1)) if match else 1
        lines = candidate.read_text(encoding="utf-8", errors="replace").splitlines()
    except (OSError, ValueError):
        return ""
    start = max(0, line_number - 3)
    end = min(len(lines), line_number + 5)
    return "\n".join(f"{index + 1:>4} | {lines[index]}" for index in range(start, end))


def external_url(value) -> str:
    candidate = str(value or "").strip()
    return candidate if candidate.startswith(("https://", "http://")) else ""


def jira_site_host(common: dict, docs_root: Optional[Path] = None) -> str:
    jira = (common.get("notifications") or {}).get("jira") or {}
    site = str(jira.get("site", "")).strip()
    if site:
        if site.startswith(("https://", "http://")):
            return site.rstrip("/")
        if "." in site:
            return f"https://{site}".rstrip("/")
        return f"https://{site}.atlassian.net"

    auth_conf = Path.home() / ".config" / "twg" / "auth.conf"
    try:
        for line in auth_conf.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("domain="):
                domain = line.split("=", 1)[1].strip().strip('"')
                if domain:
                    return domain.rstrip("/") if domain.startswith(("https://", "http://")) else f"https://{domain}".rstrip("/")
    except OSError:
        pass

    # A docs repo is the shared delivery source of truth. When an older scan
    # finding only retained a Jira key, recover the site from any story that
    # already has a published Jira URL instead of hard-coding a company host.
    if docs_root:
        stories = docs_root / "stories"
        for metadata_path in stories.glob("**/metadata.json"):
            metadata = load_json(metadata_path, {})
            url = external_url(metadata.get("jiraUrl") or metadata.get("jira_url"))
            match = re.match(r"(https?://[^/]+)", url)
            if match:
                return match.group(1)
    return ""


def jira_browse_url(issue: dict, common: dict, docs_root: Optional[Path] = None) -> str:
    url = external_url(issue.get("jira_url"))
    if url:
        return url
    key = str(issue.get("jira_key", "")).strip()
    host = jira_site_host(common, docs_root)
    return f"{host}/browse/{key}" if host and key else ""


def issue_for_dashboard(
    issue: dict,
    repository_paths: dict[str, Path],
    scan_snippets_by_id: dict[str, str],
    scan_snippets_by_match: dict[str, str],
    common: dict,
    docs_root: Optional[Path] = None,
) -> dict:
    return {
        "id": issue.get("id", ""),
        "status": issue.get("status", ""),
        "severity": issue.get("severity", ""),
        "repository": issue.get("repository", ""),
        "title": issue.get("title", ""),
        "file": issue.get("file", ""),
        "line_range": issue.get("line_range", ""),
        "impact": issue.get("impact", ""),
        "trigger": issue.get("trigger", ""),
        "suggestion": issue.get("suggestion", ""),
        "root_cause": issue.get("root_cause", ""),
        "validation": issue.get("validation", ""),
        "code_snippet": code_excerpt(issue, repository_paths, scan_snippets_by_id, scan_snippets_by_match),
        "first_seen_at": issue.get("first_seen_at", ""),
        "last_seen_at": issue.get("last_seen_at", ""),
        "resolved_at": issue.get("resolved_at", ""),
        "resolution_reason": issue.get("resolution_reason", ""),
        "stale": bool(issue.get("stale")),
        "ignored_at": issue.get("ignored_at", ""),
        "pr_url": external_url(issue.get("pr_url")),
        "jira_key": issue.get("jira_key"),
        "jira_url": jira_browse_url(issue, common, docs_root),
        "risk_finding_id": issue.get("risk_finding_id", ""),
        "canonical_fingerprint": issue.get("canonical_fingerprint", ""),
        "status_source": issue.get("status_source", "issue_registry"),
        "resolution_basis": issue.get("resolution_basis", ""),
        "resolution_basis_label": issue.get("resolution_basis_label", ""),
        "verification_status": issue.get("verification_status", ""),
        "verification_label": issue.get("verification_label", ""),
        "resolved_by": issue.get("resolved_by", ""),
        "last_verified_at": issue.get("last_verified_at", ""),
        "last_verification_run_id": issue.get("last_verification_run_id", ""),
    }


def get_scan_window_days(common: dict) -> int:
    execution = common.get("execution", {})
    if not isinstance(execution, dict):
        return 7
    try:
        days = int(execution.get("scan_window_days", 7))
    except (TypeError, ValueError):
        return 7
    return max(days, 1)


def is_dry_run(data: dict) -> bool:
    return bool(data.get("dry_run"))


def is_renderable_scan_result(data: dict) -> bool:
    if not data or is_dry_run(data):
        return False
    return bool(str(data.get("started_at") or "").strip() or str(data.get("finished_at") or "").strip())


def trend_points(runs: list, limit: int = 10) -> list:
    points = []
    for run in runs[:limit]:
        label = (run.get("finished_at") or run.get("started_at") or "")[:10]
        points.append(
            {
                "label": label,
                "high": run.get("high", 0),
                "medium": run.get("medium", 0),
                "low": run.get("low", 0),
                "total": run.get("high", 0) + run.get("medium", 0) + run.get("low", 0),
            }
        )
    return list(reversed(points))


def build_payload(root: Path) -> dict:
    common = load_json(root / "config" / "common.json", {})
    repos = load_json(root / "config" / "repos.json", {"repositories": []})
    registry = load_json(root / "state" / "issue-registry.json", {"issues": []})
    product = common.get("product", {})
    results_dir = root / common.get("paths", {}).get("results_dir", "results")
    reports_dir = root / common.get("paths", {}).get("reports_dir", "reports")
    logs_dir = root / common.get("paths", {}).get("logs_dir", "logs")
    state_dir = root / common.get("paths", {}).get("state_dir", "state")
    data_path = root / "dashboard-data.js"

    runs = []
    scan_results: list[dict] = []
    latest_run = None
    latest_path = results_dir / "scan-result.json"
    latest_data = load_json(latest_path, {})
    if is_renderable_scan_result(latest_data):
        scan_results.append(latest_data)
        latest_run = {
            "id": latest_path.stem,
            "finished_at": latest_data.get("finished_at", ""),
            "status": latest_data.get("scan_status", ""),
            "findings": latest_data.get("findings", []),
        }

    for path in sorted(results_dir.glob("scan-result-*.json"), reverse=True):
        data = load_json(path, {})
        if not is_renderable_scan_result(data):
            continue
        scan_results.append(data)
        counts = severity_counts(data.get("findings", []))
        html_path, pdf_path, report_status = resolve_report_artifacts(root, reports_dir, path, data)
        run = {
            "id": path.stem,
            "started_at": data.get("started_at", ""),
            "finished_at": data.get("finished_at", ""),
            "status": data.get("scan_status", ""),
            "repos": data.get("repositories_scanned", 0),
            "high": counts["High"],
            "medium": counts["Medium"],
            "low": counts["Low"],
            "prs": len(data.get("prs", [])),
            "html": html_path,
            "pdf": pdf_path,
            "report_status": report_status,
            "json": rel(root, path),
            "feishu": data.get("feishu", {}).get("status", ""),
            "jira": data.get("jira", {}).get("status", ""),
            "failures": len(data.get("failures", [])),
            "duration": duration_between(data.get("started_at", ""), data.get("finished_at", "")),
            "findings": data.get("findings", []),
        }
        runs.append(run)
        if latest_run is None:
            latest_run = {
                "id": run["id"],
                "finished_at": run["finished_at"],
                "status": run["status"],
                "findings": run["findings"],
            }

    repository_paths = {
        str(repository.get("name") or ""): Path(str(repository.get("path") or "")).expanduser()
        for repository in repos.get("repositories", [])
        if isinstance(repository, dict) and str(repository.get("name") or "") and str(repository.get("path") or "")
    }
    snippets_by_id, snippets_by_match = scan_code_snippets(scan_results)
    registry_issues = deduplicate_issues(registry.get("issues", []))
    lib_root = Path(__file__).resolve().parents[1]
    if str(lib_root) not in sys.path:
        sys.path.insert(0, str(lib_root))
    try:
        from risk.dashboard_overlay import apply_risk_overlay

        project_slug = str((common.get("project") or {}).get("slug") or "")
        registry_issues = apply_risk_overlay(root, registry_issues, project_slug=project_slug)
    except Exception:
        pass
    issues = sort_dashboard_issues([
        issue_for_dashboard(item, repository_paths, snippets_by_id, snippets_by_match, common, root.parent)
        for item in registry_issues
    ])
    issue_counts = {}
    for issue in issues:
        status = issue.get("status", "unknown")
        issue_counts[status] = issue_counts.get(status, 0) + 1
    issue_counts["open_total"] = sum(
        1 for issue in issues
        if str(issue.get("status", "")).lower() in {"open", "in_progress", "pr_open", "reopened"}
    )

    logs = [
        {"name": path.name, "href": rel(root, path)}
        for path in sorted(logs_dir.glob("run-*.log"), key=lambda item: item.stat().st_mtime, reverse=True)[:10]
    ]

    active_run = read_active_run(root, state_dir, logs_dir)
    run_stats = compute_run_stats(runs)
    project = common.get("project", {})

    payload = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "workspace_root": str(root),
        "scan_window_days": get_scan_window_days(common),
        "product": {
            "name": product.get("name", "Lumon"),
            "tagline": product.get("tagline", "Engineering, made legible."),
            "codename": product.get("codename", "lumon"),
        },
        "project": {
            "display_name": project.get("display_name", ""),
        },
        "config": common,
        "repositories": repos.get("repositories", []),
        "runs": runs,
        "run_stats": run_stats,
        "trend": trend_points(runs),
        "active_run": active_run,
        "latest_run": latest_run,
        "issues": issues,
        "issue_counts": issue_counts,
        "logs": logs,
    }

    return payload


def main() -> int:
    workspace_arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LUMEN_WORKSPACE", ".")
    root = Path(workspace_arg).resolve()
    payload = build_payload(root)
    data_path = root / "dashboard-data.js"
    js_text = "window.DASHBOARD_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"
    data_path.write_text(js_text, encoding="utf-8")
    print(data_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
