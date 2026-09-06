"""Verify that a Git tag matches the Lumon package version."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def read_version(path: Path) -> str:
    """Read the literal ``__version__`` assignment from a Python module."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        if node.targets[0].id == "__version__" and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                return node.value.value
    raise ValueError(f"Could not find a string __version__ assignment in {path}.")


def main(argv: list[str] | None = None) -> int:
    """Return a non-zero status when the tag and package versions differ."""

    arguments = argv if argv is not None else sys.argv[1:]
    if len(arguments) != 1:
        print("usage: check_release_version.py TAG", file=sys.stderr)
        return 2
    tag_version = arguments[0].removeprefix("v")
    package_version = read_version(Path("src/lumon/version.py"))
    if tag_version != package_version:
        print(
            f"Tag version {tag_version} does not match package version {package_version}.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
