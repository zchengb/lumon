#!/usr/bin/env python3
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

LUMEN_HOME = Path(os.environ.get("LUMEN_HOME", Path.home() / ".lumon"))
REGISTRY_PATH = LUMEN_HOME / "projects.json"
CONFIG_PATH = LUMEN_HOME / "config.json"
SCHEMA_VERSION = "1.0"
WORKSPACE_DIR_NAME = "lumon"
LEGACY_WORKSPACE_DIR_NAMES = ("lumen", ".lumen")


def ensure_registry_dir() -> None:
    LUMEN_HOME.mkdir(parents=True, exist_ok=True)


def empty_registry() -> dict:
    return {"schema_version": SCHEMA_VERSION, "projects": []}


def load_config() -> dict:
    ensure_registry_dir()
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(config: dict) -> None:
    ensure_registry_dir()
    tmp = CONFIG_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    tmp.replace(CONFIG_PATH)


def load_registry() -> dict:
    ensure_registry_dir()
    if not REGISTRY_PATH.exists():
        return empty_registry()
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        if not isinstance(data.get("projects"), list):
            return empty_registry()
        migrate_registry(data)
        return data
    except Exception:
        return empty_registry()


def save_registry(data: dict) -> None:
    ensure_registry_dir()
    tmp = REGISTRY_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(REGISTRY_PATH)


def normalize_workspace(workspace: str) -> str:
    return str(Path(workspace).resolve())


def read_display_name(workspace: str) -> str:
    common_path = Path(workspace) / "config" / "common.json"
    if not common_path.exists():
        return Path(workspace).name
    try:
        common = json.loads(common_path.read_text(encoding="utf-8"))
        name = (common.get("project") or {}).get("display_name")
        if name and str(name).strip():
            return str(name).strip()
    except Exception:
        pass
    base = Path(workspace).name
    if base in {WORKSPACE_DIR_NAME, *LEGACY_WORKSPACE_DIR_NAMES, ".auto-scan"}:
        return Path(workspace).parent.name
    return base


def is_workspace(workspace: str) -> bool:
    return (Path(workspace) / "config" / "common.json").exists()


def make_slug(name: str) -> str:
    slug = "".join(ch if ch.isalnum() else "-" for ch in str(name).strip().lower())
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-")
    return slug or "project"


def unique_slug(registry: dict, base_slug: str, exclude_id: Optional[str] = None) -> str:
    slug = base_slug
    counter = 2
    while any(
        project.get("slug") == slug and project.get("id") != exclude_id
        for project in registry.get("projects", [])
    ):
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def migrate_registry(registry: dict) -> None:
    changed = False
    for project in registry.get("projects", []):
        if not project.get("id"):
            project["id"] = new_project_id()
            changed = True
        workspace = Path(str(project.get("workspace", "")))
        if workspace.name in LEGACY_WORKSPACE_DIR_NAMES:
            visible = workspace.parent / WORKSPACE_DIR_NAME
            # A legacy directory may be recreated later by an old launchd job
            # solely for its log file. Treat it as legacy when it no longer has
            # a valid workspace configuration, so the registry still follows
            # the visible control plane.
            if is_workspace(str(visible)) and workspace.resolve() != visible.resolve():
                project["workspace"] = str(visible.resolve())
                changed = True
                workspace = visible
        if not str(project.get("name", "")).strip() and is_workspace(str(workspace)):
            project["name"] = read_display_name(str(workspace))
            changed = True
        if not project.get("slug"):
            project["slug"] = unique_slug(registry, make_slug(project.get("name", "")), project.get("id"))
            changed = True
    if changed:
        save_registry(registry)


def new_project_id() -> str:
    return str(uuid.uuid4())


