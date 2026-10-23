"""Explicit stop/resume requests and read-only worktree checkpoints."""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from uuid import UUID

from lumon.delivery.model import (
    DeliveryActivity,
    DeliveryPoll,
    DeliveryPollState,
    DeliveryRun,
    DeliveryState,
)
from lumon.delivery.store import DeliveryRunStore
from lumon.errors import PreflightError


def require_owned(run: DeliveryRun, workspace_id: UUID, attempt: int) -> None:
    if run.workspace_id not in {None, workspace_id}:
        raise PreflightError("Delivery record does not belong to this Workspace.")
    if run.attempt != attempt:
        raise PreflightError("Delivery attempt changed; refresh before trying again.")


def request_stop(
    store: DeliveryRunStore, workspace: Path, workspace_id: UUID, run_id: str, *, attempt: int
) -> None:
    run = store.load(workspace, run_id)
    require_owned(run, workspace_id, attempt)
    if run.state != DeliveryState.RUNNING or run.poll_id is None:
        raise PreflightError("Only an active managed Delivery can be stopped.")
    poll = store.load_poll(workspace, run.poll_id)
    if poll.workspace_id != workspace_id or poll.state != DeliveryPollState.RUNNING:
        raise PreflightError("Delivery execution is no longer active.")
    if store.stop_requested(workspace, poll.run_id) is None:
        raise PreflightError("This execution predates stop support; stop its owning worker first.")
    store.set_control(workspace, poll.run_id, stopping=True)


def prepare_resume(
    store: DeliveryRunStore,
    workspace: Path,
    workspace_id: UUID,
    run_id: str,
    *,
    attempt: int,
    poll: DeliveryPoll,
    reentry_id: str | None = None,
) -> DeliveryRun:
    """Called under the Workspace execution lock, before any Agent or external write."""

    run = store.load(workspace, run_id)
    require_owned(run, workspace_id, attempt)
    if run.state not in {DeliveryState.FAILED, DeliveryState.BLOCKED, DeliveryState.STOPPED}:
        raise PreflightError("Only a failed, blocked or stopped Delivery can be resumed.")
    snapshot = worktree_snapshot(workspace, run.story_key)
    store.archive_attempt(workspace, run)
    resumed = replace(
        run,
        state=DeliveryState.RUNNING,
        finished_at=None,
        attempt=run.attempt + 1,
        attempt_started_at=poll.started_at,
        poll_id=poll.run_id,
        reason=None,
        detail="Resuming saved Delivery; refreshing context and checking prior evidence.",
        verification_summary=None
        if snapshot != run.worktree_snapshot
        else run.verification_summary,
        worktree_snapshot=snapshot,
        jira_reentry_id=reentry_id or run.jira_reentry_id,
    )
    store.save(workspace, resumed)
    store.restore_history(workspace, run_id)
    store.record_activity(
        workspace,
        run_id,
        DeliveryActivity(
            poll.started_at,
            run.phase,
            f"Resume attempt {resumed.attempt}; previous outcome: {run.state}.",
        ),
    )
    return resumed


def save_checkpoint(
    store: DeliveryRunStore,
    workspace: Path,
    run_id: str,
    *,
    detail: str | None = None,
    comment_id: str | None = None,
) -> DeliveryRun:
    run = store.load(workspace, run_id)
    if comment_id and run.result_comment_id not in {None, comment_id}:
        raise PreflightError(
            "Reuse the existing Delivery result comment instead of replacing its ID."
        )
    updated = replace(
        run,
        checkpoint=detail[:4000] if detail is not None else run.checkpoint,
        worktree_snapshot=worktree_snapshot(workspace, run.story_key),
        result_comment_id=comment_id or run.result_comment_id,
    )
    store.save(workspace, updated)
    return updated


def acknowledge_stop(
    store: DeliveryRunStore, workspace: Path, poll: DeliveryPoll, now: datetime
) -> None:
    """Only the owning worker calls this, after its Agent task has been reaped."""

    for run in store.list(workspace):
        if run.poll_id != poll.run_id or run.state != DeliveryState.RUNNING:
            continue
        detail = "Stopped by user; existing work and external effects are preserved."
        store.save(
            workspace, replace(run, state=DeliveryState.STOPPED, finished_at=now, detail=detail)
        )
        store.record_activity(workspace, run.run_id, DeliveryActivity(now, run.phase, detail))
    current = store.load_poll(workspace, poll.run_id)
    claimed = [run for run in store.list(workspace) if run.poll_id == poll.run_id]
    if claimed and all(run.state == DeliveryState.COMPLETED for run in claimed):
        store.save_poll(
            workspace,
            replace(
                current,
                state=DeliveryPollState.COMPLETED,
                finished_at=now,
                detail="Delivery completed before interruption.",
            ),
        )
        return
    store.save_poll(
        workspace,
        replace(
            current,
            state=DeliveryPollState.STOPPED,
            finished_at=now,
            detail="Agent execution stopped; safe to resume.",
        ),
    )


def worktree_snapshot(workspace: Path, story_key: str) -> str:
    """Fingerprint source without persisting diffs, file contents or credentials."""

    parent = workspace / "lumon" / "worktrees" / story_key.lower()
    if not parent.exists():
        parent = workspace / "lumon" / "worktrees" / story_key
    if not parent.exists():
        return "[]"
    if not parent.is_dir():
        raise PreflightError("Delivery worktree path is not a directory.")
    if (
        not parent.resolve().is_relative_to((workspace / "lumon" / "worktrees").resolve())
        or not parent.resolve().is_relative_to(workspace.resolve())
        or parent.is_symlink()
    ):
        raise PreflightError("Delivery worktree is outside the Workspace.")
    snapshots: list[dict[str, str]] = []
    for repository in sorted(parent.iterdir()):
        if not repository.is_dir() or repository.is_symlink():
            continue
        try:
            head = _git(repository, "rev-parse", "HEAD").decode().strip()
            digest = hashlib.sha256(
                _git(repository, "diff", "HEAD", "--binary", "--no-ext-diff", "--no-textconv")
            )
            for name in _git(repository, "ls-files", "--others", "--exclude-standard", "-z").split(
                b"\0"
            ):
                if not name:
                    continue
                file = repository / name.decode()
                digest.update(name)
                if file.is_symlink() or not file.resolve().is_relative_to(repository.resolve()):
                    digest.update(b"symlink")
                    continue
                with file.open("rb") as stream:
                    while chunk := stream.read(1024 * 1024):
                        digest.update(chunk)
            snapshots.append(
                {
                    "path": str(repository.relative_to(workspace)),
                    "head": head,
                    "fingerprint": digest.hexdigest(),
                }
            )
        except (OSError, UnicodeDecodeError, subprocess.SubprocessError) as exc:
            raise PreflightError(
                "Unable to checkpoint Delivery worktree; existing files were preserved."
            ) from exc
    return json.dumps(snapshots, sort_keys=True)


def _git(repository: Path, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10,
    ).stdout
