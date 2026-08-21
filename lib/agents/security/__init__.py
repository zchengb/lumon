from __future__ import annotations

from agents.security.actions import ActionReceipt, ActionRequest
from agents.security.broker import CapabilityBroker
from agents.security.env import build_agent_env, SECRET_ENV_DENY_PREFIXES, SECRET_ENV_DENY_KEYS
from agents.security.errors import SecurityError
from agents.security.flags import (
    ISOLATED_AGENT_WORLD,
    TRUSTED_DEDICATED_MACHINE,
    agent_security_mode,
    isolated_agent_world_enabled,
    trusted_dedicated_machine_enabled,
    workspace_isolation_v2_enabled,
)
from agents.security.trusted import TrustedActionContext, execute_trusted_actions

__all__ = [
    "ActionReceipt",
    "ActionRequest",
    "CapabilityBroker",
    "SecurityError",
    "TrustedActionContext",
    "build_agent_env",
    "execute_trusted_actions",
    "run_security_check",
    "workspace_isolation_v2_enabled",
    "TRUSTED_DEDICATED_MACHINE",
    "ISOLATED_AGENT_WORLD",
    "agent_security_mode",
    "trusted_dedicated_machine_enabled",
    "isolated_agent_world_enabled",
    "SECRET_ENV_DENY_PREFIXES",
    "SECRET_ENV_DENY_KEYS",
]


def __getattr__(name: str):
    if name == "run_security_check":
        from agents.security.preflight import run_security_check

        return run_security_check
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
