"""Transactional initialization of a Lumon Workspace."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from datetime import datetime
from importlib.resources import files
from pathlib import Path

from lumon.errors import InitializationError, InvalidInputError, PreflightError
from lumon.skills.installer import SkillInstaller, SkillInstallResult, SkillPreview
from lumon.version import __version__
from lumon.workspace.config import WorkspaceConfig, load_workspace_config
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import WorkspaceManifest, load_manifest
from lumon.workspace.model import InitRequest, InitResult, RepositoryRecord, RepositorySpec
from lumon.workspace.repositories import RepositoryPreparation, RepositoryProvisioner


class WorkspaceInitializer:
    """Create or extend a Workspace while keeping side effects reversible."""

    def __init__(
        self,
        skill_installer: SkillInstaller | None = None,
        repository_provisioner: RepositoryProvisioner | None = None,
        now: Callable[[], datetime] | None = None,
        lumon_version: str = __version__,
    ) -> None:
        self.skill_installer = skill_installer or SkillInstaller()
        self.repository_provisioner = repository_provisioner or RepositoryProvisioner()
        self.now = now
        self.lumon_version = lumon_version

    def initialize(self, request: InitRequest) -> InitResult:
        """Validate, stage, provision, and commit one Workspace operation."""

        target = request.target.expanduser().resolve()
        layout = WorkspaceLayout.from_root(target)
        state = self._inspect_target(layout)

        if state == "managed":
            config = load_workspace_config(layout.workspace_config)
            name = config.name
            existing_records = config.repositories
        else:
            name = _workspace_name(request.name, target)
            existing_records = ()

        self.repository_provisioner.validate_specs(request.repositories)
        previews = self.skill_installer.preview()

        if request.dry_run:
            preparations = self.repository_provisioner.prepare(
                target,
                request.repositories,
                existing_records,
                dry_run=True,
            )
            return self._dry_run_result(
                layout,
                preparations,
                previews,
                request.repositories,
                workspace_is_managed=state == "managed",
            )

        if state == "managed" and not request.repositories:
            skill_result = self.skill_installer.install()
            return self._result_for_existing(layout, skill_result)

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
        repositories_parent_created = False
        previous_config: bytes | None = None
        config_replaced = False
        try:
            if state != "managed":
                self._write_workspace(stage, name)

            preparations = self.repository_provisioner.prepare(
                target,
                request.repositories,
                existing_records,
                staging_root=stage,
            )
            merged_records = _merge_records(
                existing_records,
                tuple(
                    preparation.record
                    for preparation in preparations
                    if preparation.record is not None
                ),
            )
            WorkspaceConfig(name=name, repositories=merged_records).write(
                WorkspaceLayout.from_root(stage).workspace_config
            )

            skill_result = self.skill_installer.install()
            if state == "managed":
                previous_config = layout.workspace_config.read_bytes()
                committed_paths, repositories_parent_created = self._commit_staged_repositories(
                    stage, layout
                )
                staged_config = WorkspaceLayout.from_root(stage).workspace_config
                staged_config.replace(layout.workspace_config)
                config_replaced = True
            else:
                committed_paths, target_created = self._commit_stage(stage, target)

            self._verify_workspace(layout, name)
            existing_names = {record.name for record in existing_records}
            changed = (
                state != "managed"
                or any(preparation.result.status == "cloned" for preparation in preparations)
                or any(
                    preparation.result.name not in existing_names for preparation in preparations
                )
            )
            status = (
                "initialized"
                if state != "managed"
                else ("updated" if changed else "already_initialized")
            )
            return InitResult(
                status=status,
                workspace=target,
                created_paths=tuple(committed_paths),
                installed_skills=skill_result.installed,
                skipped_skills=skill_result.skipped_existing,
                repositories=tuple(preparation.result for preparation in preparations),
            )
        except Exception as exc:
            if skill_result is not None:
                skill_result.rollback()
            if config_replaced and previous_config is not None:
                layout.workspace_config.write_bytes(previous_config)
            if state == "managed":
                self._rollback_staged_repositories(
                    layout,
                    committed_paths,
                    repositories_parent_created,
                )
            else:
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

    def _result_for_existing(
        self, layout: WorkspaceLayout, skill_result: SkillInstallResult
    ) -> InitResult:
        return InitResult(
            status="already_initialized",
            workspace=layout.root,
            installed_skills=skill_result.installed,
            skipped_skills=skill_result.skipped_existing,
        )

    def _dry_run_result(
        self,
        layout: WorkspaceLayout,
        preparations: tuple[RepositoryPreparation, ...],
        previews: tuple[SkillPreview, ...],
        specifications: tuple[RepositorySpec, ...],
        workspace_is_managed: bool,
    ) -> InitResult:
        """Render a no-write plan for Workspace and Repository initialization."""

        planned_paths = [] if workspace_is_managed else list(layout.generated_paths)
        new_repositories = tuple(
            preparation for preparation in preparations if preparation.result.status == "will_clone"
        )
        if specifications and (not workspace_is_managed or new_repositories):
            planned_paths.append(layout.repositories_dir)
            planned_paths.extend(
                layout.repositories_dir / preparation.result.name
                for preparation in new_repositories
            )
        return InitResult(
            status="dry_run",
            workspace=layout.root,
            planned_paths=tuple(planned_paths),
            planned_skills=tuple(item.name for item in previews if item.action == "will_install"),
            skipped_skills=tuple(
                item.name for item in previews if item.action == "skipped_existing"
            ),
            repositories=tuple(preparation.result for preparation in preparations),
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
        WorkspaceConfig(name=name).write(layout.workspace_config)
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

    def _commit_staged_repositories(
        self, stage: Path, layout: WorkspaceLayout
    ) -> tuple[list[Path], bool]:
        """Move only newly cloned Repositories into an existing Workspace."""

        staged_repositories = WorkspaceLayout.from_root(stage).repositories_dir
        if not staged_repositories.exists():
            return [], False
        if layout.repositories_dir.is_symlink():
            raise PreflightError(
                f"Repository directory must not be a symlink: {layout.repositories_dir}"
            )

        parent_created = not layout.repositories_dir.exists()
        if layout.repositories_dir.exists() and not layout.repositories_dir.is_dir():
            raise PreflightError(f"Repository path is not a directory: {layout.repositories_dir}")
        layout.repositories_dir.mkdir(parents=True, exist_ok=True)
        committed: list[Path] = []
        try:
            for child in sorted(staged_repositories.iterdir(), key=lambda path: path.name):
                destination = layout.repositories_dir / child.name
                if destination.exists() or destination.is_symlink():
                    raise PreflightError(
                        "Workspace Repository destination changed during initialization: "
                        f"{destination}"
                    )
                child.replace(destination)
                committed.append(destination)
        except Exception:
            self._rollback_staged_repositories(layout, committed, parent_created)
            raise
        return committed, parent_created

    def _verify_workspace(self, layout: WorkspaceLayout, name: str) -> None:
        """Verify the committed manifest, config, and registered Repositories."""

        load_manifest(layout.manifest)
        config = load_workspace_config(layout.workspace_config)
        if config.name != name:
            raise InitializationError(
                f"Workspace name changed during initialization: {layout.root}"
            )
        for record in config.repositories:
            ok, detail = self.repository_provisioner.inspect(layout.root, record)
            if not ok:
                raise InitializationError(f"Repository verification failed: {detail}")

    def _rollback_workspace(
        self, target: Path, committed: list[Path], target_created: bool
    ) -> None:
        for path in reversed(committed):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            elif path.exists() or path.is_symlink():
                path.unlink()
        if target_created and target.exists() and not any(target.iterdir()):
            target.rmdir()

    def _rollback_staged_repositories(
        self,
        layout: WorkspaceLayout,
        committed: list[Path],
        parent_created: bool,
    ) -> None:
        """Remove only Repository directories moved by this initialization."""

        for path in reversed(committed):
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            elif path.exists() or path.is_symlink():
                path.unlink()
        if (
            parent_created
            and layout.repositories_dir.is_dir()
            and not any(layout.repositories_dir.iterdir())
        ):
            layout.repositories_dir.rmdir()


def _workspace_name(requested: str | None, target: Path) -> str:
    name = (requested or target.name).strip()
    if not name:
        raise InvalidInputError("Workspace name must not be empty")
    if any(character in name for character in "\r\n\0"):
        raise InvalidInputError("Workspace name must not contain control characters")
    return name


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


def _merge_records(
    existing: tuple[RepositoryRecord, ...],
    prepared: tuple[RepositoryRecord, ...],
) -> tuple[RepositoryRecord, ...]:
    """Preserve registered order while appending or replacing prepared records."""

    records = list(existing)
    positions = {record.name: index for index, record in enumerate(records)}
    for record in prepared:
        position = positions.get(record.name)
        if position is None:
            positions[record.name] = len(records)
            records.append(record)
        else:
            records[position] = record
    return tuple(records)
