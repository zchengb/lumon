"""Repository target changes preserve Workspace state and do not operate on checkouts."""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from lumon.dashboard.routes import create_app
from lumon.dashboard.service import DashboardService
from lumon.errors import PreflightError
from lumon.skills.installer import SkillInstaller
from lumon.tools import github_mcp_proxy
from lumon.tools.github_mcp_proxy import github_server_name
from lumon.tools.github_repositories import GithubRepository
from lumon.workspace.config import WorkspaceConfig, load_workspace_config
from lumon.workspace.initializer import WorkspaceInitializer
from lumon.workspace.model import RepositoryRecord
from lumon.workspace.registry import WorkspaceRegistry
from lumon.workspace.repositories import RepositoryProvisioner
from lumon.workspace.settings import WorkspaceSettingsStore


@pytest.fixture
def branch_workspace(tmp_path: Path) -> Iterator[tuple[httpx.Client, str, Path, list[str]]]:
    root = tmp_path / "workspace"
    registry = WorkspaceRegistry(tmp_path / "state")
    settings = WorkspaceSettingsStore(tmp_path / "state")
    branches = ["main", "release/next"]

    class BranchProvisioner(RepositoryProvisioner):
        def list_branches(self, workspace: Path, record: RepositoryRecord) -> tuple[str, ...]:
            assert workspace == root
            assert record.name == "app"
            return tuple(branches)

    service = DashboardService(
        registry=registry,
        settings_store=settings,
        initializer=WorkspaceInitializer(
            registry=registry,
            settings_store=settings,
            skill_installer=SkillInstaller(tmp_path / "skills"),
        ),
        repository_provisioner=BranchProvisioner(),
    )
    _, registration = service.initialize_workspace(
        root,
        None,
        (),
        (
            GithubRepository(
                "app",
                "org/app",
                "https://github.com/org/app.git",
                "main",
                github_server_name("github.com"),
                False,
                True,
            ),
        ),
    )
    with TestClient(create_app(service)) as client:
        yield client, f"/api/workspaces/{registration.workspace_id}", root, branches


def test_branch_update_preserves_other_settings_and_existing_work(
    branch_workspace: tuple[httpx.Client, str, Path, list[str]],
) -> None:
    client, base, root, _ = branch_workspace
    path = root / "lumon" / "workspace.toml"
    original = load_workspace_config(path)
    work = root / "lumon" / "worktrees" / "running-task" / "app" / "dirty.txt"
    work.parent.mkdir(parents=True)
    work.write_text("keep my work")
    version = client.get(f"{base}/overview").json()["repositories_version"]
    listed = client.get(f"{base}/repositories/app/branches")
    assert listed.status_code == 200
    assert listed.headers["Cache-Control"] == "no-store"
    assert listed.json() == ["main", "release/next"]
    assert path.read_bytes() == original.as_toml().encode()
    payload = {"expected_version": version, "branch": "release/next"}
    changed = client.put(f"{base}/repositories/app/branch", json=payload)
    assert changed.status_code == 200
    current = load_workspace_config(path)
    assert current.repositories[0].branch == "release/next"
    assert current.repositories[0].auto_scan is False
    assert current.repositories[0].auto_delivery is True
    assert current.repositories[0].url == original.repositories[0].url
    assert current.repositories[0].mcp_server == original.repositories[0].mcp_server
    assert work.read_text() == "keep my work"
    assert not (root / "repos" / "app").exists()
    assert client.put(f"{base}/repositories/app/branch", json=payload).status_code == 409
    next_version = changed.json()["repositories_version"]
    assert client.get(f"{base}/overview").json()["repositories_version"] == next_version
    scope = {
        "expected_version": next_version,
        "repositories": [{"name": "app", "auto_scan": True, "auto_delivery": False}],
    }
    assert client.put(f"{base}/repositories/scope", json=scope).status_code == 200
    assert load_workspace_config(path).repositories[0].branch == "release/next"


def test_selecting_the_saved_branch_is_a_noop(
    branch_workspace: tuple[httpx.Client, str, Path, list[str]],
) -> None:
    client, base, root, _ = branch_workspace
    path = root / "lumon" / "workspace.toml"
    before = path.read_bytes()
    version = client.get(f"{base}/overview").json()["repositories_version"]
    response = client.put(
        f"{base}/repositories/app/branch", json={"expected_version": version, "branch": "main"}
    )
    assert response.status_code == 200
    assert response.json() == {"repositories_version": version}
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "branch", ["", "   ", "bad..name", "-main", "new-branch", "a\nb", "x" * 257]
)
def test_invalid_or_missing_branch_does_not_change_config(
    branch_workspace: tuple[httpx.Client, str, Path, list[str]], branch: str
) -> None:
    client, base, root, _ = branch_workspace
    path = root / "lumon" / "workspace.toml"
    before = path.read_bytes()
    version = client.get(f"{base}/overview").json()["repositories_version"]
    response = client.put(
        f"{base}/repositories/app/branch", json={"expected_version": version, "branch": branch}
    )
    assert response.status_code in {400, 422}
    assert path.read_bytes() == before


