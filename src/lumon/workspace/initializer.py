"""Transactional initialization of a v1 Workspace."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from datetime import datetime
from importlib.resources import files
from pathlib import Path

from lumon.errors import InitializationError, InvalidInputError, PreflightError
from lumon.skills.installer import SkillInstaller, SkillInstallResult
from lumon.version import __version__
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import WorkspaceManifest, load_manifest
from lumon.workspace.model import InitRequest, InitResult


class WorkspaceInitializer:
    """Create a complete Workspace while keeping global Skill writes reversible."""

    def __init__(
        self,
        skill_installer: SkillInstaller | None = None,
        now: Callable[[], datetime] | None = None,
        lumon_version: str = __version__,
    ) -> None:
        self.skill_installer = skill_installer or SkillInstaller()
        self.now = now
        self.lumon_version = lumon_version

    def initialize(self, request: InitRequest) -> InitResult:
        """Validate, stage, install missing Skills, and commit one Workspace."""

        target = request.target.expanduser().resolve()
        layout = WorkspaceLayout.from_root(target)
        state = self._inspect_target(layout)

        if state == "managed":
            skill_result = self._install_skills(request.dry_run)
            return self._result_for_existing(layout, request.dry_run, skill_result)

        name = _workspace_name(request.name, target)
        previews = self.skill_installer.preview()
        planned_paths = layout.generated_paths

        if request.dry_run:
            return InitResult(
                status="dry_run",
                workspace=target,
                planned_paths=planned_paths,
                planned_skills=tuple(
                    item.name for item in previews if item.action == "will_install"
                ),
                skipped_skills=tuple(
                    item.name for item in previews if item.action == "skipped_existing"
                ),
            )

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.lumon-init-", dir=target.parent))
        except OSError as exc:
            raise PreflightError(
                f"Unable to create Workspace staging area: {target.parent}"
            ) from exc
        skill_result: SkillInstallResult | None = None
        committed_paths: list[Path] = []
        target_created = False
        try:
            self._write_workspace(stage, name)
            skill_result = self._install_skills(False)
            committed_paths, target_created = self._commit_stage(stage, target)
            return InitResult(
                status="initialized",
                workspace=target,
                created_paths=tuple(committed_paths),
                installed_skills=skill_result.installed,
                skipped_skills=skill_result.skipped_existing,
            )
        except Exception as exc:
            if skill_result is not None:
                skill_result.rollback()
            self._rollback_workspace(target, committed_paths, target_created)
            if isinstance(exc, (InitializationError, InvalidInputError, PreflightError)):
                raise
            raise InitializationError(f"Unable to initialize Workspace: {target}") from exc
        finally:
            if stage.exists():
                shutil.rmtree(stage)

    def _inspect_target(self, layout: WorkspaceLayout) -> str:
        if layout.root.exists() and not layout.root.is_dir():
            raise PreflightError(f"Workspace target is not a directory: {layout.root}")
        if layout.root == Path(layout.root.anchor or "/"):
            raise InvalidInputError("Refusing to initialize the filesystem root")
        if not layout.root.exists():
            existing_parent = _nearest_existing_parent(layout.root.parent)
            if not _is_writable_directory(existing_parent):
                raise PreflightError(f"Workspace parent is not writable: {layout.root.parent}")
            return "missing"
        if layout.manifest.exists():
            load_manifest(layout.manifest)
            return "managed"
        if any(layout.root.iterdir()):
            raise PreflightError(
                f"Workspace target is non-empty and not managed by Lumon: {layout.root}"
            )
        if not _is_writable_directory(layout.root):
            raise PreflightError(f"Workspace target is not writable: {layout.root}")
        return "empty"

    def _install_skills(self, dry_run: bool) -> SkillInstallResult:
        if dry_run:
            return SkillInstallResult((), (), ())
        return self.skill_installer.install()

    def _result_for_existing(
        self,
        layout: WorkspaceLayout,
        dry_run: bool,
        skill_result: SkillInstallResult,
    ) -> InitResult:
        if dry_run:
            previews = self.skill_installer.preview()
            return InitResult(
                status="dry_run",
                workspace=layout.root,
                skipped_skills=tuple(
                    item.name for item in previews if item.action == "skipped_existing"
                ),
                planned_skills=tuple(
                    item.name for item in previews if item.action == "will_install"
                ),
            )
        return InitResult(
            status="already_initialized",
            workspace=layout.root,
            installed_skills=skill_result.installed,
            skipped_skills=skill_result.skipped_existing,
        )

    def _write_workspace(self, root: Path, name: str) -> None:
        layout = WorkspaceLayout.from_root(root)
        layout.control_dir.mkdir(parents=True, exist_ok=True)
        for directory in layout.runtime_directories:
            directory.mkdir(parents=True, exist_ok=True)

        layout.readme.write_text(
            f"# {name}\n\nThis Workspace was initialized by Lumon.\n",
            encoding="utf-8",
        )
        layout.agents_instructions.write_text(_read_agents_template(), encoding="utf-8")
        layout.gitignore.write_text(
            "lumon/runs/\nlumon/artifacts/\nlumon/logs/\nlumon/tmp/\n",
            encoding="utf-8",
        )
        layout.workspace_config.write_text(
            f"schema_version = 1\nname = {_toml_string(name)}\n",
            encoding="utf-8",
        )
        manifest = WorkspaceManifest.create(
            name, self.lumon_version, self.now() if self.now else None
        )
        manifest.write(layout.manifest)

    def _commit_stage(self, stage: Path, target: Path) -> tuple[list[Path], bool]:
        target_created = False
        committed: list[Path] = []
        try:
            if not target.exists():
                target.mkdir()
                target_created = True
            elif any(target.iterdir()):
                raise PreflightError(f"Workspace target changed during initialization: {target}")

            for child in sorted(stage.iterdir(), key=lambda path: path.name):
                destination = target / child.name
                if destination.exists():
                    raise PreflightError(
                        f"Workspace target changed during initialization: {destination}"
                    )
                child.replace(destination)
                committed.append(destination)
            stage.rmdir()
        except Exception:
            self._rollback_workspace(target, committed, target_created)
            raise
        return committed, target_created

    def _rollback_workspace(
        self, target: Path, committed: list[Path], target_created: bool
    ) -> None:
        for path in reversed(committed):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        if target_created and target.exists() and not any(target.iterdir()):
            target.rmdir()


def _workspace_name(requested: str | None, target: Path) -> str:
    name = (requested or target.name).strip()
    if not name:
        raise InvalidInputError("Workspace name must not be empty")
    if any(character in name for character in "\r\n\0"):
        raise InvalidInputError("Workspace name must not contain control characters")
    return name


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _read_agents_template() -> str:
    """Read the packaged Workspace instructions template."""

    try:
        return files("lumon.workspace.templates").joinpath("AGENTS.md").read_text(encoding="utf-8")
    except (ModuleNotFoundError, OSError) as exc:
        raise InitializationError(
            "The bundled Workspace AGENTS.md template is unavailable."
        ) from exc


def _is_writable_directory(path: Path) -> bool:
    return path.is_dir() and bool(path.stat().st_mode & 0o200)


def _nearest_existing_parent(path: Path) -> Path:
    current = path
    while not current.exists() and current != current.parent:
        current = current.parent
    return current
