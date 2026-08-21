#!/usr/bin/env python3
"""Read and update workspace configuration values in config/common.json."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from visual_delivery import (  # noqa: E402
    list_visual_auth_credentials,
    repos_config,
    set_visual_auth_credential,
    workspace_root_from,
)

DEFAULT_SCAN_WINDOW_DAYS = 7
MIN_SCAN_WINDOW_DAYS = 1
MAX_SCAN_WINDOW_DAYS = 365


def common_json_path(workspace: Path) -> Path:
    return workspace / "config" / "common.json"


def load_common(workspace: Path) -> dict:
    path = common_json_path(workspace)
    if not path.is_file():
        raise FileNotFoundError(f"Workspace config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_common(workspace: Path, common: dict) -> None:
    path = common_json_path(workspace)
    path.write_text(json.dumps(common, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_scan_window_days(workspace: Path) -> int:
    common = load_common(workspace)
    value = common.get("execution", {}).get("scan_window_days", DEFAULT_SCAN_WINDOW_DAYS)
    try:
        days = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid scan_window_days in common.json: {value!r}") from exc
    return days


def set_scan_window_days(workspace: Path, days: int) -> int:
    if days < MIN_SCAN_WINDOW_DAYS or days > MAX_SCAN_WINDOW_DAYS:
        raise ValueError(
            f"Scan window must be between {MIN_SCAN_WINDOW_DAYS} and {MAX_SCAN_WINDOW_DAYS} days."
        )
    common = load_common(workspace)
    execution = common.setdefault("execution", {})
    execution["scan_window_days"] = days
    save_common(workspace, common)
    return days


def read_env_var(workspace: Path, key: str) -> str | None:
    env_file = workspace / ".env.local"
    if not env_file.is_file():
        return None
    pattern = re.compile(
        rf'^{re.escape(key)}=(?:"([^"]*)"|\'([^\']*)\'|(\S+))'
    )
    for line in env_file.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line.strip())
        if match:
            return next(group for group in match.groups() if group is not None)
    return None


def read_webhook_url(workspace: Path) -> str | None:
    return read_env_var(workspace, "FEISHU_WEBHOOK_URL")


def read_cursor_api_key(workspace: Path) -> str | None:
    return read_env_var(workspace, "CURSOR_API_KEY")


def mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "[set]"
    return f"{value[:4]}...{value[-4:]}"


def mask_webhook(url: str) -> str:
    return mask_secret(url)


def jira_config(common: dict) -> dict:
    notifications = common.get("notifications", {})
    config = notifications.get("jira", {})
    if not isinstance(config, dict):
        return {}
    return config


def default_jira_config() -> dict:
    return {
        "enabled": True,
        "project_key": "MBPAS",
        "board_id": "",
        "assign_to_active_sprint": False,
        "issue_type": "Bug",
        "blocked_status": "Block",
        "severities": ["High", "Medium", "Low"],
        "summary_prefix": "[Lumen]",
    }


def merge_jira_defaults(config: dict) -> dict:
    merged = default_jira_config()
    merged.update(config)
    return merged


def set_jira_config(
    workspace: Path,
    *,
    enabled: bool | None = None,
    project_key: str | None = None,
    board_id: str | None = None,
    assign_to_active_sprint: bool | None = None,
) -> dict:
    common = load_common(workspace)
    notifications = common.setdefault("notifications", {})
    current = jira_config(common)
    jira = merge_jira_defaults(current)
    notifications["jira"] = jira

    if enabled is not None:
        jira["enabled"] = enabled
    if project_key is not None:
        jira["project_key"] = project_key.strip()
    if board_id is not None:
        jira["board_id"] = board_id.strip()
    if assign_to_active_sprint is not None:
        jira["assign_to_active_sprint"] = assign_to_active_sprint

    if jira.get("enabled") and not str(jira.get("project_key", "")).strip():
        raise ValueError("project_key is required when Jira sync is enabled")

    save_common(workspace, common)
    return jira


def cmd_show(workspace: Path) -> int:
    common_path = common_json_path(workspace)
    print(f"Workspace: {workspace}")
    print(f"Config file: {common_path}")
    print()

    try:
        common = load_common(workspace)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    execution = common.get("execution", {})
    project = common.get("project", {})
    scan_window = execution.get("scan_window_days", DEFAULT_SCAN_WINDOW_DAYS)
    model = execution.get("model", "")
    display_name = project.get("display_name", "")

    print(f"project.display_name: {display_name or '(not set)'}")
    print(f"execution.scan_window_days: {scan_window}")
    if model:
        print(f"execution.model: {model}")

    webhook = read_webhook_url(workspace)
    cursor_api_key = read_cursor_api_key(workspace)
    env_file = workspace / ".env.local"
    print()
    if webhook:
        print(f"FEISHU_WEBHOOK_URL: {mask_webhook(webhook)}  ({env_file})")
    else:
        print(f"FEISHU_WEBHOOK_URL: (not set)  ({env_file})")
    if cursor_api_key:
        print(f"CURSOR_API_KEY: {mask_secret(cursor_api_key)}  ({env_file})")
    else:
        print(f"CURSOR_API_KEY: (not set)  ({env_file})")

    jira = merge_jira_defaults(jira_config(common))
    print()
    print(f"notifications.jira.enabled: {jira.get('enabled', False)}")
    if jira.get("enabled"):
        print(f"notifications.jira.project_key: {jira.get('project_key', '')}")
        board_id = str(jira.get("board_id", "")).strip()
        print(f"notifications.jira.board_id: {board_id or '(auto-detect)'}")
        print(f"notifications.jira.assign_to_active_sprint: {jira.get('assign_to_active_sprint', True)}")
        print(f"notifications.jira.issue_type: {jira.get('issue_type', 'Bug')}")

    visual_auth = list_visual_auth_credentials(workspace)
    repos_path = repos_config(workspace_root_from(workspace))
    print()
    print(f"visual auth credentials: {repos_path}")
    if visual_auth:
        for repository, credential in sorted(visual_auth.items()):
            print(f"web auth credential ({repository}): {mask_secret(credential)}")
    else:
        print("web auth credential: (not set)")
    return 0


def cmd_set_visual_auth(workspace: Path, repository: str, credential: str) -> int:
    try:
        set_visual_auth_credential(workspace, repository, credential)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Saved Web auth credential for {repository} to {repos_config(workspace_root_from(workspace))}")
    return 0


def cmd_set_jira(workspace: Path, args: argparse.Namespace) -> int:
    if args.enable and args.disable:
        print("Error: use either --enable or --disable, not both.", file=sys.stderr)
        return 1

    enabled: bool | None = None
    if args.enable:
        enabled = True
    elif args.disable:
        enabled = False

    project_key = args.project_key
    board_id = args.board_id
    has_board_id = "--board-id" in sys.argv
    assign_to_active_sprint: bool | None = None
    if args.no_active_sprint:
        assign_to_active_sprint = False
    elif args.assign_active_sprint:
        assign_to_active_sprint = True

    if (
        enabled is None
        and project_key is None
        and not has_board_id
        and assign_to_active_sprint is None
    ):
        print(
            "Error: provide --enable, --disable, --project-key, --board-id, or sprint flags.",
            file=sys.stderr,
        )
        return 1

    if enabled and not project_key:
        existing = merge_jira_defaults(jira_config(load_common(workspace)))
        project_key = str(existing.get("project_key", "")).strip() or None
        if not project_key:
            print("Error: --project-key is required when enabling Jira sync.", file=sys.stderr)
            return 1

    try:
        jira = set_jira_config(
            workspace,
            enabled=enabled,
            project_key=project_key,
            board_id=board_id if has_board_id else None,
            assign_to_active_sprint=assign_to_active_sprint,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if jira.get("enabled"):
        board = str(jira.get("board_id", "")).strip() or "auto-detect"
        print(
            f"Jira sync enabled: project={jira.get('project_key')} "
            f"board={board} active_sprint={jira.get('assign_to_active_sprint', True)}"
        )
    elif enabled is False:
        print("Jira sync disabled.")
    else:
        board = str(jira.get("board_id", "")).strip() or "auto-detect"
        print(
            f"Jira settings updated: enabled={jira.get('enabled')} "
            f"project={jira.get('project_key')} board={board} "
            f"active_sprint={jira.get('assign_to_active_sprint', True)}"
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Lumen workspace configuration helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    show_parser = subparsers.add_parser("show", help="Print workspace configuration summary")
    show_parser.add_argument("workspace")

    get_parser = subparsers.add_parser("get-scan-window", help="Print scan_window_days")
    get_parser.add_argument("workspace")

    set_parser = subparsers.add_parser("set-scan-window", help="Set scan_window_days")
    set_parser.add_argument("workspace")
    set_parser.add_argument("days", type=int)

    jira_parser = subparsers.add_parser("set-jira", help="Enable or update Jira sync settings")
    jira_parser.add_argument("workspace")
    jira_parser.add_argument("--enable", action="store_true", help="Enable Jira sync")
    jira_parser.add_argument("--disable", action="store_true", help="Disable Jira sync")
    jira_parser.add_argument("--project-key", help="Jira project key (e.g. MBPAS)")
    jira_parser.add_argument("--board-id", help="Jira board ID for active sprint resolution")
    jira_parser.add_argument(
        "--no-active-sprint",
        action="store_true",
        help="Do not assign new bugs to the active sprint",
    )
    jira_parser.add_argument(
        "--assign-active-sprint",
        action="store_true",
        help="Assign new bugs to the active sprint",
    )

    visual_auth_parser = subparsers.add_parser(
        "set-visual-auth",
        help="Save a Visual Delivery login credential for one repository",
    )
    visual_auth_parser.add_argument("workspace")
    visual_auth_parser.add_argument("repository")
    visual_auth_parser.add_argument("credential")

    args = parser.parse_args()
    workspace = Path(args.workspace).expanduser().resolve()

    try:
        if args.command == "show":
            return cmd_show(workspace)
        if args.command == "get-scan-window":
            print(get_scan_window_days(workspace))
            return 0
        if args.command == "set-scan-window":
            days = set_scan_window_days(workspace, args.days)
            print(days)
            return 0
        if args.command == "set-visual-auth":
            return cmd_set_visual_auth(workspace, args.repository, args.credential)
        if args.command == "set-jira":
            return cmd_set_jira(workspace, args)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
