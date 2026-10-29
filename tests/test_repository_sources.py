"""HTTP contract for paginated repository discovery without a live account."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from lumon.dashboard import routes
from lumon.dashboard.service import DashboardService
from lumon.errors import PreflightError
from lumon.tools.github_mcp_proxy import github_server_name
from lumon.tools.github_repositories import GithubRepository


@pytest.fixture
def client(tmp_path: Path) -> Iterator[httpx.Client]:
    with TestClient(routes.create_app(DashboardService(state_root=tmp_path))) as client:
        yield client


@pytest.fixture
def search_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, int]]:
    calls: list[tuple[str, str, int]] = []

    def search(host: str, query: str = "", *, page: int = 1) -> tuple[GithubRepository, ...]:
        calls.append((host, query, page))
        return (
            GithubRepository(
                "app", "org/app", f"https://{host}/org/app.git", "main", github_server_name(host)
            ),
        )

    monkeypatch.setattr(routes, "search_repositories", search)
    return calls


@pytest.mark.parametrize(
    "options",
    [
        {},
        {"query": ""},
        {"query": " \t "},
        {"query": "app"},
        {"query": "", "page": 11},
        {"query": "org:example app", "page": 2},
    ],
)
def test_search_route_keeps_list_shape_and_passes_pagination(
    client: httpx.Client, search_calls: list[tuple[str, str, int]], options: dict[str, object]
) -> None:
    response = client.post(
        "/api/repository-sources/search", json={"host": "team.ghe.com", **options}
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "app",
            "full_name": "org/app",
            "clone_url": "https://team.ghe.com/org/app.git",
            "branch": "main",
            "mcp_server": github_server_name("team.ghe.com"),
            "auto_scan": True,
            "auto_delivery": True,
        }
    ]
    assert search_calls == [("team.ghe.com", options.get("query", ""), options.get("page", 1))]


@pytest.mark.parametrize("page", [0, -1, True, False, 1.0, 1.5, "1", "2&other=1", None, [], {}])
def test_page_must_be_a_positive_json_integer(
    client: httpx.Client, search_calls: list[tuple[str, str, int]], page: object
) -> None:
    response = client.post(
        "/api/repository-sources/search", json={"host": "github.com", "page": page}
    )
    assert response.status_code == 422
    assert search_calls == []


@pytest.mark.parametrize(
    "host",
    [
        "",
        "https://github.com",
        "user@github.com",
        "github.com:443",
        "github.com/path",
        "team.ghe.com.attacker.example",
        "github.com\n",
        "team.ghe.com?x=1",
        None,
    ],
)
def test_host_validation_runs_before_discovery(
    client: httpx.Client, search_calls: list[tuple[str, str, int]], host: object
) -> None:
    response = client.post("/api/repository-sources/search", json={"host": host})
    assert response.status_code == 422
    assert search_calls == []


@pytest.mark.parametrize("options", [{"query": "x" * 257}, {"query": None}, {"per_page": 200}])
def test_query_limit_and_unknown_fields_are_rejected(
    client: httpx.Client, search_calls: list[tuple[str, str, int]], options: dict[str, object]
) -> None:
    response = client.post("/api/repository-sources/search", json={"host": "github.com", **options})
    assert response.status_code == 422
    assert search_calls == []


def test_discovery_failure_uses_existing_error_contract(
    client: httpx.Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    def search(host: str, query: str = "", *, page: int = 1) -> tuple[GithubRepository, ...]:
        del host, query, page
        raise PreflightError(
            "GitHub search returned incomplete results. Narrow the search and retry."
        )

    monkeypatch.setattr(routes, "search_repositories", search)
    response = client.post(
        "/api/repository-sources/search", json={"host": "github.com", "query": "app"}
    )
    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "type": "PreflightError",
            "message": "GitHub search returned incomplete results. Narrow the search and retry.",
        }
    }


def test_search_route_rejects_foreign_origin(
    client: httpx.Client, search_calls: list[tuple[str, str, int]]
) -> None:
    response = client.post(
        "/api/repository-sources/search",
        json={"host": "github.com"},
        headers={"Origin": "https://attacker.example"},
    )
    assert response.status_code == 403
    assert search_calls == []
