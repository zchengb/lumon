"""The OS-enforced Agent World seam.

The disposable workspace is still created by the Host, but this module is the
small interface every provider process crosses before it starts.  On macOS we
use ``sandbox-exec`` when it is available.  The profile gives the child a
read/write world containing only its disposable workspace, service HOME and
temporary directory; the canonical workspace remains a Host-only path.

This is deliberately an adapter seam rather than a provider feature.  A
future container or VM adapter can satisfy the same interface without
changing Cursor, OpenCode, Codex, or the Session Host.
"""

from __future__ import annotations

import json
import os
import platform
import pwd
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from agents.runner.workspace_mounts import ensure_runner_dirs, runner_root
from agents.security.env import build_agent_env


AGENT_WORLD_CONTRACT = "agent-world/1"
_SYSTEM_READ_ROOTS = (
    "/System",
    "/usr",
    "/bin",
    "/sbin",
    "/private",
    "/opt/homebrew",
    "/Applications",
)


class AgentWorldError(RuntimeError):
    """Raised when a provider cannot be placed inside an Agent World."""


def _quote(value: str | Path) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def _configured_backend(config: Mapping[str, Any] | None = None) -> str:
    data = config if isinstance(config, Mapping) else {}
    security = data.get("agent_security") if isinstance(data.get("agent_security"), Mapping) else {}
    value = (
        os.environ.get("LUMON_AGENT_WORLD_BACKEND", "").strip()
        or str(security.get("agent_world_backend") or "").strip()
        or str(security.get("boundary_backend") or "").strip()
        or "auto"
    ).casefold().replace("-", "_")
    aliases = {
        "macos": "sandbox_exec",
        "sandbox": "sandbox_exec",
        "sandboxexec": "sandbox_exec",
        "docker_colima": "container",
        "docker": "container",
        "none": "host",
        "local": "host",
    }
    return aliases.get(value, value)


def _configured_unix_user(config: Mapping[str, Any] | None = None) -> str:
    data = config if isinstance(config, Mapping) else {}
    security = data.get("agent_security") if isinstance(data.get("agent_security"), Mapping) else {}
    configured = (
        os.environ.get("LUMON_AGENT_USER", "").strip()
        or str(security.get("agent_unix_user") or "").strip()
        or str(security.get("agent_user") or "").strip()
    )
    if configured:
        return configured
    raw_uid = os.environ.get("LUMON_AGENT_UID", "").strip()
    if raw_uid.isdigit():
        try:
            return str(pwd.getpwuid(int(raw_uid)).pw_name)
        except KeyError:
            pass
    return ""


def available_backends(config: Mapping[str, Any] | None = None) -> dict[str, bool]:
    """Report boundary adapters without starting a provider or container."""

    return {
        "sandbox_exec": platform.system() == "Darwin" and bool(shutil.which("sandbox-exec")),
        "container": bool(shutil.which("docker")),
        "unix_user": bool(_configured_unix_user(config) and shutil.which("sudo")),
        "host": True,
    }


def select_backend(config: Mapping[str, Any] | None = None) -> str:
    requested = _configured_backend(config)
    available = available_backends(config)
    if requested != "auto":
        return requested if requested in available and available[requested] else "unavailable"
    # The local macOS adapter is the strongest boundary that does not require
    # mutating the operator's account or starting a long-lived VM.
    if available["sandbox_exec"]:
        return "sandbox_exec"
    if available["container"] and os.environ.get("LUMON_AGENT_WORLD_ALLOW_CONTAINER") == "1":
        return "container"
    return "unavailable"


def _provider_read_paths() -> tuple[Path, ...]:
    """Allow provider executables/libraries while keeping the human HOME out."""

    paths: list[Path] = []
    for name in ("agent", "cursor-agent", "codex", "opencode", "node", "python3", "git", "twg", "gh"):
        path = shutil.which(name)
        if path:
            resolved = Path(path).expanduser().resolve()
            paths.extend([resolved, resolved.parent])
    for candidate in (Path.home() / ".codex" / "packages", Path.home() / ".nvm"):
        if candidate.exists():
            paths.append(candidate.resolve())
    for candidate in (
        Path(__file__).resolve().parents[2],
        Path.home() / ".lumon" / "lib",
        Path(sys.executable).expanduser().resolve(),
    ):
        if candidate.exists():
            paths.append(candidate.resolve())
    unique: list[Path] = []
    for item in paths:
        if item not in unique:
            unique.append(item)
    return tuple(unique)


