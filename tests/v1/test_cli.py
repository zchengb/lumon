"""Contract tests for the Typer CLI entrypoint."""

from __future__ import annotations

from pathlib import Path

from lumon.cli.app import main


def test_version_command(capsys) -> None:
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == "0.1.0"


def test_root_version_option(capsys) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "0.1.0"


def test_doctor_json_is_machine_readable(capsys) -> None:
    exit_code = main(["doctor", "--json"])
    output = capsys.readouterr()

    assert exit_code in (0, 3)
    assert '"checks"' in output.out
    assert '"python_version"' in output.out


def test_command_exit_code_is_preserved_for_failed_doctor(capsys, tmp_path: Path) -> None:
    workspace = tmp_path / "not-a-workspace"
    workspace.mkdir()

    assert main(["doctor", "--workspace", str(workspace), "--json"]) == 3
    assert '"ok": false' in capsys.readouterr().out