def find_by_id(registry: dict, project_id: Optional[str]):
    if not project_id:
        return None
    exact = next((project for project in registry["projects"] if project.get("id") == project_id), None)
    if exact:
        return exact
    matches = [project for project in registry["projects"] if project.get("id", "").startswith(project_id)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(project.get("name", "") for project in matches)
        raise RuntimeError(f"Ambiguous project id prefix '{project_id}'. Matches: {names}")
    return None


def find_by_workspace(registry: dict, workspace: str):
    normalized = normalize_workspace(workspace)
    for project in registry.get("projects", []):
        if normalize_workspace(project.get("workspace", "")) == normalized:
            return project
    return None


def find_by_ref(registry: dict, ref: str):
    value = str(ref or "").strip()
    if not value:
        return None

    by_id = find_by_id(registry, value)
    if by_id:
        return by_id

    slug = value.lower()
    slug_matches = [project for project in registry["projects"] if project.get("slug") == slug]
    if len(slug_matches) == 1:
        return slug_matches[0]
    if len(slug_matches) > 1:
        raise RuntimeError(f"Ambiguous project slug '{value}'.")

    lower = value.lower()
    name_matches = [project for project in registry["projects"] if project.get("name", "").lower() == lower]
    if len(name_matches) == 1:
        return name_matches[0]
    if len(name_matches) > 1:
        raise RuntimeError(f"Ambiguous project name '{value}'.")

    partial_matches = [project for project in registry["projects"] if lower in project.get("name", "").lower()]
    if len(partial_matches) == 1:
        return partial_matches[0]
    if len(partial_matches) > 1:
        names = ", ".join(project.get("name", "") for project in partial_matches)
        raise RuntimeError(f"Ambiguous project '{value}'. Matches: {names}")
    return None


def find_by_slug(registry: dict, slug: str):
    value = str(slug or "").strip().lower()
    if not value:
        return None
    matches = [project for project in registry["projects"] if project.get("slug") == value]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise RuntimeError(f"Ambiguous project slug '{slug}'.")
    return None


def resolve_slug(slug: str) -> dict:
    registry = load_registry()
    project = find_by_slug(registry, slug)
    if not project:
        raise RuntimeError(f"Project slug not found: {slug}")
    return project


def add_project(workspace: str, name: Optional[str] = None) -> dict:
    resolved = normalize_workspace(workspace)
    if not is_workspace(resolved):
        raise RuntimeError(f"No Lumen workspace found at: {resolved}")

    registry = load_registry()
    existing = find_by_workspace(registry, resolved)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    display_name = (str(name).strip() if name and str(name).strip() else read_display_name(resolved))

    if existing:
        existing["name"] = display_name
        existing["slug"] = unique_slug(registry, make_slug(display_name), existing.get("id"))
        existing["updated_at"] = now
        save_registry(registry)
        return existing

    base_slug = make_slug(display_name)
    project = {
        "id": new_project_id(),
        "name": display_name,
        "slug": unique_slug(registry, base_slug),
        "workspace": resolved,
        "created_at": now,
        "updated_at": now,
    }
    registry["projects"].append(project)
    save_registry(registry)
    return project


def remove_project(project_id: str) -> None:
    registry = load_registry()
    project = find_by_id(registry, project_id)
    if not project:
        raise RuntimeError(f"Project not found: {project_id}")
    registry["projects"] = [entry for entry in registry["projects"] if entry.get("id") != project.get("id")]
    save_registry(registry)

    config = load_config()
    if config.get("default_project_id") == project.get("id"):
        config.pop("default_project_id", None)
        save_config(config)


def set_project_slug(project_ref: str, slug: str) -> dict:
    registry = load_registry()
    project = find_by_ref(registry, project_ref)
    if not project:
        raise RuntimeError(f"Project not found: {project_ref}")

    requested = str(slug or "").strip().lower()
    normalized = make_slug(requested)
    if not requested or requested != normalized:
        raise RuntimeError("Slug must use lowercase letters, numbers, and hyphens only.")
    if any(
        entry.get("slug") == normalized and entry.get("id") != project.get("id")
        for entry in registry.get("projects", [])
    ):
        raise RuntimeError(f"Project slug already in use: {normalized}")

    project["slug"] = normalized
    project["updated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    save_registry(registry)
    return project


def resolve_ref(ref: str) -> dict:
    registry = load_registry()
    project = find_by_ref(registry, ref)
    if not project:
        raise RuntimeError(f"Project not found: {ref}")
    return project


def set_default_project(slug: str) -> dict:
    project = resolve_slug(slug)
    config = load_config()
    config["default_project_id"] = project["id"]
    save_config(config)
    return project


def clear_default_project() -> None:
    config = load_config()
    config.pop("default_project_id", None)
    save_config(config)


def get_default_project():
    config = load_config()
    if not config.get("default_project_id"):
        return None
    registry = load_registry()
    return find_by_id(registry, config["default_project_id"])


def usage() -> None:
    sys.stderr.write(
        """Usage:
  projects_registry.py list [--json]
  projects_registry.py list-lines
  projects_registry.py count
  projects_registry.py add <workspace> [--name <name>]
  projects_registry.py get <project-ref> [--workspace-only]
  projects_registry.py resolve <project-ref> [--workspace-only]
  projects_registry.py resolve-slug <slug> [--workspace-only]
  projects_registry.py set-default <slug>
  projects_registry.py clear-default
  projects_registry.py get-default [--workspace-only]
  projects_registry.py remove <project-ref>
  projects_registry.py set-slug <project-ref> --slug <slug>
"""
    )
    raise SystemExit(1)


def parse_args(argv: list[str]):
    positional = []
    flags = {}
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--json":
            flags["json"] = True
        elif arg == "--name":
            flags["name"] = argv[index + 1]
            index += 1
        elif arg == "--slug":
            flags["slug"] = argv[index + 1]
            index += 1
        elif arg == "--workspace-only":
            flags["workspace_only"] = True
        else:
            positional.append(arg)
        index += 1
    return positional, flags


def cmd_list(json_output: bool) -> None:
    registry = load_registry()
    if json_output:
        sys.stdout.write(json.dumps(registry, indent=2) + "\n")
        return
    if not registry.get("projects"):
        sys.stdout.write("No projects registered. Run 'lumen init' or 'lumen register <workspace>'.\n")
        return
    config = load_config()
    sys.stdout.write("NAME                 SLUG                 WORKSPACE\n")
    for project in registry["projects"]:
        marker = "*" if config.get("default_project_id") == project.get("id") else " "
        name = project.get("name", "")
        if len(name) > 20:
            name = name[:17] + "..."
        else:
            name = name.ljust(20)
        slug = str(project.get("slug", "")).ljust(20)
        sys.stdout.write(f"{marker} {name} {slug} {project.get('workspace', '')}\n")
    sys.stdout.write("\n* = default project (set with 'lumen use <slug>')\n")


def cmd_list_lines() -> None:
    registry = load_registry()
    for index, project in enumerate(registry.get("projects", []), start=1):
        sys.stdout.write(
            f"{index}\t{project.get('id', '')}\t{project.get('slug', '')}\t"
            f"{project.get('name', '')}\t{project.get('workspace', '')}\n"
        )


def cmd_count() -> None:
    registry = load_registry()
    sys.stdout.write(f"{len(registry.get('projects', []))}\n")


def output_project(project: dict, workspace_only: bool) -> None:
    if workspace_only:
        sys.stdout.write(f"{project.get('workspace', '')}\n")
    else:
        sys.stdout.write(json.dumps(project) + "\n")


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        usage()
    command = argv[0]
    positional, flags = parse_args(argv[1:])

    try:
        if command == "list":
            cmd_list(bool(flags.get("json")))
        elif command == "list-lines":
            cmd_list_lines()
        elif command == "count":
            cmd_count()
        elif command == "add":
            workspace = positional[0] if positional else None
            if not workspace:
                usage()
            project = add_project(workspace, flags.get("name"))
            sys.stdout.write(json.dumps(project) + "\n")
        elif command in {"get", "resolve"}:
            ref = positional[0] if positional else None
            if not ref:
                usage()
            output_project(resolve_ref(ref), bool(flags.get("workspace_only")))
        elif command == "resolve-slug":
            slug = positional[0] if positional else None
            if not slug:
                usage()
            output_project(resolve_slug(slug), bool(flags.get("workspace_only")))
        elif command == "resolve-workspace":
            workspace = positional[0] if positional else None
            if not workspace:
                usage()
            project = find_by_workspace(load_registry(), workspace)
            if not project:
                raise RuntimeError(f"Project workspace not found: {workspace}")
            output_project(project, bool(flags.get("workspace_only")))
        elif command == "set-default":
            slug = positional[0] if positional else None
            if not slug:
                usage()
            project = set_default_project(slug)
            sys.stdout.write(json.dumps(project) + "\n")
        elif command == "clear-default":
            clear_default_project()
        elif command == "get-default":
            project = get_default_project()
            if not project:
                return 1
            output_project(project, bool(flags.get("workspace_only")))
        elif command == "remove":
            ref = positional[0] if positional else None
            if not ref:
                usage()
            project = resolve_ref(ref)
            remove_project(project["id"])
        elif command == "set-slug":
            ref = positional[0] if positional else None
            slug = flags.get("slug")
            if not ref or not slug:
                usage()
            sys.stdout.write(json.dumps(set_project_slug(ref, slug)) + "\n")
        else:
            usage()
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
