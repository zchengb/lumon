"""Verify that a package build has included the compiled Dashboard frontend."""

from __future__ import annotations

from pathlib import Path


def main() -> int:
    """Return a failing status when the static Dashboard was not built."""

    root = Path(__file__).resolve().parents[1]
    index = root / "src" / "lumon" / "dashboard" / "static" / "index.html"
    logo = root / "src" / "lumon" / "dashboard" / "static" / "lumon-mark.png"
    if not index.is_file():
        print(f"Dashboard assets are missing: {index}")
        return 1
    if not logo.is_file():
        print(f"Dashboard Logo is missing: {logo}")
        return 1
    content = index.read_text(encoding="utf-8")
    if "/assets/" not in content:
        print(f"Dashboard index does not reference compiled assets: {index}")
        return 1
    print(f"Dashboard assets verified: {index}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
