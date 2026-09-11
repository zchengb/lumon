"""Tests for the native Dashboard folder picker boundary."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from lumon.dashboard.folder_picker import FolderPicker
from lumon.errors import PreflightError


def test_macos_folder_picker_returns_the_selected_absolute_path() -> None:
    calls: list[list[str]] = []

    def runner(arguments: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(arguments)
        return subprocess.CompletedProcess(arguments, 0, "/Users/me/workspace/\n", "")

    picker = FolderPicker(runner=runner, system=lambda: "Darwin")

    assert picker.choose() == Path("/Users/me/workspace")
    assert calls[0][:2] == ["osascript", "-e"]
    assert "choose folder" in calls[0][2]


def test_macos_folder_picker_returns_none_when_cancelled() -> None:
    def runner(arguments: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(arguments, 0, "\n", "")

    picker = FolderPicker(runner=runner, system=lambda: "Darwin")

    assert picker.choose() is None


def test_folder_picker_explains_unsupported_platform() -> None:
    picker = FolderPicker(system=lambda: "Linux")

    with pytest.raises(PreflightError, match="supported on macOS"):
        picker.choose()
