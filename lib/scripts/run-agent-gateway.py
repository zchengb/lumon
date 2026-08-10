#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parent.parent
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from feishu.channel import FeishuChannel
from feishu.client_registry import configured_agents, GATEWAY_AGENTS
from feishu.config import agents_enabled, agents_home, load_agents_config


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if not key:
            continue
        if key == "CURSOR_API_KEY" and value:
            os.environ[key] = value
        elif key not in os.environ:
            os.environ[key] = value


def bootstrap_env() -> None:
    home = Path(os.environ.get("LUMEN_HOME", Path.home() / ".lumon"))
    _load_dotenv(home / ".env.local")
    _load_dotenv(Path.home() / ".lumon" / ".env.local")


def pid_path() -> Path:
    return agents_home() / "gateway.pid"


def status_path() -> Path:
    return agents_home() / "gateway-status.json"


def write_status(payload: dict) -> None:
    status_path().write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def cmd_status() -> int:
    path = pid_path()
    config = load_agents_config()
    clients = configured_agents(list(GATEWAY_AGENTS))
    running = False
    pid = None
    if path.is_file():
        try:
            pid = int(path.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            running = True
        except Exception:
            running = False
    payload = {
        "running": running,
        "pid": pid if running else None,
        "agents_enabled": agents_enabled(config),
        "clients": [item.agent_id for item in clients],
        "home": str(agents_home()),
    }
    try:
        from agents.dylan.diagnostics import runtime_status_extra

        payload.update(runtime_status_extra())
    except Exception as exc:
        payload["diagnostics_error"] = str(exc)[:200]
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    return 0


def cmd_stop() -> int:
    path = pid_path()
    if not path.is_file():
        print("Agent gateway is not running.")
        return 0
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except Exception:
        path.unlink(missing_ok=True)
        print("Removed stale gateway pid file.")
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Stopped agent gateway pid {pid}")
    except ProcessLookupError:
        print("Agent gateway process not found; cleared pid file.")
    except Exception as exc:
        print(f"Failed to stop gateway: {exc}", file=sys.stderr)
        return 1
    path.unlink(missing_ok=True)
    write_status({"running": False})
    return 0


def cmd_start(*, foreground: bool = False) -> int:
    import subprocess
    import time

    config = load_agents_config()
    if not agents_enabled(config):
        print(
            "Agents are disabled. Set agents.enabled=true in "
            f"{agents_home() / 'config.json'} or export LUMEN_AGENTS_ENABLED=1",
            file=sys.stderr,
        )
        return 1
    clients = configured_agents(list(GATEWAY_AGENTS))
    if not clients:
        print(
            "No agent credentials found. Set FEISHU_*_APP_ID/SECRET for dylan, mark, irving, and/or milchick.",
            file=sys.stderr,
        )
        return 1
    path = pid_path()
    if path.is_file():
        try:
            existing = int(path.read_text(encoding="utf-8").strip())
            os.kill(existing, 0)
            print(f"Agent gateway already running (pid {existing})", file=sys.stderr)
            return 1
        except Exception:
            path.unlink(missing_ok=True)

    if not foreground:
        log_path = agents_home() / "gateway.stdout.log"
        agents_home().mkdir(parents=True, exist_ok=True)
        log_fh = open(log_path, "a", encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "start", "--foreground"],
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            cwd=str(agents_home()),
            env=os.environ.copy(),
        )
        log_fh.close()
        deadline = time.time() + 8.0
        while time.time() < deadline:
            if path.is_file():
                try:
                    child = int(path.read_text(encoding="utf-8").strip())
                    os.kill(child, 0)
                    print(f"Started agent gateway pid {child}")
                    return 0
                except Exception:
                    pass
            if proc.poll() is not None:
                break
            time.sleep(0.2)
        print(
            f"Agent gateway failed to start. See {log_path}",
            file=sys.stderr,
        )
        return 1

    path.write_text(str(os.getpid()), encoding="utf-8")
    write_status({
        "running": True,
        "pid": os.getpid(),
        "clients": [item.agent_id for item in clients],
    })

    try:
        from agents.security.preflight import run_security_check

        security = run_security_check()
        if security.get("status") != "pass":
            print(
                "Agent security preflight failed. Conversation agents will not start.\n"
                + json.dumps(security, indent=2, ensure_ascii=False),
                file=sys.stderr,
            )
            path.unlink(missing_ok=True)
            write_status({"running": False, "error": "SECURITY_PREFLIGHT_FAILED", "security": security})
            return 1
        write_status({
            "running": True,
            "pid": os.getpid(),
            "clients": [item.agent_id for item in clients],
            "security": security,
        })
    except Exception as exc:
        print(f"Agent security preflight error: {exc}", file=sys.stderr)
        path.unlink(missing_ok=True)
        write_status({"running": False, "error": f"SECURITY_PREFLIGHT_ERROR:{exc}"})
        return 1

    def _cleanup(*_args) -> None:
        path.unlink(missing_ok=True)
        write_status({"running": False})
        sys.exit(0)

    signal.signal(signal.SIGTERM, _cleanup)
    signal.signal(signal.SIGINT, _cleanup)
    try:
        from agents.dylan.reaction_cleanup import start_reaction_cleanup_worker

        start_reaction_cleanup_worker()
    except Exception:
        pass
    channel = FeishuChannel(clients=clients)
    try:
        channel.start()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        path.unlink(missing_ok=True)
        write_status({"running": False, "error": str(exc)})
        return 1
    return 0


