#!/usr/bin/env python3
"""Resolve delivery docs workspace, stories, and repository paths."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

WORKSPACE_DIR_NAME = "lumon"
LEGACY_VISIBLE_WORKSPACE_DIR_NAME = "lumen"
LEGACY_WORKSPACE_DIR_NAME = ".lumen"


@dataclass
class RepoTarget:
    name: str
    path: Path
    worktree_path: Path
    default_branch: str = "master"


@dataclass
class StoryContext:
    docs_dir: Path
    workspace_root: Path
    story_dir: Path
    story_md: Path
    technical_plan: Path
    metadata_path: Path
    metadata: dict[str, Any]
    repos: list[RepoTarget]
    branch_name: str
    delivery_config: dict[str, Any]
    workspace_config: dict[str, Any]


FRONTEND_RUNTIME_PLATFORMS = {"web", "react-native", "ios", "android", "native"}
FRONTEND_PROFILE_MARKERS = ("frontend", "web-", "web_", "react-native", "ios-", "android-")
VERIFICATION_MODES = {"auto", "custom", "skip"}


def normalize_verification_settings(value: Any, *, has_custom_commands: bool = False) -> dict[str, Any]:
    settings = value if isinstance(value, dict) else {}
    mode = str(settings.get("mode") or ("custom" if has_custom_commands else "auto")).strip().casefold()
    if mode not in VERIFICATION_MODES:
        mode = "auto"
    return {
        "mode": mode,
        "compile": settings.get("compile") is not False,
        "tests": settings.get("tests") is not False,
    }


def frontend_repository_names(context: StoryContext) -> set[str]:
    """Return repositories whose configured runtime belongs to the disabled UI scope."""
    config = read_json(workspace_lumen_dir(context.workspace_root) / "config" / "repos.json", {"repositories": []})
    entries = config.get("repositories") if isinstance(config.get("repositories"), list) else []
    by_name = {
        str(item.get("name", "")).strip(): item
        for item in entries
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    }
    names: set[str] = set()
    for repo in context.repos:
        entry = by_name.get(repo.name, {})
        runtime = entry.get("runtime") if isinstance(entry, dict) else None
        platform = str(runtime.get("platform", "")).strip().casefold() if isinstance(runtime, dict) else ""
        profile = str(entry.get("runtime_profile", "")).strip().casefold() if isinstance(entry, dict) else ""
        if platform in FRONTEND_RUNTIME_PLATFORMS or any(marker in profile for marker in FRONTEND_PROFILE_MARKERS):
            names.add(repo.name)
    return names


def frontend_delivery_disabled_reasons(context: StoryContext) -> list[str]:
    """Return the explicit reasons this delivery belongs to the disabled UI scope."""
    reasons: list[str] = []
    try:
        plan_text = context.technical_plan.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        plan_text = ""
    if re.search(r"(?mi)^#{1,6}\s+Visual Delivery Contract\b", plan_text):
        reasons.append("technical-plan.md contains a Visual Delivery Contract")

    config = read_json(workspace_lumen_dir(context.workspace_root) / "config" / "repos.json", {"repositories": []})
    entries = config.get("repositories") if isinstance(config.get("repositories"), list) else []
    by_name = {
        str(item.get("name", "")).strip(): item
        for item in entries
        if isinstance(item, dict) and str(item.get("name", "")).strip()
    }
    for repo in context.repos:
        entry = by_name.get(repo.name, {})
        runtime = entry.get("runtime") if isinstance(entry, dict) else None
        platform = str(runtime.get("platform", "")).strip().casefold() if isinstance(runtime, dict) else ""
        profile = str(entry.get("runtime_profile", "")).strip().casefold() if isinstance(entry, dict) else ""
        if platform in FRONTEND_RUNTIME_PLATFORMS or any(marker in profile for marker in FRONTEND_PROFILE_MARKERS):
            detail = platform or profile or "frontend runtime"
            reasons.append(f"repository '{repo.name}' uses {detail}")
    return reasons


def repository_delivery_disabled_reasons(context: StoryContext) -> list[str]:
    config = read_json(workspace_lumen_dir(context.workspace_root) / "config" / "repos.json", {"repositories": []})
    entries = config.get("repositories") if isinstance(config.get("repositories"), list) else []
    by_name = {str(item.get("name", "")).strip(): item for item in entries if isinstance(item, dict)}
    reasons = []
    for repo in context.repos:
        entry = by_name.get(repo.name, {})
        automation = entry.get("automation") if isinstance(entry.get("automation"), dict) else {}
        delivery = automation.get("delivery") if isinstance(automation.get("delivery"), dict) else {}
        if delivery.get("enabled") is False:
            reasons.append(f"repository '{repo.name}' is not authorized for Auto Delivery")
    return reasons


def read_json(path: Path, default: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not path.is_file():
        return default or {}
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else (default or {})


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def workspace_lumen_dir(workspace_root: Path) -> Path:
    for name in (WORKSPACE_DIR_NAME, LEGACY_VISIBLE_WORKSPACE_DIR_NAME, LEGACY_WORKSPACE_DIR_NAME):
        candidate = workspace_root / name
        if candidate.exists():
            return candidate
    return workspace_root / WORKSPACE_DIR_NAME


def delivery_results_dir(workspace_root: Path) -> Path:
    return workspace_lumen_dir(workspace_root) / "results"


def delivery_result_path(workspace_root: Path) -> Path:
    return delivery_results_dir(workspace_root) / "delivery-result.json"


def delivery_started_path(workspace_root: Path) -> Path:
    return delivery_results_dir(workspace_root) / "delivery-started.json"


def delivery_logs_dir(workspace_root: Path) -> Path:
    return workspace_lumen_dir(workspace_root) / "logs" / "delivery"


def delivery_history_dir(workspace_root: Path) -> Path:
    return workspace_lumen_dir(workspace_root) / "history" / "delivery"


def delivery_config_dir(workspace_root: Path) -> Path:
    return workspace_lumen_dir(workspace_root) / "config"


def delivery_worktrees_dir(workspace_root: Path) -> Path:
    return workspace_lumen_dir(workspace_root) / "worktrees"


def workspace_config_path(workspace_root: Path) -> Path:
    return delivery_config_dir(workspace_root) / "workspace.json"


def docs_lumen_config_dir(docs_dir: Path) -> Path:
    return workspace_lumen_dir(docs_dir) / "config"


def legacy_parent_lumen_config_dir(docs_dir: Path) -> Path:
    return workspace_lumen_dir(docs_dir.parent) / "config"


def delivery_config_path(workspace_root: Path) -> Path:
    return delivery_config_dir(workspace_root) / "delivery.json"


def worktree_path_for_repo(workspace_root: Path, repo_name: str) -> Path:
    return delivery_worktrees_dir(workspace_root) / repo_name


def story_worktree_key(metadata: dict[str, Any], story_dir: Path) -> str:
    """Return the stable directory segment for one delivery story."""
    jira_key = str(metadata.get("jiraKey", "")).strip()
    return jira_key if jira_key else slugify(story_dir.name)


def story_worktrees_dir(
    workspace_root: Path,
    metadata: dict[str, Any],
    story_dir: Path,
) -> Path:
    return delivery_worktrees_dir(workspace_root) / story_worktree_key(metadata, story_dir)


def ensure_workspace_lumen_dirs(workspace_root: Path) -> None:
    delivery_config_dir(workspace_root).mkdir(parents=True, exist_ok=True)
    delivery_worktrees_dir(workspace_root).mkdir(parents=True, exist_ok=True)
    delivery_results_dir(workspace_root).mkdir(parents=True, exist_ok=True)
    delivery_logs_dir(workspace_root).mkdir(parents=True, exist_ok=True)
    delivery_history_dir(workspace_root).mkdir(parents=True, exist_ok=True)


def legacy_docs_config_dir(docs_dir: Path) -> Path:
    return docs_lumen_config_dir(docs_dir)


def repos_container_dir(workspace_root: Path, workspace_config: dict[str, Any]) -> Path:
    repos_dir_name = str(workspace_config.get("repos_dir", "repos")).strip() or "repos"
    return workspace_root / repos_dir_name


def load_workspace_config(docs_dir: Path) -> tuple[Path, dict[str, Any]]:
    docs_dir = resolve_docs_dir(docs_dir)

    nested_path = docs_lumen_config_dir(docs_dir) / "workspace.json"
    if nested_path.is_file():
        workspace_config = read_json(nested_path)
        workspace_root = workspace_root_for_docs(docs_dir, workspace_config)
        root_config = read_json(workspace_config_path(workspace_root))
        merged = dict(root_config)
        merged.update(workspace_config)
        return workspace_root, merged

    parent_path = legacy_parent_lumen_config_dir(docs_dir) / "workspace.json"
    if parent_path.is_file():
        workspace_config = read_json(parent_path)
        workspace_root = workspace_root_for_docs(docs_dir, workspace_config)
        root_config = read_json(workspace_config_path(workspace_root))
        merged = dict(root_config)
        merged.update(workspace_config)
        return workspace_root, merged

    legacy_path = legacy_docs_config_dir(docs_dir) / "workspace.json"
    if legacy_path.is_file() and legacy_path != nested_path:
        workspace_config = read_json(legacy_path)
        workspace_root = workspace_root_for_docs(docs_dir, workspace_config)
        return workspace_root, workspace_config

    workspace_root = docs_dir.resolve()
    return workspace_root, {
        "schema_version": "1.0",
        "layout": "nested",
        "workspace_root": str(workspace_root),
        "docs_repo": ".",
        "repos_dir": "repos",
        "repositories": [],
    }


def load_delivery_config(docs_dir: Path, workspace_root: Path) -> dict[str, Any]:
    primary = delivery_config_path(workspace_root)
    if primary.is_file():
        return read_json(primary)
    legacy = legacy_docs_config_dir(docs_dir) / "delivery.json"
    if legacy.is_file():
        return read_json(legacy)
    return {}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def resolve_docs_dir(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    if (candidate / "stories").is_dir() or (candidate / "AGENTS.md").is_file():
        return candidate
    raise FileNotFoundError(f"Not a delivery docs repository: {candidate}")


def workspace_root_for_docs(docs_dir: Path, workspace_config: dict[str, Any]) -> Path:
    configured = str(workspace_config.get("workspace_root", "")).strip()
    if configured in {".", "./"}:
        return docs_dir.resolve()
    if configured:
        return Path(configured).expanduser().resolve()
    layout = str(workspace_config.get("layout", "nested")).strip().lower()
    if layout == "sibling":
        return docs_dir.parent.resolve()
    return docs_dir.resolve()


def discover_git_repos(workspace_root: Path, workspace_config: Optional[dict[str, Any]] = None) -> dict[str, Path]:
    config = workspace_config or {}
    layout = str(config.get("layout", "nested")).strip().lower()
    repos: dict[str, Path] = {}
    if not workspace_root.is_dir():
        return repos

    skip_names = {
        "lumon",
        "lumen",
        ".lumen",
        ".git",
        "stories",
        "standards",
        "templates",
        "notifications",
        "repos",
    }

    if layout != "sibling":
        container = repos_container_dir(workspace_root, config)
        if container.is_dir():
            for child in sorted(container.iterdir()):
                if child.is_dir() and (child / ".git").exists():
                    repos[child.name] = child.resolve()
            return repos

    for child in sorted(workspace_root.iterdir()):
        if not child.is_dir() or child.name in skip_names or child.name.startswith("."):
            continue
        if (child / ".git").exists():
            repos[child.name] = child.resolve()
    return repos


def repo_path_for_name(
    name: str,
    workspace_root: Path,
    workspace_config: dict[str, Any],
    discovered: dict[str, Path],
) -> Optional[Path]:
    configured = workspace_config.get("repositories") or []
    if isinstance(configured, list):
        for item in configured:
            if not isinstance(item, dict):
                continue
            if str(item.get("name", "")).strip() != name:
                continue
            rel = str(item.get("path", name)).strip() or name
            candidate = (workspace_root / rel).resolve()
            if candidate.is_dir():
                return candidate
    if name in discovered:
        return discovered[name]
    candidate = (workspace_root / name).resolve()
    if candidate.is_dir():
        return candidate
    return None


def find_story_dir(docs_dir: Path, story_ref: str) -> Path:
    stories_dir = docs_dir / "stories"
    if not stories_dir.is_dir():
        raise FileNotFoundError(f"Stories directory not found: {stories_dir}")

    ref = story_ref.strip()
    if not ref:
        candidates = sorted(
            [item for item in stories_dir.iterdir() if item.is_dir()],
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise FileNotFoundError(f"No stories found under {stories_dir}")
        return candidates[0].resolve()

    direct = stories_dir / ref
    if direct.is_dir():
        return direct.resolve()

    upper_ref = ref.upper()
    for item in stories_dir.iterdir():
        if not item.is_dir():
            continue
        if item.name == ref or item.name.upper() == upper_ref:
            return item.resolve()
        if item.name.upper().startswith(f"{upper_ref}-"):
            return item.resolve()

    needle = slugify(ref)
    for item in stories_dir.iterdir():
        if item.is_dir() and slugify(item.name) == needle:
            return item.resolve()

    raise FileNotFoundError(f"Story not found for reference: {story_ref}")


def branch_name_for_story(metadata: dict[str, Any], story_dir: Path) -> str:
    jira_key = str(metadata.get("jiraKey", "")).strip()
    slug = story_dir.name
    if jira_key:
        if slug.upper().startswith(f"{jira_key.upper()}-"):
            short_slug = slug[len(jira_key) + 1 :]
        else:
            short_slug = slug
        return f"feature/{jira_key}-{slugify(short_slug) or 'delivery'}"
    return f"feature/{slugify(slug) or 'delivery'}"


def repos_registry(workspace_root: Path) -> dict[str, dict[str, Any]]:
    config = read_json(delivery_config_dir(workspace_root) / "repos.json")
    registry: dict[str, dict[str, Any]] = {}
    for item in config.get("repositories") or []:
        if isinstance(item, dict):
            name = str(item.get("name", "")).strip()
            if name:
                registry[name] = item
    return registry


def resolve_repo_default_branch(repo_name: str, repo_path: Path, workspace_root: Path) -> str:
    configured = str(repos_registry(workspace_root).get(repo_name, {}).get("default_branch", "")).strip()
    if configured:
        return configured
    return default_branch_for_repo(repo_path)


def default_branch_for_repo(repo_path: Path) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_path), "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        value = completed.stdout.strip()
        if value.startswith("origin/"):
            return value.split("/", 1)[1]
    for candidate in ("main", "master", "develop"):
        completed = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--verify", candidate],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0:
            return candidate
    return "master"


def ensure_feature_worktree(
    repo: RepoTarget,
    branch_name: str,
    workspace_root: Path,
    metadata: dict[str, Any],
    story_dir: Path,
) -> tuple[bool, str]:
    worktrees_root = story_worktrees_dir(workspace_root, metadata, story_dir) / repo.name
    worktrees_root.parent.mkdir(parents=True, exist_ok=True)
    repo.worktree_path = worktrees_root.resolve()

    if worktrees_root.is_dir() and (worktrees_root / ".git").exists():
        completed = subprocess.run(
            ["git", "-C", str(worktrees_root), "branch", "--show-current"],
            check=False,
            capture_output=True,
            text=True,
        )
        current_branch = completed.stdout.strip()
        if completed.returncode != 0:
            return False, completed.stderr or completed.stdout or "could not inspect worktree branch"
        if current_branch != branch_name:
            status = subprocess.run(
                ["git", "-C", str(worktrees_root), "status", "--porcelain"],
                check=False,
                capture_output=True,
                text=True,
            )
            if status.stdout.strip():
                return False, (
                    f"Existing worktree is on {current_branch} with local changes; "
                    f"expected {branch_name}"
                )
            return False, f"Existing worktree is on {current_branch}; expected {branch_name}"
        repo.worktree_path = worktrees_root.resolve()
        base_branch = resolve_repo_default_branch(repo.name, repo.path, workspace_root)
        repo.default_branch = base_branch
        if str(metadata.get("baseCommit") or metadata.get("base_commit") or "").strip():
            return True, "reused story worktree at the pinned base commit"
        fetch = subprocess.run(
            ["git", "-C", str(repo.path), "fetch", "origin", base_branch],
            check=False,
            capture_output=True,
            text=True,
        )
        if fetch.returncode != 0:
            return False, fetch.stderr or fetch.stdout or "failed to fetch the latest base branch"
        update = subprocess.run(
            ["git", "-C", str(worktrees_root), "merge", "--ff-only", f"origin/{base_branch}"],
            check=False,
            capture_output=True,
            text=True,
        )
        if update.returncode != 0:
            return False, (
                update.stderr
                or update.stdout
                or f"existing worktree could not fast-forward from origin/{base_branch}"
            )
        return True, f"reused story worktree and synced origin/{base_branch}"

    if worktrees_root.exists():
        return False, f"Worktree path exists but is not a git worktree: {worktrees_root}"

    base_branch = resolve_repo_default_branch(repo.name, repo.path, workspace_root)
    repo.default_branch = base_branch
    requested_base = str(metadata.get("baseCommit") or metadata.get("base_commit") or "").strip()
    if requested_base:
        base_ref = requested_base
    else:
        fetch = subprocess.run(
            ["git", "-C", str(repo.path), "fetch", "origin", base_branch],
            check=False,
            capture_output=True,
            text=True,
        )
        if fetch.returncode != 0:
            return False, fetch.stderr or fetch.stdout or "failed to fetch base branch"
        base_ref = f"origin/{base_branch}"
    verify_base = subprocess.run(
        ["git", "-C", str(repo.path), "rev-parse", "--verify", f"{base_ref}^{{commit}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if verify_base.returncode != 0:
        return False, verify_base.stderr or verify_base.stdout or f"missing base commit {base_ref}"

    create = subprocess.run(
        [
            "git",
            "-C",
            str(repo.path),
            "worktree",
            "add",
            "-B",
            branch_name,
            str(worktrees_root),
            base_ref,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if create.returncode != 0:
        return False, create.stderr or create.stdout or "worktree add failed"
    return True, f"created worktree from {base_ref}"


def validate_story_gates(
    metadata: dict[str, Any],
    story_md: Path,
    technical_plan: Path,
) -> list[str]:
    errors: list[str] = []
    if metadata.get("businessStatus") != "ready":
        errors.append(
            f"businessStatus must be 'ready' (current: {metadata.get('businessStatus', 'missing')})"
        )
    if metadata.get("technicalStatus") != "approved":
        errors.append(
            f"technicalStatus must be 'approved' (current: {metadata.get('technicalStatus', 'missing')})"
        )
    if not story_md.is_file():
        errors.append(f"story.md not found: {story_md}")
    elif story_md.stat().st_size < 80:
        errors.append("story.md is too short to be business-ready")
    if not technical_plan.is_file():
        errors.append(f"technical-plan.md not found: {technical_plan}")
    elif technical_plan.stat().st_size < 80:
        errors.append("technical-plan.md is too short to be implementation-ready")
    return errors


def load_story_context(docs_dir: Path, story_ref: str = "", validate_gates: bool = True) -> StoryContext:
    docs_dir = resolve_docs_dir(docs_dir)
    workspace_root, workspace_config = load_workspace_config(docs_dir)
    delivery_config = load_delivery_config(docs_dir, workspace_root)
    story_dir = find_story_dir(docs_dir, story_ref)
    metadata_path = story_dir / "metadata.json"
    metadata = read_json(metadata_path)
    story_md = story_dir / "story.md"
    technical_plan = story_dir / str(metadata.get("technicalPlanFile") or "technical-plan.md")

    if validate_gates:
        errors = validate_story_gates(metadata, story_md, technical_plan)
        if errors:
            raise ValueError("; ".join(errors))

    linked = metadata.get("linkedRepos") or []
    if not isinstance(linked, list) or not linked:
        raise ValueError("metadata.json.linkedRepos must list at least one repository")

    discovered = discover_git_repos(workspace_root, workspace_config)
    repos: list[RepoTarget] = []
    for name in linked:
        repo_name = str(name).strip()
        if not repo_name:
            continue
        repo_path = repo_path_for_name(repo_name, workspace_root, workspace_config, discovered)
        if repo_path is None:
            raise FileNotFoundError(
                f"Repository '{repo_name}' not found under workspace root {workspace_root}"
            )
        repos.append(
            RepoTarget(
                name=repo_name,
                path=repo_path,
                worktree_path=story_worktrees_dir(workspace_root, metadata, story_dir) / repo_name,
                default_branch=resolve_repo_default_branch(repo_name, repo_path, workspace_root),
            )
        )

    branch_name = branch_name_for_story(metadata, story_dir)
    return StoryContext(
        docs_dir=docs_dir,
        workspace_root=workspace_root,
        story_dir=story_dir,
        story_md=story_md,
        technical_plan=technical_plan,
        metadata_path=metadata_path,
        metadata=metadata,
        repos=repos,
        branch_name=branch_name,
        delivery_config=delivery_config,
        workspace_config=workspace_config,
    )


def prepare_story_for_delivery(context: StoryContext) -> list[str]:
    messages: list[str] = []
    ensure_workspace_lumen_dirs(context.workspace_root)

    for repo in context.repos:
        ok, detail = ensure_feature_worktree(
            repo,
            context.branch_name,
            context.workspace_root,
            context.metadata,
            context.story_dir,
        )
        if not ok:
            raise RuntimeError(f"Failed to prepare worktree for {repo.name}: {detail}")
        messages.append(f"{repo.name}: {detail} at {repo.worktree_path}")

    metadata = dict(context.metadata)
    metadata["deliveryStatus"] = "in_progress"
    metadata["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    metadata["deliveryBranch"] = context.branch_name
    write_json(context.metadata_path, metadata)
    context.metadata = metadata
    messages.append(f"Updated deliveryStatus to in_progress for {context.story_dir.name}")
    return messages
