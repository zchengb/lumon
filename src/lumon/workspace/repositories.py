"""Provision and verify code Repositories inside a Lumon Workspace."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from lumon.errors import InvalidInputError, PreflightError, RepositoryError
from lumon.workspace.model import RepositoryRecord, RepositoryResult, RepositorySpec

GitRunner = Callable[..., subprocess.CompletedProcess[str]]
_REMOTE_HEAD_PATTERN = re.compile(r"^ref: refs/heads/(?P<branch>[^\s]+)\s+HEAD$")


@dataclass(frozen=True, slots=True)
class RepositoryPreparation:
    """A Repository result plus the staged path ready for Workspace commit."""

    record: RepositoryRecord | None
    result: RepositoryResult
    staged_path: Path | None = None


class RepositoryProvisioner:
    """Prepare Repositories using one concrete, testable Git seam."""

    def __init__(self, runner: GitRunner | None = None) -> None:
        self._runner = runner or subprocess.run

    def prepare(
        self,
        workspace: Path,
        specifications: Sequence[RepositorySpec],
        existing: Sequence[RepositoryRecord],
        staging_root: Path | None = None,
        dry_run: bool = False,
    ) -> tuple[RepositoryPreparation, ...]:
        """Validate, clone or reuse Repositories without committing staged paths."""

        specs = tuple(specifications)
        self.validate_specs(specs)
        existing_by_name = {record.name: record for record in existing}
        preparations: list[RepositoryPreparation] = []

        for specification in specs:
            destination = workspace / "repos" / specification.name
            previous = existing_by_name.get(specification.name)
            if previous is not None and _normalize_url(previous.url) != _normalize_url(
                specification.clone_url
            ):
                raise PreflightError(
                    f"Repository '{specification.name}' is already registered with another URL."
                )

            if destination.is_symlink():
                raise PreflightError(f"Repository destination must not be a symlink: {destination}")
            if destination.exists():
                preparations.append(
                    self._reuse_existing(specification, destination, dry_run=dry_run)
                )
                continue

            if dry_run:
                preparations.append(
                    RepositoryPreparation(
                        record=None,
                        result=RepositoryResult(
                            specification.name,
                            destination,
                            "will_clone",
                        ),
                    )
                )
                continue

            if staging_root is None:
                raise RuntimeError("staging_root is required for a real Repository preparation")
            staged_path = staging_root / "repos" / specification.name
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            branch = self._preferred_branch(specification.clone_url)
            clone_args = ["clone"]
            if branch:
                clone_args.extend(("--branch", branch))
            clone_args.extend((specification.clone_url, str(staged_path)))
            self._run(clone_args)
            record = self._record_from_checkout(specification, staged_path, branch_hint=branch)
            preparations.append(
                RepositoryPreparation(
                    record=record,
                    result=RepositoryResult(
                        specification.name,
                        destination,
                        "cloned",
                        record.branch,
                        record.revision,
                    ),
                    staged_path=staged_path,
                )
            )

        return tuple(preparations)

    def validate_specs(self, specifications: Sequence[RepositorySpec]) -> None:
        """Validate Repository names, URLs, and duplicate names before writes."""

        names: set[str] = set()
        for specification in specifications:
            if not specification.name or specification.name in {".", ".."}:
                raise InvalidInputError("Repository name must not be empty or relative.")
            if (
                any(character in specification.name for character in "/\\\0")
                or specification.name.strip() != specification.name
            ):
                raise InvalidInputError(
                    f"Repository name is not a safe directory name: {specification.name}"
                )
            if specification.name in names:
                raise InvalidInputError(f"Duplicate Repository name: {specification.name}")
            names.add(specification.name)
            validate_clone_url(specification.clone_url)

    def inspect(self, workspace: Path, record: RepositoryRecord) -> tuple[bool, str]:
        """Verify one persisted Repository without changing its working tree."""

        path = workspace / record.path
        if path.is_symlink() or not path.is_dir():
            return False, f"missing Repository directory: {path}"
        try:
            actual_url = self._remote_url(path)
            revision = self._git_text(["-C", str(path), "rev-parse", "HEAD"])
            branch = self._current_branch(path)
        except RepositoryError as exc:
            return False, str(exc)
        if _normalize_url(actual_url) != _normalize_url(record.url):
            return False, f"origin does not match configured URL: {path}"
        return True, f"{path} (branch {branch}, revision {revision[:12]})"

    def _reuse_existing(
        self,
        specification: RepositorySpec,
        destination: Path,
        dry_run: bool,
    ) -> RepositoryPreparation:
        if not destination.is_dir():
            raise PreflightError(f"Repository destination is not a directory: {destination}")
        try:
            actual_url = self._remote_url(destination)
        except RepositoryError as exc:
            raise PreflightError(
                f"Existing Repository destination is not a Git Repository: {destination}"
            ) from exc
        if _normalize_url(actual_url) != _normalize_url(specification.clone_url):
            raise PreflightError(f"Repository origin does not match requested URL: {destination}")
        if dry_run:
            return RepositoryPreparation(
                record=None,
                result=RepositoryResult(specification.name, destination, "will_reuse"),
            )
        record = self._record_from_checkout(specification, destination)
        return RepositoryPreparation(
            record=record,
            result=RepositoryResult(
                specification.name,
                destination,
                "reused",
                record.branch,
                record.revision,
            ),
        )

    def _preferred_branch(self, clone_url: str) -> str | None:
        """Prefer ``main`` and otherwise resolve the remote's advertised HEAD."""

        default_output = self._run(["ls-remote", "--symref", clone_url, "HEAD"]).stdout
        default_branch = _parse_default_branch(default_output)
        if default_branch == "main":
            return "main"

        main_result = self._run(
            ["ls-remote", "--heads", clone_url, "refs/heads/main"],
            allow_failure=True,
        )
        if main_result.returncode == 0 and main_result.stdout.strip():
            return "main"
        return default_branch

    def _record_from_checkout(
        self,
        specification: RepositorySpec,
        checkout: Path,
        branch_hint: str | None = None,
    ) -> RepositoryRecord:
        actual_url = self._remote_url(checkout)
        branch = self._current_branch(checkout) or branch_hint or "detached"
        revision = self._git_text(["-C", str(checkout), "rev-parse", "HEAD"])
        return RepositoryRecord(
            name=specification.name,
            url=actual_url,
            path=str(Path("repos") / specification.name),
            branch=branch,
            revision=revision,
        )

    def _remote_url(self, checkout: Path) -> str:
        return self._git_text(["-C", str(checkout), "remote", "get-url", "origin"])

    def _current_branch(self, checkout: Path) -> str:
        result = self._run(
            ["-C", str(checkout), "symbolic-ref", "--quiet", "--short", "HEAD"],
            allow_failure=True,
        )
        if result.returncode != 0:
            return "detached"
        return result.stdout.strip() or "detached"

    def _git_text(self, arguments: Sequence[str]) -> str:
        result = self._run(arguments)
        value = result.stdout.strip()
        if not value:
            raise RepositoryError(f"Git returned no output for: git {' '.join(arguments)}")
        return value

    def _run(
        self,
        arguments: Sequence[str],
        *,
        allow_failure: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["GIT_TERMINAL_PROMPT"] = "0"
        try:
            result = self._runner(
                ["git", *arguments],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
        except OSError as exc:
            if isinstance(exc, FileNotFoundError):
                message = "Git is required to initialize a Repository."
            else:
                message = f"Unable to execute Git for Repository: {exc}"
            raise RepositoryError(message) from exc
        if not allow_failure and result.returncode != 0:
            detail = (result.stderr or result.stdout or "Git command failed").strip()
            raise RepositoryError(f"Git command failed: {detail}")
        return result


def spec_from_url(clone_url: str) -> RepositorySpec:
    """Validate a clone URL and derive its safe Workspace Repository name."""

    validate_clone_url(clone_url)
    normalized = clone_url.strip().split("?", 1)[0].split("#", 1)[0].rstrip("/")
    candidate = normalized.rsplit("/", 1)[-1]
    if ":" in candidate and "/" not in normalized:
        candidate = candidate.rsplit(":", 1)[-1]
    candidate = candidate.removesuffix(".git")
    if not candidate or candidate in {".", ".."}:
        raise InvalidInputError(f"Unable to derive a Repository name from URL: {clone_url}")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", candidate):
        raise InvalidInputError(f"Repository URL produces an unsafe name: {candidate}")
    return RepositorySpec(name=candidate, clone_url=clone_url.strip())


def validate_clone_url(clone_url: str) -> None:
    """Reject empty, malformed, or credential-bearing clone URLs."""

    value = clone_url.strip()
    if not value or value != clone_url or any(ord(character) < 32 for character in value):
        raise InvalidInputError("Repository clone URL must be a non-empty clean string.")
    if (
        value.startswith(("http://", "https://", "ssh://"))
        and "@" in value.split("://", 1)[1].split("/", 1)[0]
    ):
        raise InvalidInputError("Repository URL must not contain embedded credentials.")
    if not ("/" in value or ":" in value):
        raise InvalidInputError(f"Repository clone URL does not look valid: {clone_url}")


def _parse_default_branch(output: str) -> str | None:
    for line in output.splitlines():
        match = _REMOTE_HEAD_PATTERN.match(line.strip())
        if match:
            return match.group("branch")
    return None


def _normalize_url(value: str) -> str:
    return value.strip().rstrip("/").removesuffix(".git")
