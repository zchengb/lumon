"""Organization and branch selection before a Workspace exists."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from lumon.dashboard import routes
from lumon.dashboard.service import DashboardService
from lumon.errors import InvalidInputError, PreflightError
from lumon.tools import github_repositories as discovery
from lumon.tools.github_mcp_proxy import github_server_name


@pytest.fixture
def pages(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    monkeypatch.setattr(discovery, "authenticated_hosts", lambda: ("team.ghe.com",))
    endpoints: list[str] = []

    def api(host: str, endpoint: str) -> object:
        assert host == "team.ghe.com"
        endpoints.append(endpoint)
        return (
            [{"login": "team"}] if endpoint.startswith("/user/orgs") else [{"name": "release/v2"}]
        )

    monkeypatch.setattr(discovery, "_github_api", api)
    return endpoints


def test_org_and_branch_pages_are_read_only(pages: list[str]) -> None:
    assert discovery.repository_organizations("team.ghe.com", page=2) == ("team",)
    assert discovery.repository_branches("team.ghe.com", "team/app", page=3) == ("release/v2",)
    assert pages == [
        "/user/orgs?per_page=100&page=2",
        "/repos/team/app/branches?per_page=100&page=3",
    ]


@pytest.mark.parametrize("repository", ["../app", "org/..", "org/app?x=1", "org/app/extra"])
def test_branch_repository_path_is_validated(pages: list[str], repository: str) -> None:
    with pytest.raises(PreflightError):
        discovery.repository_branches("team.ghe.com", repository)
    assert pages == []


@pytest.mark.parametrize(
    "payload",
    [[{"name": ""}], [{"name": " main"}], [{"name": "bad..name"}], [{"name": 3}], {}, [None]],
)
def test_bad_branch_pages_fail_without_partial_results(
    monkeypatch: pytest.MonkeyPatch, pages: list[str], payload: object
) -> None:
    def api(host: str, endpoint: str) -> object:
        return payload

    monkeypatch.setattr(discovery, "_github_api", api)
    with pytest.raises(PreflightError):
        discovery.repository_branches("team.ghe.com", "org/app")


def test_org_filter_uses_the_account_host_and_validated_path(
    pages: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def api(host: str, endpoint: str) -> object:
        pages.append(endpoint)
        return [
            {
                "name": "app",
                "full_name": "team/app",
                "clone_url": f"https://{host}/team/app.git",
                "default_branch": "main",
            }
        ]

    monkeypatch.setattr(discovery, "_github_api", api)
    assert discovery.search_repositories("team.ghe.com", organization="team")[0].name == "app"
    assert pages == ["/orgs/team/repos?per_page=100&page=1&sort=full_name&direction=asc"]
    with pytest.raises(PreflightError):
        discovery.search_repositories("team.ghe.com", organization="../other")


@pytest.fixture
def client(tmp_path: Path) -> Iterator[httpx.Client]:
    with TestClient(routes.create_app(DashboardService(state_root=tmp_path))) as session:
        yield session


def test_new_routes_do_not_call_workspace_branch_route(
    client: httpx.Client, pages: list[str]
) -> None:
    orgs = client.post("/api/repository-sources/organizations", json={"host": "team.ghe.com"})
    branches = client.post(
        "/api/repository-sources/branches",
        json={"host": "team.ghe.com", "repository": "team/app", "page": 2},
    )
    assert orgs.json() == ["team"] and branches.json() == ["release/v2"]
    assert branches.status_code == 200
    assert (
        client.post(
            "/api/repository-sources/branches",
            json={"host": "team.ghe.com", "repository": "team/app", "page": True},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/repository-sources/organizations",
            json={"host": "team.ghe.com"},
            headers={"Origin": "https://attacker.example"},
        ).status_code
        == 403
    )
    assert len(pages) == 2


def test_shared_picked_repository_validation_rejects_invalid_binding() -> None:
    repository = discovery.GithubRepository(
        "app",
        "team/app",
        "https://team.ghe.com/team/app.git",
        "main",
        github_server_name("team.ghe.com"),
    )
    assert discovery.repository_spec(repository).mcp_server == repository.mcp_server
    for invalid in [
        replace(repository, branch=""),
        replace(repository, mcp_server="other"),
        replace(repository, clone_url="https://password@team.ghe.com/team/app.git"),
    ]:
        with pytest.raises(InvalidInputError):
            discovery.repository_spec(invalid)