def cmd_logs(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lumen agents logs")
    parser.add_argument("--agent", default="dylan")
    parser.add_argument("--follow", action="store_true")
    parser.add_argument("--trace", default="")
    parser.add_argument("--event", default="")
    parser.add_argument("--level", default="")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args(argv or [])
    agent = str(args.agent or "dylan").strip().lower()
    if agent not in set(GATEWAY_AGENTS):
        print(f"Supported agents: {', '.join(GATEWAY_AGENTS)} (got {args.agent})", file=sys.stderr)
        return 1
    from agents.dylan.diagnostics import follow_jsonl_logs, read_jsonl_logs

    rows = read_jsonl_logs(
        follow=False,
        trace_id=args.trace,
        event=args.event,
        level=args.level,
        limit=args.limit,
        agent_id=agent,
    )
    for row in rows:
        print(json.dumps(row, ensure_ascii=False))
    if args.follow:
        follow_jsonl_logs(trace_id=args.trace, event=args.event, level=args.level, agent_id=agent)
    return 0


def main(argv: list[str] | None = None) -> int:
    bootstrap_env()
    parser = argparse.ArgumentParser(description="Lumen Feishu Agent Gateway")
    sub = parser.add_subparsers(dest="command", required=True)
    start_parser = sub.add_parser("start", help="Start Feishu agent gateway (daemon)")
    start_parser.add_argument(
        "--foreground",
        action="store_true",
        help="Run in the current process (used by the daemon child)",
    )
    sub.add_parser("status", help="Show gateway status")
    sub.add_parser("stop", help="Stop gateway via pid file")
    logs_parser = sub.add_parser("logs", help="Tail Dylan structured JSONL logs")
    logs_parser.add_argument("--agent", default="dylan")
    logs_parser.add_argument("--follow", action="store_true")
    logs_parser.add_argument("--trace", default="")
    logs_parser.add_argument("--event", default="")
    logs_parser.add_argument("--level", default="")
    logs_parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args(argv)
    if args.command == "start":
        return cmd_start(foreground=bool(getattr(args, "foreground", False)))
    if args.command == "status":
        return cmd_status()
    if args.command == "stop":
        return cmd_stop()
    if args.command == "logs":
        return cmd_logs(
            [
                "--agent",
                args.agent,
                *(["--follow"] if args.follow else []),
                "--trace",
                args.trace,
                "--event",
                args.event,
                "--level",
                args.level,
                "--limit",
                str(args.limit),
            ]
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
