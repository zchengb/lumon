"""Provisioning and health checks for Agent service identities.

The Host creates the directories, but never copies a developer's token or
provider auth file into them.  A provider-specific setup command may later
place a service credential in this HOME; the status interface makes that
state visible without printing secret material.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agents.runner.workspace_mounts import ensure_runner_dirs


@dataclass(frozen=True)
class ServiceIdentity:
    agent_id: str
    home: Path
    root: Path
    provider: str = ""
    credential_store: str = "file"
    provisioned: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "home": str(self.home),
            "root": str(self.root),
            "provider": self.provider,
            "credential_store": self.credential_store,
            "provisioned": self.provisioned,
            "personal_credentials_copied": False,
        }


def _identity_path(root: Path) -> Path:
    return root / "service-identity.json"


def provision_service_identity(
    agent_id: str,
    *,
    provider: str = "",
    root: Path | None = None,
) -> ServiceIdentity:
    agent = str(agent_id or "agent").strip().lower() or "agent"
    dirs = ensure_runner_dirs(agent)
    if root is not None:
        root_path = Path(root).expanduser().resolve()
        home = root_path / "home"
        tmp = root_path / "tmp"
        home.mkdir(parents=True, exist_ok=True)
        tmp.mkdir(parents=True, exist_ok=True)
    else:
        root_path = dirs["root"]
        home = dirs["home"]
    for relative in (".config/twg", ".config/gh", ".codex", ".cursor", ".local/bin", ".local/share"):
        (home / relative).mkdir(parents=True, exist_ok=True)
    identity = ServiceIdentity(
        agent_id=agent,
        home=home.resolve(),
        root=root_path.resolve(),
        provider=str(provider or "").strip().casefold(),
        provisioned=True,
    )
    path = _identity_path(root_path)
    path.write_text(json.dumps(identity.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return identity


def service_identity_status(agent_id: str, *, provider: str = "", root: Path | None = None) -> dict[str, Any]:
    identity = provision_service_identity(agent_id, provider=provider, root=root)
    home = identity.home
    provider_name = str(provider or "").strip().casefold()
    auth_paths = {
        "twg": home / ".config" / "twg" / "auth.conf",
        "github": home / ".config" / "gh" / "hosts.yml",
        "codex": home / ".codex" / "auth.json",
        "cursor": home / ".cursor" / "auth.json",
    }
    binaries = {name: bool(shutil.which(name)) for name in ("git", "gh", "twg", "curl", "python3", "node")}
    if provider_name in {"codex", "cursor", "opencode"}:
        binaries[provider_name] = bool(shutil.which(provider_name) or shutil.which("agent" if provider_name == "cursor" else provider_name))
    return {
        "agent_id": identity.agent_id,
        "provider": provider_name,
        "home": str(home),
        "root": str(identity.root),
        "service_identity": f"agent:{identity.agent_id}",
        "personal_credentials_copied": False,
        "credential_store": identity.credential_store,
        "credentials": {name: path.is_file() for name, path in auth_paths.items()},
        "binaries": binaries,
        "ready": bool(binaries.get("git") and identity.provisioned),
    }


def configure_provider_reference(agent_id: str, provider: str, *, root: Path | None = None) -> dict[str, Any]:
    """Create a non-secret provider reference for an Agent service identity."""

    identity = provision_service_identity(agent_id, provider=provider, root=root)
    path = identity.root / "provider.json"
    payload = {
        "agent_id": identity.agent_id,
        "provider": str(provider or "").strip().casefold(),
        "credential_store": identity.credential_store,
        "home": str(identity.home),
        "account_selection": "host_configured",
        "secret_values": "never_written_by_lumon",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return payload


__all__ = [
    "ServiceIdentity",
    "configure_provider_reference",
    "provision_service_identity",
    "service_identity_status",
]
