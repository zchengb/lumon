#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

LIB_DIR = Path(__file__).resolve().parent.parent
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))


def _emit(payload: dict[str, Any], *, code: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False, default=str))
    return code


def cmd_security_check(args: argparse.Namespace) -> int:
    from agents.security.preflight import run_security_check

    result = run_security_check(
        agent_id=args.agent,
        project=args.project or "",
        live=bool(getattr(args, "live", False)),
    )
    return _emit(result, code=0 if result.get("status") == "pass" else 1)


def cmd_harness_probe(args: argparse.Namespace) -> int:
    from agents.runtime.harness import probe_harness
    from feishu.config import load_agents_config

    result = probe_harness(
        args.provider,
        project=args.project or "",
        config=load_agents_config(),
        require_provider=True,
    ).to_dict()
    return _emit(result, code=0 if result.get("ready") else 1)


def cmd_action(args: argparse.Namespace) -> int:
    from feishu.config import ensure_lumen_env_loaded

    ensure_lumen_env_loaded()
    from agents.security.actions import ActionRequest
    from agents.security.broker import CapabilityBroker

    resource: dict[str, Any] = {}
    arguments: dict[str, Any] = {}
    if args.finding:
        resource["finding_id"] = args.finding
        arguments["finding_id"] = args.finding
    if args.story:
        resource["story"] = args.story
        arguments["story"] = args.story
        arguments.setdefault("issue_key", args.story)
        resource.setdefault("issue_key", args.story)
    if args.cron:
        resource["cron"] = args.cron
        arguments["cron"] = args.cron
    if args.reason:
        arguments["reason"] = args.reason
    if args.basis:
        arguments["basis"] = args.basis
    if args.project:
        arguments["project"] = args.project
    # Host/admin CLI path. Conversational agents must use ACTION_REQUEST + TrustedActionContext.
    if not args.actor:
        return _emit(
            {
                "status": "denied",
                "error_code": "HOST_ACTOR_REQUIRED",
                "error": "lumen agents action requires --actor (host/admin). Conversational agents use ACTION_REQUEST.",
            },
            code=1,
        )
    request = ActionRequest(
        agent_id=args.agent,
        action=args.action,
        project_slug=args.project or "",
        actor_user_id=args.actor or "",
        chat_id=args.chat_id or "",
        thread_id=args.thread_id or "",
        source_message_id=args.source_message_id or "",
        trace_id=args.trace_id or "",
        resource=resource,
        arguments=arguments,
        explicit_authorization=True,
    )
    receipt = CapabilityBroker().execute(request)
    code = 0 if receipt.status == "succeeded" else 1
    return _emit(receipt.to_dict(), code=code)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lumen agent security CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("security-check", help="Run agent security preflight")
    check.add_argument("--agent", default="dylan")
    check.add_argument("--project", default="")
    check.add_argument(
        "--live",
        action="store_true",
        help="Optional live probes (requires LUMEN_SECURITY_E2E=1); not needed for CI",
    )
    check.set_defaults(func=cmd_security_check)

    probe = sub.add_parser("harness-probe", help="Probe a provider Harness and its host boundary")
    probe.add_argument("--provider", required=True, choices=("cursor", "opencode", "codex", "api"))
    probe.add_argument("--project", default="")
    probe.add_argument("--json", action="store_true", help="Emit the machine-readable probe payload (the default)")
    probe.set_defaults(func=cmd_harness_probe)

    action = sub.add_parser("action", help="Execute a brokered agent action")
    action.add_argument("--agent", required=True)
    action.add_argument("--action", required=True)
    action.add_argument("--project", default="")
    action.add_argument("--actor", default="")
    action.add_argument("--chat-id", default="")
    action.add_argument("--thread-id", default="")
    action.add_argument("--source-message-id", default="")
    action.add_argument("--trace-id", default="")
    action.add_argument("--finding", default="")
    action.add_argument("--story", default="")
    action.add_argument("--cron", default="")
    action.add_argument("--reason", default="")
    action.add_argument("--basis", default="user_confirmed")
    action.add_argument("--json", action="store_true", default=True)
    action.set_defaults(func=cmd_action)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
