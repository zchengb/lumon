#!/usr/bin/env python3
"""Run one bounded Auto Patch cycle."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

LIB_DIR = Path(__file__).resolve().parent.parent
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from capture_patch_context import capture
from compose_patch_prompt import compose
from patch_jira import add_comment, blocked_comment, skipped_comment, transition_issue
from patch_runtime import (
    comments,
    blocked_statuses,
    comment_fingerprint,
    empty_progress,
    get_workitem,
    has_external_reply,
    history_dir,
    jira_fields,
    jira_key,
    jira_status,
    jira_summary,
    load_delivery_config,
    load_registry,
    logs_dir,
    new_progress,
    patch_config,
    prepare_worktree,
    progress_path,
    query_candidates,
    read_json,
    remove_worktrees,
    repo_registry,
    result_path,
    results_dir,
    save_progress,
    save_registry,
    set_phase,
    utc_now,
    workspace_lumen_dir,
    write_json,
)


def load_env(workspace: Path) -> None:
    for path in (workspace / ".env.common", workspace / ".env.local", workspace_lumen_dir(workspace) / ".env.common", workspace_lumen_dir(workspace) / ".env.local"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def lock_path(workspace: Path) -> Path:
    return workspace_lumen_dir(workspace) / "locks" / "patch-run"


def patch_model(workspace: Path) -> str:
    common = read_json(workspace_lumen_dir(workspace) / "config" / "common.json")
    execution = common.get("execution", {}) if isinstance(common, dict) else {}
    if not isinstance(execution, dict) or not execution.get("model"):
        execution = load_delivery_config(workspace).get("execution", {})
    execution = execution if isinstance(execution, dict) else {}
    return str(execution.get("model") or execution.get("patch_model") or os.environ.get("CURSOR_AGENT_MODEL") or "cursor-grok-4.5-medium").strip()


REPOSITORY_STOPWORDS = {
    "after", "again", "auto", "before", "cannot", "change", "check", "could", "current", "data",
    "ensure", "error", "existing", "fix", "from", "handle", "issue", "make", "need", "new", "old",
    "patch", "please", "request", "response", "should", "support", "task", "this", "that", "their",
    "there", "these", "they", "update", "value", "when", "where", "which", "with", "would",
    "jira", "lumen", "repository", "repositories", "registered", "context", "related", "workitem",
    "text", "paragraph", "heading", "content", "type", "marks", "strong", "code", "version",
    "public", "optional", "return", "fromfilterjson", "readstringlist", "created", "automatically",
}
REPOSITORY_SEARCH_GLOBS = (
    "!.git/**", "!node_modules/**", "!vendor/**", "!build/**", "!dist/**", "!target/**", "!coverage/**",
    "!out/**", "!tmp/**", "!*.lock", "!*.map", "!*.min.js", "!*.png", "!*.jpg", "!*.jpeg", "!*.gif",
    "!*.zip",
)


def repository_enabled(repo: dict[str, Any]) -> bool:
    automation = repo.get("automation") if isinstance(repo.get("automation"), dict) else {}
    patch = automation.get("patch") if isinstance(automation.get("patch"), dict) else {}
    return bool(patch.get("enabled", True))


def _jira_context_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(_jira_context_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_jira_context_text(item) for item in value)
    return ""


def _repository_keywords(item: dict[str, Any], context: dict[str, Any] | None = None) -> list[str]:
    fields = jira_fields(item)
    source_values: list[tuple[str, int]] = [(jira_summary(item), 3)]
    for name in ("description", "labels", "components", "environment", "parent", "issuelinks", "subtasks"):
        if name in fields:
            source_values.append((_jira_context_text(fields.get(name)), 2 if name in {"labels", "components"} else 1))
    if isinstance(context, dict):
        workitems = [context.get("workitem"), *(context.get("related_workitems") or [])]
        for related in workitems:
            if not isinstance(related, dict):
                continue
            related_fields = jira_fields(related)
            source_values.append((jira_summary(related), 1))
            source_values.append((_jira_context_text(related_fields.get("description")), 1))
            source_values.append((_jira_context_text(related_fields.get("labels")), 1))

    weights: dict[str, int] = {}
    for text, weight in source_values:
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", text):
            normalized = token.strip("-_").casefold()
            if not normalized or normalized in REPOSITORY_STOPWORDS or normalized.isdigit():
                continue
            if re.fullmatch(r"[a-z]+-\d+", normalized):
                continue
            if len(normalized) < 4 and not token.isupper():
                continue
            weights[normalized] = weights.get(normalized, 0) + weight
    return sorted(weights, key=lambda token: (-weights[token], -len(token), token))[:8]


def _repository_name_matches(value: Any, eligible: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = _jira_context_text(value)
    matches: list[dict[str, Any]] = []
    for repo in eligible:
        name = str(repo.get("name") or "").strip()
        if name and re.search(rf"(?<![A-Za-z0-9_-]){re.escape(name)}(?![A-Za-z0-9_-])", text, re.IGNORECASE):
            matches.append(repo)
    return matches


def _authoritative_repository_matches(item: dict[str, Any], eligible: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Read repository labels/fields and explicit `Repository:` lines only.

    A plain mention in a suggestion or code example is deliberately not an
    explicit selection; those mentions are weak evidence for the scorer.
    """
    fields = jira_fields(item)
    matches: list[dict[str, Any]] = []

    def add(values: list[dict[str, Any]]) -> None:
        for repo in values:
            if repo not in matches:
                matches.append(repo)

    labels = fields.get("labels")
    if isinstance(labels, list):
        for label in labels:
            add(_repository_name_matches(str(label), eligible))

    for field_name, value in fields.items():
        lowered = str(field_name).casefold()
        if "repo" in lowered or lowered in {"labels", "components"}:
            add(_repository_name_matches(value, eligible))

    for value in (fields.get("description"), fields.get("environment")):
        text = _jira_context_text(value)
        for match in re.finditer(r"(?im)\b(?:repositories?|repos?)\s*:\s*([^\n]+)", text):
            add(_repository_name_matches(match.group(1), eligible))
    return matches


