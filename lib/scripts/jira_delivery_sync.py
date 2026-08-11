#!/usr/bin/env python3
"""Sync JIRA Story status/comments for Lumen delivery runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from jira_sync import add_pr_link_to_jira, parse_twg_json, refresh_twg_auth, run_twg, site_args, truncate_error, twg_ready


def jira_delivery_config(delivery_config: dict) -> dict:
    jira = delivery_config.get("jira", {})
    return jira if isinstance(jira, dict) else {}


def should_sync_jira(delivery_config: dict) -> tuple[bool, str]:
    config = jira_delivery_config(delivery_config)
    if config.get("enabled") is False:
        return False, "JIRA delivery sync disabled in delivery.json"
    if config.get("enabled") is True:
        ready, reason = twg_ready()
        if not ready:
            return False, reason
        return True, ""
    if config.get("auto_enable_when_twg_ready", True):
        ready, reason = twg_ready()
        return ready, reason
    return False, "JIRA delivery sync not enabled"


def transition_issue(jira_key: str, status_name: str, config: dict) -> None:
    if not status_name:
        return
    returncode, output = run_twg(
        [
            "jira",
            "workitem",
            "update",
            "--id",
            jira_key,
            "--status",
            status_name,
            "-o",
            "json",
            *site_args(config),
        ]
    )
    if returncode != 0:
        raise RuntimeError(truncate_error(output or f"twg status update failed with status {returncode}"))
    payload = parse_twg_json(output)
    data = payload.get("data") if isinstance(payload, dict) else None
    transition = data.get("transition") if isinstance(data, dict) else None
    if isinstance(data, dict) and data.get("success") is False or isinstance(transition, dict) and transition.get("success") is False:
        errors = transition.get("errors") if isinstance(transition, dict) else data.get("errors", [])
        detail = "; ".join(str(item) for item in errors if str(item).strip())
        raise RuntimeError(truncate_error(detail or f"JIRA transition to '{status_name}' was rejected"))


def add_delivery_comment(jira_key: str, comment: str, config: dict, comment_format: str = "markdown") -> None:
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
            comment_format,
            "-o",
            "json",
            *site_args(config),
        ]
    )
    if returncode != 0:
        raise RuntimeError(truncate_error(output or f"twg comment update failed with status {returncode}"))


def delivery_duration(delivery: dict) -> str:
    try:
        started = datetime.fromisoformat(str(delivery.get("started_at", "")).replace("Z", "+00:00"))
        finished = datetime.fromisoformat(str(delivery.get("finished_at", "")).replace("Z", "+00:00"))
    except ValueError:
        return "not recorded"
    seconds = max(0, int((finished - started).total_seconds()))
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"


def delivery_pr_lines(delivery: dict) -> list[str]:
    lines: list[str] = []
    for item in delivery.get("repos_touched", []):
        if not isinstance(item, dict):
            continue
        url = str(item.get("pr_url") or "").strip()
        if url:
            lines.append(f"- {item.get('name') or 'Repository'}: {url}")
    if lines:
        return lines
    return [f"- Pull request: {url}" for url in delivery.get("pr_urls", []) if str(url).strip()]


def completion_comment(delivery: dict) -> str:
    verification = [item for item in delivery.get("verification_results", []) if isinstance(item, dict)]
    passed = sum(item.get("status") == "passed" for item in verification)
    failed = sum(item.get("status") == "failed" for item in verification)
    skipped = sum(item.get("status") == "skipped" for item in verification)
    repositories = ", ".join(
        str(item.get("name", "")).strip()
        for item in delivery.get("repos_touched", [])
        if isinstance(item, dict) and item.get("name")
    ) or "n/a"
    lines = [
        "Lumen Delivery · Completed",
        "",
        f"- Status: Completed",
        f"- Assignee: {str(delivery.get('jira_assignee') or 'Unassigned')}",
        f"- Branch: `{str(delivery.get('branch') or 'n/a')}`",
        f"- Repositories: {repositories}",
        f"- Duration: {delivery_duration(delivery)}",
        f"- Verification: {passed} passed, {failed} failed, {skipped} skipped",
    ]
    deployment = delivery.get("deployment") if isinstance(delivery.get("deployment"), dict) else {}
    if deployment:
        provider = str(deployment.get("provider") or "CI/CD").replace("_", " ").title()
        lines.extend([
            f"- Deployment: {provider} · {str(deployment.get('status') or 'unknown')}",
            f"- Deployment detail: {str(deployment.get('detail') or 'n/a')}",
        ])
        if deployment.get("url"):
            lines.append(f"- Deployment link: {deployment['url']}")
    pr_lines = delivery_pr_lines(delivery)
    if pr_lines:
        lines.extend(["", "Pull requests:", *pr_lines])
    return "\n".join(lines)


def attention_comment(delivery: dict) -> str:
    status = str(delivery.get("delivery_status") or "blocked").replace("_", " ")
    failures = [
        str(item.get("label") or "verification")
        for item in delivery.get("verification_results", [])
        if isinstance(item, dict) and item.get("status") == "failed"
    ]
    detail = ", ".join(failures) if failures else "See Lumen delivery logs for the blocking detail."
    repositories = ", ".join(
        str(item.get("name", "")).strip()
        for item in delivery.get("repos_touched", [])
        if isinstance(item, dict) and item.get("name")
    ) or "n/a"
    deployment = delivery.get("deployment") if isinstance(delivery.get("deployment"), dict) else {}
    lines = [
            "Lumen Delivery · Needs attention",
            "",
            f"- Status: {status.title()}",
            f"- Assignee: {str(delivery.get('jira_assignee') or 'Unassigned')}",
            f"- Branch: `{str(delivery.get('branch') or 'n/a')}`",
            f"- Scope: {repositories}",
            f"- Duration: {delivery_duration(delivery)}",
            f"- Reason: {detail}",
            "- JIRA status moved to Block for follow-up.",
        ]
    deployment_detail = str(deployment.get("detail") or "").strip()
    if deployment_detail:
        lines.append(f"- Deployment detail: {deployment_detail}")
    if deployment.get("url"):
        lines.append(f"- Deployment link: {deployment['url']}")
    return "\n".join(lines)


def started_comment(delivery: dict) -> str:
    repositories = ", ".join(
        str(item.get("name", "")).strip()
        for item in delivery.get("repos_touched", [])
        if isinstance(item, dict) and item.get("name")
    ) or "n/a"
    return "\n".join(
        [
            "Lumen Delivery · Started",
            "",
            "- Status: In progress",
            f"- Assignee: {str(delivery.get('jira_assignee') or 'Unassigned')}",
            f"- Branch: `{str(delivery.get('branch') or 'n/a')}`",
            f"- Scope: {repositories}",
        ]
    )


def sync_delivery_jira(
    delivery: dict,
    delivery_config: dict,
    story_metadata: dict,
    dry_run: bool = False,
    event: str = "",
) -> Dict[str, Any]:
    result: Dict[str, Any] = {"status": "skipped", "detail": ""}
    config = jira_delivery_config(delivery_config)
    enabled, reason = should_sync_jira(delivery_config)
    if not enabled:
        result["detail"] = reason
        return result

    jira_key = str(delivery.get("jira_key") or story_metadata.get("jiraKey") or "").strip()
    if not jira_key:
        result["detail"] = "No JIRA key on story"
        return result

    if dry_run:
        result["status"] = "dry_run"
        result["detail"] = f"Would sync JIRA issue {jira_key}"
        return result

    refreshed, reason = refresh_twg_auth(force=True)
    if not refreshed:
        result["status"] = "failed"
        result["detail"] = reason
        return result

    try:
        in_dev_status = str(config.get("in_dev_status", "IN DEV")).strip()
        dev_done_status = str(config.get("dev_done_status", "DEV DONE")).strip()
        blocked_status = str(config.get("blocked_status", "Block")).strip()
        delivery_status = str(delivery.get("delivery_status", "")).strip()
        registry_issue: dict[str, Any] = {"jira_pr_url": story_metadata.get("jira_pr_url", "")}
        transitions: list[str] = []

        if event == "delivery.started" or delivery_status == "in_progress":
            if in_dev_status:
                transition_issue(jira_key, in_dev_status, config)
                transitions.append(in_dev_status)
            add_delivery_comment(jira_key, started_comment(delivery), config)

        pr_urls = delivery.get("pr_urls") or []
        if pr_urls:
            for pr_url in pr_urls:
                url = str(pr_url).strip()
                if url:
                    add_pr_link_to_jira(jira_key, url, config, registry_issue)

        if event in {"delivery.deployed", "delivery.dev_done"} or delivery_status in {"completed", "dev_done", "pr_open"}:
            if dev_done_status:
                transition_issue(jira_key, dev_done_status, config)
                transitions.append(dev_done_status)
            add_delivery_comment(jira_key, completion_comment(delivery), config)

        if event in {"delivery.deployment_failed", "delivery.failed", "delivery.blocked"} or delivery_status in {"failed", "blocked"}:
            if blocked_status:
                transition_issue(jira_key, blocked_status, config)
                transitions.append(blocked_status)
            add_delivery_comment(jira_key, attention_comment(delivery), config)

        result["status"] = "synced"
        result["jira_key"] = jira_key
        result["detail"] = f"Updated {jira_key}" + (
            f" -> {', '.join(transitions)}" if transitions else ""
        )
        if registry_issue.get("jira_pr_url"):
            result["jira_pr_url"] = registry_issue["jira_pr_url"]
    except Exception as exc:
        result["status"] = "failed"
        result["detail"] = str(exc)
    return result
