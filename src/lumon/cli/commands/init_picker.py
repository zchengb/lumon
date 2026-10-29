"""Numbered GitHub repository selection for interactive initialization."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import typer

from lumon.tools.github_repositories import (
    GithubRepository,
    repository_branches,
    repository_organizations,
    repository_spec,
    search_repositories,
)
from lumon.workspace.model import RepositorySpec


def pick_repositories(hosts: tuple[str, ...]) -> tuple[RepositorySpec, ...]:
    """Use the same discovery and validation as Dashboard, without cloning."""
    host = (
        hosts[0]
        if len(hosts) == 1
        else _choose_name("GitHub host", lambda page: hosts if page == 1 else (), hosts[0])
    )
    organization = _choose_name(
        "Organization", lambda page: repository_organizations(host, page=page), ""
    )
    selected = _pick_repositories(host, organization)
    specifications: list[RepositorySpec] = []
    for repository in selected:
        typer.echo(repository.full_name)
        branch = _choose_name(
            "Target branch",
            lambda page, repository=repository: repository_branches(
                host, repository.full_name, page=page
            ),
            repository.branch,
        )
        configured = replace(
            repository,
            branch=branch,
            auto_scan=typer.confirm("Include in Auto Scan?", default=True),
            auto_delivery=typer.confirm("Include in Auto Delivery?", default=True),
        )
        specifications.append(repository_spec(configured))
    return tuple(specifications)


def _choose_name(label: str, load: Callable[[int], tuple[str, ...]], default: str) -> str:
    page = 1
    items = load(page)
    while True:
        typer.echo(f"{label} — 0: {default or 'All repositories'}")
        for index, name in enumerate(items, 1):
            typer.echo(f"  {index}. {name}")
        choice = typer.prompt("Number (n: next page, p: previous page)", default="0").strip()
        if choice == "0":
            return default
        if choice == "n" and len(items) == 100:
            page += 1
            items = load(page)
        elif choice == "p" and page > 1:
            page -= 1
            items = load(page)
        elif choice.isdecimal() and 1 <= int(choice) <= len(items):
            return items[int(choice) - 1]
        else:
            typer.echo("Select a displayed number or an available page.")


def _pick_repositories(host: str, organization: str) -> tuple[GithubRepository, ...]:
    selected: dict[str, GithubRepository] = {}
    page = 1
    items = search_repositories(host, page=page, organization=organization)
    while True:
        typer.echo(f"Repositories — page {page}; selected: {len(selected)}")
        for index, repository in enumerate(items, 1):
            marker = "x" if repository.clone_url in selected else " "
            typer.echo(f"  {index}. [{marker}] {repository.full_name}")
        choice = typer.prompt("Numbers separated by commas; n/p: page; d: done").strip()
        if choice == "d":
            if selected:
                return tuple(selected.values())
            typer.echo("Select at least one repository, or cancel with Ctrl+C.")
        elif choice == "n" and len(items) == 100:
            page += 1
            items = search_repositories(host, page=page, organization=organization)
        elif choice == "p" and page > 1:
            page -= 1
            items = search_repositories(host, page=page, organization=organization)
        else:
            _toggle_choices(choice, items, selected)


def _toggle_choices(
    choice: str, items: tuple[GithubRepository, ...], selected: dict[str, GithubRepository]
) -> None:
    numbers = [part.strip() for part in choice.split(",")]
    if not numbers or any(
        not number.isdecimal() or not 1 <= int(number) <= len(items) for number in numbers
    ):
        typer.echo("Select displayed numbers or an available page.")
        return
    for index in dict.fromkeys(int(number) - 1 for number in numbers):
        repository = items[index]
        if repository.clone_url in selected:
            del selected[repository.clone_url]
        else:
            selected[repository.clone_url] = repository
