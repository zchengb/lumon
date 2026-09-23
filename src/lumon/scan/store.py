"""Owner-only JSON receipts for Auto Scan history."""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path

from lumon.errors import PreflightError
from lumon.scan.model import ScanRun
from lumon.workspace.layout import WorkspaceLayout

_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ScanRunStore:
    """Persist and list scan receipts without putting them in user state."""

    def path_for(self, workspace: Path, run_id: str) -> Path:
        """Return a safe run directory under the Workspace control tree."""

        if _RUN_ID.fullmatch(run_id) is None:
            raise PreflightError("Auto Scan run ID contains unsafe characters.")
        return WorkspaceLayout.from_root(workspace).scan_runs_dir / run_id

    def save(self, workspace: Path, run: ScanRun) -> None:
        """Atomically write one non-sensitive run receipt."""

        directory = self.path_for(workspace, run.run_id)
        directory.mkdir(parents=True, exist_ok=True)
        _secure_directory(directory)
        _atomic_write(directory / "run.json", run.as_payload())

    def load(self, workspace: Path, run_id: str) -> ScanRun:
        """Read one scan receipt."""

        path = self.path_for(workspace, run_id) / "run.json"
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return ScanRun.from_payload(payload)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise PreflightError(f"Unable to read Auto Scan run: {path}") from exc

    def list(self, workspace: Path) -> tuple[ScanRun, ...]:
        """Return valid history entries newest first."""

        directory = WorkspaceLayout.from_root(workspace).scan_runs_dir
        if not directory.is_dir():
            return ()
        runs: list[ScanRun] = []
        for path in directory.iterdir():
            if not path.is_dir() or _RUN_ID.fullmatch(path.name) is None:
                continue
            try:
                runs.append(self.load(workspace, path.name))
            except PreflightError:
                continue
        return tuple(sorted(runs, key=lambda run: run.started_at, reverse=True))

    def artifact_path(self, workspace: Path, run_id: str, kind: str) -> Path:
        """Resolve one generated report artifact without allowing traversal."""

        filename = {"html": "report.html", "pdf": "report.pdf"}.get(kind)
        if filename is None:
            raise PreflightError("Unknown Auto Scan artifact.")
        run = self.load(workspace, run_id)
        expected = run.html_path if kind == "html" else run.pdf_path
        if expected != filename:
            raise PreflightError("Auto Scan artifact is not available.")
        path = self.path_for(workspace, run_id) / filename
        if not path.is_file():
            raise PreflightError("Auto Scan artifact is not available.")
        return path


def _atomic_write(path: Path, payload: Mapping[str, object]) -> None:
    temporary: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(temporary_name)
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        path.chmod(0o600)
    except OSError as exc:
        raise PreflightError(f"Unable to write Auto Scan receipt: {path}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _secure_directory(path: Path) -> None:
    try:
        path.chmod(0o700)
    except OSError as exc:
        raise PreflightError(f"Unable to secure Auto Scan receipt directory: {path}") from exc