def _jira_keys(value: Any) -> list[str]:
    return sorted(set(re.findall(r"\b[A-Z][A-Z0-9_]+-\d+\b", json.dumps(value, ensure_ascii=False))))


def _repository_history(repo: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    path = Path(str(repo.get("path") or "")).expanduser()
    if not path.is_dir() or not (path / ".git").exists() or not keys:
        return {"jira_keys": [], "subjects": []}
    search_keys = keys[:10]
    args = ["git", "-C", str(path), "log", "--all", "-n", "50", "--format=%s", "--regexp-ignore-case"]
    for key in search_keys:
        args.extend(["--grep", key])
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {"jira_keys": [], "subjects": []}
    subjects = list(dict.fromkeys(line.strip() for line in result.stdout.splitlines() if line.strip()))[:6]
    matched_keys = [key for key in search_keys if any(re.search(re.escape(key), subject, re.IGNORECASE) for subject in subjects)]
    return {"jira_keys": matched_keys, "subjects": subjects}


def _repository_code_search(repo: dict[str, Any], keywords: list[str]) -> dict[str, Any]:
    path = Path(str(repo.get("path") or "")).expanduser()
    rg = shutil.which("rg")
    if not rg or not path.is_dir() or not keywords:
        return {"keywords": [], "files": 0, "sample_files": []}
    pattern = "(?i)(?:" + "|".join(re.escape(keyword) for keyword in keywords) + ")"
    args = [rg, "--hidden", "--no-messages", "--files-with-matches"]
    for glob in REPOSITORY_SEARCH_GLOBS:
        args.extend(["--glob", glob])
    args.extend(["-e", pattern, str(path)])
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=4, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {"keywords": [], "files": 0, "sample_files": []}
    if result.returncode not in {0, 1}:
        return {"keywords": [], "files": 0, "sample_files": []}
    files = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()][:40]
    matched: set[str] = set()
    samples: list[str] = []
    for file_path in files[:20]:
        try:
            if file_path.stat().st_size > 1_000_000:
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")[:200_000].casefold()
        except OSError:
            continue
        matched.update(keyword for keyword in keywords if keyword in text)
        if len(samples) < 3:
            try:
                samples.append(str(file_path.relative_to(path)))
            except ValueError:
                samples.append(str(file_path))
    return {"keywords": sorted(matched), "files": len(files), "sample_files": samples}


