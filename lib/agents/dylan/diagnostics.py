from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

from agents.dylan.schemas import ConversationFlags
from feishu.config import agents_home, load_agents_config
from risk.store import GlobalAgentStore


def _check(name: str, status: str, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail}


def doctor_deep(*, common: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    try:
        from agents.dylan.model_client import _load_lumen_dotenv

        _load_lumen_dotenv()
    except Exception:
        pass
    config = load_agents_config()
    flags = ConversationFlags.from_common(common or {}, config)
    from agents.runtime.openai_compatible import default_api_key_env, is_api_provider
    from agents.runtime.cursor_runtime import canonical_agent_provider

    api_provider = is_api_provider(flags.model.provider)
    harness_provider = canonical_agent_provider(flags.model.provider) == "opencode"
    checks: list[dict[str, str]] = []
    checks.append(
        _check(
            "conversation_v4",
            "PASS" if flags.autonomous else "WARN",
            f"enabled={flags.v4_enabled} mode={flags.autonomous_mode or '-'}",
        )
    )
    checks.append(
        _check(
            "conversation_v3",
            "PASS" if flags.v3_enabled or flags.autonomous else "WARN",
            f"enabled={flags.v3_enabled} routing_mode={flags.routing_mode}",
        )
    )
    checks.append(
        _check(
            "routing_mode",
            "PASS" if flags.autonomous or flags.agent_only else "WARN",
            "autonomous_workspace" if flags.autonomous else flags.routing_mode,
        )
    )
    agent_bin = shutil.which("agent") or shutil.which("cursor-agent")
    from agents.runtime.opencode_runtime import find_opencode_bin

    opencode_bin = find_opencode_bin()
    checks.append(
        _check(
            "agent_cli",
            "N/A" if api_provider or harness_provider else ("PASS" if agent_bin else ("WARN" if flags.model.provider == "fake" else "FAIL")),
            opencode_bin if harness_provider else (agent_bin or "not found"),
        )
    )
    if harness_provider:
        checks.append(_check("opencode_cli", "PASS" if opencode_bin else "FAIL", opencode_bin or "not found"))
        key_env = flags.model.api_key_env or "DEEPSEEK_API_KEY"
        checks.append(_check("opencode_auth", "PASS" if os.environ.get(key_env, "").strip() else "FAIL", key_env))
    if api_provider:
        key_env = flags.model.api_key_env or default_api_key_env(flags.model.provider)
        checks.append(
            _check(
                "model_auth",
                "PASS" if os.environ.get(key_env, "").strip() else "FAIL",
                key_env,
            )
        )
    elif agent_bin and flags.model.provider in {"cursor", "cursor_cli"}:
        try:
            completed = subprocess.run(
                [agent_bin, "status"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            status_text = (completed.stdout or completed.stderr or "").strip()
            logged_in = "not logged in" not in status_text.lower() and completed.returncode == 0
            if os.environ.get("CURSOR_API_KEY"):
                logged_in = True
                status_text = "CURSOR_API_KEY present"
            checks.append(
                _check(
                    "agent_auth",
                    "PASS" if logged_in else "FAIL",
                    status_text[:160] or f"exit={completed.returncode}",
                )
            )
        except Exception as exc:
            checks.append(_check("agent_auth", "FAIL", str(exc)[:120]))
    checks.append(
        _check(
            "model",
            "PASS" if (flags.model.provider in {"cursor", "cursor_cli", "fake"} or harness_provider and os.environ.get(flags.model.api_key_env or "DEEPSEEK_API_KEY", "").strip() or (api_provider and os.environ.get(flags.model.api_key_env or default_api_key_env(flags.model.provider), "").strip())) else "FAIL",
            f"{flags.model.provider}/{flags.model.model_name} required={flags.model.required}",
        )
    )
    has_creds = bool(os.environ.get("FEISHU_DYLAN_APP_ID") and os.environ.get("FEISHU_DYLAN_APP_SECRET"))
    checks.append(_check("feishu_credentials", "PASS" if has_creds else "WARN", "FEISHU_DYLAN_APP_ID/SECRET"))
    checks.append(
        _check(
            "reaction",
            "PASS" if flags.reaction.enabled else "WARN",
            f"emoji_type={flags.reaction.emoji_type}",
        )
    )
    home = agents_home()
    jsonl = home / "dylan.jsonl"
    try:
        jsonl.parent.mkdir(parents=True, exist_ok=True)
        with jsonl.open("a", encoding="utf-8") as handle:
            handle.write("")
        checks.append(_check("log_write", "PASS", str(jsonl)))
    except Exception as exc:
        checks.append(_check("log_write", "FAIL", str(exc)[:120]))
    try:
        gs = GlobalAgentStore()
        gs.conn.execute("SELECT 1 FROM conversation_trace LIMIT 1")
        checks.append(_check("trace_db", "PASS", str(gs.path)))
        gs.close()
    except Exception as exc:
        checks.append(_check("trace_db", "FAIL", str(exc)[:120]))
    fails = sum(1 for c in checks if c["status"] == "FAIL")
    warns = sum(1 for c in checks if c["status"] == "WARN")
    return {
        "summary": "FAIL" if fails else ("WARN" if warns else "PASS"),
        "checks": checks,
        "flags": {
            "v3_enabled": flags.v3_enabled,
            "v4_enabled": flags.v4_enabled,
            "autonomous": flags.autonomous,
            "routing_mode": flags.routing_mode,
            "provider": flags.model.provider,
            "model": flags.model.model_name,
            "reaction_emoji": flags.reaction.emoji_type,
        },
    }


def format_trace_timeline(trace_id: str) -> str:
    from agents.dylan.observability import Observability

    obs = Observability()
    try:
        trace = obs.get_trace(trace_id)
        if not trace:
            return f"Trace not found: {trace_id}"
        events = obs.events_for_trace(trace_id)
        started = trace.get("started_at") or ""
        lines = [f"trace_id={trace_id} state={trace.get('state')} project={trace.get('project_slug') or '-'}"]
        base = None
        for event in events:
            created = str(event.get("created_at") or "")
            # ponytail: display relative ms only when ISO-ish timestamps share prefix; else show absolute
            suffix = created
            if started and created.startswith(started[:10]):
                try:
                    from datetime import datetime

                    t0 = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    t1 = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    ms = int((t1 - t0).total_seconds() * 1000)
                    suffix = f"{ms}ms"
                except Exception:
                    suffix = created
            payload = {}
            try:
                payload = json.loads(event.get("payload_json") or "{}")
            except Exception:
                payload = {}
            extra = ""
            if payload.get("tool"):
                extra = f" {payload.get('tool')}"
            if payload.get("latency_ms") is not None:
                extra += f" latency={payload.get('latency_ms')}ms"
            lines.append(f"{suffix:>8}  {event.get('event')}{extra}")
        return "\n".join(lines)
    finally:
        obs.close()


def read_jsonl_logs(
    *,
    follow: bool = False,
    trace_id: str = "",
    event: str = "",
    level: str = "",
    limit: int = 200,
    agent_id: str = "dylan",
) -> list[dict[str, Any]]:
    agent = str(agent_id or "dylan").strip().lower() or "dylan"
    path = agents_home() / f"{agent}.jsonl"
    if not path.is_file():
        return []

    def _match(row: dict[str, Any]) -> bool:
        if trace_id and str(row.get("trace_id") or "") != trace_id:
            return False
        if event and str(row.get("event") or "") != event:
            return False
        if level and str(row.get("level") or "").upper() != level.upper():
            return False
        return True

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if _match(row):
                rows.append(row)
    rows = rows[-limit:]
    if not follow:
        return rows
    return rows


def follow_jsonl_logs(
    *,
    trace_id: str = "",
    event: str = "",
    level: str = "",
    agent_id: str = "dylan",
) -> None:
    agent = str(agent_id or "dylan").strip().lower() or "dylan"
    path = agents_home() / f"{agent}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    with path.open("r", encoding="utf-8") as handle:
        handle.seek(0, 2)
        while True:
            line = handle.readline()
            if not line:
                time.sleep(0.4)
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if trace_id and str(row.get("trace_id") or "") != trace_id:
                continue
            if event and str(row.get("event") or "") != event:
                continue
            if level and str(row.get("level") or "").upper() != level.upper():
                continue
            print(json.dumps(row, ensure_ascii=False))


def runtime_status_extra() -> dict[str, Any]:
    config = load_agents_config()
    flags = ConversationFlags.from_common({}, config)
    out: dict[str, Any] = {
        "routing_mode": "autonomous_workspace" if flags.autonomous else flags.routing_mode,
        "provider": flags.model.provider,
        "model": flags.model.model_name,
        "reaction_emoji": flags.reaction.emoji_type,
        "v3_enabled": flags.v3_enabled,
        "v4_enabled": flags.v4_enabled,
        "autonomous": flags.autonomous,
    }
    try:
        gs = GlobalAgentStore()
        out["active_jobs"] = gs.conn.execute(
            "SELECT COUNT(*) AS c FROM conversation_job WHERE state NOT IN ('completed','failed','timed_out')"
        ).fetchone()["c"]
        last = gs.conn.execute(
            "SELECT * FROM agent_invocation ORDER BY id DESC LIMIT 1"
        ).fetchone()
        out["last_agent_call"] = dict(last) if last else None
        fail = gs.conn.execute(
            "SELECT * FROM conversation_trace WHERE state='failed' ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        out["last_failure"] = dict(fail) if fail else None
        gs.close()
    except Exception as exc:
        out["store_error"] = str(exc)[:200]
    version_path = Path(__file__).resolve().parents[3] / "VERSION"
    if not version_path.is_file():
        version_path = Path(__file__).resolve().parents[2] / "VERSION"
    if version_path.is_file():
        out["version"] = version_path.read_text(encoding="utf-8").strip()
    return out
