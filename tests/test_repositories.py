"""Contract tests for Repository-aware Workspace initialization."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from lumon.cli.app import app
from lumon.cli.commands import init as init_command
from lumon.errors import InvalidInputError, PreflightError, RepositoryError
from lumon.workspace.config import load_workspace_config
from lumon.workspace.doctor import Doctor
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import InitRequest
from lumon.workspace.repositories import spec_from_url

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="Git is required")


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _create_remote(root: Path, name: str, branch: str, also_main: bool = False) -> str:
    root.mkdir(parents=True)
    source = root / f"{name}-source"
    bare = root / f"{name}.git"
    _git("init", "--quiet", f"--initial-branch={branch}", str(source))
    (source / "README.md").write_text(f"{name}\n", encoding="utf-8")
    _git("-C", str(source), "add", "README.md")
    _git(
        "-C",
        str(source),
        "-c",
        "user.name=Lumon Test",
        "-c",
        "user.email=lumon-test@example.com",
        "commit",
        "--quiet",
        "-m",
        "initial",
    )
    if also_main and branch != "main":
        _git("-C", str(source), "branch", "main")
    _git("clone", "--quiet", "--bare", str(source), str(bare))
    _git("-C", str(bare), "symbolic-ref", "HEAD", f"refs/heads/{branch}")
    return bare.as_uri()


def test_init_clones_main_and_persists_repository_metadata(
    initializer: WorkspaceInitializer, tmp_path: Path
) -> None:
    remote = _create_remote(tmp_path / "remote", "product", "main")
    target = tmp_path / "workspace"

    result = initializer.initialize(InitRequest(target, repositories=(spec_from_url(remote),)))

    assert result.status == "initialized"
    assert len(result.repositories) == 1
    repository = result.repositories[0]
    assert repository.name == "product"
    assert repository.status == "cloned"
    assert repository.branch == "main"
    checkout = target / "repos" / "product"
    assert repository.path == checkout
    assert (checkout / "README.md").is_file()

    config = load_workspace_config(target / "lumon" / "workspace.toml")
    assert len(config.repositories) == 1
    record = config.repositories[0]
    assert record.name == "product"
    assert record.url == remote
    assert record.path == "repos/product"
    assert record.branch == "main"
    assert len(record.revision) == 40


def test_init_falls_back_to_remote_default_branch(
    initializer: WorkspaceInitializer, tmp_path: Path
) -> None:
    remote = _create_remote(tmp_path / "remote", "legacy", "master")
    target = tmp_path / "workspace"

    result = initializer.initialize(InitRequest(target, repositories=(spec_from_url(remote),)))

    assert result.repositories[0].branch == "master"
    record = load_workspace_config(target / "lumon" / "workspace.toml").repositories[0]
    assert record.branch == "master"


def test_init_prefers_main_when_remote_default_is_another_branch(
    initializer: WorkspaceInitializer, tmp_path: Path
) -> None:
    remote = _create_remote(tmp_path / "remote", "product", "master", also_main=True)
    target = tmp_path / "workspace"

    result = initializer.initialize(InitRequest(target, repositories=(spec_from_url(remote),)))

    assert result.repositories[0].branch == "main"
    record = load_workspace_config(target / "lumon" / "workspace.toml").repositories[0]
    assert record.branch == "main"


def test_existing_matching_repository_is_reused_without_touching_worktree(
    initializer: WorkspaceInitializer, tmp_path: Path
) -> None:
    remote = _create_remote(tmp_path / "remote", "product", "main")
    target = tmp_path / "workspace"
    specification = spec_from_url(remote)
    initializer.initialize(InitRequest(target, repositories=(specification,)))
    sentinel = target / "repos" / "product" / "local-notes.txt"
    sentinel.write_text("keep me\n", encoding="utf-8")

    result = initializer.initialize(InitRequest(target, repositories=(specification,)))

    assert result.status == "already_initialized"
    assert result.repositories[0].status == "reused"
    assert sentinel.read_text(encoding="utf-8") == "keep me\n"


def test_existing_workspace_can_add_a_new_repository(
    initializer: WorkspaceInitializer, tmp_path: Path
) -> None:
    product = _create_remote(tmp_path / "product", "product", "main")
    backend = _create_remote(tmp_path / "backend", "backend", "main")
    target = tmp_path / "workspace"
    initializer.initialize(InitRequest(target, repositories=(spec_from_url(product),)))

    result = initializer.initialize(InitRequest(target, repositories=(spec_from_url(backend),)))

    assert result.status == "updated"
    assert result.repositories[0].status == "cloned"
    assert [
        record.name
        for record in load_workspace_config(target / "lumon" / "workspace.toml").repositories
    ] == ["product", "backend"]


def test_doctor_reports_registered_repository(
    initializer: WorkspaceInitializer, tmp_path: Path
) -> None:
    remote = _create_remote(tmp_path / "remote", "product", "main")
    target = tmp_path / "workspace"
    initializer.initialize(InitRequest(target, repositories=(spec_from_url(remote),)))

    report = Doctor(tmp_path / "skills").inspect(target)

    repository_check = next(check for check in report.checks if check.name == "repository:product")
    assert repository_check.ok
    assert "branch main" in repository_check.detail


def test_mismatched_registered_repository_is_rejected(
    initializer: WorkspaceInitializer, tmp_path: Path
) -> None:
    first = _create_remote(tmp_path / "first", "product", "main")
    second = _create_remote(tmp_path / "second", "product", "main")
    target = tmp_path / "workspace"
    initializer.initialize(InitRequest(target, repositories=(spec_from_url(first),)))

    with pytest.raises(PreflightError, match="another URL"):
        initializer.initialize(InitRequest(target, repositories=(spec_from_url(second),)))

    assert load_workspace_config(target / "lumon" / "workspace.toml").repositories[0].url == first


def test_existing_non_git_repository_directory_is_rejected(
    initializer: WorkspaceInitializer, tmp_path: Path
) -> None:
    remote = _create_remote(tmp_path / "remote", "loose", "main")
    target = tmp_path / "workspace"
    initializer.initialize(InitRequest(target))
    destination = target / "repos" / "loose"
    destination.mkdir(parents=True)
    marker = destination / "keep.txt"
    marker.write_text("user data\n", encoding="utf-8")

    with pytest.raises(PreflightError, match="not a Git Repository"):
        initializer.initialize(InitRequest(target, repositories=(spec_from_url(remote),)))

    assert marker.read_text(encoding="utf-8") == "user data\n"


def test_dry_run_with_repository_does_not_clone_or_write(
    initializer: WorkspaceInitializer, skills_root: Path, tmp_path: Path
) -> None:
    target = tmp_path / "workspace"
    remote = "git@github.com:example/product.git"

    result = initializer.initialize(
        InitRequest(target, repositories=(spec_from_url(remote),), dry_run=True)
    )

    assert result.status == "dry_run"
    assert result.repositories[0].status == "will_clone"
    assert result.repositories[0].path == target / "repos" / "product"
    assert not target.exists()
    assert not skills_root.exists()


def test_clone_failure_rolls_back_workspace_and_staged_skills(
    initializer: WorkspaceInitializer, skills_root: Path, tmp_path: Path
) -> None:
    target = tmp_path / "workspace"
    invalid_remote = (tmp_path / "missing.git").as_uri()

    with pytest.raises(RepositoryError):
        initializer.initialize(InitRequest(target, repositories=(spec_from_url(invalid_remote),)))

    assert not target.exists()
    assert not skills_root.exists()


def test_noninteractive_init_without_repository_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(init_command, "_interactive_terminal", lambda: False)

    assert init_command.collect_repository_specifications(None, json_output=False) == ()


def test_explicit_repository_options_are_all_resolved_without_prompt() -> None:
    urls = [
        "git@github.com:example/product.git",
        "git@github.com:example/backend.git",
    ]

    specifications = init_command.collect_repository_specifications(urls, json_output=False)

    assert [specification.name for specification in specifications] == ["product", "backend"]


def test_cli_accepts_repeated_repository_options_in_json_dry_run(tmp_path: Path) -> None:
    runner = CliRunner()
    target = tmp_path / "workspace"

    result = runner.invoke(
        app,
        [
            "init",
            str(target),
            "--dry-run",
            "--json",
            "--repository",
            "git@github.com:example/product.git",
            "--repository",
            "git@github.com:example/backend.git",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert [repository["name"] for repository in payload["repositories"]] == [
        "product",
        "backend",
    ]
    assert not target.exists()


def test_repository_url_cannot_contain_embedded_credentials() -> None:
    with pytest.raises(InvalidInputError, match="embedded credentials"):
        spec_from_url("https://user:password@example.com/product.git")


def test_interactive_repository_collection_stops_on_empty_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(["git@github.com:example/product.git", ""])
    confirmations = iter([True, True])

    def prompt(*_args: object, **_kwargs: object) -> str:
        return next(responses)

    def confirm(*_args: object, **_kwargs: object) -> bool:
        return next(confirmations)

    monkeypatch.setattr(init_command, "_interactive_terminal", lambda: True)
    monkeypatch.setattr(init_command.typer, "prompt", prompt)
    monkeypatch.setattr(init_command.typer, "confirm", confirm)

    specifications = init_command.collect_repository_specifications(None, json_output=False)

    assert specifications == (spec_from_url("git@github.com:example/product.git"),)
