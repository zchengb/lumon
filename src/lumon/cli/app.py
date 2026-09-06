"""The single Python CLI entrypoint for Lumon."""

from __future__ import annotations

from collections.abc import Sequence

import click
import typer

from lumon.cli.commands import doctor, init, update, version
from lumon.version import __version__

app = typer.Typer(
    name="lumon",
    help="Lumon Workspace and Agent tooling.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def callback(
    version_flag: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the installed version.",
    ),
) -> None:
    """Global CLI options."""

    del version_flag


app.command("init")(init.command)
app.command("doctor")(doctor.command)
app.command("update")(update.command)
app.command("version")(version.command)


def main(argv: Sequence[str] | None = None) -> int:
    """Run Typer without allowing Click to call ``sys.exit`` internally."""

    try:
        result = app(
            prog_name="lumon",
            args=list(argv) if argv is not None else None,
            standalone_mode=False,
        )
        return int(result or 0)
    except click.exceptions.Exit as exc:
        return int(exc.exit_code or 0)
    except click.exceptions.ClickException as exc:
        typer.echo(exc.format_message(), err=True)
        return exc.exit_code
    return 0