def build_sandbox_profile(
    *,
    operator_home: Path,
    canonical: Path,
    world_root: Path,
    workspace: Path,
    service_home: Path,
    tmp: Path,
    provider_paths: Iterable[Path] = (),
) -> str:
    """Build a conservative macOS seatbelt profile.

    The profile intentionally has no rule for the canonical repository.  It
    is therefore unavailable even if the provider somehow learns its path.
    System/provider binaries are readable; writes are limited to Agent World
    paths and network is explicitly available.
    """

    read_roots = [Path(item) for item in _SYSTEM_READ_ROOTS if str(item) != "/private"]
    read_roots.extend(Path(item) for item in provider_paths)
    lines = [
        "(version 1)",
        '(import "system.sb")',
        "(deny default)",
        "(allow process-fork)",
        "(allow process-exec*)",
        "(allow file-read-metadata)",
        "(allow sysctl*)",
        "(allow mach-lookup)",
        "(allow signal)",
        "(allow ipc-posix-shm)",
        "(allow network*)",
    ]
    for root in read_roots:
        lines.append(f"(allow file-read* (subpath {_quote(root)}))")
    for executable in ("/usr/bin/sudo", "/bin/su", "/usr/bin/su", "/usr/bin/login"):
        lines.append(f"(deny process-exec (literal {_quote(executable)}))")
    # The operator HOME is denied after the broad system rules.  More specific
    # Agent World rules below reopen only the disposable/service directories.
    lines.append(f"(deny file-read* (subpath {_quote(operator_home)}))")
    lines.append(f"(deny file-write* (subpath {_quote(operator_home)}))")
    # The canonical checkout is denied explicitly even when it lives outside
    # the operator HOME (for example a mounted workspace or CI checkout).
    lines.append(f"(deny file-read* (subpath {_quote(canonical)}))")
    lines.append(f"(deny file-write* (subpath {_quote(canonical)}))")
    for root in (world_root, workspace, service_home, tmp):
        lines.append(f"(allow file-read* (subpath {_quote(root)}))")
        lines.append(f"(allow file-write* (subpath {_quote(root)}))")
    # Provider binaries may live in ~/.local/bin or ~/.nvm.  Read-only access
    # is enough; credentials remain in the service HOME.
    for root in provider_paths:
        lines.append(f"(allow file-read* (subpath {_quote(root)}))")
    lines.extend(
        [
            "(allow file-read* (literal \"/dev/null\"))",
            "(allow file-write* (literal \"/dev/null\"))",
            "(allow file-read* (literal \"/dev/urandom\"))",
            "(allow file-read* (literal \"/dev/random\"))",
        ]
    )
    return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class AgentWorldSpec:
    agent_id: str
    world_id: str
    backend: str
    root: Path
    workspace: Path
    service_home: Path
    tmp: Path
    canonical: Path
    canonical_access: str = "host_only"
    network: str = "allow"
    contract: str = AGENT_WORLD_CONTRACT
    operator_uid: int = -1
    agent_uid: int = -1
    agent_user: str = ""
    profile_path: Path | None = None
    command_prefix: tuple[str, ...] = field(default_factory=tuple)

    @property
    def boundary_enforced(self) -> bool:
        return self.backend in {"sandbox_exec", "container", "unix_user"}

    @property
    def dedicated_identity(self) -> bool:
        return self.agent_uid >= 0 and self.operator_uid >= 0 and self.agent_uid != self.operator_uid

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "world_id": self.world_id,
            "backend": self.backend,
            "root": str(self.root),
            "workspace": str(self.workspace),
            "service_home": str(self.service_home),
            "tmp": str(self.tmp),
            "canonical_access": self.canonical_access,
            "network": self.network,
            "contract": self.contract,
            "operator_uid": self.operator_uid,
            "agent_uid": self.agent_uid,
            "agent_user": self.agent_user,
            "boundary_enforced": self.boundary_enforced,
            "dedicated_identity": self.dedicated_identity,
            "profile_path": str(self.profile_path) if self.profile_path else "",
        }


