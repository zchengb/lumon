#!/usr/bin/env python3
"""Post-process delivery runs: metadata, JIRA, and Feishu notifications."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
LIB_DIR = SCRIPT_DIR.parent
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from delivery_workspace import delivery_config_path, read_json, workspace_lumen_dir, write_json
from delivery_progress import set_phase, update_notifications
from jira_delivery_sync import sync_delivery_jira
from jira_sync import jira_browse_url_from_config
from notifications.events import NotificationEvent
from notifications.router import publish_notification
from notifications.transports.legacy_webhook import LegacyWebhookTransport


def load_render_helpers():
    module_path = SCRIPT_DIR / "render-report-and-notify.py"
    spec = importlib.util.spec_from_file_location("render_report_and_notify", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load helpers from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.send_feishu, module.redact


send_feishu, redact = load_render_helpers()


def _merged_notify_config(*configs: dict) -> dict:
    merged: dict[str, Any] = {"notifications": {}}
    for config in configs:
        if not isinstance(config, dict):
            continue
        notifications = config.get("notifications")
        if isinstance(notifications, dict):
            current = merged["notifications"]
            for key, value in notifications.items():
                if isinstance(value, dict) and isinstance(current.get(key), dict):
                    current[key] = {**current[key], **value}
                else:
                    current[key] = value
            if "mode" in notifications:
                current["mode"] = notifications["mode"]
            if "fallback_to_legacy_webhook" in notifications:
                current["fallback_to_legacy_webhook"] = notifications["fallback_to_legacy_webhook"]
    return merged


def _publish_workflow_feishu(
    *,
    event_type: str,
    workflow: str,
    owner_agent: str,
    card: dict | None,
    webhook: str,
    config: dict,
    dry_run: bool,
    skip_feishu: bool,
    feishu_enabled: bool,
) -> dict[str, Any]:
    if dry_run:
        payload = NotificationEvent(
            event_type=event_type,
            workflow=workflow,
            owner_agent=owner_agent,
            dry_run=True,
        )
    elif skip_feishu:
        payload = NotificationEvent(
            event_type=event_type,
            workflow=workflow,
            owner_agent=owner_agent,
            skip=True,
            skip_detail="LUMEN_SKIP_FEISHU enabled",
        )
    elif not feishu_enabled:
        payload = NotificationEvent(
            event_type=event_type,
            workflow=workflow,
            owner_agent=owner_agent,
            skip=True,
            skip_detail="Feishu notifications are disabled",
        )
    elif not webhook:
        payload = NotificationEvent(
            event_type=event_type,
            workflow=workflow,
            owner_agent=owner_agent,
            skip=True,
            skip_detail="FEISHU_WEBHOOK_URL not set",
        )
    else:
        payload = NotificationEvent(
            event_type=event_type,
            workflow=workflow,
            owner_agent=owner_agent,
            card=card,
            webhook_url=webhook,
        )
    result = publish_notification(
        payload,
        config=config,
        legacy_transport=LegacyWebhookTransport(send_fn=send_feishu),
    )
    status = str(result.get("status") or "skipped")
    if status == "sent":
        return {"status": "sent", "event": event_type}
    if status == "dry_run":
        return {"status": "dry_run", "event": event_type}
    if status == "failed":
        return {"status": "failed", "detail": redact(str(result.get("error") or result.get("detail") or "failed"))}
    detail = result.get("detail") or result.get("error") or "skipped"
    return {"status": "skipped", "detail": redact(str(detail))}


def format_duration(started_at: object, finished_at: object) -> str:
    if not isinstance(started_at, str) or not isinstance(finished_at, str):
        return ""
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        finish = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    except ValueError:
        return ""
    seconds = max(0, int((finish - start).total_seconds()))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


def load_delivery_result(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def resolve_docs_dir(delivery: dict[str, Any], result_path: Path) -> Path:
    docs_dir = str(delivery.get("docs_dir", "")).strip()
    if docs_dir:
        return Path(docs_dir).expanduser().resolve()

    workspace_root = result_path.parent.parent.resolve()
    if (workspace_root / "stories").is_dir():
        return workspace_root
    for child in sorted(workspace_root.iterdir()):
        if child.is_dir() and (child / "stories").is_dir():
            return child.resolve()
    return workspace_root


def jira_assignee(workspace_root: Path, story_path: object) -> str:
    story_name = Path(str(story_path or "")).name
    if not story_name:
        return ""
    snapshot = read_json(workspace_lumen_dir(workspace_root) / "context" / story_name / "jira-context.json")
    workitem = snapshot.get("workitem") if isinstance(snapshot, dict) else {}
    item = workitem[0] if isinstance(workitem, list) and workitem else workitem
    assignee = item.get("assignee") if isinstance(item, dict) else {}
    if isinstance(assignee, dict):
        return str(assignee.get("displayName") or assignee.get("display_name") or assignee.get("name") or "").strip()
    return ""


def align_delivery_timing(delivery: dict[str, Any], workspace_root: Path) -> None:
    """Use the run-level start time for the notification and dashboard history."""
    progress = read_json(workspace_lumen_dir(workspace_root) / "results" / "delivery-progress.json")
    if not isinstance(progress, dict):
        return
    if progress.get("story_id") != delivery.get("story_id"):
        return
    started_at = str(progress.get("started_at") or "").strip()
    if started_at:
        delivery["started_at"] = started_at


def build_delivery_feishu_card(
    event: str,
    delivery: dict[str, Any],
    story_metadata: dict[str, Any],
    docs_dir: Path,
) -> dict[str, Any]:
    jira_key = str(delivery.get("jira_key") or story_metadata.get("jiraKey") or "").strip()
    title = str(story_metadata.get("title") or delivery.get("story_id") or "Delivery").strip()
    status = str(delivery.get("delivery_status") or story_metadata.get("deliveryStatus") or "unknown")
    branch = str(delivery.get("branch") or story_metadata.get("deliveryBranch") or "").strip()
    repos = ", ".join(
        str(item.get("name", "")).strip()
        for item in delivery.get("repos_touched", [])
        if isinstance(item, dict) and item.get("name")
    )
    jira_url = str(story_metadata.get("jiraUrl") or "").strip()
    pr_urls = [str(url).strip() for url in delivery.get("pr_urls") or [] if str(url).strip()]
    verification = [item for item in delivery.get("verification_results") or [] if isinstance(item, dict)]
    passed = [item for item in verification if item.get("status") == "passed"]
    failed = [item for item in verification if item.get("status") == "failed"]
    skipped = [item for item in verification if item.get("status") == "skipped"]

    event_titles = {
        "delivery.started": "Delivery Started",
        "delivery.submitted": "Deployment Tracking Started",
        "delivery.dev_done": "Delivery Completed",
        "delivery.deployed": "Deployment Completed",
        "delivery.failed": "Delivery Needs Attention",
        "delivery.deployment_failed": "Deployment Needs Attention",
        "delivery.blocked": "Delivery Blocked",
    }
    event_templates = {
        "delivery.started": "blue",
        "delivery.submitted": "blue",
        "delivery.dev_done": "green",
        "delivery.deployed": "green",
        "delivery.failed": "red",
        "delivery.deployment_failed": "red",
        "delivery.blocked": "orange",
    }
    event_title = f"Lumen · {event_titles.get(event, 'Delivery Update')}"
    template = event_templates.get(event, "grey")

    status_label = {
        "in_progress": "In progress",
        "awaiting_deploy": "Awaiting deployment",
        "completed": "Completed",
        "ready_for_finalize": "Ready for finalization",
        "failed": "Failed",
        "blocked": "Blocked",
    }.get(status, status.replace("_", " ").title())
    duration = format_duration(delivery.get("started_at"), delivery.get("finished_at"))
    assignee = str(delivery.get("jira_assignee") or "").strip()

    overview = [
        f"**Status:**  {status_label}",
        f"**Model:**  `{_notification_model(delivery.get('model'))}`",
        f"**Assignee:**  {assignee or 'Unassigned'}",
        f"**Scope:**  {repos or 'No repository recorded'}",
    ]
    if branch:
        overview.append(f"**Branch:**  `{branch}`")
    if duration:
        overview.append(f"**Duration:**  {duration}")

    elements: list[dict[str, Any]] = [
        {"tag": "markdown", "content": "\n".join(overview)},
        {"tag": "hr"},
    ]

    if event == "delivery.started":
        elements.append(
            {
                "tag": "markdown",
                "content": "**What happens next**\nLumen has prepared isolated feature worktrees and started the implementation agent.",
            }
        )
    elif event == "delivery.submitted":
        deployment = delivery.get("deployment") if isinstance(delivery.get("deployment"), dict) else {}
        provider = str(deployment.get("provider") or "CI/CD").replace("_", " ").title()
        detail = str(deployment.get("detail") or "Deployment tracking is now running.").strip()
        url = str(deployment.get("url") or "").strip()
        content = f"**What happens next**\nChanges are published. Lumen is tracking the {provider} deployment before reporting completion.\n\n{detail}"
        if url:
            content += f"\n\n[Open deployment]({url})"
        elements.append({"tag": "markdown", "content": content})
    elif event == "delivery.deployed":
        deployment = delivery.get("deployment") if isinstance(delivery.get("deployment"), dict) else {}
        provider = str(deployment.get("provider") or "CI/CD").replace("_", " ").title()
        detail = str(deployment.get("detail") or "Deployment completed successfully.").strip()
        url = str(deployment.get("url") or "").strip()
        content = f"**Deployment result**\n{provider} reports a successful deployment.\n\n{detail}"
        if url:
            content += f"\n\n[Open deployment]({url})"
        elements.append({"tag": "markdown", "content": content})
    elif event in {"delivery.deployment_failed", "delivery.failed"}:
        failed_labels = ", ".join(str(item.get("label") or "verification") for item in failed) or "Delivery verification"
        deployment = delivery.get("deployment") if isinstance(delivery.get("deployment"), dict) else {}
        failure_detail = str(deployment.get("detail") or "The full verification profile did not pass. No commit or pull request was created.")
        if any("suitable driver class" in str(item.get("summary", "")).lower() for item in failed):
            failure_detail = "The full test suite could not initialise its test database configuration. No commit or pull request was created."
        elements.append(
            {
                "tag": "markdown",
                "content": f"**Action required**\n{failure_detail}\n\n**Failed check**  {failed_labels}",
            }
        )
    else:
        summary = f"**Verification**\nPassed: **{len(passed)}**"
        if failed:
            summary += f"  |  Failed: **{len(failed)}**"
        if skipped:
            summary += f"  |  Skipped: **{len(skipped)}**"
        elements.append({"tag": "markdown", "content": summary})

    if pr_urls:
        elements.extend([
            {"tag": "hr"},
            {"tag": "markdown", "content": f"**Pull requests**\n" + "\n".join(pr_urls)},
        ])

    card: dict[str, Any] = {
        "msg_type": "interactive",
        "card": {
            "schema": "2.0",
            "header": {
                "title": {"tag": "plain_text", "content": event_title},
                "subtitle": {"tag": "plain_text", "content": " · ".join(part for part in (jira_key, title) if part)},
                "template": template,
            },
            "body": {
                "elements": elements
            },
        },
    }
    if jira_url:
        card["card"]["card_link"] = {"url": jira_url}
    return card


PATCH_PHASE_LABELS = {
    "capture": "Capture",
    "screen": "Initial screening",
    "context": "Jira context",
    "repository": "Repository mapping",
    "agent": "Patch agent",
    "self_check": "Self-check",
    "publish": "Publish",
    "jira_notify": "Jira & Feishu",
}


def _patch_text(value: object, default: str = "") -> str:
    return " ".join(str(value or default).split())


def _notification_model(value: object, config: dict[str, Any] | None = None, patch: bool = False) -> str:
    execution = config.get("execution") if isinstance(config, dict) and isinstance(config.get("execution"), dict) else {}
    configured = execution.get("patch_model") if patch else execution.get("model")
    return _patch_text(
        value or os.environ.get("LUMEN_MODEL") or os.environ.get("CURSOR_AGENT_MODEL") or configured,
        "cursor-grok-4.5-medium",
    )


def _patch_repositories(patch: dict[str, Any]) -> list[dict[str, Any]]:
    for field in ("repos_touched", "repositories"):
        value = patch.get(field)
        if isinstance(value, list):
            repositories = [item for item in value if isinstance(item, dict)]
            if repositories:
                return repositories
    return []


def _patch_files(repositories: list[dict[str, Any]]) -> list[str]:
    files: list[str] = []
    for repository in repositories:
        values = repository.get("files_changed")
        if not isinstance(values, list):
            continue
        for value in values:
            name = _patch_text(value)
            if name and name not in files:
                files.append(name)
    return files


def _patch_panel(title: str, lines: list[str]) -> dict[str, Any] | None:
    if not lines:
        return None
    return {
        "tag": "collapsible_panel",
        "expanded": False,
        "header": {"title": {"tag": "plain_text", "content": title}},
        "elements": [{"tag": "markdown", "content": "\n".join(lines)}],
    }


def build_patch_feishu_card(event: str, patch: dict[str, Any]) -> dict[str, Any]:
    key = _patch_text(patch.get("jira_key"))
    title = _patch_text(patch.get("jira_summary") or patch.get("jira_title"), "Auto Patch")
    status = _patch_text(patch.get("patch_status"), "unknown").replace("_", " ").title()
    jira_status = _patch_text(patch.get("jira_status"))
    phase = PATCH_PHASE_LABELS.get(_patch_text(patch.get("current_phase")), _patch_text(patch.get("current_phase")))
    repositories = _patch_repositories(patch)
    repo_names = ", ".join(_patch_text(item.get("name")) for item in repositories if _patch_text(item.get("name")))
    if not repo_names:
        repo_names = "Resolving repository mapping" if phase == "Repository mapping" else ("Preparing" if event == "patch.started" else "No repository recorded")
    raw_checks = patch.get("self_checks")
    checks = [item for item in raw_checks if isinstance(item, dict)] if isinstance(raw_checks, list) else []
    counts = {state: sum(1 for item in checks if _patch_text(item.get("status")).casefold() == state) for state in ("passed", "failed", "skipped")}
    files = _patch_files(repositories)
    pr_urls = [str(url).strip() for url in patch.get("pr_urls") or [] if str(url).strip()]
    commits = [item for item in patch.get("commits") or [] if isinstance(item, dict)]
    jira_url = _patch_text(patch.get("jira_url"))
    event_meta = {
        "patch.started": ("Lumen Auto Patch · Started", "blue"),
        "patch.skipped": ("Lumen Auto Patch · Skipped", "grey"),
        "patch.completed": ("Lumen Auto Patch · Completed", "green"),
        "patch.blocked": ("Lumen Auto Patch · Action required", "orange"),
        "patch.failed": ("Lumen Auto Patch · Failed", "red"),
    }
    event_title, template = event_meta.get(event, ("Lumen Auto Patch · Update", "grey"))

    overview = [f"**Status:**  {status}", f"**Model:**  `{_notification_model(patch.get('model'), {}, patch=True)}`"]
    if phase:
        overview.append(f"**Stage:**  {phase}")
    if jira_status:
        overview.append(f"**Jira status:**  {jira_status}")
    if repo_names:
        overview.append(f"**Repository:**  {repo_names}")
    if patch.get("branch"):
        overview.append(f"**Branch:**  `{_patch_text(patch.get('branch'))}`")
    if event in {"patch.blocked", "patch.failed"} and patch.get("blocked_at"):
        overview.append(f"**Waiting since:**  {_patch_text(patch.get('blocked_at'))}")
    duration = format_duration(patch.get("started_at"), patch.get("finished_at"))
    if duration:
        overview.append(f"**Duration:**  {duration}")
    if jira_url and key:
        overview.append(f"**Jira:**  [Open {key}]({jira_url})")
    elements: list[dict[str, Any]] = [{"tag": "markdown", "content": "\n".join(overview)}]

    if event == "patch.started":
        elements.extend([
            {"tag": "hr"},
            {"tag": "markdown", "content": "**Scope**\nBug fixes, small copy adjustments, and bounded functional changes with explicit acceptance criteria; related repositories may be changed as one flow."},
            {"tag": "markdown", "content": "**Next step**\nLumen is reading the Jira context and resolving the target repository."},
        ])
    elif event in {"patch.blocked", "patch.failed"}:
        reason = _patch_text(patch.get("summary"), "Auto Patch could not continue safely.")
        question = _patch_text(patch.get("question"))
        elements.extend([{"tag": "hr"}, {"tag": "markdown", "content": f"**Confirmed**\n{reason}"}])
        if question:
            elements.append({"tag": "markdown", "content": f"**Question**\n{question}"})
        raw_failures = patch.get("failures")
        failures = [
            f"• {_patch_text(item.get('stage'), 'patch')}: {_patch_text(item.get('detail'), 'failed')}"
            for item in raw_failures if isinstance(item, dict)
        ] if isinstance(raw_failures, list) else []
        if isinstance(patch.get("jira"), dict) and patch["jira"].get("comment"):
            failures.append(f"• Jira comment: {_patch_text(patch['jira'].get('comment'))}")
        panel = _patch_panel("View attempts and failures", failures)
        if panel:
            elements.append(panel)
        elements.append({"tag": "markdown", "content": "**Next step**\nReply in Jira; the next Auto Patch cycle will re-read the comments and retry automatically."})
    elif event == "patch.skipped":
        reason = _patch_text(patch.get("summary"), "Auto Patch made no code changes.")
        elements.extend([
            {"tag": "hr"},
            {"tag": "markdown", "content": f"**Reason**\n{reason}"},
            {"tag": "markdown", "content": "**Result**\nNo code was changed, committed, published, or transitioned in Jira."},
        ])
        if checks:
            elements.append({"tag": "markdown", "content": f"**Self-check**\n✓ {counts['passed']} passed · ✕ {counts['failed']} failed · ⊘ {counts['skipped']} skipped"})
    else:
        summary = _patch_text(patch.get("summary"))
        if summary:
            elements.extend([{"tag": "hr"}, {"tag": "markdown", "content": f"**Change summary**\n{summary}"}])
        if files:
            elements.append({"tag": "markdown", "content": f"**Changes**\n{len(files)} file(s) changed"})
            panel = _patch_panel("View changed files", [f"• `{name}`" for name in files])
            if panel:
                elements.append(panel)
        if checks:
            elements.append({"tag": "markdown", "content": f"**Self-check**\n✓ {counts['passed']} passed · ✕ {counts['failed']} failed · ⊘ {counts['skipped']} skipped"})
            panel = _patch_panel(
                "View self-check details",
                [f"• {_patch_text(item.get('label'), 'check')}: {_patch_text(item.get('status'), 'unknown')} — {_patch_text(item.get('summary'))}" for item in checks],
            )
            if panel:
                elements.append(panel)
        publish_lines: list[str] = []
        if patch.get("publish_mode"):
            publish_lines.append(f"**Mode:** {_patch_text(patch.get('publish_mode')).upper()}")
        publish_lines.extend(f"• [Open pull request]({url})" for url in pr_urls)
        publish_lines.extend(f"• Commit `{_patch_text(item.get('sha'))}`" for item in commits if _patch_text(item.get("sha")))
        if publish_lines:
            elements.extend([{"tag": "hr"}, {"tag": "markdown", "content": "**Publish**\n" + "\n".join(publish_lines)}])

    card: dict[str, Any] = {
        "msg_type": "interactive",
        "card": {
            "schema": "2.0",
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": event_title},
                "subtitle": {"tag": "plain_text", "content": " · ".join(part for part in (key, title) if part)},
                "template": template,
            },
            "body": {"elements": elements},
        },
    }
    if jira_url:
        card["card"]["card_link"] = {"url": jira_url}
    return card


def update_story_metadata(
    metadata_path: Path,
    delivery: dict[str, Any],
    pr_urls: list[str],
) -> dict[str, Any]:
    metadata = read_json(metadata_path)
    status = str(delivery.get("delivery_status", "")).strip()
    if status == "awaiting_deploy":
        metadata["deliveryStatus"] = "deploying"
    elif status == "completed":
        metadata["deliveryStatus"] = "pr_open" if pr_urls else "dev_done"
    elif status == "blocked":
        metadata["deliveryStatus"] = "blocked"
    elif status == "failed":
        metadata["deliveryStatus"] = "blocked"
    metadata["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if pr_urls:
        metadata["prUrl"] = pr_urls[0]
        metadata["jira_pr_url"] = pr_urls[0]
    logs = metadata.get("logs")
    if not isinstance(logs, list):
        logs = []
    logs.append(
        {
            "type": "delivery.run",
            "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": metadata.get("deliveryStatus"),
            "result": delivery.get("delivery_status"),
        }
    )
    metadata["logs"] = logs[-20:]
    write_json(metadata_path, metadata)
    return metadata


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: render-delivery-and-notify.py <delivery-result.json> [--event delivery.dev_done]", file=sys.stderr)
        return 1

    result_path = Path(sys.argv[1]).resolve()
    event = "delivery.dev_done"
    if len(sys.argv) >= 4 and sys.argv[2] == "--event":
        event = sys.argv[3]

    if not result_path.is_file():
        print(f"Error: delivery result not found: {result_path}", file=sys.stderr)
        return 1

    dry_run = os.environ.get("LUMEN_DRY_RUN", "").strip().lower() in {"1", "true", "yes"}
    delivery = load_delivery_result(result_path)
    if "patch_status" in delivery:
        workspace_root = result_path.parent.parent.parent
        progress_path = result_path.with_name("patch-progress.json")
        progress = read_json(progress_path, {})
        progress = progress if isinstance(progress, dict) else {}
        notification = {**progress, **delivery}
        delivery_config = read_json(delivery_config_path(workspace_root), {})
        notification["model"] = _notification_model(notification.get("model"), delivery_config, patch=True)
        key = _patch_text(notification.get("jira_key"))
        common = read_json(workspace_lumen_dir(workspace_root) / "config" / "common.json", {})
        jira_config = common.get("notifications", {}).get("jira", {}) if isinstance(common.get("notifications"), dict) else {}
        if not notification.get("jira_url") and isinstance(jira_config, dict) and key:
            jira_url = jira_browse_url_from_config(key, jira_config)
            if jira_url:
                notification["jira_url"] = jira_url
        webhook = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
        feishu_result = {"status": "skipped", "detail": "FEISHU_WEBHOOK_URL not set"}
        notifications = delivery_config.get("notifications", {})
        feishu_enabled = True
        if isinstance(notifications, dict) and isinstance(notifications.get("feishu"), dict) and "enabled" in notifications["feishu"]:
            feishu_enabled = bool(notifications["feishu"].get("enabled"))
        common_notifications = common.get("notifications", {})
        if isinstance(common_notifications, dict) and isinstance(common_notifications.get("feishu"), dict) and "enabled" in common_notifications["feishu"]:
            feishu_enabled = bool(common_notifications["feishu"].get("enabled"))
        skip_feishu = os.environ.get("LUMEN_SKIP_FEISHU", "").strip().casefold() in {"1", "true", "yes"}
        notify_config = _merged_notify_config(delivery_config, common)
        try:
            feishu_result = _publish_workflow_feishu(
                event_type=event,
                workflow="auto_patch",
                owner_agent="irving",
                card=build_patch_feishu_card(event, notification) if webhook and feishu_enabled and not dry_run and not skip_feishu else None,
                webhook=webhook,
                config=notify_config,
                dry_run=dry_run,
                skip_feishu=skip_feishu,
                feishu_enabled=feishu_enabled,
            )
        except Exception as exc:
            feishu_result = {"status": "failed", "detail": redact(str(exc))}
        delivery["feishu"] = feishu_result
        progress["feishu"] = feishu_result
        write_json(progress_path, progress)
        write_json(result_path, delivery)
        run_id = _patch_text(progress.get("run_id"))
        if run_id:
            history_path = result_path.parent.parent / "history" / "patch" / f"{run_id}.json"
            history = read_json(history_path, {})
            if isinstance(history, dict):
                history.setdefault("patch", {})["feishu"] = feishu_result
                history.setdefault("progress", {})["feishu"] = feishu_result
                write_json(history_path, history)
        print(json.dumps({"feishu": feishu_result}, indent=2, ensure_ascii=False))
        return 0
    docs_dir = resolve_docs_dir(delivery, result_path)
    workspace_root = Path(str(delivery.get("workspace_root", "")).strip() or docs_dir).expanduser().resolve()
    delivery_config = read_json(delivery_config_path(workspace_root))
    delivery["model"] = _notification_model(delivery.get("model"), delivery_config)
    align_delivery_timing(delivery, workspace_root)
    should_launch_deployment_tracking = False
    if (
        event == "delivery.dev_done"
        and not dry_run
        and os.environ.get("LUMEN_SKIP_DEPLOYMENT_TRACKING", "").strip().casefold() not in {"1", "true", "yes"}
    ):
        try:
            from deployment_tracking import normalized_config, prepare_tracking

            should_launch_deployment_tracking = bool(
                prepare_tracking(result_path, normalized_config(delivery_config), "delivery")
            )
            if should_launch_deployment_tracking:
                delivery = load_delivery_result(result_path)
                event = "delivery.submitted"
        except Exception as exc:
            delivery["deployment_tracking_error"] = str(exc)[:500]
    story_path = delivery.get("story_path")
    if story_path:
        metadata_path = (docs_dir / str(story_path) / "metadata.json").resolve()
    else:
        metadata_path = docs_dir / "stories" / "metadata.json"

    story_metadata = read_json(metadata_path) if metadata_path.is_file() else {}
    delivery["jira_assignee"] = jira_assignee(workspace_root, story_path)
    webhook = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
    pr_urls = [str(url).strip() for url in delivery.get("pr_urls", []) if str(url).strip()]

    if not dry_run and metadata_path.is_file():
        story_metadata = update_story_metadata(metadata_path, delivery, pr_urls)

    jira_result = sync_delivery_jira(
        delivery,
        delivery_config,
        story_metadata,
        dry_run=dry_run,
        event=event,
    )
    delivery["jira"] = jira_result

    feishu_result = {"status": "skipped", "detail": "FEISHU_WEBHOOK_URL not set"}
    notifications = delivery_config.get("notifications", {})
    feishu_enabled = True
    if isinstance(notifications, dict):
        feishu_cfg = notifications.get("feishu", {})
        if isinstance(feishu_cfg, dict) and "enabled" in feishu_cfg:
            feishu_enabled = bool(feishu_cfg.get("enabled"))

    skip_feishu = os.environ.get("LUMEN_SKIP_FEISHU", "").strip().casefold() in {"1", "true", "yes"}
    try:
        card = None
        if webhook and feishu_enabled and not dry_run and not skip_feishu:
            card = build_delivery_feishu_card(event, delivery, story_metadata, docs_dir)
        feishu_result = _publish_workflow_feishu(
            event_type=event,
            workflow="auto_delivery",
            owner_agent="milchick" if event in {"delivery.deployed", "delivery.deployment_failed"} else "mark",
            card=card,
            webhook=webhook,
            config=delivery_config if isinstance(delivery_config, dict) else {},
            dry_run=dry_run,
            skip_feishu=skip_feishu,
            feishu_enabled=feishu_enabled,
        )
    except Exception as exc:
        feishu_result = {"status": "failed", "detail": redact(str(exc))}

    delivery["feishu"] = feishu_result
    try:
        update_notifications(workspace_root, jira_result, feishu_result)
        if event == "delivery.started":
            set_phase(workspace_root, "jira_start", "completed", str(jira_result.get("detail", "")))
        elif event == "delivery.submitted":
            set_phase(workspace_root, "deployment", "in_progress", "CI/CD deployment tracking started")
            set_phase(workspace_root, "notify", "completed", str(feishu_result.get("status", "")))
        elif event == "delivery.deployed":
            deployment = delivery.get("deployment") if isinstance(delivery.get("deployment"), dict) else {}
            set_phase(workspace_root, "deployment", "completed", str(deployment.get("detail", "")))
            set_phase(workspace_root, "jira_done", "completed", str(jira_result.get("detail", "")))
            set_phase(workspace_root, "notify", "completed", str(feishu_result.get("status", "")))
        elif event == "delivery.deployment_failed":
            deployment = delivery.get("deployment") if isinstance(delivery.get("deployment"), dict) else {}
            set_phase(workspace_root, "deployment", "failed", str(deployment.get("detail", "")))
            set_phase(workspace_root, "notify", "completed", str(feishu_result.get("status", "")))
    except Exception:
        pass
    write_json(result_path, delivery)
    if should_launch_deployment_tracking:
        try:
            from deployment_tracking import launch_tracker

            launch_tracker(result_path, "delivery")
        except Exception as exc:
            delivery["deployment_tracking_error"] = str(exc)[:500]
            write_json(result_path, delivery)
    print(json.dumps({"jira": jira_result, "feishu": feishu_result}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