def _repository_candidate(repo: dict[str, Any], search_text: str, keywords: list[str], history_keys: list[str]) -> dict[str, Any]:
    name = str(repo.get("name") or "").strip()
    mention = bool(name and re.search(rf"(?<![A-Za-z0-9_-]){re.escape(name)}(?![A-Za-z0-9_-])", search_text, re.IGNORECASE))
    evidence = _repository_code_search(repo, keywords)
    history = _repository_history(repo, history_keys)
    matched_keywords = evidence["keywords"]
    score = (70 if history["jira_keys"] else 0) + (3 if mention else 0) + len(matched_keywords) * 10 + min(int(evidence["files"]), 5)
    high_confidence = bool(history["jira_keys"]) or len(matched_keywords) >= 2 or any(len(keyword) >= 8 for keyword in matched_keywords)
    return {"repo": repo, "mention": mention, "score": score, "high": high_confidence, "evidence": evidence, "history": history}


def _candidate_summary(candidate: dict[str, Any]) -> str:
    name = str(candidate["repo"].get("name") or "unknown")
    evidence = candidate["evidence"]
    details: list[str] = []
    if candidate["mention"]:
        details.append("Jira name mention")
    if candidate["history"]["jira_keys"]:
        details.append(f"history: {', '.join(candidate['history']['jira_keys'])}")
    if evidence["keywords"]:
        details.append(f"code keywords: {', '.join(evidence['keywords'][:4])}")
    if evidence["files"]:
        details.append(f"{evidence['files']} file(s)")
    if evidence["sample_files"]:
        details.append(f"e.g. {', '.join(evidence['sample_files'][:2])}")
    return f"{name} (score {candidate['score']}; {'; '.join(details) or 'no local evidence'})"


