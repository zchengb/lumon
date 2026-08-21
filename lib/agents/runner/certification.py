"""Provider certification for the M0.7 Agent World contract.

Certification is intentionally provider-agnostic at the boundary.  It proves
the same properties for Cursor, OpenCode, and Codex: the child can write its
disposable workspace, cannot read/write the canonical checkout, cannot read a
host credential location, and cannot use sudo to escape the world.  The
provider adapter is only used to locate the executable and exercise the
connected-tool CLI where it is installed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

from agents.runner.agent_world import AGENT_WORLD_CONTRACT, AgentWorld, AgentWorldError, probe_agent_world


def _run(world: AgentWorld, workspace: Path, env: Mapping[str, str], command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        world.command(command),
        cwd=str(workspace),
        env=dict(env),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def _provider_binary(provider: str) -> str:
    name = str(provider or "").strip().casefold()
    if name == "cursor":
        return shutil.which("agent") or shutil.which("cursor-agent") or ""
    return shutil.which(name) or ""


def certify_provider(
    provider: str,
    *,
    agent_id: str = "certification",
    config: Mapping[str, Any] | None = None,
    live: bool = False,
) -> dict[str, Any]:
    """Return a stable JSON report for one provider's world contract.

    ``live=False`` is safe for CI and reports static backend readiness.  The
    filesystem probes run only with ``live=True`` because they create a
    disposable temporary checkout and start a sandboxed subprocess.
    """

    provider_name = str(provider or "").strip().casefold()
    world_probe = probe_agent_world(agent_id=agent_id, config=config)
    report: dict[str, Any] = {
        "contract": AGENT_WORLD_CONTRACT,
        "provider": provider_name,
        "agent_id": str(agent_id or "certification").strip().lower(),
        "live": bool(live),
        "backend": world_probe.get("checks", {}).get("backend", "unavailable"),
        "provider_binary": bool(_provider_binary(provider_name)),
        "workspace_write": False,
        "twg": False,
        "canonical_write": False,
        "canonical_delete": False,
        "host_escape": False,
        "sudo": False,
        "secret_read": False,
        "identity": False,
        "details": {},
        "warnings": list(world_probe.get("warnings") or []),
    }
    if not live:
        report["workspace_write"] = world_probe.get("ready") is True
        report["canonical_write"] = world_probe.get("checks", {}).get("canonical_access") == "host_only"
        report["canonical_delete"] = report["canonical_write"]
        report["host_escape"] = report["canonical_write"]
        report["secret_read"] = report["canonical_write"]
        report["sudo"] = report["canonical_write"]
        report["identity"] = bool(world_probe.get("checks", {}).get("dedicated_unix_identity"))
        report["status"] = "ready" if world_probe.get("ready") and report["identity"] else "not_ready"
        report["ready"] = bool(world_probe.get("ready") and report["identity"])
        return report

    if not world_probe.get("ready"):
        report["status"] = "not_ready"
        report["ready"] = False
        report["error"] = "Agent World backend is not ready"
        return report

    try:
        with tempfile.TemporaryDirectory(prefix=f"lumon-cert-{provider_name}-") as temp:
            root = Path(temp).resolve()
            canonical = root / "canonical"
            workspace = root / "workspace"
            canonical.mkdir()
            workspace.mkdir()
            protected = canonical / "protected.txt"
            protected.write_text("host-only\n", encoding="utf-8")
            secret = canonical / ".env.secret"
            secret.write_text("TOKEN=never-readable\n", encoding="utf-8")
            world = AgentWorld.create(
                canonical=canonical,
                workspace=workspace,
                agent_id=agent_id,
                config=config,
                require_boundary=True,
            )
            try:
                env = world.environment(project="certification")
                write = _run(world, workspace, env, ["/bin/sh", "-c", "printf ok > workspace-proof.txt"])
                report["workspace_write"] = write.returncode == 0 and (workspace / "workspace-proof.txt").is_file()

                canonical_write = _run(world, workspace, env, ["/bin/sh", "-c", f"printf no > {canonical / 'blocked.txt'}"])
                report["canonical_write"] = canonical_write.returncode != 0 and not (canonical / "blocked.txt").exists()

                canonical_delete = _run(world, workspace, env, ["/bin/sh", "-c", f"rm -f {protected}"])
                report["canonical_delete"] = canonical_delete.returncode != 0 and protected.exists()

                secret_read = _run(world, workspace, env, ["/bin/sh", "-c", f"cat {secret}"])
                report["secret_read"] = secret_read.returncode != 0 and "never-readable" not in secret_read.stdout

                host_target = Path.home().expanduser() / ".ssh"
                host_escape = _run(world, workspace, env, ["/bin/sh", "-c", f"test -r {host_target}"])
                report["host_escape"] = host_escape.returncode != 0
                if not host_target.exists():
                    report["details"]["host_escape"] = "target_absent_but_host_home_is_not_in_world"

                sudo_bin = shutil.which("sudo")
                if sudo_bin:
                    sudo = _run(world, workspace, env, [sudo_bin, "-n", "true"])
                    report["sudo"] = sudo.returncode != 0
                else:
                    report["sudo"] = True
                    report["details"]["sudo"] = "sudo_not_installed"

                uid = _run(world, workspace, env, ["/usr/bin/id", "-u"])
                uid_value = (uid.stdout or "").strip()
                report["details"]["uid"] = uid_value
                report["identity"] = bool(
                    uid.returncode == 0
                    and world.spec.dedicated_identity
                    and uid_value == str(world.spec.agent_uid)
                )
                if not report["identity"]:
                    report["details"]["identity"] = "sandbox boundary active; dedicated Unix identity is not configured"

                twg = shutil.which("twg")
                if twg:
                    twg_result = _run(world, workspace, env, [twg, "--help"])
                    report["twg"] = twg_result.returncode == 0
                    report["details"]["twg"] = "available" if report["twg"] else (twg_result.stderr or twg_result.stdout or "failed")[:180]
                else:
                    report["details"]["twg"] = "unavailable"
            finally:
                world.close()
    except (AgentWorldError, OSError, subprocess.SubprocessError) as exc:
        report["error"] = str(exc)[:400]

    mandatory = ("workspace_write", "twg", "canonical_write", "canonical_delete", "host_escape", "sudo", "secret_read", "identity")
    report["ready"] = all(bool(report.get(key)) for key in mandatory)
    report["status"] = "pass" if report["ready"] else "fail"
    if not report["provider_binary"]:
        report["warnings"].append(f"{provider_name} provider binary was not found; boundary certification still ran")
    return report


__all__ = ["certify_provider"]
