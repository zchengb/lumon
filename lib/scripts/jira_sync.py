#!/usr/bin/env python3
"""Create Jira work items for Lumen findings via Atlassian TWG CLI."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SEVERITY_PRIORITY = {
    "High": "High",
    "Medium": "Medium",
    "Low": "Low",
}


def jira_config(common: dict) -> dict:
    notifications = common.get("notifications", {})
    config = notifications.get("jira", {})
    if not isinstance(config, dict):
        return {}
    return config


def workspace_jira_config(workspace_root: Path) -> dict:
    """Load the one workspace-level Jira configuration shared by every loop."""
    for relative in ("config/common.json", "lumon/config/common.json", "lumen/config/common.json", ".lumen/config/common.json"):
        path = workspace_root / relative
        if not path.is_file():
            continue
        try:
            common = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return jira_config(common) if isinstance(common, dict) else {}
    return {}


def is_enabled(common: dict) -> bool:
    config = jira_config(common)
    return bool(config.get("enabled"))


def allowed_severities(config: dict) -> List[str]:
    severities = config.get("severities") or config.get("create_for_severities")
    if isinstance(severities, list) and severities:
        return [str(item) for item in severities]
    return list(SEVERITY_PRIORITY)


def twg_binary() -> Optional[str]:
    return shutil.which("twg")


def twg_ready(*, refresh: bool = False) -> Tuple[bool, str]:
    binary = twg_binary()
    if not binary:
        return False, "twg CLI not found in PATH. Install from https://developer.atlassian.com/cloud/twg-cli/"
    auth_conf = Path.home() / ".config" / "twg" / "auth.conf"
    if not auth_conf.is_file():
        return False, "twg is not authenticated. Run: twg login"
    if refresh:
        return refresh_twg_auth(force=True)
    return True, ""


def refresh_twg_auth(*, force: bool = True) -> Tuple[bool, str]:
    ready, reason = twg_ready()
    if not ready:
        return False, reason
    args = ["auth", "refresh"]
    if force:
        args.append("--force")
    returncode, output = run_twg(args)
    if returncode != 0:
        return False, truncate_error(output or "twg auth refresh failed")
    return True, ""


def delivery_jira_config_enabled(delivery_config: dict) -> bool:
    jira = delivery_config.get("jira", {})
    if not isinstance(jira, dict):
        return False
    if jira.get("enabled") is False:
        return False
    return jira.get("enabled") is True or bool(jira.get("auto_enable_when_twg_ready", True))


def refresh_twg_for_scan_workspace(workspace_root: Path) -> Tuple[bool, str]:
    common_path = workspace_root / "config" / "common.json"
    if not common_path.is_file():
        return True, ""
    try:
        common = json.loads(common_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True, ""
    if not is_enabled(common):
        return True, ""
    return refresh_twg_auth(force=True)


def refresh_twg_for_delivery_workspace(workspace_root: Path) -> Tuple[bool, str]:
    delivery_path = workspace_root / "config" / "delivery.json"
    if not delivery_path.is_file():
        return True, ""
    try:
        delivery_config = json.loads(delivery_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True, ""
    if not delivery_jira_config_enabled(delivery_config):
        return True, ""
    return refresh_twg_auth(force=True)


def run_twg(args: List[str]) -> Tuple[int, str]:
    binary = twg_binary()
    if not binary:
        raise RuntimeError("twg CLI not found in PATH")
    completed = subprocess.run(
        [binary, *args],
        check=False,
        capture_output=True,
        text=True,
    )
    output = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
    return completed.returncode, output


def parse_twg_json(output: str) -> Optional[Any]:
    text = output.strip()
    if not text:
        return None

    stdout_path = extract_output_file_path(text, "stdout:")
    if stdout_path:
        path = Path(stdout_path)
        if path.is_file():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = None
            if isinstance(payload, (dict, list)):
                return payload

    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line.startswith(("{", "[")):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, (dict, list)):
            return payload
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, (dict, list)) else None


def extract_output_file_path(output: str, prefix: str) -> Optional[str]:
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip().strip('"')
    return None


def site_args(config: dict) -> List[str]:
    site = str(config.get("site", "")).strip()
    if site:
        return ["--site", site]
    return []


def assign_to_active_sprint_enabled(config: dict) -> bool:
    if "assign_to_active_sprint" in config:
        return bool(config.get("assign_to_active_sprint"))
    return bool(str(config.get("board_id", "")).strip())


def resolve_board_id(config: dict) -> Optional[str]:
    board_id = str(config.get("board_id", "")).strip()
    if board_id:
        return board_id

    project_key = str(config.get("project_key", "")).strip()
    if not project_key:
        return None

    returncode, output = run_twg(["jira", "board", "query", "--project", project_key, "--max-results", "50", "-o", "json", *site_args(config)])
    if returncode != 0:
        return None

    payload = parse_twg_json(output)
    boards = ((payload or {}).get("data") or {}).get("boards") or []
    boards = [board for board in boards if isinstance(board, dict) and board.get("id") is not None]
    if len(boards) == 1:
        return str(boards[0]["id"]).strip()
    scrum_boards = [board for board in boards if str(board.get("type") or "").casefold() == "scrum"]
    if len(scrum_boards) != 1:
        return None
    return str(scrum_boards[0]["id"]).strip()


def resolve_active_sprint(config: dict) -> Tuple[Optional[str], Optional[str]]:
    board_id = resolve_board_id(config)
    if not board_id:
        return None, None

    returncode, output = run_twg(
        [
            "jira",
            "sprint",
            "snapshot",
            "--board-id",
            board_id,
            "-o",
            "json",
            *site_args(config),
        ]
    )
    if returncode != 0:
        raise RuntimeError(truncate_error(output or f"twg sprint snapshot failed with status {returncode}"))

    payload = parse_twg_json(output)
    data = (payload or {}).get("data") or {}
    sprint = data.get("sprint") if isinstance(data.get("sprint"), dict) else {}
    sprint_id = sprint.get("id")
    if sprint_id is None:
        selected = (data.get("activeSprints") or {}).get("selectedId")
        sprint_id = selected

    if sprint_id is None:
        return None, None

    sprint_name = str(sprint.get("name", "")).strip() or None
    return str(sprint_id), sprint_name


def assign_workitem_to_sprint(issue_key: str, sprint_id: str, config: dict) -> None:
    returncode, output = run_twg(
        [
            "jira",
            "workitem",
            "update",
            "--id",
            issue_key,
            "--sprint",
            sprint_id,
            "-o",
            "json",
            *site_args(config),
        ]
    )
    if returncode != 0:
        raise RuntimeError(truncate_error(output or f"twg workitem update failed with status {returncode}"))


def add_pr_link_to_jira(
    jira_key: str,
    pr_url: str,
    config: dict,
    registry_issue: dict,
) -> bool:
    if registry_issue.get("jira_pr_url") == pr_url:
        return False

    comment = f"Pull request opened: [{pr_url}]({pr_url})"
    returncode, output = run_twg(
        [
            "jira",
            "workitem",
            "update",
            "--id",
            jira_key,
            "--comment",
            comment,
            "--comment-format",
            "markdown",
            "-o",
            "json",
            *site_args(config),
        ]
    )
    if returncode != 0:
        raise RuntimeError(truncate_error(output or f"twg workitem update failed with status {returncode}"))

    registry_issue["jira_pr_url"] = pr_url
    return True


def build_summary(finding: dict, config: dict) -> str:
    prefix = str(config.get("summary_prefix", "[Lumen]")).strip()
    title = str(finding.get("title", "Untitled finding")).strip()
    if prefix and not title.startswith(prefix):
        return f"{prefix} {title}"
    return title


def finding_pr_url(finding: dict, registry_issue: Optional[dict] = None) -> Optional[str]:
    for source in (finding, registry_issue or {}):
        url = str(source.get("pr_url", "")).strip()
        if url:
            return url
    return None


def build_description(finding: dict, issue_id: str, registry_issue: Optional[dict] = None) -> str:
    lines = [
        f"**Lumen issue:** `{issue_id}`",
        f"**Severity:** {finding.get('severity', 'Unknown')}",
        f"**Repository:** {finding.get('repository', 'unknown')}",
        "",
        "## Impact",
        str(finding.get("impact", "")).strip(),
        "",
        "## Trigger",
        str(finding.get("trigger", "")).strip(),
        "",
        "## Location",
        f"`{finding.get('file', '')}` ({finding.get('line_range', '')})",
        "",
        "## Root cause",
        str(finding.get("root_cause", "")).strip(),
        "",
        "## Suggestion",
        str(finding.get("suggestion", "")).strip(),
    ]
    validation = str(finding.get("validation", "")).strip()
    if validation:
        lines.extend(["", "## Validation", validation])
    pr_url = finding_pr_url(finding, registry_issue)
    if pr_url:
        lines.extend(["", "## Pull request", f"[Open pull request]({pr_url})", "", pr_url])
    code = str(finding.get("code_snippet", "")).strip()
    if code:
        lines.extend(["", "## Code snippet", "```", code, "```"])
    lines.extend(["", "_Created automatically by Lumen scan._"])
    return "\n".join(lines).strip()


def build_labels(finding: dict) -> List[str]:
    labels = ["lumen", "auto-scan"]
    severity = str(finding.get("severity", "")).strip().lower()
    if severity:
        labels.append(f"severity-{severity}")
    repository = str(finding.get("repository", "")).strip().lower()
    if repository:
        labels.append(repository.replace(" ", "-"))
    return labels


def parse_issue_key(output: str) -> Tuple[Optional[str], Optional[str]]:
    text = output.strip()
    if not text:
        return None, None

    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line or line.startswith("{"):
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = extract_key_from_payload(payload)
            if key:
                return key, jira_browse_url(key, payload)
    try:
        payload = json.loads(text)
        key = extract_key_from_payload(payload)
        if key:
            return key, jira_browse_url(key, payload)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\b([A-Z][A-Z0-9_]+-\d+)\b", text)
    if match:
        key = match.group(1)
        return key, None
    return None, None


def extract_key_from_payload(payload: Any) -> Optional[str]:
    if isinstance(payload, dict):
        for path in (
            ("key",),
            ("issueKey",),
            ("data", "key"),
            ("data", "issueKey"),
            ("data", "issue", "key"),
            ("result", "key"),
            ("result", "issueKey"),
        ):
            value: Any = payload
            for part in path:
                if not isinstance(value, dict):
                    value = None
                    break
                value = value.get(part)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for value in payload.values():
            key = extract_key_from_payload(value)
            if key:
                return key
    elif isinstance(payload, list):
        for item in payload:
            key = extract_key_from_payload(item)
            if key:
                return key
    return None


def jira_browse_url(key: str, payload: Any) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    for path in (
        ("url",),
        ("browseUrl",),
        ("data", "url"),
        ("data", "browseUrl"),
        ("data", "issue", "url"),
    ):
        value: Any = payload
        for part in path:
            if not isinstance(value, dict):
                value = None
                break
            value = value.get(part)
        if isinstance(value, str) and value.startswith("http"):
            return value
    return None


def jira_browse_url_from_config(key: str, config: dict) -> Optional[str]:
    site = str(config.get("site", "")).strip().rstrip("/")
    if not site:
        auth_conf = Path.home() / ".config" / "twg" / "auth.conf"
        try:
            for line in auth_conf.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("domain="):
                    site = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                    break
        except OSError:
            pass
    if not site:
        return None
    if not site.startswith(("https://", "http://")):
        site = f"https://{site if '.' in site else site + '.atlassian.net'}"
    return f"{site}/browse/{key}"


def create_workitem(
    finding: dict,
    issue_id: str,
    config: dict,
    sprint_id: Optional[str] = None,
    registry_issue: Optional[dict] = None,
) -> Tuple[str, Optional[str]]:
    ready, reason = twg_ready()
    if not ready:
        raise RuntimeError(reason)

    project_key = str(config.get("project_key", "")).strip()
    if not project_key:
        raise RuntimeError("notifications.jira.project_key is not set in config/common.json")

    issue_type = str(config.get("issue_type", "Bug")).strip() or "Bug"

    command = [
        "jira",
        "workitem",
        "create",
        "--space",
        project_key,
        "--type",
        issue_type,
        "--summary",
        build_summary(finding, config),
        "--description",
        build_description(finding, issue_id, registry_issue),
        "--description-format",
        "markdown",
        "--labels",
        ",".join(build_labels(finding)),
        "-o",
        "json",
    ]

    priority = SEVERITY_PRIORITY.get(str(finding.get("severity", "")))
    if priority:
        command.extend(["--priority", priority])

    command.extend(site_args(config))

    returncode, output = run_twg(command)
    if returncode != 0:
        raise RuntimeError(truncate_error(output or f"twg exited with status {returncode}"))

    key, url = parse_issue_key(output)
    if not key:
        raise RuntimeError(f"Could not parse Jira issue key from twg output: {truncate_error(output)}")
    url = url or jira_browse_url_from_config(key, config)

    if sprint_id:
        try:
            assign_workitem_to_sprint(key, sprint_id, config)
        except Exception as exc:
            # Jira creation is the durable operation. Sprint placement is a
            # convenience and must not turn a successfully-created finding
            # into a false sync failure.
            print(f"Warning: created {key}, sprint assignment skipped: {truncate_error(str(exc))}", file=sys.stderr)

    pr_url = finding_pr_url(finding, registry_issue)
    if pr_url and registry_issue is not None:
        registry_issue["jira_pr_url"] = pr_url

    return key, url


def truncate_error(message: str, limit: int = 240) -> str:
    clean = re.sub(r"\s+", " ", message).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1] + "…"


def index_registry_issues(registry: dict) -> Dict[str, dict]:
    indexed = {}
    for issue in registry.get("issues", []):
        issue_id = issue.get("id")
        if issue_id:
            indexed[str(issue_id)] = issue
    return indexed


def sync_jira_issues(
    scan: dict,
    registry: dict,
    registry_path: Path,
    common: dict,
    dry_run: bool = False,
    persist: bool = True,
) -> dict:
    config = jira_config(common)
    summary = {
        "status": "disabled",
        "created": 0,
        "skipped": 0,
        "updated": 0,
        "failed": 0,
        "errors": [],
        "warnings": [],
    }

    if not config.get("enabled"):
        return summary

    ready, reason = twg_ready()
    if not ready:
        summary["status"] = "not_configured"
        summary["errors"].append(reason)
        return summary

    if dry_run:
        summary["status"] = "dry_run_skipped"
        return summary

    refreshed, reason = refresh_twg_auth(force=True)
    if not refreshed:
        summary["status"] = "not_configured"
        summary["errors"].append(reason)
        return summary

    allowed = set(allowed_severities(config))
    indexed = index_registry_issues(registry)

    sprint_id: Optional[str] = None
    if assign_to_active_sprint_enabled(config):
        try:
            sprint_id, _ = resolve_active_sprint(config)
        except Exception as exc:
            sprint_id = None
            summary["warnings"].append(f"Sprint lookup skipped: {truncate_error(str(exc))}")
        if not sprint_id:
            summary["warnings"].append("No active sprint found; Jira findings will be created without sprint assignment.")

    for finding in scan.get("findings", []):
        severity = str(finding.get("severity", ""))
        if severity not in allowed:
            continue

        issue_id = str(finding.get("issue_id", "")).strip()
        if not issue_id:
            continue

        registry_issue = indexed.get(issue_id)
        if registry_issue and registry_issue.get("jira_key"):
            finding["jira_key"] = registry_issue.get("jira_key")
            finding["jira_url"] = registry_issue.get("jira_url")
            pr_url = finding_pr_url(finding, registry_issue)
            if pr_url:
                try:
                    if add_pr_link_to_jira(registry_issue["jira_key"], pr_url, config, registry_issue):
                        summary["updated"] += 1
                except Exception as exc:
                    summary["failed"] += 1
                    summary["errors"].append(f"{issue_id}: {exc}")
            summary["skipped"] += 1
            continue

        try:
            jira_key, jira_url = create_workitem(
                finding,
                issue_id,
                config,
                sprint_id=sprint_id,
                registry_issue=registry_issue,
            )
        except Exception as exc:
            summary["failed"] += 1
            summary["errors"].append(f"{issue_id}: {exc}")
            continue

        finding["jira_key"] = jira_key
        if jira_url:
            finding["jira_url"] = jira_url

        if registry_issue is not None:
            registry_issue["jira_key"] = jira_key
            if jira_url:
                registry_issue["jira_url"] = jira_url
            registry_issue["jira_synced_at"] = scan.get("finished_at")
        summary["created"] += 1

    if summary["failed"] > 0:
        summary["status"] = "completed_with_failures"
    elif summary["created"] > 0 or summary["updated"] > 0:
        summary["status"] = "synced"
    else:
        summary["status"] = "noop"

    if persist and config.get("enabled"):
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        with registry_path.open("w", encoding="utf-8") as handle:
            json.dump(registry, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh TWG OAuth credentials before automated Lumen runs.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    refresh_parser = subparsers.add_parser("refresh", help="Refresh TWG OAuth when Jira sync is enabled for a workspace")
    refresh_parser.add_argument("--scan-workspace", type=Path, help="Scan workspace root (config/common.json)")
    refresh_parser.add_argument("--delivery-workspace", type=Path, help="Delivery workspace root (config/delivery.json)")
    args = parser.parse_args(argv)

    if args.command != "refresh":
        parser.error(f"unsupported command: {args.command}")

    if args.scan_workspace:
        ok, reason = refresh_twg_for_scan_workspace(args.scan_workspace.expanduser().resolve())
    elif args.delivery_workspace:
        ok, reason = refresh_twg_for_delivery_workspace(args.delivery_workspace.expanduser().resolve())
    else:
        refresh_parser.error("pass --scan-workspace or --delivery-workspace")

    if not ok:
        print(reason, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
