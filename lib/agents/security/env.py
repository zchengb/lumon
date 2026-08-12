from __future__ import annotations

import os
from typing import Optional


SECRET_ENV_DENY_KEYS = frozenset(
    {
        "CURSOR_API_KEY",
        "DEEPSEEK_API_KEY",
        "FEISHU_DYLAN_APP_ID",
        "FEISHU_DYLAN_APP_SECRET",
        "FEISHU_MARK_APP_ID",
        "FEISHU_MARK_APP_SECRET",
        "FEISHU_IRVING_APP_ID",
        "FEISHU_IRVING_APP_SECRET",
        "FEISHU_MILCHICK_APP_ID",
        "FEISHU_MILCHICK_APP_SECRET",
        "DYLAN_FEISHU_APP_SECRET",
        "MARK_FEISHU_APP_SECRET",
        "JIRA_TOKEN",
        "JIRA_API_TOKEN",
        "JIRA_EMAIL",
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "DATABASE_URL",
        "SSH_AUTH_SOCK",
        "SSH_AGENT_PID",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
    }
)

SECRET_ENV_DENY_PREFIXES = (
    "AWS_",
    "FEISHU_",
    "JIRA_",
    "GITHUB_",
    "GH_",
    "SSH_",
    "NPM_TOKEN",
    "DOCKER_",
    "DEEPSEEK_",
)

_ALLOW_KEYS = (
    "PATH",
    "HOME",
    "TMPDIR",
    "TMP",
    "TEMP",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TERM",
    "USER",
    "LOGNAME",
    "SHELL",
    "XDG_RUNTIME_DIR",
    "AGENT_CLI_CREDENTIAL_STORE",
)


def _is_denied(key: str) -> bool:
    name = str(key or "")
    if name in SECRET_ENV_DENY_KEYS:
        return True
    upper = name.upper()
    return any(upper.startswith(prefix) for prefix in SECRET_ENV_DENY_PREFIXES)


def build_agent_env(
    *,
    agent_id: str = "",
    project: str = "",
    extra: Optional[dict[str, str]] = None,
    source: Optional[dict[str, str]] = None,
) -> dict[str, str]:
    base = source if source is not None else os.environ
    env: dict[str, str] = {}
    for key in _ALLOW_KEYS:
        value = base.get(key)
        if value:
            env[key] = value
    # CLI provider credential reference only — never copy host secret dumps.
    cursor_key = base.get("CURSOR_API_KEY", "").strip()
    if cursor_key:
        env["CURSOR_API_KEY"] = cursor_key
        env.setdefault("AGENT_CLI_CREDENTIAL_STORE", "file")
    if agent_id:
        env["LUMEN_AGENT_ID"] = str(agent_id).strip().lower()
    if project:
        env["LUMEN_PROJECT"] = str(project).strip()
    lumen_home = base.get("LUMEN_HOME", "").strip()
    if lumen_home:
        env["LUMEN_HOME"] = lumen_home
    lumen_bin = base.get("LUMEN_CLI_BIN", "").strip() or base.get("LUMEN_BIN", "").strip()
    if lumen_bin:
        env["LUMEN_CLI_BIN"] = lumen_bin
    if extra:
        for key, value in extra.items():
            name = str(key or "").strip()
            if not name or _is_denied(name):
                continue
            env[name] = str(value)
    for key in list(env):
        if _is_denied(key) and key != "CURSOR_API_KEY":
            env.pop(key, None)
    return env


def env_contains_secrets(env: dict[str, str]) -> list[str]:
    leaked: list[str] = []
    for key in env:
        if key == "CURSOR_API_KEY":
            continue
        if _is_denied(key):
            leaked.append(key)
    return sorted(leaked)
