"""Small provider seam for post-publish deployment tracking.

The delivery and quick-change runners only know that a deployment is pending.
This module owns provider-specific polling and the final customer/Agent report.
Credentials are deliberately read from environment variables, never persisted.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
LIB_DIR = SCRIPT_DIR.parent
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from delivery_workspace import workspace_lumen_dir

PENDING = {"queued", "running"}
TERMINAL = {"succeeded", "failed", "cancelled", "timeout"}
PROVIDERS = {"none", "jenkins", "github_actions"}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalized_config(delivery_config: dict[str, Any]) -> dict[str, Any]:
    raw = delivery_config.get("deployment_tracking")
    raw = raw if isinstance(raw, dict) else {}
    provider = str(raw.get("provider") or "none").strip().casefold()
    if provider not in PROVIDERS:
        provider = "none"
    try:
        poll_interval = max(5, min(3600, int(raw.get("poll_interval_seconds") or 30)))
    except (TypeError, ValueError):
        poll_interval = 30
    try:
        timeout = max(60, min(7 * 24 * 3600, int(raw.get("timeout_seconds") or 3600)))
    except (TypeError, ValueError):
        timeout = 3600
    jenkins = raw.get("jenkins") if isinstance(raw.get("jenkins"), dict) else {}
    github = raw.get("github_actions") if isinstance(raw.get("github_actions"), dict) else {}
    return {
        "enabled": bool(raw.get("enabled", False)) and provider != "none",
        "provider": provider,
        "poll_interval_seconds": poll_interval,
        "timeout_seconds": timeout,
        "failure_policy": "notify" if raw.get("failure_policy") == "notify" else "dispatch_agent",
        "jenkins": {
            "job": str(jenkins.get("job") or "").strip(),
            "trigger_mode": "cli" if jenkins.get("trigger_mode") == "cli" else "observe",
            "url_env": str(jenkins.get("url_env") or "JENKINS_URL").strip() or "JENKINS_URL",
            "auth_env": str(jenkins.get("auth_env") or "JENKINS_AUTH").strip() or "JENKINS_AUTH",
            "cli": str(jenkins.get("cli") or "jenkins-cli").strip() or "jenkins-cli",
        },
        "github_actions": {
            "repository": str(github.get("repository") or "").strip(),
            "workflow": str(github.get("workflow") or "").strip(),
            "trigger_mode": "gh" if github.get("trigger_mode") == "gh" else "observe",
            "gh_bin": str(github.get("gh_bin") or "gh").strip() or "gh",
        },
    }


def deployment_config_for_workspace(workspace_root: Path) -> dict[str, Any]:
    candidates = [workspace_lumen_dir(workspace_root) / "config" / "delivery.json", workspace_root / "config" / "delivery.json"]
    for path in candidates:
        if path.is_file():
            return normalized_config(load_json(path, {}))
    return normalized_config({})


def commit_sha(result: dict[str, Any]) -> str:
    direct = str(result.get("commit_sha") or "").strip()
    if direct:
        return direct
    commits = result.get("commits")
    if isinstance(commits, list):
        for item in reversed(commits):
            if isinstance(item, dict) and str(item.get("sha") or "").strip():
                return str(item["sha"]).strip()
    return ""


def prepare_tracking(result_path: Path, config: dict[str, Any], source: str) -> dict[str, Any] | None:
    result = load_json(result_path, {})
    if not isinstance(result, dict) or not config.get("enabled"):
        return None
    sha = commit_sha(result)
    pr_urls = [str(value).strip() for value in result.get("pr_urls") or [] if str(value).strip()]
    if not sha and not pr_urls:
        return None
    existing = result.get("deployment") if isinstance(result.get("deployment"), dict) else {}
    deployment = {
        **existing,
        "provider": config["provider"],
        "status": str(existing.get("status") or "queued"),
        "source": source,
        "commit_sha": sha,
        "branch": str(result.get("branch") or result.get("base_branch") or "").strip(),
        "url": str(existing.get("url") or (pr_urls[0] if pr_urls else "")).strip(),
        "started_at": str(existing.get("started_at") or utc_now()),
        "last_checked_at": str(existing.get("last_checked_at") or ""),
        "finished_at": str(existing.get("finished_at") or ""),
        "detail": str(existing.get("detail") or "CI/CD deployment tracking started"),
    }
    result["deployment"] = deployment
    result["status"] = "awaiting_deploy"
    result["delivery_status"] = "awaiting_deploy"
    result["updated_at"] = utc_now()
    save_json(result_path, result)
    return deployment


def _github_status(value: Any, conclusion: Any) -> str:
    status = str(value or "").casefold()
    result = str(conclusion or "").casefold()
    if status in {"queued", "waiting", "pending", "requested"}:
        return "queued"
    if status in {"in_progress", "running"}:
        return "running"
    if status == "completed":
        if result in {"success", "neutral", "skipped"}:
            return "succeeded"
        if result in {"cancelled", "canceled"}:
            return "cancelled"
        return "failed"
    return "queued"


def poll_github(config: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    settings = config.get("github_actions", {})
    repository = str(settings.get("repository") or "").strip()
    workflow = str(settings.get("workflow") or "").strip()
    sha = str(target.get("commit_sha") or "").strip()
    if not repository:
        return {"status": "failed", "detail": "GitHub Actions repository is not configured"}
    args = [
        str(settings.get("gh_bin") or "gh"),
        "run",
        "list",
        "--repo",
        repository,
        "--limit",
        "20",
        "--json",
        "databaseId,status,conclusion,url,workflowName,headSha,headBranch,createdAt,updatedAt",
    ]
    if sha:
        args.extend(["--commit", sha])
    if workflow:
        args.extend(["--workflow", workflow])
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "queued", "detail": f"GitHub Actions is not reachable yet: {exc}"}
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "GitHub Actions query failed").strip()
        return {"status": "queued", "detail": detail[-500:]}
    try:
        runs = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError:
        return {"status": "queued", "detail": "GitHub Actions returned an unreadable run list"}
    if not isinstance(runs, list) or not runs:
        return {"status": "queued", "detail": "Waiting for a matching GitHub Actions run"}
    run = next((item for item in runs if isinstance(item, dict) and (not sha or item.get("headSha") == sha)), runs[0])
    status = _github_status(run.get("status"), run.get("conclusion"))
    return {
        "status": status,
        "detail": f"{run.get('workflowName') or workflow or 'GitHub Actions'}: {run.get('status') or 'unknown'}",
        "url": str(run.get("url") or "").strip(),
        "run_id": str(run.get("databaseId") or "").strip(),
        "branch": str(run.get("headBranch") or "").strip(),
    }


def _jenkins_api_url(base: str, job: str) -> str:
    path = "/job/" + "/job/".join(urllib.parse.quote(part, safe="") for part in job.split("/") if part)
    return base.rstrip("/") + path + "/lastBuild/api/json"


def poll_jenkins(config: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    settings = config.get("jenkins", {})
    job = str(settings.get("job") or "").strip()
    base = os.environ.get(str(settings.get("url_env") or "JENKINS_URL"), "").strip()
    if not job:
        return {"status": "failed", "detail": "Jenkins job is not configured"}
    if not base:
        return {"status": "failed", "detail": f"Jenkins URL env {settings.get('url_env') or 'JENKINS_URL'} is not set"}
    request = urllib.request.Request(_jenkins_api_url(base, job), headers={"Accept": "application/json"})
    auth = os.environ.get(str(settings.get("auth_env") or "JENKINS_AUTH"), "").strip()
    if auth:
        request.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return {"status": "queued", "detail": f"Waiting for Jenkins: {exc}"}
    if not isinstance(payload, dict):
        return {"status": "queued", "detail": "Jenkins returned an unreadable build payload"}
    sha = str(target.get("commit_sha") or "").strip()
    raw = json.dumps(payload, ensure_ascii=False)
    if sha and sha not in raw:
        return {"status": "queued", "detail": "Waiting for Jenkins to expose the published commit"}
    result = str(payload.get("result") or "").upper()
    if payload.get("building") or not result:
        status = "running"
    elif result == "SUCCESS":
        status = "succeeded"
    elif result == "ABORTED":
        status = "cancelled"
    else:
        status = "failed"
    return {
        "status": status,
        "detail": f"Jenkins {job} #{payload.get('number') or '?'}: {result or 'BUILDING'}",
        "url": str(payload.get("url") or "").strip(),
        "run_id": str(payload.get("number") or "").strip(),
    }


def trigger_jenkins(config: dict[str, Any]) -> dict[str, Any]:
    settings = config.get("jenkins", {})
    job = str(settings.get("job") or "").strip()
    if not job:
        return {"status": "failed", "detail": "Jenkins job is not configured"}
    try:
        completed = subprocess.run(
            [str(settings.get("cli") or "jenkins-cli"), "build", job, "-s", "-v"],
            capture_output=True,
            text=True,
            timeout=max(60, int(config.get("timeout_seconds") or 3600)),
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "failed", "detail": f"Jenkins CLI failed: {exc}"}
    output = (completed.stdout or completed.stderr or "").strip()
    return {
        "status": "succeeded" if completed.returncode == 0 else "failed",
        "detail": output[-500:] or f"Jenkins CLI exited with {completed.returncode}",
    }


def poll(config: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    if config.get("provider") == "jenkins":
        return poll_jenkins(config, target)
    if config.get("provider") == "github_actions":
        return poll_github(config, target)
    return {"status": "succeeded", "detail": "Deployment tracking is disabled"}


def _write_tracking(result_path: Path, status: str, update: dict[str, Any]) -> dict[str, Any]:
    result = load_json(result_path, {})
    deployment = result.get("deployment") if isinstance(result.get("deployment"), dict) else {}
    deployment.update(update)
    deployment["status"] = status
    deployment["last_checked_at"] = utc_now()
    if status in TERMINAL:
        deployment["finished_at"] = utc_now()
    result["deployment"] = deployment
    result["status"] = "awaiting_deploy" if status in PENDING else ("completed" if status == "succeeded" else "failed")
    result["delivery_status"] = result["status"]
    result["updated_at"] = utc_now()
    save_json(result_path, result)
    return result


def _render_standard(result_path: Path, event: str) -> None:
    renderer = SCRIPT_DIR / "render-delivery-and-notify.py"
    if not renderer.is_file():
        return
    env = os.environ.copy()
    env["LUMEN_SKIP_DEPLOYMENT_TRACKING"] = "1"
    subprocess.run([sys.executable, str(renderer), str(result_path), "--event", event], env=env, check=False)
    result = load_json(result_path, {})
    workspace_root = Path(str(result.get("workspace_root") or result_path.parent.parent.parent)).expanduser().resolve()
    status = "completed" if event == "delivery.deployed" else "failed"
    progress = SCRIPT_DIR / "delivery_progress.py"
    progress_path = result_path.parent / "delivery-progress.json"
    if progress.is_file():
        subprocess.run(
            [sys.executable, str(progress), "finish", "--workspace-root", str(workspace_root), status, "Deployment tracking finished"],
            check=False,
        )
    archive = SCRIPT_DIR / "archive_delivery_run.py"
    if archive.is_file() and status in {"completed", "failed"}:
        subprocess.run(
            [
                sys.executable,
                str(archive),
                "--workspace-root",
                str(workspace_root),
                "--result",
                str(result_path),
                "--progress",
                str(progress_path),
                "--log-file",
                str((result.get("deployment") or {}).get("monitor_log") or ""),
            ],
            check=False,
        )


def _quick_reply(result: dict[str, Any], succeeded: bool) -> bool:
    message_id = str(result.get("source_message_id") or os.environ.get("LUMEN_QUICK_CHANGE_SOURCE_MESSAGE_ID") or "").strip()
    if not message_id:
        return False
    deployment = result.get("deployment") if isinstance(result.get("deployment"), dict) else {}
    state = "成功完成" if succeeded else "失败"
    text = (
        f"部署跟踪结果：{state}。\n\n"
        f"Provider：{deployment.get('provider') or 'CI/CD'}\n"
        f"状态：{deployment.get('status') or 'unknown'}\n"
        f"{deployment.get('detail') or ''}"
    ).strip()
    if deployment.get("url"):
        text += f"\n链接：{deployment['url']}"
    try:
        from feishu.messenger import FeishuMessenger, should_reply_in_thread

        return bool(
            FeishuMessenger("mark").safe_reply_text(
                message_id,
                text,
                reply_in_thread=should_reply_in_thread(
                    {"chat_id": result.get("chat_id"), "thread_id": result.get("thread_id")}
                ),
            )
        )
    except Exception:
        return False


def _dispatch_failure(result: dict[str, Any]) -> bool:
    if not result.get("deployment") or str(result["deployment"].get("status")) not in {"failed", "timeout", "cancelled"}:
        return False
    original = str(
        result.get("user_message")
        or result.get("request")
        or os.environ.get("LUMEN_DELIVERY_USER_MESSAGE")
        or ""
    ).strip()
    if not original:
        return False
    deployment = result["deployment"]
    handoff = (
        "[LUMEN DEPLOYMENT FAILURE — NEW TURN]\n"
        "The user's original change was published, but its CI/CD deployment did not complete. "
        "Treat this as a new repair turn. Read the workspace and CI evidence yourself; do not rely on stale session context.\n\n"
        f"Original user request:\n{original}\n\n"
        f"Run: {result.get('run_id') or ''}\n"
        f"Provider: {deployment.get('provider') or ''}\n"
        f"State: {deployment.get('status') or ''}\n"
        f"Evidence: {deployment.get('detail') or ''}\n"
        f"URL: {deployment.get('url') or '(none)'}"
    )
    try:
        from agents.bridge import handle_agent_message

        outcome = handle_agent_message(
            agent_id="mark",
            text=handoff,
            meta={
                "_new_agent_turn": "1",
                "_deployment_followup": "1",
                "message_id": str(result.get("source_message_id") or os.environ.get("LUMEN_DELIVERY_SOURCE_MESSAGE_ID") or ""),
                "chat_id": str(result.get("chat_id") or os.environ.get("LUMEN_DELIVERY_CHAT_ID") or ""),
                "thread_id": str(result.get("thread_id") or os.environ.get("LUMEN_DELIVERY_THREAD_ID") or ""),
                "project_slug": str(result.get("project_slug") or os.environ.get("LUMEN_DELIVERY_PROJECT") or ""),
                "_project_slug": str(result.get("project_slug") or os.environ.get("LUMEN_DELIVERY_PROJECT") or ""),
            },
        )
        return bool(outcome)
    except Exception:
        return False


def track(result_path: Path, source: str = "delivery") -> int:
    result = load_json(result_path, {})
    if source == "delivery":
        result.setdefault("source_message_id", os.environ.get("LUMEN_DELIVERY_SOURCE_MESSAGE_ID", ""))
        result.setdefault("chat_id", os.environ.get("LUMEN_DELIVERY_CHAT_ID", ""))
        result.setdefault("thread_id", os.environ.get("LUMEN_DELIVERY_THREAD_ID", ""))
        result.setdefault("project_slug", os.environ.get("LUMEN_DELIVERY_PROJECT", ""))
        result.setdefault("user_message", os.environ.get("LUMEN_DELIVERY_USER_MESSAGE", ""))
        save_json(result_path, result)
    workspace_root = Path(str(result.get("workspace_root") or result_path.parent.parent.parent)).expanduser().resolve()
    config = deployment_config_for_workspace(workspace_root)
    deployment = result.get("deployment") if isinstance(result.get("deployment"), dict) else None
    if deployment is None:
        deployment = prepare_tracking(result_path, config, source)
    if not deployment:
        return 0

    if config.get("provider") == "jenkins" and config.get("jenkins", {}).get("trigger_mode") == "cli":
        result = _write_tracking(result_path, "running", {"detail": "Jenkins CLI build started"})
        update = trigger_jenkins(config)
        final_status = str(update.pop("status") or "failed")
        result = _write_tracking(result_path, final_status, update)
    else:
        deadline = time.monotonic() + int(config.get("timeout_seconds") or 3600)
        while True:
            result = load_json(result_path, {})
            target = result.get("deployment") if isinstance(result.get("deployment"), dict) else deployment
            update = poll(config, target)
            status = str(update.pop("status") or "queued").casefold()
            if status not in PENDING | TERMINAL:
                status = "queued"
            result = _write_tracking(result_path, status, update)
            if status in TERMINAL:
                break
            if time.monotonic() >= deadline:
                _write_tracking(result_path, "timeout", {"detail": "Deployment tracking timed out"})
                result = load_json(result_path, {})
                break
            time.sleep(int(config.get("poll_interval_seconds") or 30))

    deployment = result.get("deployment") if isinstance(result.get("deployment"), dict) else {}
    succeeded = deployment.get("status") == "succeeded"
    if source == "quick_change":
        if not succeeded and config.get("failure_policy") == "dispatch_agent":
            dispatched = _dispatch_failure(result)
            if not dispatched:
                _quick_reply(result, False)
        else:
            _quick_reply(result, succeeded)
    else:
        _render_standard(result_path, "delivery.deployed" if succeeded else "delivery.deployment_failed")
        if not succeeded and config.get("failure_policy") == "dispatch_agent":
            _dispatch_failure(result)
    return 0 if succeeded else 1


def launch_tracker(result_path: Path, source: str) -> bool:
    result = load_json(result_path, {})
    workspace_root = Path(str(result.get("workspace_root") or result_path.parent.parent.parent)).expanduser().resolve()
    config = deployment_config_for_workspace(workspace_root)
    if not prepare_tracking(result_path, config, source):
        return False
    result = load_json(result_path, {})
    log_path = workspace_lumen_dir(workspace_root) / "logs" / "deployment" / f"{result.get('run_id') or result_path.stem}.log"
    deployment = result.get("deployment") if isinstance(result.get("deployment"), dict) else {}
    deployment["monitor_log"] = str(log_path)
    result["deployment"] = deployment
    save_json(result_path, result)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("a", encoding="utf-8")
    command = [sys.executable, str(SCRIPT_DIR / "track_deployment.py"), str(result_path), "--source", source]
    try:
        subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    finally:
        handle.close()
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_path")
    parser.add_argument("--source", default="delivery")
    args = parser.parse_args(argv)
    return track(Path(args.result_path).expanduser().resolve(), args.source)


if __name__ == "__main__":
    raise SystemExit(main())
