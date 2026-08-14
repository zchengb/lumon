#!/usr/bin/env python3
"""Manage macOS launchd timers for Workspace Git synchronization."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path


def interval_minutes_from_cron(expression: str) -> int | None:
    parts = expression.strip().split()
    if len(parts) != 5 or parts[1:] != ["*", "*", "*", "*"] or not parts[0].startswith("*/"):
        return None
    try:
        value = int(parts[0][2:])
    except ValueError:
        return None
    return value if value > 0 else None


def label_for(slug: str) -> str:
    return f"com.lumen.workspace-sync.{slug}"


def plist_path(label: str) -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"


def launchctl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["launchctl", *args], capture_output=True, text=True, check=False)


def install(args: argparse.Namespace) -> int:
    interval = interval_minutes_from_cron(args.cron)
    if interval is None:
        print("Error: Workspace sync schedule must look like '*/N * * * *'.", file=sys.stderr)
        return 1
    path = plist_path(label_for(args.project))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": label_for(args.project),
        "ProgramArguments": [args.lumen_bin, "workspace", "sync", "--project", args.project],
        "EnvironmentVariables": {
            "PATH": args.path,
            "HOME": str(Path.home()),
            "LUMEN_HOME": args.lumen_home,
            "AGENT_CLI_CREDENTIAL_STORE": "file",
        },
        "StartInterval": interval * 60,
        "StandardOutPath": args.log_file,
        "StandardErrorPath": args.log_file,
        "ProcessType": "Background",
        "RunAtLoad": False,
    }
    path.write_bytes(plistlib.dumps(payload, fmt=plistlib.FMT_XML, sort_keys=False))
    domain = f"gui/{os.getuid()}"
    launchctl("bootout", domain, str(path))
    loaded = launchctl("bootstrap", domain, str(path))
    if loaded.returncode != 0:
        print(f"Error: {(loaded.stderr or loaded.stdout or 'launchctl bootstrap failed').strip()}", file=sys.stderr)
        return 1
    print(json.dumps({"path": str(path), "description": f"every {interval} minutes"}))
    return 0


def remove(args: argparse.Namespace) -> int:
    path = plist_path(label_for(args.project))
    launchctl("bootout", f"gui/{os.getuid()}", str(path))
    if path.exists():
        path.unlink()
    return 0


def status(args: argparse.Namespace) -> int:
    path = plist_path(label_for(args.project))
    if not path.exists():
        print(json.dumps({"enabled": False, "path": str(path), "interval_seconds": 0}))
        return 0
    try:
        payload = plistlib.loads(path.read_bytes())
        interval = int(payload.get("StartInterval") or 0)
    except (OSError, ValueError, plistlib.InvalidFileException):
        interval = 0
    print(json.dumps({"enabled": interval > 0, "path": str(path), "interval_seconds": interval}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    add = subparsers.add_parser("add")
    add.add_argument("--project", required=True)
    add.add_argument("--cron", required=True)
    add.add_argument("--lumen-bin", required=True)
    add.add_argument("--lumen-home", required=True)
    add.add_argument("--path", required=True)
    add.add_argument("--log-file", required=True)
    remove_parser = subparsers.add_parser("remove")
    remove_parser.add_argument("--project", required=True)
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--project", required=True)
    args = parser.parse_args()
    return {"add": install, "remove": remove, "status": status}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