class AgentWorld:
    """Host-owned lifecycle for one provider process world."""

    def __init__(self, spec: AgentWorldSpec) -> None:
        self.spec = spec
        self._closed = False

    @classmethod
    def create(
        cls,
        *,
        canonical: Path,
        workspace: Path,
        agent_id: str,
        config: Mapping[str, Any] | None = None,
        require_boundary: bool = True,
    ) -> "AgentWorld":
        canonical_path = Path(canonical).expanduser().resolve()
        workspace_path = Path(workspace).expanduser().resolve()
        if not workspace_path.is_dir():
            raise AgentWorldError(f"Agent workspace is not a directory: {workspace_path}")
        if workspace_path == canonical_path:
            raise AgentWorldError("canonical workspace cannot be mounted as the Agent workspace")
        agent = str(agent_id or "agent").strip().lower() or "agent"
        dirs = ensure_runner_dirs(agent)
        root = dirs["root"].resolve()
        world_id = f"world-{uuid.uuid4().hex[:16]}"
        backend = select_backend(config)
        if backend == "unavailable" and require_boundary:
            raise AgentWorldError(
                "no OS Agent World backend is available; install sandbox-exec support, "
                "configure a container/VM backend, or explicitly use the test-only host backend"
            )
        if backend == "unavailable":
            backend = "host"
        if backend == "container":
            # The container adapter is intentionally a separate seam. Until
            # it can mount the disposable workspace and forward the provider
            # command without host-path leakage, fail closed instead of
            # pretending that a bare Docker binary is an isolation boundary.
            raise AgentWorldError(
                "container Agent World backend is detected but not provisioned; "
                "use the macOS sandbox-exec backend or install the container adapter"
            )
        profile_path: Path | None = None
        prefix: tuple[str, ...] = ()
        agent_user = _configured_unix_user(config)
        agent_uid = -1
        if backend == "unix_user":
            sudo = shutil.which("sudo")
            if not sudo or not agent_user:
                raise AgentWorldError("unix_user Agent World requires LUMON_AGENT_USER and passwordless sudo")
            identity = subprocess.run(
                [sudo, "-n", "-u", agent_user, "--", "/usr/bin/id", "-u"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if identity.returncode != 0 or not identity.stdout.strip().isdigit():
                raise AgentWorldError(
                    f"configured Agent user {agent_user!r} is not available through passwordless sudo"
                )
            agent_uid = int(identity.stdout.strip())
            prefix = (sudo, "-n", "-u", agent_user, "--")
        if backend == "sandbox_exec":
            profile_dir = root / "profiles"
            profile_dir.mkdir(parents=True, exist_ok=True)
            profile_path = profile_dir / f"{world_id}.sb"
            profile_path.write_text(
                build_sandbox_profile(
                    operator_home=Path.home().expanduser().resolve(),
                    canonical=canonical_path,
                    world_root=root,
                    workspace=workspace_path,
                    service_home=dirs["home"],
                    tmp=dirs["tmp"],
                    provider_paths=_provider_read_paths(),
                ),
                encoding="utf-8",
            )
            profile_path.chmod(0o600)
            prefix = (str(shutil.which("sandbox-exec") or "/usr/bin/sandbox-exec"), "-f", str(profile_path))
        spec = AgentWorldSpec(
            agent_id=agent,
            world_id=world_id,
            backend=backend,
            root=root,
            workspace=workspace_path,
            service_home=dirs["home"].resolve(),
            tmp=dirs["tmp"].resolve(),
            canonical=canonical_path,
            operator_uid=int(getattr(os, "geteuid", lambda: -1)()),
            agent_uid=agent_uid,
            agent_user=agent_user,
            profile_path=profile_path,
            command_prefix=prefix,
        )
        return cls(spec)

    def environment(
        self,
        *,
        project: str = "",
        source: Mapping[str, str] | None = None,
        extra: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        values = {
            "HOME": str(self.spec.service_home),
            "TMPDIR": str(self.spec.tmp),
            "TMP": str(self.spec.tmp),
            "TEMP": str(self.spec.tmp),
            "LUMEN_AGENT_WORLD": "1",
            "LUMEN_AGENT_WORLD_ID": self.spec.world_id,
            "LUMEN_AGENT_WORLD_BACKEND": self.spec.backend,
            "LUMEN_AGENT_WORLD_CONTRACT": self.spec.contract,
            "LUMEN_CANONICAL_WORKSPACE": "host_only",
            "LUMEN_HOST_BOUNDARY": "closed",
            "LUMEN_ROOT_ESCALATION": "disabled",
            "PYTHONPATH": str(Path(__file__).resolve().parents[2]),
        }
        values.update({str(k): str(v) for k, v in (extra or {}).items()})
        env = build_agent_env(agent_id=self.spec.agent_id, project=project, extra=values, source=dict(source or os.environ))
        env.update({key: values[key] for key in ("HOME", "TMPDIR", "TMP", "TEMP")})
        # Never give the child a canonical path or host Lumon home.  The Host
        # retains both and performs publication after the child exits.
        env.pop("LUMEN_HOME", None)
        env.pop("LUMON_HOME", None)
        env.pop("LUMEN_CANONICAL_PATH", None)
        return env

    def command(self, command: Iterable[str]) -> list[str]:
        return [*self.spec.command_prefix, *(str(item) for item in command)]

    def contract_checks(self) -> dict[str, Any]:
        return {
            "backend": self.spec.backend,
            "boundary": "pass" if self.spec.boundary_enforced else "fail",
            "canonical": "host_only" if self.spec.canonical_access == "host_only" else "fail",
            "workspace_write": "pass" if self.spec.workspace.is_dir() else "fail",
            "service_home": "pass" if self.spec.service_home.is_dir() else "fail",
            "network": self.spec.network,
            "identity": "pass" if self.spec.dedicated_identity else "sandbox_uid_not_separate",
        }

    def close(self) -> None:
        if self._closed:
            return
        if self.spec.profile_path is not None:
            try:
                self.spec.profile_path.resolve().relative_to(self.spec.root)
                self.spec.profile_path.unlink(missing_ok=True)
            except (OSError, ValueError):
                pass
        self._closed = True

    def __enter__(self) -> "AgentWorld":
        return self

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self.close()


def probe_agent_world(*, agent_id: str = "probe", config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return a side-effect-free backend/capability report."""

    backends = available_backends(config)
    selected = select_backend(config)
    uid = int(getattr(os, "geteuid", lambda: -1)())
    checks = {
        "backend": selected,
        "available_backends": backends,
        "boundary_enforced": selected in {"sandbox_exec", "unix_user"},
        "dedicated_unix_identity": bool(os.environ.get("LUMON_AGENT_UID", "").strip())
        and str(os.environ.get("LUMON_AGENT_UID")).strip() != str(uid),
        "canonical_access": "host_only",
        "network": "allow",
        "operator_uid": uid,
    }
    warnings: list[str] = []
    if selected == "sandbox_exec" and not checks["dedicated_unix_identity"]:
        warnings.append("sandbox-exec enforces file/process access but does not change the Unix uid; configure a container/VM or LUMON_AGENT_UID for identity isolation")
    if selected == "container":
        warnings.append("Docker/Colima is detected, but no container adapter is provisioned; Lumon will not treat a bare Docker binary as a boundary")
    if selected in {"unavailable", "host"}:
        warnings.append("no OS-enforced Agent World backend is active")
    return {
        "contract": AGENT_WORLD_CONTRACT,
        "agent_id": str(agent_id or "probe").strip().lower(),
        "ready": bool(checks["boundary_enforced"] and checks["canonical_access"] == "host_only"),
        "checks": checks,
        "warnings": warnings,
    }


__all__ = [
    "AGENT_WORLD_CONTRACT",
    "AgentWorld",
    "AgentWorldError",
    "AgentWorldSpec",
    "available_backends",
    "build_sandbox_profile",
    "probe_agent_world",
    "select_backend",
]
