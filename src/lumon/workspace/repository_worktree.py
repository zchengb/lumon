"""Fetch a configured branch and prepare an isolated, pinned Git worktree."""

from __future__ import annotations

import fcntl
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from uuid import uuid4

from lumon.errors import PreflightError
from lumon.tools.github_mcp_proxy import github_credential_helper, github_server_name
from lumon.workspace.config import load_workspace_config
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.model import RepositoryRecord
from lumon.workspace.repositories import validate_clone_url

WorktreeMode = Literal["read", "work", "delivery"]
HistoryIssue = Literal["deepen_failed", "deepen_limit"]
_SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_REVISION = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_HISTORY_DEEPEN_STEPS = (256, 1024)


@dataclass(frozen=True, slots=True)
class PreparedWorktree:
    """A worktree and the exact remote revision observed for this preparation."""

    repository: str
    branch: str
    remote_revision: str
    revision: str
    path: str
    fetched_at: str
    reused: bool
    dirty: bool
    contains_remote: bool
    shallow: bool = False
    history_covered: bool | None = None
    history_issue: HistoryIssue | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe preparation receipt without remote URLs."""

        return asdict(self)


def prepare_worktree(
    workspace: Path,
    repository: RepositoryRecord,
    task: str,
    *,
    mode: WorktreeMode,
    history_since: datetime | None = None,
) -> PreparedWorktree:
    """Fetch one registered branch and create or safely reuse its task worktree.

    The canonical checkout and any existing task worktree are never reset or pulled.
    """

    root = WorkspaceLayout.from_root(workspace).root
    _validate_names(repository, task, mode)
    if history_since is not None and history_since.utcoffset() is None:
        raise PreflightError("Repository history window must include a timezone.")
    source = root / repository.path
    if source.is_symlink() or (root / "repos").is_symlink():
        raise PreflightError(f"Repository '{repository.name}' is missing or unsafe.")
    destination = _worktree_path(root, repository.name, task, mode)
    _validate_destination(root, destination)
    lock_dir = root / "lumon" / "repository-locks"
    _validate_destination(root, lock_dir / repository.name)
    lock_dir.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(
            lock_dir / f"{repository.name}.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
        )
    except OSError as exc:
        raise PreflightError("Unable to lock Repository preparation safely.") from exc
    with os.fdopen(descriptor, "a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if not source.exists() and repository.mcp_server is not None:
            _clone_registered_repository(root, source, repository)
        if source.is_symlink() or not source.is_dir():
            raise PreflightError(f"Repository '{repository.name}' is missing or unsafe.")
        return _prepare_locked(source, destination, repository, task, mode, history_since)


def _clone_registered_repository(root: Path, source: Path, repository: RepositoryRecord) -> None:
    """Materialize only a remote registration; never replace an existing checkout."""

    validate_clone_url(repository.url)
    temporary_parent = root / "lumon" / "tmp"
    _validate_destination(root, temporary_parent / "repository")
    temporary_parent.mkdir(parents=True, exist_ok=True)
    source.parent.mkdir(parents=True, exist_ok=True)
    if source.parent.is_symlink() or source.is_symlink():
        raise PreflightError("Repository checkout path is unsafe.")
    temporary = Path(tempfile.mkdtemp(prefix="repository-", dir=temporary_parent))
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    try:
        try:
            result = subprocess.run(
                [
                    "git",
                    *_github_git_config(repository),
                    "clone",
                    "--no-checkout",
                    "--single-branch",
                    "--depth=1",
                    "--branch",
                    repository.branch,
                    "--",
                    repository.url,
                    str(temporary),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=300,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PreflightError("Unable to prepare the remote Repository.") from exc
        if result.returncode != 0:
            raise PreflightError("Unable to clone the configured Repository branch.")
        try:
            source.mkdir()
        except FileExistsError as exc:
            raise PreflightError(
                "Repository checkout appeared during preparation; preserved it."
            ) from exc
        try:
            (temporary / ".git").rename(source / ".git")
        except OSError:
            try:
                source.rmdir()
            except OSError:
                pass
            raise
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def registered_repository(workspace: Path, name: str) -> RepositoryRecord:
    """Resolve only a Repository registered in this Workspace."""

    config = load_workspace_config(WorkspaceLayout.from_root(workspace).workspace_config)
    repository = next((item for item in config.repositories if item.name == name), None)
    if repository is None:
        raise PreflightError(f"Repository '{name}' is not registered in this Workspace.")
    return repository


def remove_read_worktree(
    workspace: Path, repository: RepositoryRecord, task: str, prepared: PreparedWorktree
) -> bool:
    """Remove only an unchanged read worktree created by this preparation."""

    if not verify_read_worktree(workspace, repository, task, prepared):
        return False
    root = WorkspaceLayout.from_root(workspace).root
    source = root / repository.path
    destination = _worktree_path(root, repository.name, task, "read")
    _git(source, "worktree", "remove", "--", str(destination))
    return True


def verify_read_worktree(
    workspace: Path, repository: RepositoryRecord, task: str, prepared: PreparedWorktree
) -> bool:
    """Check the recorded read worktree still contains the fetched source unchanged."""

    root = WorkspaceLayout.from_root(workspace).root
    _validate_names(repository, task, "read")
    source = root / repository.path
    destination = _worktree_path(root, repository.name, task, "read")
    _validate_destination(root, destination)
    if prepared.path != str(destination) or prepared.repository != repository.name:
        return False
    if destination.is_symlink() or not destination.is_dir():
        return False
    source_git = _git(source, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout
    target_git = _git(destination, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout
    target_root = _git(destination, "rev-parse", "--show-toplevel").stdout.strip()
    current = _git(destination, "rev-parse", "--verify", "HEAD").stdout.strip()
    attached = _git(destination, "symbolic-ref", "--quiet", "HEAD", allowed=(0, 1)).returncode == 0
    status = _git(destination, "status", "--porcelain=v1", "--untracked-files=all", "--ignored")
    return not (
        Path(source_git.strip()).resolve() != Path(target_git.strip()).resolve()
        or Path(target_root).resolve() != destination.resolve()
        or current != prepared.revision
        or current != prepared.remote_revision
        or attached
        or status.stdout
    )


def _prepare_locked(
    source: Path,
    destination: Path,
    repository: RepositoryRecord,
    task: str,
    mode: WorktreeMode,
    history_since: datetime | None,
) -> PreparedWorktree:
    _verify_source(source, repository)
    reference = f"refs/lumon/prepared/{uuid4().hex}"
    try:
        revision = _fetch_revision(source, repository, reference)
        history_covered = None
        history_issue = None
        if history_since is not None:
            revision, history_covered, history_issue = _cover_history(
                source, repository, reference, revision, history_since
            )
        shallow = _git(source, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"
        fetched_at = datetime.now(UTC).isoformat()
        reused = destination.exists() or destination.is_symlink()
        if reused:
            _verify_existing(source, destination, repository, task, mode)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            _create_worktree(source, destination, repository, task, mode, revision)
        current = _git(destination, "rev-parse", "--verify", "HEAD").stdout.strip()
        status = _git(destination, "status", "--porcelain=v1", "--untracked-files=normal")
        dirty = bool(status.stdout)
        contains_remote = (
            _git(
                destination, "merge-base", "--is-ancestor", revision, current, allowed=(0, 1)
            ).returncode
            == 0
        )
        return PreparedWorktree(
            repository=repository.name,
            branch=repository.branch,
            remote_revision=revision,
            revision=current,
            path=str(destination),
            fetched_at=fetched_at,
            reused=reused,
            dirty=dirty,
            contains_remote=contains_remote,
            shallow=shallow,
            history_covered=history_covered,
            history_issue=history_issue,
        )
    finally:
        _git(source, "update-ref", "-d", reference, allowed=(0, 1, 128))


def _fetch_revision(
    source: Path, repository: RepositoryRecord, reference: str, *, deepen: int | None = None
) -> str:
    arguments = [
        "fetch",
        "--no-tags",
        "--no-write-fetch-head",
        "--no-recurse-submodules",
        "--refmap=",
    ]
    if deepen is not None:
        arguments.append(f"--deepen={deepen}")
    arguments.extend(("origin", f"+refs/heads/{repository.branch}:{reference}"))
    _git(source, *_github_git_config(repository), *arguments)
    revision = _git(source, "rev-parse", "--verify", reference).stdout.strip()
    if not _REVISION.fullmatch(revision):
        raise PreflightError(f"Repository '{repository.name}' returned an invalid revision.")
    return revision


def _github_git_config(repository: RepositoryRecord) -> tuple[str, ...]:
    host = urlsplit(repository.url).hostname
    try:
        if not host or repository.mcp_server != github_server_name(host):
            return ()
    except ValueError:
        return ()
    helper = github_credential_helper()
    if helper is None:
        raise PreflightError("GitHub CLI is required to fetch this Repository.")
    return ("-c", "credential.helper=", "-c", f"credential.helper={helper}")


def _cover_history(
    source: Path,
    repository: RepositoryRecord,
    reference: str,
    revision: str,
    since: datetime,
) -> tuple[str, bool, HistoryIssue | None]:
    for deepen in _HISTORY_DEEPEN_STEPS:
        if not _shallow_boundary_in_window(source, revision, since):
            return revision, True, None
        try:
            revision = _fetch_revision(source, repository, reference, deepen=deepen)
        except PreflightError:
            return revision, False, "deepen_failed"
    covered = not _shallow_boundary_in_window(source, revision, since)
    return revision, covered, None if covered else "deepen_limit"


def _shallow_boundary_in_window(source: Path, revision: str, since: datetime) -> bool:
    path_text = _git(source, "rev-parse", "--path-format=absolute", "--git-path", "shallow").stdout
    shallow_path = Path(path_text.strip())
    if not shallow_path.exists():
        return False
    try:
        boundary = set(shallow_path.read_text(encoding="ascii").splitlines())
    except (OSError, UnicodeDecodeError) as exc:
        raise PreflightError("Unable to verify the Repository's shallow history.") from exc
    if not boundary or any(not _REVISION.fullmatch(item) for item in boundary):
        raise PreflightError("Repository shallow history metadata is invalid.")
    recent = _git(source, "rev-list", f"--since={since.isoformat()}", revision).stdout.splitlines()
    return bool(boundary.intersection(recent))


def _verify_source(source: Path, repository: RepositoryRecord) -> None:
    top = _git(source, "rev-parse", "--show-toplevel").stdout.strip()
    if Path(top).resolve() != source.resolve():
        raise PreflightError(f"Repository '{repository.name}' is not the configured checkout.")
    origin = _git(source, "remote", "get-url", "origin").stdout.strip()
    if origin.rstrip("/").removesuffix(".git") != repository.url.rstrip("/").removesuffix(".git"):
        raise PreflightError(
            f"Repository '{repository.name}' origin does not match its registration."
        )
    _git(source, "check-ref-format", f"refs/heads/{repository.branch}")


def _create_worktree(
    source: Path,
    destination: Path,
    repository: RepositoryRecord,
    task: str,
    mode: WorktreeMode,
    revision: str,
) -> None:
    arguments = ["-c", "core.hooksPath=/dev/null", "worktree", "add"]
    if mode == "read":
        arguments.append("--detach")
    else:
        branch = _task_branch(repository, task, mode)
        _git(source, "check-ref-format", f"refs/heads/{branch}")
        existing = _git(
            source, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", allowed=(0, 1)
        )
        if existing.returncode == 0:
            raise PreflightError("The task branch already exists; existing work was preserved.")
        arguments.extend(("-b", branch))
    _git(source, *arguments, "--", str(destination), revision)


def _verify_existing(
    source: Path, destination: Path, repository: RepositoryRecord, task: str, mode: WorktreeMode
) -> None:
    if mode == "read" or destination.is_symlink() or not destination.is_dir():
        raise PreflightError("The task worktree already exists; existing files were preserved.")
    source_git = _git(source, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout
    target_git = _git(destination, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout
    target_root = _git(destination, "rev-parse", "--show-toplevel").stdout.strip()
    branch = _git(destination, "symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip()
    if (
        Path(source_git.strip()).resolve() != Path(target_git.strip()).resolve()
        or Path(target_root).resolve() != destination.resolve()
        or branch != _task_branch(repository, task, mode)
    ):
        raise PreflightError("The existing worktree does not match this task; it was preserved.")


def _task_branch(repository: RepositoryRecord, task: str, mode: WorktreeMode) -> str:
    if mode == "delivery":
        return f"lumon/delivery-{task}"
    return f"lumon/{task}/{repository.name}"


def _worktree_path(root: Path, name: str, task: str, mode: WorktreeMode) -> Path:
    worktrees = root / "lumon" / "worktrees"
    return worktrees / "_reads" / task / name if mode == "read" else worktrees / task / name


def _validate_names(repository: RepositoryRecord, task: str, mode: WorktreeMode) -> None:
    if not _SAFE_NAME.fullmatch(repository.name) or not _SAFE_NAME.fullmatch(task):
        raise PreflightError("Repository and task names must be safe directory names.")
    if mode not in {"read", "work", "delivery"}:
        raise PreflightError("Unknown Repository worktree mode.")
    if Path(repository.path) != Path("repos") / repository.name:
        raise PreflightError("Repository path does not match its registration.")


def _validate_destination(root: Path, destination: Path) -> None:
    if not destination.resolve().is_relative_to(root / "lumon"):
        raise PreflightError("Repository worktree path is outside the Workspace.")
    current = root
    for component in destination.relative_to(root).parts:
        current /= component
        if current.is_symlink():
            raise PreflightError("Repository worktree paths must not contain symlinks.")


def _git(
    directory: Path, *arguments: str, allowed: tuple[int, ...] = (0,)
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    try:
        result = subprocess.run(
            ["git", "-C", str(directory), *arguments],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PreflightError("Git could not complete the Repository preparation.") from exc
    if result.returncode not in allowed:
        raise PreflightError(
            f"Git could not complete Repository preparation "
            f"({arguments[0]}, exit {result.returncode})."
        )
    return result