def test_branch_access_is_scoped_and_updates_require_local_origin(
    branch_workspace: tuple[httpx.Client, str, Path, list[str]],
) -> None:
    client, base, root, branches = branch_workspace
    path = root / "lumon" / "workspace.toml"
    version = client.get(f"{base}/overview").json()["repositories_version"]
    before = path.read_bytes()
    payload = {"expected_version": version, "branch": "release/next"}
    assert client.get(f"{base}/repositories/unknown/branches").status_code == 422
    assert client.put(f"{base}/repositories/unknown/branch", json=payload).status_code == 422
    assert (
        client.put(
            f"{base}/repositories/app/branch",
            json=payload,
            headers={"Origin": "https://untrusted.example"},
        ).status_code
        == 403
    )
    branches.remove("release/next")
    assert client.put(f"{base}/repositories/app/branch", json=payload).status_code == 422
    assert path.read_bytes() == before
    path.write_bytes(before + b"# preserve user formatting\n")
    payload["expected_version"] = client.get(f"{base}/overview").json()["repositories_version"]
    assert client.put(f"{base}/repositories/app/branch", json=payload).status_code == 409
    assert path.read_bytes() == before + b"# preserve user formatting\n"


def test_remote_branch_reader_uses_workspace_credentials_without_git_mutations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = RepositoryRecord(
        "app",
        "https://team.ghe.com/org/app.git",
        "repos/app",
        "main",
        github_server_name("team.ghe.com"),
    )
    WorkspaceConfig("Example", (record,)).write(tmp_path / "lumon" / "workspace.toml")
    monkeypatch.setattr(
        github_mcp_proxy, "github_credential_helper", lambda: "!/known/gh auth git-credential"
    )
    calls: list[list[str]] = []

    def run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: int,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert not check and capture_output and text and timeout == 30
        assert env["GIT_TERMINAL_PROMPT"] == "0"
        assert env["GCM_INTERACTIVE"] == "never"
        assert "credential.https://team.ghe.com.helper" in env.values()
        assert "!/known/gh auth git-credential" in env.values()
        return subprocess.CompletedProcess(
            command, 0, f"{'a' * 40}\trefs/heads/release/next\n{'b' * 40}\trefs/heads/main\n", ""
        )

    assert RepositoryProvisioner(run).list_branches(tmp_path, record) == ("main", "release/next")
    assert calls == [["git", "ls-remote", "--heads", "--", record.url]]
    assert not (tmp_path / "repos").exists()


@pytest.mark.parametrize(
    "output",
    [
        "bad response",
        f"{'a' * 40}\trefs/tags/v1\n",
        f"{'a' * 40}\trefs/heads/bad..name\n",
        f"{'a' * 40}\trefs/heads/ padded\n",
    ],
)
def test_invalid_remote_data_is_not_an_empty_branch_list(tmp_path: Path, output: str) -> None:
    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, output, "")

    record = RepositoryRecord("app", "https://github.com/org/app.git", "repos/app", "main")
    with pytest.raises(PreflightError, match="invalid branch data"):
        RepositoryProvisioner(run).list_branches(tmp_path, record)


@pytest.mark.parametrize(
    "failure", [OSError("sensitive upstream detail"), subprocess.TimeoutExpired("git", 30)]
)
def test_branch_read_errors_are_redacted(tmp_path: Path, failure: Exception) -> None:
    def run(_command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise failure

    record = RepositoryRecord("app", "https://github.com/org/app.git", "repos/app", "main")
    with pytest.raises(PreflightError, match="Check Repository access") as error:
        RepositoryProvisioner(run).list_branches(tmp_path, record)
    assert "sensitive upstream detail" not in str(error.value)


def test_failed_git_command_is_not_reported_as_no_branches(tmp_path: Path) -> None:
    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 128, "", "sensitive authentication detail")

    record = RepositoryRecord("app", "https://github.com/org/app.git", "repos/app", "main")
    with pytest.raises(PreflightError, match="Check Repository access") as error:
        RepositoryProvisioner(run).list_branches(tmp_path, record)
    assert "sensitive authentication detail" not in str(error.value)
