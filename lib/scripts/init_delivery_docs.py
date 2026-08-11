#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path


def template_root() -> Path:
    return Path(__file__).resolve().parents[1] / "templates" / "delivery-docs"


def story_slug(example_key: str) -> str:
    return "mini-web-welcome"


def render_text(text: str, values: dict[str, str]) -> str:
    rendered = text
    for key, value in values.items():
        rendered = rendered.replace(f"__{key}__", value)
    return rendered


def copy_rendered(src: Path, dest: Path, values: dict[str, str], force: bool, merge: bool) -> None:
    if dest.exists() and not force:
        if merge:
            return
        raise FileExistsError(f"Refusing to overwrite existing file: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() in {".md", ".json", ".txt", ".mdc"} or src.name in {"AGENTS.md", ".gitignore"}:
        dest.write_text(render_text(src.read_text(encoding="utf-8"), values), encoding="utf-8")
    else:
        shutil.copy2(src, dest)


def sync_guidance(target: Path, project_name: str, backup_dir: Path | None = None) -> None:
    src_root = template_root()
    values = {"PROJECT_NAME": project_name or target.name}
    for relative in ("AGENTS.md", "README.md", "standards/business-loop.md", "standards/development-loop.md", "standards/technical-loop.md"):
        source = src_root / relative
        destination = target / relative
        if not source.is_file():
            continue
        content = render_text(source.read_text(encoding="utf-8"), values)
        if destination.is_file() and destination.read_text(encoding="utf-8") == content:
            continue
        if destination.exists() and backup_dir is not None:
            backup = backup_dir / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, backup)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")


def init_docs(
    target: Path,
    project_name: str,
    example_key: str,
    force: bool,
    merge: bool = False,
    no_example: bool = False,
) -> None:
    src_root = template_root()
    if not src_root.exists():
        raise FileNotFoundError(f"Delivery docs templates not found: {src_root}")

    target = target.expanduser().resolve()
    docs_root = target
    if target.exists() and any(target.iterdir()) and not force and not merge:
        raise FileExistsError(f"Target is not empty: {target}. Re-run with --force to merge/overwrite templates.")
    target.mkdir(parents=True, exist_ok=True)
    runtime_dir = target / "lumon"
    for legacy in (target / "lumen", target / ".lumen"):
        if not runtime_dir.exists() and legacy.exists():
            runtime_dir = legacy
            break
    runtime_dir_name = runtime_dir.name

    values = {
        "PROJECT_NAME": project_name,
        "JIRA_KEY": example_key,
        "STORY_SLUG": story_slug(example_key),
        "TODAY": dt.datetime.now().strftime("%Y-%m-%d"),
        "WORKSPACE_ROOT": str(docs_root),
        "DOCS_ROOT": str(docs_root),
        "DOCS_REPO_NAME": ".",
    }

    for src in src_root.rglob("*"):
        if src.is_dir():
            continue
        source_rel = src.relative_to(src_root)
        if source_rel.parts and source_rel.parts[0] in {"lumen", "lumon"}:
            source_rel = Path(runtime_dir_name) / Path(*source_rel.parts[1:])
        rel = render_text(str(source_rel), values)
        if no_example and rel.startswith("stories/") and rel != "stories/.gitkeep":
            continue
        dest = target / rel
        copy_rendered(src, dest, values, force, merge)

    template_workspace = src_root / "lumon"
    if not template_workspace.is_dir():
        template_workspace = src_root / "lumen"
    delivery_template = template_workspace / "config" / "delivery.json"
    if delivery_template.is_file():
        copy_rendered(
            delivery_template,
            runtime_dir / "config" / "delivery.example.json",
            values,
            force,
            merge,
        )

    for keep_dir in [
        target / "topics",
        target / "stories",
        target / "repos",
        runtime_dir / "config",
        runtime_dir / "worktrees",
        runtime_dir / "results",
        runtime_dir / "logs" / "delivery",
    ]:
        keep_dir.mkdir(parents=True, exist_ok=True)
        (keep_dir / ".gitkeep").touch()

    print(f"✓ Initialized Lumen workspace: {target}")
    print(f"✓ Workspace root: {docs_root}")
    print(f"✓ Code repositories directory: {target / 'repos'}")
    print(f"✓ Workspace config: {runtime_dir / 'config' / 'workspace.json'}")
    if not no_example:
        print(f"✓ Example story: stories/{story_slug(example_key)}/")
    print("Next:")
    print(f"  cd {target}")
    print("  Add repositories under repos/; Scan and Delivery use the same workspace")
    print("  git init  # optional, recommended for team sharing")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize Lumen workspace delivery assets.")
    parser.add_argument("--target", required=True)
    parser.add_argument("--project-name", default="Delivery Docs")
    parser.add_argument("--sync-guidance", action="store_true", help="Refresh root loop guidance without touching Stories or config")
    parser.add_argument("--backup-dir", default="")
    parser.add_argument("--example-key", default="DEMO-001")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--merge", action="store_true", help="Add missing delivery files without overwriting an existing workspace")
    parser.add_argument("--no-example", action="store_true", help="Do not create the example Story")
    args = parser.parse_args()
    try:
        if args.sync_guidance:
            sync_guidance(Path(args.target).expanduser().resolve(), args.project_name, Path(args.backup_dir).expanduser() if args.backup_dir else None)
            print(f"✓ Refreshed loop guidance: {args.target}")
            return 0
        init_docs(
            Path(args.target),
            args.project_name,
            args.example_key,
            args.force,
            args.merge,
            args.no_example,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