def _explicit_reply_repositories(item: dict[str, Any], eligible: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Use the latest human Jira reply when it names exact registered repositories."""
    for comment in reversed(comments(item)):
        if not isinstance(comment, dict):
            continue
        comment_json = json.dumps(comment, ensure_ascii=False)
        if "Lumen Auto Patch" in comment_json:
            continue
        comment_text = _jira_context_text(comment)
        matches = [
            repo for repo in eligible
            if re.search(rf"(?<![A-Za-z0-9_-]){re.escape(str(repo.get('name') or '').strip())}(?![A-Za-z0-9_-])", comment_text, re.IGNORECASE)
        ]
        return matches
    return []


def select_repositories(workspace: Path, item: dict[str, Any], context_path: Path | None = None) -> tuple[list[dict[str, Any]], str]:
    repositories = repo_registry(workspace)
    eligible = [repo for repo in repositories if repository_enabled(repo)]
    if not eligible:
        return [], "Auto Patch is disabled for every registered repository."
    if len(eligible) == 1:
        repo = eligible[0]
        return [repo], "Only one Auto Patch-authorized repository is available."
    if not repositories:
        return [], "No registered repository is available."
    explicit = _explicit_reply_repositories(item, eligible)
    if explicit:
        names = ", ".join(str(repo.get("name") or "") for repo in explicit)
        return explicit, f"Latest human Jira reply explicitly selected registered repositories: {names}."
    context = read_json(context_path, {}) if context_path else {}
    context = context if isinstance(context, dict) else {}
    primary_explicit = _authoritative_repository_matches(item, eligible)
    if primary_explicit:
        names = ", ".join(str(repo.get("name") or "") for repo in primary_explicit)
        return primary_explicit, f"Jira labels and explicit Repository fields identify: {names}."
    related_explicit: list[dict[str, Any]] = []
    for related in context.get("related_workitems") or []:
        if isinstance(related, dict):
            for repo in _authoritative_repository_matches(related, eligible):
                if repo not in related_explicit:
                    related_explicit.append(repo)
    if related_explicit:
        names = ", ".join(str(repo.get("name") or "") for repo in related_explicit)
        return related_explicit, f"Related Jira context identifies registered repositories: {names}."
    search_text = json.dumps(item, ensure_ascii=False)
    if context:
        search_text += json.dumps(context, ensure_ascii=False)
    keywords = _repository_keywords(item, context)
    history_keys = _jira_keys({"item": item, "context": context})
    candidates = [_repository_candidate(repo, search_text, keywords, history_keys) for repo in eligible]
    historical = [candidate for candidate in candidates if candidate["history"]["jira_keys"]]
    if historical:
        names = ", ".join(str(candidate["repo"].get("name") or "") for candidate in historical)
        keys = sorted({key for candidate in historical for key in candidate["history"]["jira_keys"]})
        return [candidate["repo"] for candidate in historical], f"Local Git history matches Jira key(s) {', '.join(keys)} in: {names}."
    ranked = sorted((candidate for candidate in candidates if candidate["score"] > 0), key=lambda candidate: candidate["score"], reverse=True)
    strong = [candidate for candidate in ranked if candidate["high"] and len(candidate["evidence"]["keywords"]) >= 2 and candidate["score"] >= 20]
    if len(strong) >= 2 and strong[0]["score"] - strong[-1]["score"] <= 20:
        names = ", ".join(str(candidate["repo"].get("name") or "") for candidate in strong[:5])
        return [candidate["repo"] for candidate in strong[:5]], f"Multiple registered repositories have strong local code evidence for the same Jira flow: {names}."
    if ranked and ranked[0]["high"] and (len(ranked) == 1 or ranked[0]["score"] > ranked[1]["score"] + 8):
        candidate = ranked[0]
        evidence = candidate["evidence"]
        return [candidate["repo"]], f"High-confidence Jira keyword and local code match: {candidate['repo'].get('name')} ({', '.join(evidence['keywords'])} in {evidence['files']} file(s))."
    keyword_text = ", ".join(keywords) or "none"
    candidate_text = "; ".join(_candidate_summary(candidate) for candidate in ranked[:5]) or "none"
    return [], f"Jira keywords and local code search did not identify one high-confidence registered repository. Keywords: {keyword_text}. Candidates: {candidate_text}."


def select_repository(workspace: Path, item: dict[str, Any], context_path: Path | None = None) -> tuple[dict[str, Any] | None, str]:
    """Compatibility wrapper for callers that still require a single repository."""
    repositories, reason = select_repositories(workspace, item, context_path)
    if len(repositories) == 1:
        return repositories[0], reason
    if len(repositories) > 1:
        return None, f"Multiple high-confidence repositories were selected by the multi-repository mapper: {reason}"
    return None, reason


def result_from_progress(progress: dict[str, Any], status: str, summary: str, question: str = "", failures: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "patch_status": status,
        "jira_key": progress.get("jira_key", ""),
        "jira_summary": progress.get("jira_summary", ""),
        "jira_status": progress.get("jira_status", ""),
        "model": progress.get("model", ""),
        "summary": summary,
        "repository_decision": progress.get("repository_decision", {}),
        "repos_touched": progress.get("repositories", []),
        "self_checks": progress.get("self_checks", []),
        "question": question,
        "failures": failures or [],
        "jira": progress.get("jira", {}),
        "blocked_at": progress.get("blocked_at", ""),
        "started_at": progress.get("started_at", ""),
        "finished_at": utc_now(),
    }


def validate_result(result: dict[str, Any], key: str) -> str:
    if result.get("schema_version") != "1.0":
        return "Agent result schema_version must be 1.0"
    if str(result.get("jira_key") or "").strip().upper() != key:
        return f"Agent result jira_key must be {key}"
    status = str(result.get("patch_status") or "").strip()
    if status not in {"completed", "blocked", "skipped", "failed"}:
        return "Agent result patch_status must be completed, blocked, skipped, or failed"
    if not isinstance(result.get("self_checks"), list):
        return "Agent result self_checks must be an array"
    if status == "completed" and not isinstance(result.get("repos_touched"), list):
        return "Completed Agent results must contain repos_touched as an array"
    if status in {"blocked", "failed"} and not str(result.get("question") or "").strip():
        return "Blocked or failed Agent results must contain one question"
    return ""


def write_terminal(workspace: Path, progress: dict[str, Any], result: dict[str, Any]) -> None:
    progress.update({"patch_status": result.get("patch_status"), "finished_at": result.get("finished_at", utc_now()), "question": result.get("question", ""), "failures": result.get("failures", []), "self_checks": result.get("self_checks", [])})
    save_progress(workspace, progress)
    write_json(result_path(workspace), result)
    history_dir(workspace).mkdir(parents=True, exist_ok=True)
    write_json(history_dir(workspace) / f"{progress.get('run_id')}.json", {"progress": progress, "patch": result})


def notify(workspace: Path, event: str) -> None:
    renderer = Path(__file__).with_name("render-delivery-and-notify.py")
    if not renderer.is_file():
        return
    subprocess.run([sys.executable, str(renderer), str(result_path(workspace)), "--event", event], env=os.environ.copy(), capture_output=True, text=True, check=False)


def block(workspace: Path, progress: dict[str, Any], question: str, reason: str) -> int:
    key = str(progress.get("jira_key") or "")
    progress["blocked_at"] = utc_now()
    transition_result = "sent"
    comment_result = "sent"
    try:
        progress["jira_status"] = transition_issue(workspace, key, str(patch_config(workspace).get("blocked_status", "Block")))
    except Exception as exc:
        transition_result = "failed"
        progress.setdefault("failures", []).append({"stage": "jira", "detail": str(exc)})
    try:
        add_comment(workspace, key, blocked_comment(reason, question), "html")
    except Exception as exc:
        comment_result = "failed"
        progress.setdefault("failures", []).append({"stage": "jira_comment", "detail": str(exc)})
    progress["jira"] = {
        "status": "sent" if comment_result == "sent" else "failed",
        "event": "patch.blocked",
        "transition": transition_result,
        "comment": comment_result,
    }
    registry = load_registry(workspace)
    registry.setdefault("issues", {})[key] = {"status": "blocked", "blocked_at": utc_now(), "question_hash": comment_fingerprint({"body": question}), "updated": registry.get("issues", {}).get(key, {}).get("updated", "")}
    save_registry(workspace, registry)
    result = result_from_progress(progress, "blocked", reason, question, progress.get("failures"))
    write_terminal(workspace, progress, result)
    notify(workspace, "patch.blocked")
    remove_worktrees(progress.get("repositories") or [])
    return 0


def skip(workspace: Path, progress: dict[str, Any], result: dict[str, Any]) -> int:
    key = str(progress.get("jira_key") or "")
    reason = str(result.get("summary") or "Agent found no actionable Auto Patch change.").strip()
    original_status = str(progress.get("original_jira_status") or "").strip()
    final_status = str(patch_config(workspace).get("done_status", "Done")).strip()
    current_status = str(progress.get("jira_status") or "").strip()
    transition_result = "unchanged"
    comment_result = "sent"
    if final_status and current_status.casefold() != final_status.casefold():
        try:
            progress["jira_status"] = transition_issue(workspace, key, final_status)
            transition_result = "moved"
        except Exception as exc:
            transition_result = "failed"
            progress.setdefault("failures", []).append({"stage": "jira", "detail": str(exc)})
    try:
        comment_status = final_status if transition_result in {"moved", "unchanged"} else ""
        add_comment(workspace, key, skipped_comment(reason, comment_status), "html")
    except Exception as exc:
        comment_result = "failed"
        progress.setdefault("failures", []).append({"stage": "jira_comment", "detail": str(exc)})
    progress["jira"] = {
        "status": "sent" if comment_result == "sent" else "failed",
        "event": "patch.skipped",
        "transition": transition_result,
        "comment": comment_result,
    }
    registry = load_registry(workspace)
    updated = ""
    try:
        updated = str(jira_fields(get_workitem(workspace, key)).get("updated") or "")
    except Exception:
        pass
    registry_entry = {
        "status": "skipped",
        "updated": updated,
        "finished_at": utc_now(),
    }
    if original_status.casefold() in {status.casefold() for status in blocked_statuses(workspace)}:
        registry_entry["blocked_at"] = utc_now()
    registry.setdefault("issues", {})[key] = registry_entry
    save_registry(workspace, registry)
    set_phase(
        workspace,
        progress,
        "jira_notify",
        "completed" if comment_result == "sent" else "failed",
        "Skip reason recorded in Jira; no code was published" if comment_result == "sent" and transition_result != "failed" else (
            "Skip reason recorded in Jira; Jira status could not be moved to the configured done status" if comment_result == "sent" else "Unable to record the skip reason in Jira"
        ),
    )
    result.update({"jira": progress["jira"], "failures": progress.get("failures", []), "finished_at": utc_now()})
    write_terminal(workspace, progress, result)
    notify(workspace, "patch.skipped")
    remove_worktrees(progress.get("repositories") or [])
    return 0


def run_agent(workspace: Path, prompt: str, log_file: Path) -> int:
    sandbox = os.environ.get("CURSOR_AGENT_SANDBOX", "enabled").strip().lower()
    if sandbox != "enabled":
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text("Auto Patch requires CURSOR_AGENT_SANDBOX=enabled; unsafe Cursor execution is disabled.\n", encoding="utf-8")
        return 78
    output_format = os.environ.get("CURSOR_AGENT_OUTPUT_FORMAT", "stream-json")
    args = [sys.executable, str(Path(__file__).with_name("run-workflow-agent.py")), "--workspace", str(workspace), "--workflow", "auto_patch", "--agent-id", "irving", "--project", os.environ.get("LUMON_PROJECT", ""), "--sandbox", sandbox, "--output-format", output_format, prompt]
    env = os.environ.copy()
    env["CURSOR_AGENT_SANDBOX"] = "enabled"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("w", encoding="utf-8") as handle:
        completed = subprocess.run(args, stdout=handle, stderr=subprocess.STDOUT, env=env, check=False)
    return completed.returncode


def write_idle_state(workspace: Path, message: str) -> str:
    idle = empty_progress()
    idle.update({"patch_status": "idle", "current_step": message, "finished_at": utc_now()})
    save_progress(workspace, idle)
    write_json(result_path(workspace), {"schema_version": "1.0", "patch_status": "idle", "jira_key": "", "summary": message, "finished_at": idle["finished_at"]})
    return message


def choose_item(workspace: Path, requested: str) -> tuple[dict[str, Any] | None, bool]:
    registry = load_registry(workspace).get("issues", {})
    candidates = query_candidates(workspace, include_blocked=True)
    if requested:
        candidates = [candidate for candidate in candidates if jira_key(candidate) == requested]
    for candidate in candidates:
        key = jira_key(candidate)
        item = get_workitem(workspace, key)
        record = registry.get(key, {}) if isinstance(registry, dict) else {}
        blocked = jira_status(item).casefold() in {status.casefold() for status in blocked_statuses(workspace)}
        waiting_for_reply = blocked or record.get("status") == "blocked"
        resumed = False
        if waiting_for_reply:
            if not has_external_reply(item, record):
                continue
            resumed = record.get("status") == "blocked"
        if record.get("status") in {"completed", "skipped"} and record.get("updated") == str(jira_fields(item).get("updated") or ""):
            continue
        registered = repo_registry(workspace)
        if registered and not any(repository_enabled(repo) for repo in registered):
            continue
        return item, resumed
    return None, False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    parser.add_argument("--jira-key", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    load_env(workspace)
    lock = lock_path(workspace)
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        lock.mkdir()
    except FileExistsError:
        print("Auto Patch already running; skipped this cycle.")
        return 0
    try:
        (lock / "pid").write_text(str(os.getpid()), encoding="utf-8")
        progress: dict[str, Any] | None = None
        try:
            item, resumed = choose_item(workspace, args.jira_key.strip().upper())
        except RuntimeError as exc:
            if str(exc) == "No active sprint found for the configured Jira board":
                message = write_idle_state(workspace, "No active sprint found for the configured Jira board.")
                print(message)
                return 0
            raise
        if not item:
            message = write_idle_state(workspace, "No eligible Auto Patch Jira card found in the current active sprint.")
            print(message)
            return 0
        key = jira_key(item)
        progress = new_progress(datetime.now().strftime("%Y%m%d-%H%M%S"), item, workspace)
        progress["model"] = patch_model(workspace)
        progress["original_jira_status"] = progress.get("jira_status", "")
        save_progress(workspace, progress)
        set_phase(workspace, progress, "capture", "in_progress", f"Selected {key}")
        set_phase(workspace, progress, "capture", "completed", "Primary Jira workitem captured")
        if resumed:
            progress["messages"] = [{"at": utc_now(), "message": "New external Jira reply detected; restarting Auto Patch."}]
        set_phase(workspace, progress, "screen", "in_progress", "Checking issue type, status, and actionable scope")
        fields = jira_fields(item)
        current_type = str(fields.get("issuetype", {}).get("name") if isinstance(fields.get("issuetype"), dict) else fields.get("issuetype") or "").strip()
        from patch_runtime import issue_types
        if current_type.casefold() not in {value.casefold() for value in issue_types(workspace)}:
            result = result_from_progress(progress, "skipped", f"Issue type {current_type or 'unknown'} is outside Auto Patch scope")
            write_terminal(workspace, progress, result)
            notify(workspace, "patch.completed")
            return 0
        set_phase(workspace, progress, "screen", "completed", "Deterministic Jira gates passed")
        if args.dry_run:
            set_phase(workspace, progress, "context", "in_progress", "Dry run: reading Jira context")
            context_path = capture(workspace, key)
            set_phase(workspace, progress, "context", "completed", f"Context captured at {context_path}")
            repositories, repo_reason = select_repositories(workspace, item, context_path)
            if not repositories:
                result = result_from_progress(progress, "blocked", "Dry run could not resolve registered repositories", "Which registered repository or repositories should Auto Patch modify?")
                write_terminal(workspace, progress, result)
                return 0
            progress["repository_decision"] = {"repositories": [repo.get("name") for repo in repositories], "reason": repo_reason}
            prompt = compose(workspace, key, jira_summary(item), context_path, repositories)
            prompt_path = results_dir(workspace) / "patch-prompt.txt"
            prompt_path.write_text(prompt, encoding="utf-8")
            progress["prompt_path"] = str(prompt_path)
            set_phase(workspace, progress, "repository", "completed", f"Dry run mapped {len(repositories)} repository(ies): {', '.join(str(repo.get('name')) for repo in repositories)}")
            set_phase(workspace, progress, "agent", "skipped", "Dry run")
            result = result_from_progress(progress, "skipped", f"Dry run completed; composed prompt at {prompt_path}")
            write_terminal(workspace, progress, result)
            return 0
        try:
            progress["jira_status"] = transition_issue(workspace, key, str(patch_config(workspace).get("in_progress_status", "In Progress")))
        except Exception as exc:
            return block(workspace, progress, f"Can Auto Patch transition {key} to the configured In Progress status?", str(exc))
        save_progress(workspace, progress)
        result_path(workspace).unlink(missing_ok=True)
        write_json(result_path(workspace), result_from_progress(progress, "running", f"Auto Patch started for {key}"))
        notify(workspace, "patch.started")
        set_phase(workspace, progress, "context", "in_progress", "Reading primary and related Jira context")
        context_path = capture(workspace, key)
        set_phase(workspace, progress, "context", "completed", f"Context captured at {context_path}")
        set_phase(workspace, progress, "repository", "in_progress", "Resolving registered repositories")
        repositories, repo_reason = select_repositories(workspace, item, context_path)
        if not repositories:
            return block(workspace, progress, "Which registered repository or repositories should Auto Patch modify?", repo_reason)
        progress["repository_decision"] = {"repositories": [repo.get("name") for repo in repositories], "reason": repo_reason}
        prepared: list[dict[str, Any]] = []
        try:
            for repo in repositories:
                prepared.append(prepare_worktree(workspace, key, jira_summary(item), repo))
        except Exception as exc:
            remove_worktrees(prepared)
            return block(workspace, progress, "Should Auto Patch retry after preparing all selected repositories?", str(exc))
        progress["repositories"] = prepared
        progress["branch"] = prepared[0].get("branch", "") if prepared else ""
        save_progress(workspace, progress)
        set_phase(workspace, progress, "repository", "completed", f"Prepared {len(prepared)} patch worktree(s)")
        set_phase(workspace, progress, "agent", "in_progress", "Running Auto Patch Agent")
        prompt = compose(workspace, key, jira_summary(item), context_path, repositories)
        log_file = logs_dir(workspace) / f"run-{progress['run_id']}.log"
        progress["log_file"] = str(log_file)
        save_progress(workspace, progress)
        exit_code = run_agent(workspace, prompt, log_file)
        set_phase(workspace, progress, "agent", "completed" if exit_code == 0 else "failed", f"Agent exited with {exit_code}")
        if exit_code != 0:
            return block(workspace, progress, "Should Auto Patch retry after the Agent failed?", f"Agent exited with code {exit_code}; see {log_file}")
        result = json.loads(result_path(workspace).read_text(encoding="utf-8")) if result_path(workspace).is_file() else {}
        if not isinstance(result, dict):
            return block(workspace, progress, "Can the Agent write the required patch-result.json contract?", "Agent result is not a JSON object")
        validation_error = validate_result(result, key)
        if validation_error:
            return block(workspace, progress, "Can the Agent provide a valid patch-result.json contract?", validation_error)
        status = str(result.get("patch_status") or "").strip()
        if status == "blocked":
            progress["question"] = str(result.get("question") or "Please clarify the expected behavior.")
            progress["self_checks"] = result.get("self_checks") or []
            return block(workspace, progress, progress["question"], str(result.get("summary") or "Agent could not determine a safe patch"))
        if status == "skipped":
            progress["self_checks"] = result.get("self_checks") or []
            set_phase(workspace, progress, "self_check", "completed", "Agent self-check evidence recorded")
            set_phase(workspace, progress, "publish", "skipped", "No code changes to publish")
            return skip(workspace, progress, result)
        if status != "completed":
            return block(workspace, progress, "Should Auto Patch retry after the Agent reported a failure?", str(result.get("question") or result.get("summary") or "Agent reported a failure"))
        progress["self_checks"] = result.get("self_checks") or []
        set_phase(workspace, progress, "self_check", "completed", "Agent self-check evidence recorded")
        set_phase(workspace, progress, "publish", "in_progress", "Committing and publishing changes")
        finalize = subprocess.run([sys.executable, str(Path(__file__).with_name("finalize_patch.py")), str(workspace)], capture_output=True, text=True, check=False)
        if finalize.returncode != 0:
            return block(workspace, progress, "Should Auto Patch retry the failed publish operation?", (finalize.stderr or finalize.stdout or "Patch finalization failed").strip()[-1000:])
        result = json.loads(result_path(workspace).read_text(encoding="utf-8"))
        progress["self_checks"] = result.get("self_checks") or progress.get("self_checks", [])
        set_phase(workspace, progress, "publish", "completed", "Changes published")
        set_phase(workspace, progress, "jira_notify", "in_progress", "Updating Jira and Feishu")
        done_status = str(patch_config(workspace).get("done_status", "Done"))
        progress["jira_status"] = transition_issue(workspace, key, done_status)
        pr_lines = ", ".join(result.get("pr_urls") or []) or ", ".join(item.get("sha", "") for item in result.get("commits") or [])
        add_comment(workspace, key, f"Lumen Auto Patch · Completed\n\n- Summary: {result.get('summary', '')}\n- Publish: {pr_lines or 'completed'}")
        registry = load_registry(workspace)
        registry.setdefault("issues", {})[key] = {"status": "completed", "updated": str(jira_fields(item).get("updated") or ""), "finished_at": utc_now()}
        save_registry(workspace, registry)
        set_phase(workspace, progress, "jira_notify", "completed", "Jira and Feishu updates sent")
        write_terminal(workspace, progress, result)
        notify(workspace, "patch.completed")
        remove_worktrees(progress.get("repositories") or [])
        return 0
    except Exception as exc:
        print(f"Auto Patch error: {exc}", file=sys.stderr)
        if args.dry_run and progress:
            result = result_from_progress(progress, "failed", "Dry run failed before prompt composition", "What should Auto Patch adjust before the next dry run?", [{"stage": "dry_run", "detail": str(exc)}])
            write_terminal(workspace, progress, result)
            return 0
        if progress and progress.get("jira_key"):
            return block(workspace, progress, "What should Auto Patch do to continue safely?", str(exc))
        return 1
    finally:
        shutil.rmtree(lock, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
