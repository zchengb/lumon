"""Contract tests for the Typer CLI entrypoint."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from lumon.cli.app import main

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def test_version_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == "1.0.7"


def test_root_version_option(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "1.0.7"


def test_help_command_is_compatible_with_common_cli_usage(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["help"]) == 0
    output = _ANSI_ESCAPE.sub("", capsys.readouterr().out)
    assert "Usage: lumon" in output


def test_unknown_command_has_a_friendly_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["not-a-command"]) == 2
    output = capsys.readouterr()
    combined_output = output.out + output.err

    assert "No such command 'not-a-command'" in combined_output
    assert "Traceback" not in combined_output


def test_doctor_json_is_machine_readable(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["doctor", "--json"])
    output = capsys.readouterr()

    assert exit_code in (0, 3)
    assert '"checks"' in output.out
    assert '"python_version"' in output.out


def test_command_exit_code_is_preserved_for_failed_doctor(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    workspace = tmp_path / "not-a-workspace"
    workspace.mkdir()

    assert main(["doctor", "--workspace", str(workspace), "--json"]) == 3
    assert '"ok": false' in capsys.readouterr().out
