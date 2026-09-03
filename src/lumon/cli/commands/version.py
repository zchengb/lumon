"""The ``lumon version`` command."""

import typer

from lumon.version import __version__


def command() -> None:
    """Print the installed Lumon version."""

    typer.echo(__version__)
