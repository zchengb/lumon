"""Fail when the retired product spelling reappears in shipped sources."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (
    ROOT / ".github",
    ROOT / "dashboard-ui" / "src",
    ROOT / "dashboard-ui" / "index.html",
    ROOT / "docs",
    ROOT / "src",
    ROOT / "tests",
    ROOT / "tools",
    ROOT / "AGENTS.md",
    ROOT / "README.md",
)
SKIP_PARTS = {"node_modules", "dist", "build", "__pycache__"}


def main() -> int:
    retired_spelling = "l" + "umen"
    violations: list[str] = []
    for root in SCAN_ROOTS:
        paths = [root] if root.is_file() else root.rglob("*") if root.exists() else []
        for path in paths:
            if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                if retired_spelling in line.casefold():
                    violations.append(f"{path.relative_to(ROOT)}:{line_number}")
    if violations:
        print("Retired product spelling found:")
        print("\n".join(violations))
        return 1
    print("Brand check passed: Lumon only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
