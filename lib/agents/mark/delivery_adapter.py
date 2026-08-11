from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from delivery_workspace import workspace_lumen_dir


def _docs_dir(workspace: Path) -> Path:
    root = Path(workspace).expanduser().resolve()
    if (root / "stories").is_dir():
        return root
    for child in ("docs", "mbpass-docs"):
        candidate = root / child
        if (candidate / "stories").is_dir():
            return candidate
    parent = root.parent
    if (parent / "stories").is_dir():
        return parent
    return root


def _find_story_dir(docs_dir: Path, story_ref: str) -> Optional[Path]:
    needle = str(story_ref or "").strip()
    if not needle:
        return None
    stories = docs_dir / "stories"
    if not stories.is_dir():
        return None
    direct = stories / needle
    if direct.is_dir():
        return direct
    upper = needle.upper()
    for path in stories.iterdir():
        if not path.is_dir():
            continue
        meta_path = path / "metadata.json"
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
            if str(meta.get("jiraKey") or "").upper() == upper:
                return path
            if str(meta.get("storyId") or "").upper() == upper:
                return path
        if upper in path.name.upper():
            return path
    return None


def _load_progress(workspace_root: Path) -> dict[str, Any]:
    for candidate in (
        workspace_lumen_dir(workspace_root) / "results" / "delivery-progress.json",
        workspace_root / "results" / "delivery-progress.json",
    ):
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                return data if isinstance(data, dict) else {}
            except Exception:
                return {}
    return {}


def _load_result(workspace_root: Path, run_id: str = "") -> dict[str, Any]:
    results_dirs = (
        workspace_lumen_dir(workspace_root) / "results",
        workspace_root / "results",
    )
    for results in results_dirs:
        path = results / "delivery-result.json"
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    if not run_id or str(data.get("run_id") or "") == run_id:
                        return data
            except Exception:
                pass
        if run_id:
            named = results / f"{run_id}.json"
            if named.is_file():
                try:
                    data = json.loads(named.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        return data
                except Exception:
                    pass
    return {}


def _quick_result_candidates(workspace_root: Path, run_id: str = "") -> list[Path]:
    roots = [Path(workspace_root).expanduser().resolve()]
    if roots[0].parent != roots[0]:
        roots.append(roots[0].parent)
    paths: list[Path] = []
    for root in roots:
        for state_dir in (workspace_lumen_dir(root), root):
            result_dir = state_dir / "results" / "quick-changes"
            if run_id:
                paths.append(result_dir / f"{run_id}.json")
            elif result_dir.is_dir():
                paths.extend(sorted(result_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True))
    return paths


def _load_quick_result(workspace_root: Path, run_id: str = "") -> dict[str, Any]:
    for path in _quick_result_candidates(workspace_root, run_id):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict) and (not run_id or str(payload.get("run_id") or "") == run_id):
            return payload
    return {}


def _load_active_quick_result(workspace_root: Path) -> dict[str, Any]:
    for path in _quick_result_candidates(workspace_root):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(payload, dict) and str(payload.get("status") or "").casefold() in {"running", "started"}:
            return payload
    return {}


def _delivery_lock_candidates(workspace: Path) -> list[Path]:
    root = Path(workspace).expanduser().resolve()
    return [root / "locks" / "delivery-run", workspace_lumen_dir(root) / "locks" / "delivery-run"]


def _terminate_process_tree(pid: int) -> None:
    try:
        children = subprocess.run(["pgrep", "-P", str(pid)], capture_output=True, text=True, check=False).stdout.split()
    except OSError:
        children = []
    for child in children:
        try:
            _terminate_process_tree(int(child))
        except ValueError:
            continue
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, OSError):
        return
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.05)
    try:
        os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, OSError):
        pass


