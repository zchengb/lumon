"""Transactional initialization of a Lumon Workspace."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from importlib.resources import files
from pathlib import Path
from typing import Literal
from uuid import UUID

from lumon.errors import InitializationError, InvalidInputError, PreflightError
from lumon.skills.installer import SkillInstaller, SkillInstallResult, SkillPreview
from lumon.version import __version__
from lumon.workspace.config import WorkspaceConfig, load_workspace_config
from lumon.workspace.layout import WorkspaceLayout
from lumon.workspace.manifest import WorkspaceManifest, load_manifest
from lumon.workspace.model import InitRequest, InitResult, RepositoryRecord, RepositorySpec
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.repositories import RepositoryPreparation, RepositoryProvisioner
from lumon.workspace.settings import WorkspaceSettingsStore

_TargetState = Literal["missing", "empty", "managed"]
_PRESERVED_ERRORS = (InitializationError, InvalidInputError, PreflightError)


@dataclass(frozen=True, slots=True)
class _InitializationPlan:
    """Validated inputs and discovered state for one initialization operation."""

    target: Path
    layout: WorkspaceLayout
    state: _TargetState
    name: str
    existing_records: tuple[RepositoryRecord, ...]
    specifications: tuple[RepositorySpec, ...]
    previews: tuple[SkillPreview, ...]
    dry_run: bool

    @property
    def refresh_only(self) -> bool:
        """Return whether the operation only refreshes an existing Workspace."""

        return self.state == "managed" and not self.specifications


@dataclass(frozen=True, slots=True)
class _UserStateSnapshot:
    """User-level state captured before profile or registry writes."""

    workspace_id: UUID
    profile: bytes | None


@dataclass(slots=True)
class _CommitState:
    """Filesystem state required to undo a successful commit phase."""

    committed_paths: list[Path]
    target_created: bool = False
    repositories_parent_created: bool = False
    previous_config: bytes | None = None
    config_replaced: bool = False


@dataclass(slots=True)
class _InitializationState:
    """Mutable transaction state kept separate from the phase orchestration."""

    registry_snapshot: bytes | None
    stage: Path | None = None
    skill_result: SkillInstallResult | None = None
    user_state: _UserStateSnapshot | None = None
    commit_state: _CommitState | None = None


class WorkspaceInitializer:
    """Create or extend a Workspace while keeping side effects reversible."""

    def __init__(
        self,
        skill_installer: SkillInstaller | None = None,
        repository_provisioner: RepositoryProvisioner | None = None,
        registry: WorkspaceRegistry | None = None,
        settings_store: WorkspaceSettingsStore | None = None,
        now: Callable[[], datetime] | None = None,
        lumon_version: str = __version__,
    ) -> None:
        self.skill_installer = skill_installer or SkillInstaller()
        self.repository_provisioner = repository_provisioner or RepositoryProvisioner()
        self.registry = registry or WorkspaceRegistry()
        self.settings_store = settings_store or WorkspaceSettingsStore()
        self.now = now
        self.lumon_version = lumon_version

    def initialize(self, request: InitRequest) -> InitResult:
        """Validate, stage, provision, and commit one Workspace operation."""

        plan = self._build_plan(request)
        if plan.dry_run:
            return self._preview(plan)
        return self._execute(plan)

    def _build_plan(self, request: InitRequest) -> _InitializationPlan:
        target = request.target.expanduser().resolve()
        layout = WorkspaceLayout.from_root(target)
        state = self._inspect_target(layout)
        name, existing_records = self._workspace_details(request, layout, state, target)
        self.repository_provisioner.validate_specs(request.repositories)
        previews = self.skill_installer.preview()
        return _InitializationPlan(
            target=target,
            layout=layout,
            state=state,
            name=name,
            existing_records=existing_records,
            specifications=request.repositories,
            previews=previews,
            dry_run=request.dry_run,
        )

    def _workspace_details(
        self,
        request: InitRequest,
        layout: WorkspaceLayout,
        state: _TargetState,
        target: Path,
    ) -> tuple[str, tuple[RepositoryRecord, ...]]:
        if state == "managed":
            config = load_workspace_config(layout.workspace_config)
            return config.name, config.repositories
        return _workspace_name(request.name, target), ()

    def _preview(self, plan: _InitializationPlan) -> InitResult:
        preparations = self.repository_provisioner.prepare(
            plan.target,
            plan.specifications,
            plan.existing_records,
            dry_run=True,
        )
        return self._dry_run_result(
            plan.layout,
            preparations,
            plan.previews,
            plan.specifications,
            workspace_is_managed=plan.state == "managed",
        )

    def _execute(self, plan: _InitializationPlan) -> InitResult:
        state = _InitializationState(registry_snapshot=self.registry.raw_snapshot())
        try:
            if plan.refresh_only:
                return self._refresh_existing(plan, state)
            preparations = self._prepare_workspace(plan, state)
            state.skill_result = self.skill_installer.install()
            self._commit_workspace(plan, state)
            self._verify_workspace(plan.layout, plan.name)
            self._capture_user_state(plan, state)
            self._register_workspace(plan.layout)
            return self._initialization_result(plan, state, preparations)
        except Exception as exc:
            self._rollback(plan, state)
            if isinstance(exc, _PRESERVED_ERRORS):
                raise
            raise InitializationError(f"Unable to initialize Workspace: {plan.target}") from exc
        finally:
            self._cleanup_stage(state)

    def _refresh_existing(
        self, plan: _InitializationPlan, state: _InitializationState
    ) -> InitResult:
        """Refresh Skills and user registration for an existing Workspace."""

        state.skill_result = self.skill_installer.install()
        self._capture_user_state(plan, state)
        self._register_workspace(plan.layout)
        return self._result_for_existing(plan.layout, self._require_skill_result(state))

    def _prepare_workspace(
        self, plan: _InitializationPlan, state: _InitializationState
    ) -> tuple[RepositoryPreparation, ...]:
        """Build a staged Workspace and prepare its Repository metadata."""

        stage = self._create_stage(plan)
        state.stage = stage
        if plan.state != "managed":
            self._write_workspace(stage, plan.name)

        preparations = self.repository_provisioner.prepare(
            plan.target,
            plan.specifications,
            plan.existing_records,
            staging_root=stage,
        )
        merged_records = _merge_records(
            plan.existing_records,
            tuple(
                preparation.record for preparation in preparations if preparation.record is not None
            ),
        )
        WorkspaceConfig(name=plan.name, repositories=merged_records).write(
            WorkspaceLayout.from_root(stage).workspace_config
        )
        return preparations

    def _create_stage(self, plan: _InitializationPlan) -> Path:
        """Create the private staging directory after preflight succeeds."""

        try:
            plan.target.parent.mkdir(parents=True, exist_ok=True)
            return Path(
                tempfile.mkdtemp(
                    prefix=f".{plan.target.name}.lumon-init-",
                    dir=plan.target.parent,
                )
            )
        except OSError as exc:
            raise PreflightError(
                f"Unable to create Workspace staging area: {plan.target.parent}"
            ) from exc

    def _commit_workspace(self, plan: _InitializationPlan, state: _InitializationState) -> None:
        """Commit staged Workspace or Repository paths and record undo data."""

        stage = self._require_stage(state)
        if plan.state == "managed":
            previous_config = plan.layout.workspace_config.read_bytes()
            committed_paths, parent_created = self._commit_staged_repositories(stage, plan.layout)
            commit_state = _CommitState(
                committed_paths=committed_paths,
                repositories_parent_created=parent_created,
                previous_config=previous_config,
            )
            state.commit_state = commit_state
            staged_config = WorkspaceLayout.from_root(stage).workspace_config
            staged_config.replace(plan.layout.workspace_config)
            commit_state.config_replaced = True
            return

        committed_paths, target_created = self._commit_stage(stage, plan.target)
        state.commit_state = _CommitState(
            committed_paths=committed_paths,
            target_created=target_created,
        )

    def _capture_user_state(self, plan: _InitializationPlan, state: _InitializationState) -> None:
        """Capture profile bytes before the registration phase can mutate them."""

        workspace_id, profile = self._capture_user_profile(plan.layout)
        state.user_state = _UserStateSnapshot(workspace_id=workspace_id, profile=profile)

    def _initialization_result(
        self,
        plan: _InitializationPlan,
        state: _InitializationState,
        preparations: tuple[RepositoryPreparation, ...],
    ) -> InitResult:
        """Translate committed phase state into the existing public result."""

        skill_result = self._require_skill_result(state)
        commit_state = self._require_commit_state(state)
        existing_names = {record.name for record in plan.existing_records}
        changed = (
            plan.state != "managed"
            or any(preparation.result.status == "cloned" for preparation in preparations)
            or any(preparation.result.name not in existing_names for preparation in preparations)
        )
        status = (
            "initialized"
            if plan.state != "managed"
            else ("updated" if changed else "already_initialized")
        )
        return InitResult(
            status=status,
            workspace=plan.target,
            created_paths=tuple(commit_state.committed_paths),
            installed_skills=skill_result.installed,
            skipped_skills=skill_result.skipped_existing,
            repositories=tuple(preparation.result for preparation in preparations),
        )

    def _rollback(self, plan: _InitializationPlan, state: _InitializationState) -> None:
        """Compensate completed phases in their established order."""

        if state.skill_result is not None:
            state.skill_result.rollback()
        if state.user_state is not None:
            self._restore_user_state(
                state.user_state.workspace_id,
                state.user_state.profile,
                state.registry_snapshot,
            )
        self._rollback_commit(plan, state)

    def _rollback_commit(self, plan: _InitializationPlan, state: _InitializationState) -> None:
        """Undo committed Workspace or Repository paths and restored config."""

        commit_state = state.commit_state
        if commit_state is None:
            return
        if commit_state.config_replaced and commit_state.previous_config is not None:
            plan.layout.workspace_config.write_bytes(commit_state.previous_config)
        if plan.state == "managed":
            self._rollback_staged_repositories(
                plan.layout,
                commit_state.committed_paths,
                commit_state.repositories_parent_created,
            )
            return
        self._rollback_workspace(
            plan.target,
            commit_state.committed_paths,
            commit_state.target_created,
        )

    def _cleanup_stage(self, state: _InitializationState) -> None:
        """Remove the private staging directory after success or rollback."""

        if state.stage is not None and state.stage.exists():
            shutil.rmtree(state.stage)

    @staticmethod
    def _require_stage(state: _InitializationState) -> Path:
        if state.stage is None:
            raise InitializationError("Workspace initialization staging area is not ready.")
        return state.stage

    @staticmethod
    def _require_skill_result(state: _InitializationState) -> SkillInstallResult:
        if state.skill_result is None:
            raise InitializationError("Workspace Skills were not installed.")
        return state.skill_result

    @staticmethod
    def _require_commit_state(state: _InitializationState) -> _CommitState:
        if state.commit_state is None:
            raise InitializationError("Workspace commit state is not ready.")
        return state.commit_state

    def _capture_user_profile(self, layout: WorkspaceLayout) -> tuple[UUID, bytes | None]:
        """Capture the profile state before this initialization registers a Workspace."""

        manifest = load_manifest(layout.manifest)
        return manifest.workspace_id, self.settings_store.raw_snapshot(manifest.workspace_id)

    def _register_workspace(self, layout: WorkspaceLayout) -> None:
        """Ensure a profile exists and register the validated Workspace path."""

        manifest = load_manifest(layout.manifest)
        self.settings_store.ensure(manifest.workspace_id)
        self.registry.register(layout.root)

    def _restore_user_state(
        self,
        workspace_id: UUID,
        profile_snapshot: bytes | None,
        registry_snapshot: bytes | None,
    ) -> None:
        """Restore user-level state when Workspace initialization cannot commit."""

        self.settings_store.restore_raw(workspace_id, profile_snapshot)
        self.registry.restore_raw(registry_snapshot)

    def _inspect_target(self, layout: WorkspaceLayout) -> _TargetState:
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
        layout.flows_dir.mkdir(parents=True, exist_ok=True)
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
