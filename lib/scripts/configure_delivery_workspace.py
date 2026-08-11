#!/usr/bin/env python3
"""Configure an external workspace and repository mappings for delivery docs."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from delivery_workspace import docs_lumen_config_dir, read_json, workspace_lumen_dir, write_json


def ensure_delivery_config(workspace_root: Path) -> Path:
    target = workspace_lumen_dir(workspace_root) / "config" / "delivery.json"
    if target.is_file():
        return target
    template_root = Path(__file__).resolve().parents[1] / "templates" / "delivery-docs"
    template = template_root / "lumon" / "config" / "delivery.json"
    if not template.is_file():
        template = template_root / "lumen" / "config" / "delivery.json"
    if not template.is_file():
        raise FileNotFoundError(f"Delivery config template not found: {template}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template, target)
    return target


def parse_repository(value: str, workspace_root: Path) -> dict[str, str]:
    name, separator, raw_path = value.partition("=")
    if not separator or not name.strip() or not raw_path.strip():
        raise ValueError("Repository mappings must use NAME=PATH")
    path = Path(raw_path.strip()).expanduser()
    if not path.is_absolute():
        path = (workspace_root / path).resolve()
    else:
        path = path.resolve()
    if not (path / ".git").exists():
        raise FileNotFoundError(f"Repository is not a Git checkout: {path}")
    try:
        saved_path = str(path.relative_to(workspace_root))
    except ValueError:
        saved_path = str(path)
    return {"name": name.strip(), "path": saved_path}


def configure(
    docs_dir: Path,
    workspace_root: Path,
    mappings: list[str],
    replace_repositories: bool,
) -> dict[str, Any]:
    docs_dir = docs_dir.expanduser().resolve()
    workspace_root = workspace_root.expanduser().resolve()
    if not (docs_dir / "stories").is_dir():
        raise FileNotFoundError(f"Not a delivery docs repository: {docs_dir}")
    if not workspace_root.is_dir():
        raise FileNotFoundError(f"Workspace root does not exist: {workspace_root}")

    config_path = docs_lumen_config_dir(docs_dir) / "workspace.json"
    current = read_json(config_path, {})
    existing = {} if replace_repositories else {
        str(item.get("name", "")).strip(): item
        for item in current.get("repositories", [])
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    }
    for mapping in mappings:
        parsed = parse_repository(mapping, workspace_root)
        prior = existing.get(parsed["name"], {})
        if prior.get("default_branch"):
            parsed["default_branch"] = str(prior["default_branch"])
        existing[parsed["name"]] = parsed

    payload = {
        "schema_version": "1.1",
        "layout": "external",
        "workspace_root": str(workspace_root),
        "docs_repo": str(docs_dir),
        "repos_dir": "",
        "repositories": [existing[name] for name in sorted(existing)],
    }
    write_json(config_path, payload)
    ensure_delivery_config(workspace_root)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-dir", required=True)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--repo", action="append", default=[], help="NAME=PATH; repeat as needed")
    parser.add_argument("--replace-repositories", action="store_true")
    args = parser.parse_args()
    try:
        payload = configure(
            Path(args.docs_dir),
            Path(args.workspace_root),
            args.repo,
            args.replace_repositories,
        )
    except (OSError, ValueError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