class DeliveryActionAdapter:
    def readiness(self, *, workspace: Path, story: str) -> dict[str, Any]:
        docs = _docs_dir(workspace)
        story_dir = _find_story_dir(docs, story)
        if story_dir is None:
            return {
                "status": "not_ready",
                "code": "STORY_NOT_FOUND",
                "story_id": story,
                "message": f"Story not found for {story}",
            }
        meta_path = story_dir / "metadata.json"
        if not meta_path.is_file():
            return {
                "status": "not_ready",
                "code": "METADATA_MISSING",
                "story_id": story,
                "message": "metadata.json is missing",
            }
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:
            return {
                "status": "not_ready",
                "code": "METADATA_INVALID",
                "story_id": story,
                "message": str(exc)[:200],
            }
        story_md = story_dir / "story.md"
        plan = story_dir / str(metadata.get("technicalPlanFile") or "technical-plan.md")
        if not story_md.is_file():
            return {
                "status": "not_ready",
                "code": "STORY_MISSING",
                "story_id": story,
                "message": "story.md is missing",
            }
        if not plan.is_file():
            return {
                "status": "not_ready",
                "code": "TECHNICAL_PLAN_MISSING",
                "story_id": story,
                "message": "technical-plan.md is missing",
            }
        if str(metadata.get("businessStatus") or "") != "ready":
            return {
                "status": "not_ready",
                "code": "BUSINESS_NOT_READY",
                "story_id": story,
                "message": f"businessStatus={metadata.get('businessStatus')}",
                "metadata": metadata,
            }
        if str(metadata.get("technicalStatus") or "") != "approved":
            return {
                "status": "not_ready",
                "code": "TECHNICAL_PLAN_NOT_APPROVED",
                "story_id": story,
                "message": f"technicalStatus={metadata.get('technicalStatus')}",
                "metadata": metadata,
            }
        repos = metadata.get("linkedRepos") if isinstance(metadata.get("linkedRepos"), list) else []
        if not repos:
            return {
                "status": "not_ready",
                "code": "REPOS_MISSING",
                "story_id": story,
                "message": "linkedRepos is empty",
            }
        return {
            "status": "ready",
            "code": "READY",
            "story_id": str(metadata.get("jiraKey") or story),
            "story_dir": str(story_dir),
            "repositories": repos,
            "metadata": {
                "businessStatus": metadata.get("businessStatus"),
                "technicalStatus": metadata.get("technicalStatus"),
                "jiraKey": metadata.get("jiraKey"),
            },
        }

    def status(self, *, workspace: Path, story: str = "", run_id: str = "") -> dict[str, Any]:
        root = Path(workspace).expanduser().resolve()
        workspace_root = root.parent if root.name in {"lumon", "lumen", ".lumen"} else root
        progress = _load_progress(workspace_root)
        result = _load_result(workspace_root, run_id=run_id)
        quick_result = _load_quick_result(workspace_root, run_id=run_id)
        if not quick_result and not run_id:
            quick_result = _load_active_quick_result(workspace_root)
        return {
            "status": "ok",
            "story_id": story or progress.get("jira_key") or progress.get("story_id") or quick_result.get("repository") or "",
            "run_id": run_id or progress.get("run_id") or result.get("run_id") or quick_result.get("run_id") or "",
            "delivery_status": progress.get("delivery_status") or result.get("status") or quick_result.get("status") or "unknown",
            "progress": progress,
            "result": result,
            "quick_change": quick_result,
        }

    def result(self, *, workspace: Path, run_id: str = "") -> dict[str, Any]:
        root = Path(workspace).expanduser().resolve()
        workspace_root = root.parent if root.name in {"lumon", "lumen", ".lumen"} else root
        payload = _load_result(workspace_root, run_id=run_id)
        if not payload:
            payload = _load_quick_result(workspace_root, run_id=run_id)
        if not payload:
            return {"status": "not_found", "code": "RESULT_NOT_FOUND", "run_id": run_id}
        return {"status": "ok", "run_id": run_id or payload.get("run_id"), "result": payload}

    def start(
        self,
        *,
        workspace: Path,
        story: str,
        actor: str = "",
        source_message_id: str = "",
        trace_id: str = "",
        chat_id: str = "",
        thread_id: str = "",
        project_slug: str = "",
        user_message: str = "",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        ready = self.readiness(workspace=workspace, story=story)
        if ready.get("status") != "ready":
            return {
                "status": "blocked",
                "code": ready.get("code") or "NOT_READY",
                "story_id": story,
                "message": ready.get("message") or "Story is not ready for delivery",
                "readiness": ready,
            }
        docs = _docs_dir(workspace)
        run_id = f"delivery-{uuid.uuid4().hex[:12]}"
        env = os.environ.copy()
        if dry_run:
            env["LUMEN_DRY_RUN"] = "1"
        if actor:
            env["LUMEN_DELIVERY_ACTOR"] = actor
        if source_message_id:
            env["LUMEN_DELIVERY_SOURCE_MESSAGE_ID"] = source_message_id
        if trace_id:
            env["LUMEN_DELIVERY_TRACE_ID"] = trace_id
        env["LUMEN_DELIVERY_CHAT_ID"] = chat_id
        env["LUMEN_DELIVERY_THREAD_ID"] = thread_id
        env["LUMEN_DELIVERY_PROJECT"] = project_slug
        env["LUMEN_DELIVERY_USER_MESSAGE"] = user_message
        env["LUMEN_DELIVERY_RUN_ID"] = run_id
        lumen_bin = env.get("LUMEN_CLI_BIN") or str(Path.home() / ".local" / "bin" / "lumen")
        cmd = [lumen_bin, "delivery", "run", "--story", story, str(docs)]
        if dry_run:
            cmd.insert(3, "--dry-run")

        def _bg() -> None:
            try:
                subprocess.run(cmd, env=env, check=False, capture_output=True, text=True)
            except Exception:
                pass

        threading.Thread(target=_bg, daemon=True).start()
        return {
            "status": "started",
            "run_id": run_id,
            "story_id": ready.get("story_id") or story,
            "workspace": str(docs),
            "repositories": ready.get("repositories") or [],
            "dry_run": dry_run,
            "actor": actor,
            "source_message_id": source_message_id,
            "trace_id": trace_id,
            "next_poll_after_seconds": 5,
        }

    def quick_change(
        self,
        *,
        workspace: Path,
        repository: str,
        target_files: Any,
        request: str,
        target_version: str = "",
        change_type: str = "small_change",
        actor: str = "",
        source_message_id: str = "",
        trace_id: str = "",
        chat_id: str = "",
        thread_id: str = "",
        project_slug: str = "",
        user_message: str = "",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        repository = str(repository or "").strip()
        request = str(request or "").strip()
        if not repository:
            raise ValueError("repository required")
        if not request:
            raise ValueError("request required")
        if isinstance(target_files, str):
            files = [item.strip() for item in target_files.replace(",", "\n").splitlines() if item.strip()]
        elif isinstance(target_files, (list, tuple)):
            files = [str(item).strip() for item in target_files if str(item).strip()]
        else:
            files = []
        if not files:
            raise ValueError("target_files required")
        if len(files) > 8:
            raise ValueError("quick change allows at most 8 target files")
        docs = _docs_dir(workspace)
        run_id = f"quick-{uuid.uuid4().hex[:12]}"
        script = Path(__file__).resolve().parents[2] / "scripts" / "quick_change_runner.py"
        env = os.environ.copy()
        env.update(
            {
                "LUMEN_QUICK_CHANGE_RUN_ID": run_id,
                "LUMEN_QUICK_CHANGE_ACTOR": actor,
                "LUMEN_QUICK_CHANGE_SOURCE_MESSAGE_ID": source_message_id,
                "LUMEN_QUICK_CHANGE_TRACE_ID": trace_id,
                "LUMEN_QUICK_CHANGE_CHAT_ID": chat_id,
                "LUMEN_QUICK_CHANGE_THREAD_ID": thread_id,
                "LUMEN_QUICK_CHANGE_PROJECT": project_slug,
                "LUMEN_QUICK_CHANGE_USER_MESSAGE": user_message or request,
            }
        )
        cmd = [
            sys.executable,
            str(script),
            str(docs),
            "--run-id",
            run_id,
            "--repository",
            repository,
            "--request",
            request,
            "--change-type",
            str(change_type or "small_change"),
        ]
        if target_version:
            cmd.extend(["--target-version", str(target_version).strip()])
        if dry_run:
            cmd.append("--dry-run")
        for item in files:
            cmd.extend(["--target-file", item])

        def _bg() -> None:
            try:
                subprocess.run(cmd, env=env, check=False, capture_output=True, text=True)
            except Exception:
                pass

        threading.Thread(target=_bg, daemon=True).start()
        return {
            "status": "started",
            "run_id": run_id,
            "repository": repository,
            "target_files": files,
            "target_version": str(target_version or "").strip(),
            "change_type": str(change_type or "small_change").strip(),
            "workspace": str(docs),
            "source_message_id": source_message_id,
            "chat_id": chat_id,
            "thread_id": thread_id,
            "next_poll_after_seconds": 3,
        }

    def cancel(self, *, workspace: Path, run_id: str, actor: str = "") -> dict[str, Any]:
        requested = str(run_id or "").strip()
        workspace_root = Path(workspace).expanduser().resolve()
        progress = _load_progress(workspace_root)
        quick_active = _load_active_quick_result(workspace_root)
        active_run = str(progress.get("run_id") or quick_active.get("run_id") or "").strip()
        active_story = str(progress.get("jira_key") or progress.get("story_id") or "").strip()
        if requested and active_story and requested == active_story:
            requested = active_run
        target_run = requested or active_run
        for lock in _delivery_lock_candidates(workspace_root):
            pid_path = lock / "pid"
            if not pid_path.is_file():
                continue
            if requested and active_run and requested != active_run:
                return {
                    "status": "not_found",
                    "code": "DELIVERY_RUN_MISMATCH",
                    "run_id": requested,
                    "active_run_id": active_run,
                    "actor": actor,
                }
            try:
                pid = int(pid_path.read_text(encoding="utf-8").strip())
            except ValueError as exc:
                raise RuntimeError("delivery process id is invalid") from exc
            if pid <= 1:
                raise RuntimeError("delivery process id is invalid")
            _terminate_process_tree(pid)
            quick_result = _load_quick_result(workspace_root, run_id=target_run)
            if quick_result:
                quick_result["status"] = "cancelled"
                quick_result["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                for path in _quick_result_candidates(workspace_root, target_run):
                    if path.is_file():
                        path.write_text(json.dumps(quick_result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                        break
            return {
                "status": "cancelled",
                "code": "DELIVERY_CANCELLED",
                "run_id": target_run,
                "pid": pid,
                "actor": actor,
                "message": "The delivery process was stopped safely.",
            }
        return {
            "status": "not_found",
            "code": "DELIVERY_NOT_ACTIVE",
            "run_id": target_run,
            "actor": actor,
            "message": "No active delivery process was found.",
        }
