"""Contract tests for the Typer CLI entrypoint."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from lumon.cli.app import main
from lumon.dashboard.server import DashboardServer
from lumon.version import __version__

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


@pytest.mark.parametrize(
    ("options", "expected_port"),
    [([], 15778), (["--port", "8080"], 8080), (["--port", "0"], 0)],
)
def test_ui_uses_fixed_default_port_and_allows_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    options: list[str],
    expected_port: int,
) -> None:
    calls: list[tuple[int, bool]] = []

    def run(self: DashboardServer, *, port: int, open_browser: bool) -> None:
        del self
        calls.append((port, open_browser))

    monkeypatch.setenv("LUMON_HOME", str(tmp_path / "state"))
    monkeypatch.setattr(DashboardServer, "run", run)

    assert main(["ui", "--no-open", *options]) == 0
    assert calls == [(expected_port, False)]


def test_version_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_root_version_option(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


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
