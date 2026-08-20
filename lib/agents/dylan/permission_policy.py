from __future__ import annotations

import json
from pathlib import Path
from typing import Any


HOST_INTROSPECTION_DENY = [
    "Shell(system_profiler)",
    "Shell(hostname)",
    "Shell(scutil)",
    "Shell(sw_vers)",
    "Shell(uname)",
    "Shell(sysctl)",
    "Shell(ioreg)",
    "Shell(diskutil)",
    "Shell(ifconfig)",
    "Shell(networksetup)",
    "Shell(ps)",
    "Shell(launchctl)",
    "Shell(whoami)",
    "Shell(id)",
    "Shell(dscl)",
    "Shell(defaults)",
    "Shell(mdfind)",
    "Shell(top)",
    "Shell(lsof)",
    "Shell(netstat)",
    "Shell(open)",
    "Shell(osascript)",
]

GIT_WRITE_DENY = [
    "Shell(git checkout)",
    "Shell(git reset)",
    "Shell(git clean)",
    "Shell(git commit)",
    "Shell(git push)",
    "Shell(git fetch)",
    "Shell(git pull)",
    "Shell(git clone)",
    "Shell(git switch)",
    "Shell(git restore)",
    "Shell(git rebase)",
    "Shell(git merge)",
]

# M0.3.1 Permission Profile v2 — project-centric, no host enumeration shells.
SECURE_PERMISSIONS = {
    "permissions": {
        "allow": [
            "Read(**)",
            "Shell(lumen)",
            "Shell(git)",
            "Shell(rg)",
        ],
        "deny": [
            "Write(**)",
            "Delete(**)",
            "Read(**/.env*)",
            "Read(**/*.pem)",
            "Read(**/*.key)",
            "Write(**/.env*)",
            "Write(**/*.pem)",
            "Write(**/*.key)",
            "Shell(ls)",
            "Shell(find)",
            "Shell(cat)",
            "Shell(head)",
            "Shell(tail)",
            "Shell(wc)",
            "Shell(pytest)",
            "Shell(sudo)",
            "Shell(ssh)",
            "Shell(scp)",
            "Shell(rm)",
            "Shell(curl)",
            "Shell(wget)",
            "Shell(python)",
            "Shell(python3)",
            "Shell(node)",
            "Shell(npm)",
            "Shell(pnpm)",
            "Shell(yarn)",
            *HOST_INTROSPECTION_DENY,
            *GIT_WRITE_DENY,
        ],
    }
}

DEFAULT_PERMISSIONS = SECURE_PERMISSIONS

# M0.8 direct engineering profile.  Mark and Irving may change files in the
# already-resolved isolated workspace and run project-local verification, but
# they still cannot inspect the personal host, secrets, or publish from the
# provider session.  The runner remains responsible for enforcing the
# workspace boundary and publishing an approved result.
WORKSPACE_WRITE_PERMISSIONS = {
    "permissions": {
        "allow": [
            "Read(**)",
            "Write(**)",
            "Shell(lumen)",
            "Shell(git)",
            "Shell(rg)",
            "Shell(cargo)",
            "Shell(gradle)",
            "Shell(./gradlew)",
            "Shell(mvn)",
            "Shell(./mvnw)",
            "Shell(node)",
            "Shell(npm)",
            "Shell(pnpm)",
            "Shell(yarn)",
            "Shell(pytest)",
            "Shell(python)",
            "Shell(python3)",
            "Shell(go)",
            "Shell(swift)",
            "Shell(xcodebuild)",
        ],
        "deny": [
            "Delete(**)",
            "Read(**/.env*)",
            "Read(**/*.pem)",
            "Read(**/*.key)",
            "Write(**/.env*)",
            "Write(**/*.pem)",
            "Write(**/*.key)",
            "Write(.cursor/**)",
            "Write(AGENTS.md)",
            "Write(**/.git/**)",
            "Shell(sudo)",
            "Shell(ssh)",
            "Shell(scp)",
            "Shell(rm)",
            "Shell(curl)",
            "Shell(wget)",
            *HOST_INTROSPECTION_DENY,
            *GIT_WRITE_DENY,
        ],
    }
}

# Loop planning needs to persist business/technical artifacts, but it must not
# turn the conversational Agent into a source-code or publishing worker.
LOOP_PERMISSIONS = {
    "permissions": {
        "allow": [
            "Read(**)",
            "Write(topics/**)",
            "Write(stories/**)",
            "Shell(lumen)",
            "Shell(rg)",
            "Shell(git)",
        ],
        "deny": [
            "Write(**/.env*)",
            "Write(**/*.pem)",
            "Write(**/*.key)",
            "Write(.cursor/**)",
            "Write(AGENTS.md)",
            "Write(lumen/**)",
            "Write(repos/**)",
            "Write(lumen/worktrees/**)",
            "Write(**/.git/**)",
            "Write(**/package.json)",
            "Write(**/pyproject.toml)",
            "Write(**/*.py)",
            "Write(**/*.java)",
            "Write(**/*.kt)",
            "Write(**/*.js)",
            "Write(**/*.jsx)",
            "Write(**/*.ts)",
            "Write(**/*.tsx)",
            "Write(**/*.go)",
            "Write(**/*.rs)",
            "Write(**/*.rb)",
            "Write(**/*.swift)",
            "Write(**/*.c)",
            "Write(**/*.cc)",
            "Write(**/*.cpp)",
            "Write(**/*.h)",
            "Write(**/*.hpp)",
            "Shell(ls)",
            "Shell(find)",
            "Shell(cat)",
            "Shell(head)",
            "Shell(tail)",
            "Shell(wc)",
            "Shell(python)",
            "Shell(python3)",
            "Shell(node)",
            "Shell(npm)",
            "Shell(pnpm)",
            "Shell(yarn)",
            "Shell(sudo)",
            "Shell(ssh)",
            "Shell(scp)",
            "Shell(curl)",
            "Shell(wget)",
            *HOST_INTROSPECTION_DENY,
            *GIT_WRITE_DENY,
            "Shell(git add)",
        ],
    }
}


def write_permission_profile(workspace: Path, *, force: bool = True) -> Path:
    cursor_dir = Path(workspace).expanduser().resolve() / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    path = cursor_dir / "cli.json"
    if force or not path.is_file():
        path.write_text(json.dumps(SECURE_PERMISSIONS, indent=2) + "\n", encoding="utf-8")
    return path


def write_workspace_write_permission_profile(workspace: Path, *, force: bool = True) -> Path:
    cursor_dir = Path(workspace).expanduser().resolve() / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    path = cursor_dir / "cli.json"
    if force or not path.is_file():
        path.write_text(json.dumps(WORKSPACE_WRITE_PERMISSIONS, indent=2) + "\n", encoding="utf-8")
    return path


def write_loop_permission_profile(workspace: Path, *, force: bool = True) -> Path:
    cursor_dir = Path(workspace).expanduser().resolve() / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    path = cursor_dir / "cli.json"
    if force or not path.is_file():
        path.write_text(json.dumps(LOOP_PERMISSIONS, indent=2) + "\n", encoding="utf-8")
    return path


def validate_workspace_bound(session_workspace: str, resolved_workspace: Path) -> None:
    left = str(Path(session_workspace).expanduser().resolve())
    right = str(Path(resolved_workspace).expanduser().resolve())
    if left != right:
        raise RuntimeError(f"workspace mismatch for session: {left} != {right}")
