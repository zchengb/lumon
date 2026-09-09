"""Run the local Dashboard API and bundled static frontend."""

from __future__ import annotations

import socket
import webbrowser
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlencode
from uuid import UUID

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from lumon.dashboard.routes import create_app
from lumon.dashboard.service import DashboardService
from lumon.errors import PreflightError

LOCAL_HOST = "127.0.0.1"


class DashboardServer:
    """Own the local-only server lifecycle and browser launch policy."""

    def __init__(
        self,
        app: FastAPI | None = None,
        browser_opener: Callable[[str], bool] | None = None,
        runner: Callable[..., None] | None = None,
        initial_workspace_id: UUID | None = None,
    ) -> None:
        self.app = app or create_dashboard_app()
        self._browser_opener = browser_opener or webbrowser.open
        self._runner = runner or uvicorn.run
        self._initial_workspace_id = initial_workspace_id

    def run(self, port: int = 0, open_browser: bool = True) -> None:
        """Select a local port, optionally open the browser, and block until stopped."""

        actual_port = select_port(port)
        query = (
            "?"
            + urlencode(
                {
                    "workspace": str(self._initial_workspace_id),
                    "view": "overview",
                }
            )
            if self._initial_workspace_id
            else ""
        )
        url = f"http://{LOCAL_HOST}:{actual_port}/{query}"
        print(f"Lumon Dashboard: {url}", flush=True)
        if open_browser:
            self._browser_opener(url)
        self._runner(
            self.app,
            host=LOCAL_HOST,
            port=actual_port,
            log_level="info",
        )


def add_static_frontend(app: FastAPI, static_dir: Path | None = None) -> FastAPI:
    """Mount the compiled SPA at the root without affecting ``/api`` routes."""

    directory = static_dir or Path(__file__).parent / "static"
    if directory.is_dir():
        app.mount("/", StaticFiles(directory=str(directory), html=True), name="dashboard")
    return app


def create_dashboard_app(
    service: DashboardService | None = None,
    static_dir: Path | None = None,
) -> FastAPI:
    """Create the API app and mount the bundled frontend when it exists."""

    return add_static_frontend(create_app(service), static_dir)


def select_port(requested: int) -> int:
    """Validate a requested port and reserve an available OS-selected port."""

    if requested < 0 or requested > 65_535:
        raise PreflightError("Dashboard port must be between 0 and 65535.")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((LOCAL_HOST, requested))
        except OSError as exc:
            raise PreflightError(f"Dashboard port is unavailable: {requested}") from exc
        return int(probe.getsockname()[1])
