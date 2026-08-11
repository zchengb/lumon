#!/usr/bin/env python3
"""Import an existing Jira Story into a Lumen delivery workspace."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from delivery_workspace import workspace_lumen_dir
from jira_sync import parse_twg_json, run_twg, site_args, twg_ready, workspace_jira_config


KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_]*-\d+$")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:72] or "imported-story"


def unwrap(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict) and "data" in payload:
        payload = payload["data"]
    if isinstance(payload, list):
        payload = next((item for item in payload if isinstance(item, dict)), {})
    return payload if isinstance(payload, dict) else {}


def field(item: dict[str, Any], name: str) -> Any:
    for source in (item, item.get("fields")):
        if not isinstance(source, dict):
            continue
        for key, value in source.items():
            if key.lower() == name.lower():
                return value
    return ""


def plain_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(part for item in value if (part := plain_text(item)))
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"].strip()
        for key in ("content", "value", "name"):
            if key in value:
                text = plain_text(value[key])
                if text:
                    return text
    return ""


def jira_config(docs_dir: Path) -> dict[str, Any]:
    return workspace_jira_config(docs_dir)


def jira_url(item: dict[str, Any], key: str, config: dict[str, Any]) -> str:
    for name in ("jiraUrl", "browseUrl", "url"):
        value = str(field(item, name) or "").strip()
        if value.startswith(("https://", "http://")) and "/browse/" in value:
            return value
    site = str(config.get("site") or "").strip().rstrip("/")
    if not site:
        return ""
    if not site.startswith(("https://", "http://")):
        site = f"https://{site if '.' in site else site + '.atlassian.net'}"
    return f"{site}/browse/{key}"


def find_story(docs_dir: Path, jira_key: str) -> Path | None:
    matches = [
        path.parent
        for path in (docs_dir / "stories").glob("*/metadata.json")
        if str(load_json(path).get("jiraKey") or "").upper() == jira_key.upper()
    ]
    if len(matches) > 1:
        raise ValueError(f"Multiple workspace Stories are linked to {jira_key}: {', '.join(str(path) for path in matches)}")
    return matches[0] if matches else None


def story_markdown(key: str, title: str, url: str, description: str) -> str:
    link = f"[{key}]({url})" if url else key
    background = description or "Imported from Jira. Review and refine the business context before marking this Story ready."
    return f"""---
title: {json.dumps(title, ensure_ascii=False)}
jiraUrl: {json.dumps(url, ensure_ascii=False)}
---

# {key} {title}

> Imported from Jira {link}. Review this content before using the Business Loop to mark the Story ready.

## Background

{background}

## Acceptance Criteria

- Review the Jira description and convert confirmed outcomes into Given/When/Then criteria.

## Business Rules

- TBD

## Clarifications

| Question | Answer |
|---|---|
| What remains unclear from the imported Jira Story? | TBD |

## Out of Scope

- TBD
"""


def import_story(docs_dir: Path, jira_key: str) -> Path:
    docs_dir = docs_dir.expanduser().resolve()
    jira_key = jira_key.upper()
    if not KEY.fullmatch(jira_key):
        raise ValueError("Jira key must look like PROJECT-123")
    if not (docs_dir / "stories").is_dir():
        raise ValueError(f"No Lumen delivery workspace found at: {docs_dir}")
    ready, reason = twg_ready()
    if not ready:
        raise RuntimeError(reason)
    config = jira_config(docs_dir)
    code, output = run_twg(["jira", "workitem", "get", jira_key, "-o", "json", *site_args(config)])
    if code != 0:
        raise RuntimeError((output or f"Unable to read Jira {jira_key}").strip()[-1000:])
    payload = parse_twg_json(output)
    item = unwrap(payload)
    key = str(field(item, "key") or jira_key).upper()
    if key != jira_key:
        raise RuntimeError(f"Jira returned {key}, expected {jira_key}")
    title = plain_text(field(item, "summary")) or key
    description = plain_text(field(item, "description"))
    issue_type = plain_text(field(item, "issuetype")) or "Story"
    source_updated_at = str(field(item, "updated") or "").strip()
    url = jira_url(item, key, config)
    story_dir = find_story(docs_dir, key)
    if not story_dir:
        story_dir = docs_dir / "stories" / f"{key}-{slugify(title)}"
        if story_dir.exists():
            raise ValueError(f"Refusing to overwrite existing directory: {story_dir}")
    metadata_path = story_dir / "metadata.json"
    story_path = story_dir / "story.md"
    previous = load_json(metadata_path)
    source_hash = digest(json.dumps(item, ensure_ascii=False, sort_keys=True))
    source_changed = bool(previous) and previous.get("jiraSnapshotHash") != source_hash
    story_dir.mkdir(parents=True, exist_ok=True)
    story = story_markdown(key, title, url, description)
    if not previous:
        story_path.write_text(story, encoding="utf-8")
    snapshot_path = workspace_lumen_dir(docs_dir) / "context" / story_dir.name / "jira-import.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps({"imported_at": now(), "jira_key": key, "workitem": item}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    metadata = {
        **previous,
        "storyId": key,
        "title": previous.get("title") or title,
        "jiraKey": key,
        "jiraUrl": url,
        "jiraIssueType": issue_type,
        "jiraPublishedAt": previous.get("jiraPublishedAt") or now(),
        "jiraImportedAt": now(),
        "jiraSourceUpdatedAt": source_updated_at,
        "jiraSnapshotFile": str(snapshot_path.relative_to(docs_dir)),
        "jiraSnapshotHash": source_hash if not source_changed else previous.get("jiraSnapshotHash", ""),
        "jiraLatestSnapshotHash": source_hash,
        "jiraStoryHash": previous.get("jiraStoryHash") or digest(story),
        "jiraSyncStatus": "imported" if not previous else "changed" if source_changed else "synced",
        # A newer Jira copy invalidates the plan, but does not silently revoke the
        # locally confirmed business contract. The Technical Loop asks which source wins.
        "businessStatus": "draft" if not previous else previous.get("businessStatus") or "draft",
        "technicalStatus": "draft" if not previous or source_changed else previous.get("technicalStatus") or "draft",
        "deliveryStatus": "not_started" if not previous else previous.get("deliveryStatus") or "not_started",
        "linkedRepos": previous.get("linkedRepos") or [],
        "updatedAt": now(),
        "technicalPlanFile": previous.get("technicalPlanFile") or "technical-plan.md",
        "logs": previous.get("logs") or [],
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    plan = story_dir / "technical-plan.md"
    template = docs_dir / "templates" / "technical-plan.md"
    if not plan.exists() and template.is_file():
        plan.write_text(template.read_text(encoding="utf-8").replace("<Story Title>", title), encoding="utf-8")
    return story_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docs_dir")
    parser.add_argument("jira_key")
    args = parser.parse_args()
    try:
        story_dir = import_story(Path(args.docs_dir), args.jira_key)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=__import__("sys").stderr)
        return 1
    metadata = load_json(story_dir / "metadata.json")
    print(json.dumps({
        "story": str(story_dir),
        "jira_key": str(metadata.get("jiraKey") or args.jira_key.upper()),
        "jira_sync_status": str(metadata.get("jiraSyncStatus") or ""),
        "business_status": str(metadata.get("businessStatus") or ""),
        "next": "business_loop",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
