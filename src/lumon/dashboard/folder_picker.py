"""Open a native local folder picker for Dashboard Workspace selection."""

from __future__ import annotations

import platform
import subprocess
from collections.abc import Callable
from pathlib import Path

from lumon.errors import PreflightError

FolderPickerRunner = Callable[..., subprocess.CompletedProcess[str]]
SystemName = Callable[[], str]

_MACOS_FOLDER_PICKER_SCRIPT = """try
    set selectedFolder to choose folder with prompt "Select Lumon Workspace"
    return POSIX path of selectedFolder
on error number -128
    return ""
end try"""


class FolderPicker:
    """Open an OS-native folder selector without exposing browser-local paths."""

    def __init__(
        self,
        runner: FolderPickerRunner | None = None,
        system: SystemName | None = None,
    ) -> None:
        self._runner = runner or subprocess.run
        self._system = system or platform.system

    def choose(self) -> Path | None:
        """Return the selected absolute directory, or ``None`` when cancelled."""

        if self._system() != "Darwin":
            raise PreflightError(
                "The native folder selector is currently supported on macOS. "
                "Enter the Workspace path manually."
            )
        return self._choose_macos()

    def _choose_macos(self) -> Path | None:
        try:
            result = self._runner(
                ["osascript", "-e", _MACOS_FOLDER_PICKER_SCRIPT],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            raise PreflightError(
                "Unable to open the macOS folder selector. Enter the Workspace path manually."
            ) from exc

        if result.returncode != 0:
            raise PreflightError(
                "Unable to open the macOS folder selector. Enter the Workspace path manually."
            )
        selected = result.stdout.strip()
        return Path(selected).expanduser().resolve() if selected else None
