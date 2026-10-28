"""Repository preparation against isolated local Git remotes."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lumon.cli.app import app
from lumon.errors import PreflightError
from lumon.workspace.config import WorkspaceConfig
from lumon.workspace.manifest import WorkspaceManifest
from lumon.workspace.model import RepositoryRecord
from lumon.workspace.repository_worktree import (
    PreparedWorktree,
    prepare_worktree,
    remove_read_worktree,
)
from lumon.workspace.settings import AutoDeliverySettings, WorkspaceSettings, WorkspaceSettingsStore


def test_remote_registration_is_cloned_only_when_a_worktree_is_needed(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
) -> None:
    workspace, _source, _remote, existing = repositories
    record = replace(existing, mcp_server="github")
    shutil.rmtree(workspace / record.path)

    prepared = prepare_worktree(workspace, record, "TASK-1", mode="read")

    assert (Path(prepared.path) / "file.txt").read_text() == "initial\n"
    assert (workspace / record.path / ".git").is_dir()
    assert not (workspace / record.path / "file.txt").exists()
    assert remove_read_worktree(workspace, record, "TASK-1", prepared)


def test_remote_clone_failure_does_not_create_a_checkout(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
) -> None:
    workspace, _source, _remote, existing = repositories
    record = replace(existing, url=str(workspace / "missing.git"), mcp_server="github")
    shutil.rmtree(workspace / record.path)

    with pytest.raises(PreflightError, match="Unable to clone"):
        prepare_worktree(workspace, record, "TASK-1", mode="read")

    assert not (workspace / record.path).exists()
    assert not tuple((workspace / "lumon" / "tmp").iterdir())


def git(directory: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(directory), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repositories(tmp_path: Path) -> tuple[Path, Path, Path, RepositoryRecord]:
    source = tmp_path / "source"
    remote = tmp_path / "remote.git"
    workspace = tmp_path / "workspace"
    source.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(source)], check=True)
    git(source, "config", "user.name", "Lumon Test")
    git(source, "config", "user.email", "test@example.invalid")
    (source / "file.txt").write_text("initial\n", encoding="utf-8")
    git(source, "add", "file.txt")
    git(source, "commit", "-qm", "initial")
    subprocess.run(["git", "clone", "-q", "--bare", str(source), str(remote)], check=True)
    (workspace / "repos").mkdir(parents=True)
    subprocess.run(
        ["git", "clone", "-q", remote.as_uri(), str(workspace / "repos" / "app")], check=True
    )
    git(source, "remote", "add", "origin", remote.as_uri())
    record = RepositoryRecord("app", remote.as_uri(), "repos/app", "main")
    return workspace, source, remote, record


def advance(source: Path, content: str) -> str:
    (source / "file.txt").write_text(content, encoding="utf-8")
    git(source, "add", "file.txt")
    git(source, "commit", "-qm", "advance")
    git(source, "push", "-q", "origin", "main")
    return git(source, "rev-parse", "HEAD")


def test_fetches_latest_in_detached_worktree_and_preserves_checkout(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
) -> None:
    workspace, source, _remote, record = repositories
    checkout = workspace / record.path
    original_head = git(checkout, "rev-parse", "HEAD")
    original_tracking = git(checkout, "rev-parse", "refs/remotes/origin/main")
    (checkout / "file.txt").write_text("local change\n", encoding="utf-8")
    (checkout / "untracked.txt").write_text("keep\n", encoding="utf-8")
    latest = advance(source, "remote change\n")

    prepared = prepare_worktree(workspace, record, "review-1", mode="read")

    assert prepared.remote_revision == prepared.revision == latest
    assert prepared.contains_remote and not prepared.dirty and not prepared.reused
    assert (Path(prepared.path) / "file.txt").read_text(encoding="utf-8") == "remote change\n"
    assert git(checkout, "rev-parse", "HEAD") == original_head
    assert git(checkout, "rev-parse", "refs/remotes/origin/main") == original_tracking
    assert (checkout / "file.txt").read_text(encoding="utf-8") == "local change\n"
    assert (checkout / "untracked.txt").read_text(encoding="utf-8") == "keep\n"
    assert git(checkout, "for-each-ref", "refs/lumon/prepared") == ""


def test_cli_prepares_the_registered_repository(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
) -> None:
    workspace, source, _remote, record = repositories
    (workspace / "lumon").mkdir()
    WorkspaceManifest.create("test", "1.0.0").write(workspace / "lumon" / "manifest.json")
    WorkspaceConfig("test", (record,)).write(workspace / "lumon" / "workspace.toml")
    latest = advance(source, "latest\n")

    result = CliRunner().invoke(
        app,
        [
            "workspace",
            "prepare-repository",
            "app",
            "--workspace",
            str(workspace),
            "--task",
            "TASK-1",
            "--mode",
            "delivery",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    receipt = json.loads(result.output)
    assert receipt["remote_revision"] == latest
    assert git(Path(receipt["path"]), "branch", "--show-current") == "lumon/delivery-TASK-1"


def test_delivery_uses_the_saved_target_branch_override(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace, source, _remote, record = repositories
    git(source, "checkout", "-qb", "release")
    (source / "file.txt").write_text("release branch\n", encoding="utf-8")
    git(source, "add", "file.txt")
    git(source, "commit", "-qm", "release change")
    git(source, "push", "-q", "origin", "release")
    (workspace / "lumon").mkdir()
    manifest = WorkspaceManifest.create("test", "1.0.0")
    manifest.write(workspace / "lumon" / "manifest.json")
    WorkspaceConfig("test", (record,)).write(workspace / "lumon" / "workspace.toml")
    state = tmp_path / "state"
    monkeypatch.setenv("LUMON_HOME", str(state))
    WorkspaceSettingsStore(state).save(
        WorkspaceSettings(
            manifest.workspace_id,
            auto_delivery=AutoDeliverySettings(target_branch="release"),
        )
    )

    result = CliRunner().invoke(
        app,
        [
            "workspace",
            "prepare-repository",
            "app",
            "--workspace",
            str(workspace),
            "--task",
            "TASK-2",
            "--mode",
            "delivery",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    receipt = json.loads(result.output)
    assert receipt["branch"] == "release"
    assert (Path(receipt["path"]) / "file.txt").read_text() == "release branch\n"
    assert (workspace / record.path / "file.txt").read_text() == "initial\n"


def test_symlinked_task_directory_is_rejected(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
) -> None:
    workspace, _source, _remote, record = repositories
    worktrees = workspace / "lumon" / "worktrees" / "_reads"
    worktrees.mkdir(parents=True)
    (worktrees / "other").mkdir()
    (worktrees / "task").symlink_to(worktrees / "other", target_is_directory=True)

    with pytest.raises(PreflightError, match="symlink"):
        prepare_worktree(workspace, record, "task", mode="read")
    assert not (worktrees / "other" / "app").exists()


def test_reuses_dirty_delivery_worktree_without_discarding_a_new_remote_revision(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
) -> None:
    workspace, source, _remote, record = repositories
    first = prepare_worktree(workspace, record, "MBPAS-1", mode="delivery")
    worktree = Path(first.path)
    assert git(worktree, "branch", "--show-current") == "lumon/delivery-MBPAS-1"
    (worktree / "file.txt").write_text("in-progress work\n", encoding="utf-8")
    latest = advance(source, "new remote\n")

    resumed = prepare_worktree(workspace, record, "MBPAS-1", mode="delivery")

    assert resumed.reused and resumed.dirty
    assert resumed.remote_revision == latest and not resumed.contains_remote
    assert resumed.revision == first.revision
    assert (worktree / "file.txt").read_text(encoding="utf-8") == "in-progress work\n"


def test_fetch_failure_never_falls_back_to_a_stale_worktree(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
) -> None:
    workspace, _source, remote, record = repositories
    remote.rename(remote.with_name("unavailable.git"))

    with pytest.raises(PreflightError, match="fetch"):
        prepare_worktree(workspace, record, "failed", mode="read")

    assert not (workspace / "lumon" / "worktrees" / "_reads" / "failed").exists()


def test_read_and_edit_worktrees_can_use_the_same_task_key(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
) -> None:
    workspace, _source, _remote, record = repositories
    read = prepare_worktree(workspace, record, "task-1", mode="read")
    work = prepare_worktree(workspace, record, "task-1", mode="work")
    assert read.path != work.path
    assert read.revision == work.revision
    assert git(Path(work.path), "branch", "--show-current") == "lumon/task-1/app"


def test_scan_preparation_deepens_shallow_history_to_cover_its_window(
    repositories: tuple[Path, Path, Path, RepositoryRecord], tmp_path: Path
) -> None:
    _workspace, source, remote, record = repositories
    advance(source, "second commit\n")
    workspace = tmp_path / "shallow-workspace"
    (workspace / "repos").mkdir(parents=True)
    subprocess.run(
        ["git", "clone", "-q", "--depth=1", remote.as_uri(), str(workspace / "repos" / "app")],
        check=True,
    )
    assert git(workspace / record.path, "rev-parse", "--is-shallow-repository") == "true"

    prepared = prepare_worktree(
        workspace,
        record,
        "scan-window",
        mode="read",
        history_since=datetime.now(UTC) - timedelta(days=7),
    )

    assert prepared.history_covered is True
    assert git(Path(prepared.path), "rev-list", "--count", "HEAD") == "2"


def test_shallow_history_is_reported_when_the_deepen_budget_is_not_enough(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _workspace, source, remote, record = repositories
    advance(source, "second commit\n")
    advance(source, "third commit\n")
    workspace = tmp_path / "shallow-workspace"
    (workspace / "repos").mkdir(parents=True)
    subprocess.run(
        ["git", "clone", "-q", "--depth=1", remote.as_uri(), str(workspace / "repos" / "app")],
        check=True,
    )
    monkeypatch.setattr("lumon.workspace.repository_worktree._HISTORY_DEEPEN_STEPS", (1,))

    prepared = prepare_worktree(
        workspace,
        record,
        "scan-window",
        mode="read",
        history_since=datetime.now(UTC) - timedelta(days=7),
    )

    assert prepared.shallow is True and prepared.history_covered is False
    assert prepared.history_issue == "deepen_limit"
    assert git(Path(prepared.path), "rev-list", "--count", "HEAD") == "2"


def test_cli_can_request_history_coverage(
    repositories: tuple[Path, Path, Path, RepositoryRecord], tmp_path: Path
) -> None:
    _workspace, source, remote, record = repositories
    advance(source, "second commit\n")
    workspace = tmp_path / "shallow-workspace"
    (workspace / "repos").mkdir(parents=True)
    subprocess.run(
        ["git", "clone", "-q", "--depth=1", remote.as_uri(), str(workspace / "repos" / "app")],
        check=True,
    )
    (workspace / "lumon").mkdir()
    WorkspaceManifest.create("test", "1.0.0").write(workspace / "lumon" / "manifest.json")
    WorkspaceConfig("test", (record,)).write(workspace / "lumon" / "workspace.toml")

    result = CliRunner().invoke(
        app,
        [
            "workspace",
            "prepare-repository",
            "app",
            "--workspace",
            str(workspace),
            "--task",
            "history",
            "--history-days",
            "7",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["history_covered"] is True


def test_failed_deepening_keeps_the_fresh_commit_and_marks_history_incomplete(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _workspace, source, remote, record = repositories
    latest = advance(source, "latest\n")
    workspace = tmp_path / "shallow-workspace"
    (workspace / "repos").mkdir(parents=True)
    subprocess.run(
        ["git", "clone", "-q", "--depth=1", remote.as_uri(), str(workspace / "repos" / "app")],
        check=True,
    )
    git_binary = shutil.which("git")
    assert git_binary is not None
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    wrapper = bin_dir / "git"
    wrapper.write_text(
        '#!/bin/sh\ncase "$*" in *--deepen=*) exit 8;; esac\n'
        f'exec {shlex.quote(git_binary)} "$@"\n',
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")

    prepared = prepare_worktree(
        workspace,
        record,
        "scan-window",
        mode="read",
        history_since=datetime.now(UTC) - timedelta(days=7),
    )

    assert prepared.remote_revision == latest
    assert prepared.history_covered is False and prepared.history_issue == "deepen_failed"
    assert (Path(prepared.path) / "file.txt").read_text(encoding="utf-8") == "latest\n"


def test_concurrent_tasks_get_independent_worktrees(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
) -> None:
    workspace, _source, _remote, record = repositories

    def prepare(task: str) -> PreparedWorktree:
        return prepare_worktree(workspace, record, task, mode="read")

    with ThreadPoolExecutor(max_workers=2) as pool:
        prepared = list(pool.map(prepare, ("first", "second")))
    assert prepared[0].path != prepared[1].path
    assert prepared[0].revision == prepared[1].revision
    assert all(Path(item.path).is_dir() for item in prepared)


def test_cleanup_removes_only_unchanged_read_worktrees(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
) -> None:
    workspace, _source, _remote, record = repositories
    clean = prepare_worktree(workspace, record, "scan-clean", mode="read")
    changed = prepare_worktree(workspace, record, "scan-changed", mode="read")
    (Path(changed.path) / "new-file.txt").write_text("preserve", encoding="utf-8")

    assert remove_read_worktree(workspace, record, "scan-clean", clean)
    assert not Path(clean.path).exists()
    assert not remove_read_worktree(workspace, record, "scan-changed", changed)
    assert (Path(changed.path) / "new-file.txt").read_text(encoding="utf-8") == "preserve"


def test_cleanup_keeps_ignored_files_in_the_read_worktree(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
) -> None:
    workspace, source, _remote, record = repositories
    (source / ".gitignore").write_text("scratch.tmp\n", encoding="utf-8")
    git(source, "add", ".gitignore")
    git(source, "commit", "-qm", "ignore temporary file")
    git(source, "push", "-q", "origin", "main")
    snapshot = prepare_worktree(workspace, record, "scan-ignored", mode="read")
    (Path(snapshot.path) / "scratch.tmp").write_text("keep", encoding="utf-8")

    assert not remove_read_worktree(workspace, record, "scan-ignored", snapshot)
    assert (Path(snapshot.path) / "scratch.tmp").read_text(encoding="utf-8") == "keep"


def test_existing_task_branch_is_never_replaced(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
) -> None:
    workspace, _source, _remote, record = repositories
    checkout = workspace / record.path
    git(checkout, "branch", "lumon/delivery-MBPAS-2")
    previous = git(checkout, "rev-parse", "lumon/delivery-MBPAS-2")

    with pytest.raises(PreflightError, match="branch already exists"):
        prepare_worktree(workspace, record, "MBPAS-2", mode="delivery")
    assert git(checkout, "rev-parse", "lumon/delivery-MBPAS-2") == previous


def test_existing_unrelated_directory_and_unsafe_task_are_never_changed(
    repositories: tuple[Path, Path, Path, RepositoryRecord],
) -> None:
    workspace, _source, _remote, record = repositories
    target = workspace / "lumon" / "worktrees" / "existing" / "app"
    target.mkdir(parents=True)
    (target / "keep").write_text("user data", encoding="utf-8")

    with pytest.raises(PreflightError):
        prepare_worktree(workspace, record, "existing", mode="delivery")
    with pytest.raises(PreflightError):
        prepare_worktree(workspace, record, "../outside", mode="read")
    assert (target / "keep").read_text(encoding="utf-8") == "user data"
