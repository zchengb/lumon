"""Create SHA256SUMS for package distributions."""

from __future__ import annotations

import sys
from hashlib import sha256
from pathlib import Path


def create_checksums(directory: Path) -> Path:
    """Write sorted SHA256 entries for all distributions in ``directory``."""

    distributions = sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and (path.name.endswith(".whl") or path.name.endswith(".tar.gz"))
    )
    if not distributions:
        raise ValueError(f"No distributions found in {directory}.")

    checksum_path = directory / "SHA256SUMS"
    lines = [f"{sha256(path.read_bytes()).hexdigest()}  {path.name}" for path in distributions]
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return checksum_path


def main(argv: list[str] | None = None) -> int:
    """Create checksums for the directory given on the command line."""

    arguments = argv if argv is not None else sys.argv[1:]
    if len(arguments) != 1:
        print("usage: create_checksums.py DIST_DIRECTORY", file=sys.stderr)
        return 2
    try:
        create_checksums(Path(arguments[0]))
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
