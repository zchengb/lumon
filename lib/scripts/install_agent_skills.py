#!/usr/bin/env python3
"""Install Lumen's project-scoped workflow skill adapters safely."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


MANAGED = "<!-- Lumen managed: agent-skill -->"
SKILLS = ("lumen-business-loop", "lumen-technical-loop", "lumen-jira-story-import")


def project_root(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if (path / "config" / "common.json").is_file():
        return path.parent
    for name in ("lumon", "lumen", ".lumen"):
        if (path / name / "config" / "common.json").is_file():
            return path
    raise ValueError(f"No Lumen workspace found at: {path}")


def managed(path: Path) -> bool:
    return path.is_file() and MANAGED in path.read_text(encoding="utf-8", errors="ignore")


def write(path: Path, text: str, force: bool) -> None:
    if path.exists() and not managed(path) and not force:
        raise FileExistsError(f"Refusing to overwrite unmanaged file: {path} (re-run with --force)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def remove_managed(path: Path) -> None:
    if managed(path):
        path.unlink()


def copy_skill(source: Path, target: Path, force: bool) -> None:
    existing = target / "SKILL.md"
    if existing.exists() and not managed(existing) and not force:
        raise FileExistsError(f"Refusing to overwrite unmanaged skill: {target} (re-run with --force)")
    for item in source.rglob("*"):
        if item.is_file():
            write(target / item.relative_to(source), item.read_text(encoding="utf-8"), force)


def adapter(skill: str, platform: str, canonical: Path) -> tuple[Path, str]:
    if platform == "claude":
        return Path(".claude") / "skills" / skill / "SKILL.md", f"---\nname: {skill}\ndescription: Explicit Lumen workflow; invoke only with /{skill}.\n---\n\n{MANAGED}\n\nRead and follow `{canonical}/SKILL.md` and its references. Do not start this workflow implicitly.\n"
    if platform == "codex":
        return Path(".agents") / "skills" / skill / "SKILL.md", f"---\nname: {skill}\ndescription: Explicit Lumen workflow; invoke only with ${skill}.\n---\n\n{MANAGED}\n\nRead and follow `{canonical}/SKILL.md` and its references. Do not start this workflow implicitly.\n"
    return Path(".cursor") / "commands" / f"{skill}.md", f"{MANAGED}\n\n# /{skill}\n\nRead and follow `{canonical}/SKILL.md` and its references. This is an explicitly invoked workflow; do not start it implicitly.\n"


def install(workspace: str, platforms: list[str], force: bool) -> None:
    root = project_root(workspace)
    runtime_dir = next(
        (root / name for name in ("lumon", "lumen", ".lumen") if (root / name / "config" / "common.json").is_file()),
        root / "lumon",
    )
    source_root = Path(__file__).resolve().parents[1] / "templates" / "agent-skills"
    selected = ("claude", "codex") if "all" in platforms else tuple(dict.fromkeys(platforms))
    for skill in SKILLS:
        canonical = runtime_dir / "skills" / skill
        copy_skill(source_root / skill, canonical, force)
        for platform in selected:
            relative, text = adapter(skill, platform, runtime_dir.relative_to(root) / "skills" / skill)
            write(root / relative, text, force)
        if "all" in platforms:
            remove_managed(root / ".cursor" / "commands" / f"{skill}.md")
    if "codex" in selected:
        write(root / ".agents" / "openai.yaml", f"{MANAGED}\npolicy:\n  allow_implicit_invocation: false\n", force)
    print(f"Installed Lumen skills for {', '.join(selected)} in {root}; Cursor uses the shared .agents skills.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Lumen workflow skills into a project.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--platform", action="append", required=True, choices=("claude", "cursor", "codex", "all"))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        install(args.workspace, args.platform, args.force)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
