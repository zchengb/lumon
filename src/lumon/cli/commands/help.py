"""The ``lumon help`` compatibility command."""

from __future__ import annotations

import typer


def command(context: typer.Context) -> None:
    """Show the root command help for users who prefer ``lumon help``."""

    root_context = context.parent or context
    typer.echo(root_context.get_help())
