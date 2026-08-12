from __future__ import annotations

from pathlib import Path


HOST_INTROSPECTION_COMMANDS = frozenset(
    {
        "system_profiler",
        "hostname",
        "scutil",
        "sw_vers",
        "uname",
        "sysctl",
        "ioreg",
        "diskutil",
        "ifconfig",
        "networksetup",
        "ps",
        "launchctl",
        "whoami",
        "id",
        "dscl",
        "defaults",
        "mdfind",
        "mdls",
        "top",
        "lsof",
        "netstat",
        "route",
        "arp",
        "ping",
        "traceroute",
        "open",
        "osascript",
    }
)

FORBIDDEN_HOST_ROOTS = (
    ".ssh",
    ".gnupg",
    ".aws",
    ".config",
    ".lumen",
    ".lumon",
    "Library",
    "Desktop",
    "Documents",
    "Downloads",
    "Applications",
)


def _home() -> Path:
    return Path.home().resolve()


def forbidden_paths() -> tuple[Path, ...]:
    home = _home()
    roots = [home / name for name in FORBIDDEN_HOST_ROOTS]
    roots.extend(
        [
            Path("/Applications").resolve(),
            Path("/System").resolve(),
            Path("/Library").resolve(),
            Path("/Volumes").resolve(),
            Path("/etc").resolve(),
            Path("/private/etc").resolve(),
            Path("/private/var/db").resolve(),
        ]
    )
    return tuple(roots)


def canonicalize(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def is_forbidden_host_path(path: str | Path) -> bool:
    resolved = canonicalize(path)
    for root in forbidden_paths():
        try:
            if resolved == root or resolved.is_relative_to(root):
                return True
        except (OSError, ValueError):
            continue
    return False


def assert_within_workspace(path: str | Path, workspace: str | Path) -> Path:
    resolved = canonicalize(path)
    root = canonicalize(workspace)
    if is_forbidden_host_path(resolved):
        raise PermissionError(f"WORKSPACE_READ_ESCAPE: host path denied: {resolved}")
    try:
        if not resolved.is_relative_to(root):
            raise PermissionError(f"WORKSPACE_READ_ESCAPE: {resolved}")
    except ValueError as exc:
        raise PermissionError(f"WORKSPACE_READ_ESCAPE: {resolved}") from exc
    return resolved


def assert_read_allowed(path: str | Path, workspace: str | Path) -> Path:
    return assert_within_workspace(path, workspace)


def assert_write_denied_outside_worktree(path: str | Path, allowed_root: str | Path | None = None) -> None:
    resolved = canonicalize(path)
    if is_forbidden_host_path(resolved):
        raise PermissionError(f"host write denied: {resolved}")
    if allowed_root is None:
        raise PermissionError(f"write denied outside managed worktree: {resolved}")
    root = canonicalize(allowed_root)
    if not resolved.is_relative_to(root):
        raise PermissionError(f"write denied outside managed worktree: {resolved}")


def is_host_introspection_command(command: str) -> bool:
    tokens = str(command or "").strip().split()
    if not tokens:
        return False
    binary = Path(tokens[0]).name.lower()
    return binary in HOST_INTROSPECTION_COMMANDS
