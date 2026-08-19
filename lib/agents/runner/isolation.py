"""Disposable workspace layer and no-irreversible-delete publish guard."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from agents.runner.workspace_mounts import runner_root


_SECRET_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "id_rsa",
    "id_ed25519",
    "authorized_keys",
}
_SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")
_SECRET_DIRS = {".ssh", ".gnupg", ".aws", ".lumen", ".lumon"}
_INTERNAL_DIRS = {".git"}


class IsolationError(RuntimeError):
    """Raised when the host cannot establish the disposable workspace."""


@dataclass(frozen=True)
class PublishReceipt:
    status: str
    code: str = ""
    added_files: tuple[str, ...] = ()
    modified_files: tuple[str, ...] = ()
    renamed_files: tuple[tuple[str, str], ...] = ()
    deleted_files: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "code": self.code,
            "added_files": list(self.added_files),
            "modified_files": list(self.modified_files),
            "renamed_files": [list(item) for item in self.renamed_files],
            "deleted_files": list(self.deleted_files),
        }


def _is_secret_path(path: Path) -> bool:
    name = path.name.casefold()
    return name in _SECRET_FILE_NAMES or name.endswith(_SECRET_SUFFIXES) or any(
        part.casefold() in _SECRET_DIRS for part in path.parts
    )


def _relative_files(root: Path) -> Iterable[tuple[Path, Path]]:
    root = root.resolve()
    if not root.is_dir():
        return
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_dir():
            continue
        if path.is_symlink() or _is_secret_path(relative) or any(
            part.casefold() in _INTERNAL_DIRS for part in relative.parts
        ):
            continue
        yield relative, path


def snapshot_tree(root: Path) -> dict[str, str]:
    """Return a content manifest excluding secrets and symlinks."""
    manifest: dict[str, str] = {}
    for relative, path in _relative_files(root):
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
        manifest[str(relative)] = digest
    return manifest


def _safe_destination(root: Path, relative: str) -> Path:
    destination = (root / relative).resolve()
    try:
        destination.relative_to(root.resolve())
    except ValueError as exc:
        raise IsolationError(f"path escapes workspace: {relative}") from exc
    return destination


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.is_dir():
        raise IsolationError(f"file/directory type conflict at {destination}")
    shutil.copy2(source, destination)


def _copy_visible_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for relative, path in _relative_files(source):
        _copy_file(path, _safe_destination(destination, str(relative)))


def _git_clone(source: Path, destination: Path) -> bool:
    if not (source / ".git").exists():
        return False
    completed = subprocess.run(
        ["git", "clone", "--quiet", "--no-local", "--no-hardlinks", "--no-checkout", str(source), str(destination)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise IsolationError(f"cannot create disposable Git workspace: {(completed.stderr or '').strip()[:240]}")
    checkout = subprocess.run(
        ["git", "-C", str(destination), "checkout", "--quiet", "--force", "--detach", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if checkout.returncode != 0:
        raise IsolationError(f"cannot checkout disposable Git workspace: {(checkout.stderr or '').strip()[:240]}")
    # A disposable clone must never carry a remote that the child could push.
    subprocess.run(["git", "-C", str(destination), "remote", "remove", "origin"], capture_output=True, check=False)
    return True


def _prune_to_source(source: Path, destination: Path, source_manifest: dict[str, str]) -> None:
    # `git checkout` materializes every tracked file before the visible-tree
    # copy runs.  Walk the clone independently of `_relative_files`, because
    # that helper intentionally skips secrets and would otherwise leave a
    # tracked `.env`/key in the Agent layer.
    entries = sorted(
        (
            (path.relative_to(destination), path)
            for path in destination.rglob("*")
            if not any(part.casefold() in _INTERNAL_DIRS for part in path.relative_to(destination).parts)
        ),
        key=lambda item: len(item[0].parts),
        reverse=True,
    )
    manifest_names = set(source_manifest)
    for relative, path in entries:
        name = str(relative)
        if path.is_dir() and not path.is_symlink():
            has_visible_descendant = any(
                candidate == name or candidate.startswith(f"{name}/")
                for candidate in manifest_names
            )
            if _is_secret_path(relative) or not has_visible_descendant:
                try:
                    shutil.rmtree(path)
                except OSError as exc:
                    raise IsolationError(f"cannot prepare disposable workspace: {name}") from exc
            continue
        if _is_secret_path(relative) or name not in manifest_names:
            try:
                path.unlink()
            except OSError as exc:
                raise IsolationError(f"cannot prepare disposable workspace: {name}") from exc
    _copy_visible_tree(source, destination)


@dataclass
class DisposableWorkspace:
    canonical: Path
    path: Path
    before: dict[str, str]
    agent_id: str
    publish_receipt: PublishReceipt | None = None
    _closed: bool = field(default=False, init=False, repr=False)

    @classmethod
    def create(cls, canonical: Path, agent_id: str) -> "DisposableWorkspace":
        source = Path(canonical).expanduser().resolve()
        if not source.is_dir():
            raise IsolationError(f"workspace is not a directory: {source}")
        root = runner_root(agent_id).resolve()
        workspace_root = root / "workspaces"
        workspace_root.mkdir(parents=True, exist_ok=True)
        path = workspace_root / f"run-{uuid.uuid4().hex[:16]}"
        before = snapshot_tree(source)
        try:
            cloned = _git_clone(source, path)
            if cloned:
                _prune_to_source(source, path, before)
            else:
                path.mkdir(parents=True, exist_ok=False)
                _copy_visible_tree(source, path)
        except Exception:
            shutil.rmtree(path, ignore_errors=True)
            raise
        return cls(canonical=source, path=path, before=before, agent_id=agent_id)

    def stage_paths(self, paths: Iterable[Path]) -> list[Path]:
        """Copy explicitly granted external inputs into the disposable layer."""
        target_root = self.path / ".lumon" / "attachments"
        staged: list[Path] = []
        for index, raw in enumerate(paths):
            source = Path(raw).expanduser().resolve()
            if not source.exists() or _is_secret_path(source):
                continue
            target = target_root / f"input-{index + 1}-{source.name}"
            if source.is_file():
                _copy_file(source, target)
                staged.append(target)
            elif source.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                _copy_visible_tree(source, target)
                staged.append(target)
        return staged

    def publish(self) -> PublishReceipt:
        after = snapshot_tree(self.path)
        deleted = sorted(set(self.before) - set(after))
        added = sorted(set(after) - set(self.before))
        modified = sorted(path for path in set(after) & set(self.before) if after[path] != self.before[path])

        unmatched_deleted = set(deleted)
        unmatched_added = set(added)
        renames: list[tuple[str, str]] = []
        for old in sorted(unmatched_deleted):
            match = next((new for new in sorted(unmatched_added) if self.before[old] == after[new]), None)
            if match:
                renames.append((old, match))
                unmatched_deleted.remove(old)
                unmatched_added.remove(match)

        if unmatched_deleted:
            receipt = PublishReceipt(
                status="blocked",
                code="DELETE_REQUIRES_EXPLICIT_CAPABILITY",
                added_files=tuple(sorted(unmatched_added)),
                modified_files=tuple(modified),
                renamed_files=tuple(renames),
                deleted_files=tuple(sorted(unmatched_deleted)),
            )
            self.publish_receipt = receipt
            return receipt

        for relative in sorted(unmatched_added | set(modified) | {new for _, new in renames}):
            source = _safe_destination(self.path, relative)
            if not source.is_file():
                raise IsolationError(f"publish source is not a regular file: {relative}")
            _copy_file(source, _safe_destination(self.canonical, relative))
        for old, _new in renames:
            old_path = _safe_destination(self.canonical, old)
            if old_path.is_file() or old_path.is_symlink():
                old_path.unlink()

        receipt = PublishReceipt(
            status="succeeded",
            added_files=tuple(sorted(unmatched_added)),
            modified_files=tuple(modified),
            renamed_files=tuple(renames),
        )
        self.publish_receipt = receipt
        return receipt

    def close(self) -> None:
        if self._closed:
            return
        root = runner_root(self.agent_id).resolve()
        try:
            self.path.resolve().relative_to(root)
        except ValueError as exc:
            raise IsolationError("refusing to remove a workspace outside the runner root") from exc
        shutil.rmtree(self.path, ignore_errors=True)
        self._closed = True

    def __enter__(self) -> "DisposableWorkspace":
        return self

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self.close()


def protected_delete_probe() -> dict[str, Any]:
    """Pure probe used by readiness checks; it never touches a real workspace."""
    with tempfile_probe_workspace() as pair:
        before, disposable = pair
        (disposable / "protected.txt").unlink()
        receipt = DisposableWorkspace(
            canonical=before,
            path=disposable,
            before=snapshot_tree(before),
            agent_id="probe",
        ).publish()
        return {
            "status": receipt.status,
            "code": receipt.code,
            "canonical_deleted": not (before / "protected.txt").is_file(),
            "deleted_files": list(receipt.deleted_files),
        }


class tempfile_probe_workspace:
    def __enter__(self) -> tuple[Path, Path]:
        import tempfile

        self._tmp = tempfile.TemporaryDirectory(prefix="lumon-delete-probe-")
        root = Path(self._tmp.name)
        canonical = root / "canonical"
        disposable = root / "disposable"
        canonical.mkdir()
        disposable.mkdir()
        (canonical / "protected.txt").write_text("protected\n", encoding="utf-8")
        shutil.copy2(canonical / "protected.txt", disposable / "protected.txt")
        return canonical, disposable

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self._tmp.cleanup()
