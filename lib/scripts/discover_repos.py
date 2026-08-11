#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {
    "lumon",
    "lumen",
    ".lumen",
    ".auto-scan",
    ".auto-scan-backup",
    "node_modules",
    ".idea",
    ".review-temp",
    "build",
    "dist",
    "tmp",
    "worktrees",
    "reports",
    "results",
    "logs",
    "state",
}


def is_git_repo(directory: Path) -> bool:
    return (directory / ".git").exists()


def default_branch(repo_path: Path) -> str:
    for command in (
        ["git", "symbolic-ref", "--short", "HEAD"],
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
    ):
        try:
            result = subprocess.run(
                command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            branch = result.stdout.strip()
            if branch:
                return branch
        except Exception:
            continue
    return "main"


def infer_profile(repo_path: Path) -> str:
    try:
        files = {entry.name for entry in repo_path.iterdir()}
    except Exception:
        return "local-generic-review-only"

    if files & {"gradlew", "build.gradle", "build.gradle.kts", "pom.xml"}:
        return "local-java-review-only"

    if "composer.json" in files:
        return "local-php-review-only"

    package_json = repo_path / "package.json"
    if package_json.exists():
        try:
            package = json.loads(package_json.read_text(encoding="utf-8"))
            deps = {}
            deps.update(package.get("dependencies") or {})
            deps.update(package.get("devDependencies") or {})
            if "react-native" in deps or "expo" in deps:
                return "local-react-native-review-only"
        except Exception:
            pass

    return "local-generic-review-only"


def discover(workspace_root: str) -> list:
    root = Path(workspace_root).resolve()
    repos = []
    seen = set()

    def add_repo(name: str, repo_path: Path) -> None:
        resolved = repo_path.resolve()
        key = str(resolved)
        if key in seen:
            return
        seen.add(key)
        repos.append(
            {
                "name": name,
                "path": str(resolved),
                "default_branch": default_branch(resolved),
                "runtime_profile": infer_profile(resolved),
            }
        )

    if is_git_repo(root):
        add_repo(root.name, root)

    try:
        entries = list(root.iterdir())
    except Exception:
        return sorted(repos, key=lambda item: item["name"])

    for entry in entries:
        if not entry.is_dir():
            continue
        if entry.name.startswith("."):
            continue
        if entry.name in SKIP_DIRS:
            continue
        if is_git_repo(entry):
            add_repo(entry.name, entry)

    return sorted(repos, key=lambda item: item["name"])


def parse_selection(selection: str, maximum: int) -> list:
    value = str(selection or "").strip().lower()
    if not value:
        return []
    if value == "all":
        return list(range(1, maximum + 1))
    indices = []
    for part in [piece for piece in value.replace(",", " ").split() if piece]:
        if not part.isdigit():
            raise RuntimeError(f"Invalid selection: {part}")
        index = int(part)
        if index < 1 or index > maximum:
            raise RuntimeError(f"Selection out of range: {part}")
        if index not in indices:
            indices.append(index)
    indices.sort()
    return indices


def usage() -> None:
    sys.stderr.write(
        """Usage:
  discover_repos.py list <workspace-root>
  discover_repos.py select <workspace-root> <selection>
"""
    )
    raise SystemExit(1)


def main() -> int:
    argv = sys.argv[1:]
    if len(argv) < 2:
        usage()
    command, workspace_root = argv[0], argv[1]
    repos = discover(workspace_root)

    if command == "list":
        sys.stdout.write(json.dumps(repos, indent=2) + "\n")
        return 0

    if command == "select":
        selection_arg = argv[2] if len(argv) > 2 else ""
        indices = parse_selection(selection_arg, len(repos))
        selected = [repos[index - 1] for index in indices]
        sys.stdout.write(json.dumps(selected, indent=2) + "\n")
        return 0

    usage()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
