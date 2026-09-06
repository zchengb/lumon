"""The ``lumon update`` command."""

from __future__ import annotations

from typing import Annotated

import typer

from lumon.cli.output import emit_error, emit_update
from lumon.errors import LumonError
from lumon.update import UpdateRequest, default_repository, default_service, python_version


def command(
    check_only: Annotated[
        bool, typer.Option("--check", help="Only check whether an update is available.")
    ] = False,
    repository: Annotated[
        str | None,
        typer.Option("--repository", help="GitHub repository in OWNER/REPOSITORY format."),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Render a JSON result.")] = False,
) -> None:
    """Check for and install the latest stable Lumon GitHub Release."""

    request = UpdateRequest(
        repository=repository or default_repository(),
        check_only=check_only,
        python_version=python_version(),
    )
    try:
        result = default_service().update(request)
    except LumonError as exc:
        emit_error(exc, json_output)
        raise typer.Exit(code=exc.exit_code) from exc
    emit_update(result, json_output)
