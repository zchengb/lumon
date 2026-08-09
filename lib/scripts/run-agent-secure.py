#!/usr/bin/env python3
"""Run a child command with the same isolated environment as conversational agents."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parent.parent
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from agents.runner.runner_env import build_runner_env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-id", required=True)
    parser.add_argument("--project", default="")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        parser.error("a child command is required after --")

    env = build_runner_env(
        agent_id=args.agent_id,
        project=args.project,
        source=os.environ,
    )
    env["CURSOR_AGENT_SANDBOX"] = "enabled"
    os.execvpe(command[0], command, env)
    return 127


if __name__ == "__main__":
    raise SystemExit(main())
