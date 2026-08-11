#!/usr/bin/env python3
"""Internal Visual Delivery contracts, runtime detection, diagnostics, and execution."""

from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import shlex
import shutil
import signal
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from pathlib import Path
from typing import Any

from delivery_workspace import (
    StoryContext,
    frontend_delivery_disabled_reasons,
    read_json,
    workspace_lumen_dir,
    write_json,
)


FAILURE_CATEGORIES = {
    "environment_failed",
    "dependency_failed",
    "runtime_failed",
    "readiness_failed",
    "authentication_failed",
    "browser_start_failed",
    "browser_connection_failed",
    "fixture_failed",
    "navigation_failed",
    "observation_failed",
    "interaction_failed",
    "stability_failed",
    "capture_failed",
    "session_unhealthy",
    "visual_difference",
    "cleanup_failed",
    "frontend_delivery_disabled",
}

# Keep Lumen-owned Metro off the app-dev default (8081).
LUMEN_METRO_PORT = 8091


def metro_ready_url(port: int = LUMEN_METRO_PORT) -> str:
    return f"http://127.0.0.1:{port}/status"


def metro_start_command(manager: str, script: str, port: int = LUMEN_METRO_PORT) -> str:
    if manager == "npm":
        return f"npm run {script} -- --port {port}"
    return f"{manager} {script} --port {port}"


def visual_section(text: str) -> str:
    text = re.sub(r"(?s)<!--.*?-->", "", text)
    return heading_section(text, "Visual Delivery Contract")


def subsection(text: str, title: str) -> str:
    return heading_section(text, title)


def heading_section(text: str, title: str) -> str:
    headings = list(re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", text))
    for index, heading in enumerate(headings):
        if heading.group(2).strip() != title:
            continue
        level = len(heading.group(1))
        end = len(text)
        for following in headings[index + 1:]:
            if len(following.group(1)) <= level:
                end = following.start()
                break
        return text[heading.end():end].strip()
    return ""


def markdown_table(text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []
    rows = [[cell.strip().strip("`") for cell in line.strip("|").split("|")] for line in lines]
    headers = rows[0]
    if not all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in rows[1]):
        return []
    return [dict(zip(headers, row)) for row in rows[2:] if len(row) == len(headers)]


def visual_contract(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    section = visual_section(path.read_text(encoding="utf-8", errors="ignore"))
    if not section:
        return None
    runtime_rows = markdown_table(subsection(section, "Runtime"))
    runtime = {
        row.get("Property", "").strip().lower().replace(" ", "_"): row.get("Value", "").strip()
        for row in runtime_rows
    }
    references = markdown_table(subsection(section, "Design Source"))
    states = markdown_table(subsection(section, "Visual State Matrix"))
    verification = markdown_table(subsection(section, "Visual Verification"))
    mappings = markdown_table(subsection(section, "Figma-to-Code Component Mapping"))
    checks = {
        (row.get("Screen", ""), row.get("State", "")): row for row in verification
    }
    scenarios: list[dict[str, Any]] = []
    for row in states:
        screen, state = row.get("Screen", ""), row.get("State", "")
        check = checks.get((screen, state), {})
        threshold = str(check.get("Maximum difference", "1%")).strip()
        ratio: float | None = None
        if threshold.upper() != "N/A":
            try:
                ratio = float(threshold.rstrip("%")) / (100 if threshold.endswith("%") else 1)
            except ValueError:
                ratio = None
        scenarios.append(
            {
                "screen": screen,
                "state": state,
                "fixture": row.get("Fixture", ""),
                "reference": row.get("Reference", ""),
                "stable_marker": row.get("Stable marker", ""),
                "maestro_flow": row.get("Maestro flow", ""),
                "navigation": row.get("Navigation", ""),
                "viewport": row.get("Viewport", ""),
                "comparison": check.get("Comparison", "Full content area"),
                "maximum_difference_ratio": ratio,
                "maximum_difference": threshold,
            }
        )
    return {
        "runtime": runtime,
        "references": references,
        "states": states,
        "mappings": mappings,
        "platform_rules": subsection(section, "Platform Rules"),
        "scenarios": scenarios,
    }


def validate_contract(contract: dict[str, Any]) -> list[str]:
    runtime = contract.get("runtime", {})
    def absent(value: Any) -> bool:
        return not str(value or "").strip() or str(value).strip().upper() == "TBD"
    missing = [
        label for key, label in (
            ("repository", "target repository"),
            ("runtime_profile", "runtime profile"),
            ("platform", "platform"),
            ("navigation", "navigation"),
            ("authentication", "authentication"),
        ) if absent(runtime.get(key))
    ]
    if not contract.get("references") or not any(
        not absent(row.get("Node ID")) or not absent(row.get("Approved reference"))
        for row in contract.get("references", [])
    ):
        missing.append("Figma node or approved reference")
    for row in contract.get("references", []):
        figma_file = str(row.get("Figma file", "")).strip()
        snapshot = str(row.get("Design context snapshot", "")).strip()
        if "figma.com" in figma_file and absent(snapshot):
            missing.append("Figma design context snapshot")
    if not contract.get("scenarios"):
        missing.append("required visual states")
    else:
        for index, item in enumerate(contract["scenarios"], 1):
            for key in ("screen", "state", "fixture", "reference", "stable_marker"):
                if absent(item.get(key)):
                    missing.append(f"visual state {index} {key.replace('_', ' ')}")
            if str(item.get("maximum_difference", "")).strip().upper() == "TBD":
                missing.append(f"visual state {index} verification expectation")
    if not contract.get("mappings") or all(absent(row.get("Figma component")) for row in contract.get("mappings", [])):
        missing.append("component mapping")
    if absent(contract.get("platform_rules")):
        missing.append("platform-specific behavior")
    return missing


def matching_scenarios(contract: dict[str, Any] | None, screen: str = "", state: str = "") -> list[dict[str, Any]]:
    return [
        item for item in (contract or {}).get("scenarios", [])
        if (not screen or item.get("screen") == screen) and (not state or item.get("state") == state)
    ]


def package_manager(repo: Path) -> str:
    for lock, manager in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("package-lock.json", "npm")):
        if (repo / lock).is_file():
            return manager
    return "npm"


def package_scripts(repo: Path) -> dict[str, str]:
    package = read_json(repo / "package.json", {})
    scripts = package.get("scripts") if isinstance(package.get("scripts"), dict) else {}
    return {str(key): str(value) for key, value in scripts.items()}


def detect_runtime(repo: Path) -> tuple[str, dict[str, Any]] | None:
    if not (repo / "package.json").is_file():
        return None
    manager = package_manager(repo)
    scripts = package_scripts(repo)
    package = read_json(repo / "package.json", {})
    dependencies = {**(package.get("dependencies") or {}), **(package.get("devDependencies") or {})}
    install = f"{manager} install" + (" --frozen-lockfile" if manager == "pnpm" else "")
    is_mobile = bool({"react-native", "expo"} & set(dependencies)) or any((repo / name).exists() for name in ("ios", "android", "app.json"))
    if is_mobile:
        metro_script = "start" if "start" in scripts else ""
        runtime = {
            "platform": "react-native",
            "package_manager": manager,
            "install_command": install,
            "metro_command": metro_start_command(manager, metro_script) if metro_script else "",
            "metro_port": LUMEN_METRO_PORT,
            "ready_url": metro_ready_url(),
            "launch_strategy": "preinstalled-debug-app",
            "auth_strategy": "saved-session",
            "fixture_strategy": "",
            "ios": {"device": "iPhone 15", "os_version": ""},
            "ready_timeout_seconds": 120,
        }
        return "react-native-ios-visual", {"runtime_status": "incomplete", "runtime": runtime}
    start_script = next((name for name in ("dev", "start:dev", "start") if name in scripts), "")
    web_evidence = (
        any(repo.glob("vite.config.*"))
        or any(repo.glob("next.config.*"))
        or "react-scripts" in dependencies
        or bool(start_script)
    )
    if not web_evidence:
        return None
    start = f"{manager} run {start_script}" if manager == "npm" else f"{manager} {start_script}"
    port = 3000 if any(repo.glob("next.config.*")) or "react-scripts" in dependencies else 5173
    runtime = {
        "platform": "web",
        "package_manager": manager,
        "install_command": install,
        "start_command": start,
        "base_url": f"http://127.0.0.1:{port}",
        "ready_url": f"http://127.0.0.1:{port}",
        "ready_timeout_seconds": 60,
        "browser_mode": "managed",
        "browser": "chromium",
        "browser_cdp_url": "",
        "viewport": {"width": 1440, "height": 900},
        "test_id_attribute": "data-testid",
        "auth_strategy": "login-endpoint",
        "auth_identity": "configured identity",
        "auth_credential_env": "LUMEN_VISUAL_AUTH_REPOSITORY",
        "auth_storage_state_env": "LUMEN_WEB_STORAGE_STATE",
        "fixture_strategy": "",
    }
    return "web-visual", {"runtime_status": "incomplete", "runtime": runtime}


def repos_config(workspace_root: Path) -> Path:
    return workspace_lumen_dir(workspace_root) / "config" / "repos.json"


def resolve_visual_fixture_file(
    workspace_root: Path,
    story_dir: Path,
    repo_path: Path,
    runtime: dict[str, Any],
) -> Path | None:
    configured = str(runtime.get("fixture_file", "")).strip()
    if not configured:
        return None
    candidate = Path(configured).expanduser()
    if candidate.is_absolute():
        return candidate
    for base in (story_dir, workspace_root, repo_path):
        resolved = (base / candidate).resolve()
        if resolved.is_file():
            return resolved
    return (workspace_root / candidate).resolve()


def local_runtime_port_in_use(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    if host not in {"localhost", "127.0.0.1", "::1"}:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False


def visual_auth_env_name(repository: str, runtime: dict[str, Any]) -> str:
    configured = str(runtime.get("auth_credential_env", "")).strip()
    if configured:
        return configured
    slug = re.sub(r"[^A-Za-z0-9]+", "_", repository).strip("_").upper()
    return f"LUMEN_VISUAL_AUTH_{slug}"


def workspace_root_from(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    if resolved.name in {"lumon", "lumen", ".lumen"}:
        return resolved.parent
    return resolved


def repo_config_entry(config: dict[str, Any], repository: str) -> dict[str, Any] | None:
    for item in config.get("repositories", []):
        if isinstance(item, dict) and str(item.get("name", "")).strip() == repository:
            return item
    return None


def list_visual_auth_credentials(path: Path) -> dict[str, str]:
    workspace_root = workspace_root_from(path)
    config = read_json(repos_config(workspace_root), {"repositories": []})
    env_values: dict[str, str] = {}
    env_path = workspace_lumen_dir(workspace_root) / ".env.local"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                env_values[key.strip()] = value.strip().strip("\"'")
    credentials: dict[str, str] = {}
    for item in config.get("repositories", []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        runtime = item.get("runtime")
        if not name or not isinstance(runtime, dict):
            continue
        credential = str(runtime.get("visual_auth_credential", "") or env_values.get(visual_auth_env_name(name, runtime), "")).strip()
        if credential:
            credentials[name] = credential
    return credentials


def set_visual_auth_credential(path: Path, repository: str, credential: str) -> None:
    credential = str(credential).strip()
    if not credential:
        raise ValueError("credential must not be empty")
    workspace_root = workspace_root_from(path)
    config_path = repos_config(workspace_root)
    config = read_json(config_path, {"repositories": []})
    entry = repo_config_entry(config, repository)
    if entry is None:
        raise ValueError(f"repository '{repository}' is not configured in {config_path}")
    runtime = entry.setdefault("runtime", {})
    if not isinstance(runtime, dict):
        runtime = {}
        entry["runtime"] = runtime
    env_name = visual_auth_env_name(repository, runtime)
    runtime["visual_auth_credential"] = credential
    runtime.pop("auth_credential_env", None)
    write_json(config_path, config)
    env_path = workspace_lumen_dir(workspace_root) / ".env.local"
    if env_path.is_file():
        lines = [line for line in env_path.read_text(encoding="utf-8").splitlines() if not line.startswith(f"{env_name}=")]
        env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def resolve_visual_auth_credential(runtime: dict[str, Any], env: dict[str, str]) -> str:
    direct = str(runtime.get("visual_auth_credential", "")).strip()
    if direct:
        return direct
    env_name = str(runtime.get("auth_credential_env", "")).strip()
    if env_name and str(env.get(env_name, "")).strip():
        return str(env[env_name]).strip()
    return ""


def enrich_repositories(workspace_root: Path) -> list[dict[str, Any]]:
    path = repos_config(workspace_root)
    config = read_json(path, {"repositories": []})
    repositories = config.get("repositories") if isinstance(config.get("repositories"), list) else []
    for item in repositories:
        if not isinstance(item, dict) or item.get("runtime"):
            continue
        repo = Path(str(item.get("path", ""))).expanduser()
        if not repo.is_absolute():
            repo = (workspace_root / repo).resolve()
        detected = detect_runtime(repo)
        if detected:
            profile, values = detected
            item["runtime_profile"] = profile
            item.update(values)
    config["repositories"] = repositories
    write_json(path, config)
    return repositories


def redact(text: str, env: dict[str, str]) -> str:
    redacted = text
    for key, value in env.items():
        if value and len(value) >= 4 and (key.startswith("LUMEN_VISUAL_") or key == "LUMEN_WEB_AUTH_CREDENTIAL" or any(word in key.upper() for word in ("PASSWORD", "SECRET", "TOKEN"))):
            redacted = redacted.replace(value, "[REDACTED]")
    return redacted


def web_auth_storage_path(runtime: dict[str, Any], env: dict[str, str]) -> str:
    state_env = str(runtime.get("auth_storage_state_env", "LUMEN_WEB_STORAGE_STATE"))
    return str(env.get(state_env, "")).strip()


def web_auth_auto_login_configured(runtime: dict[str, Any], env: dict[str, str]) -> bool:
    login_path = str(runtime.get("auth_login_path", "")).strip()
    if not login_path:
        return False
    return bool(resolve_visual_auth_credential(runtime, env))


def web_auth_ready(runtime: dict[str, Any], env: dict[str, str]) -> bool:
    strategy = str(runtime.get("auth_strategy", "existing-session")).strip().casefold()
    if strategy in {"existing-session", "saved-session"}:
        return str(runtime.get("browser_mode", "managed")).strip().casefold() == "cdp" and bool(runtime.get("browser_cdp_url"))
    if strategy in {"login-endpoint", "fake-login"}:
        return bool(str(runtime.get("auth_login_path", "")).strip()) and bool(resolve_visual_auth_credential(runtime, env))
    if strategy in {"storage-state", "playwright-storage-state"}:
        if web_auth_auto_login_configured(runtime, env) and str(runtime.get("auth_login_path", "")).strip():
            return True
        storage = web_auth_storage_path(runtime, env)
        return bool(storage) and Path(storage).is_file()
    return False


def fixture_auth_ready(runtime: dict[str, Any], env: dict[str, str]) -> bool:
    fixture_command = str(runtime.get("fixture_command", ""))
    if "{fixture}" not in fixture_command:
        return True
    return bool(resolve_visual_auth_credential(runtime, env))


def dependencies_installed(repo: Path, runtime: Optional[dict[str, Any]] = None) -> bool:
    node_modules = repo / "node_modules"
    if not node_modules.is_dir():
        return False
    return not runtime or runtime.get("platform") != "web" or (node_modules / "playwright").is_dir()


def configured_node_version(repo: Path, runtime: dict[str, Any]) -> str:
    configured = str(runtime.get("node_version", "")).strip()
    if configured:
        return configured
    for name in (".nvmrc", ".node-version"):
        path = repo / name
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    return ""


def runtime_command(repo: Path, runtime: dict[str, Any], command: str) -> list[str]:
    version = configured_node_version(repo, runtime)
    if not version:
        return shlex.split(command)
    nvm_dir = Path(os.environ.get("NVM_DIR", Path.home() / ".nvm"))
    nvm = nvm_dir / "nvm.sh"
    if not nvm.is_file():
        raise EnvironmentError(f"Node {version} is required but nvm.sh was not found; set NVM_DIR or install nvm")
    return ["bash", "-lc", f"source {shlex.quote(str(nvm))} && nvm install {shlex.quote(version)} >/dev/null && nvm exec {shlex.quote(version)} bash -lc {shlex.quote(command)}"]


def ensure_dependencies(repo: Path, runtime: dict[str, Any], env: dict[str, str]) -> None:
    if dependencies_installed(repo, runtime):
        return
    command = str(runtime.get("install_command", "")).strip()
    if not command:
        raise EnvironmentError("dependencies are missing and install_command is not configured")
    print(f"[visual] Installing dependencies in {repo}", flush=True)
    installed = subprocess.run(runtime_command(repo, runtime, command), cwd=repo, env=env, check=False, capture_output=True, text=True)
    if installed.returncode != 0:
        detail = redact((installed.stderr or installed.stdout or "dependency install failed").strip(), env)
        raise EnvironmentError(detail[-500:])


def prepare_web_auth_storage(
    repo: Path,
    runtime: dict[str, Any],
    env: dict[str, str],
    output: Path,
) -> str:
    strategy = str(runtime.get("auth_strategy", "")).strip().casefold()
    if strategy not in {"playwright-storage-state", "storage-state", "login-endpoint", "fake-login"}:
        return ""
    state_env = str(runtime.get("auth_storage_state_env", "LUMEN_WEB_STORAGE_STATE"))
    username = resolve_visual_auth_credential(runtime, env)
    login_path = str(runtime.get("auth_login_path", "")).strip()
    login_field = str(runtime.get("auth_login_field", "wiw")).strip() or "wiw"
    if username and login_path:
        base = str(runtime.get("base_url", "")).rstrip("/")
        output.parent.mkdir(parents=True, exist_ok=True)
        body = json.dumps({login_field: username})
        script = """
const { chromium } = require('playwright');
(async () => {
  const [baseUrl, loginPath, bodyJson, outPath, cdpUrl] = process.argv.slice(1);
  const browser = cdpUrl ? await chromium.connectOverCDP(cdpUrl) : await chromium.launch({ headless: true });
  const context = cdpUrl ? browser.contexts()[0] : await browser.newContext({ ignoreHTTPSErrors: true });
  const page = await context.newPage();
  if (cdpUrl) await (await context.newCDPSession(page)).send('Security.setIgnoreCertificateErrors', { ignore: true });
  await page.goto(`${baseUrl}/user/login`, { waitUntil: 'domcontentloaded' });
  if (cdpUrl) {
    const response = await page.evaluate(async ({ url, body }) => { const reply = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body }); return { ok: reply.ok, status: reply.status, detail: await reply.text() }; }, { url: `${baseUrl}${loginPath}`, body: bodyJson });
    if (!response.ok) throw new Error(`fake login failed (${response.status}): ${response.detail}`);
  } else {
    const response = await page.request.post(`${baseUrl}${loginPath}`, { data: JSON.parse(bodyJson) });
    if (!response.ok()) throw new Error(`fake login failed (${response.status()}): ${await response.text()}`);
  }
  await page.goto(`${baseUrl}/`, { waitUntil: 'networkidle' });
  await context.storageState({ path: outPath });
  await browser.close();
})().catch((error) => { console.error(error.message); process.exit(1); });
"""
        completed = subprocess.run(
            ["node", "-e", script, base, login_path, body, str(output), str(runtime.get("browser_cdp_url", ""))],
            cwd=repo, env=env, check=False, capture_output=True, text=True,
        )
        if completed.returncode != 0:
            detail = redact((completed.stderr or completed.stdout or "fake login failed").strip(), env)
            if "Cannot find module 'playwright'" in detail:
                raise ModuleNotFoundError("Playwright is not installed in the repository")
            raise PermissionError(detail[-500:])
        env[state_env] = str(output)
        return str(output)
    storage = web_auth_storage_path(runtime, env)
    if storage and Path(storage).is_file():
        return storage
    raise PermissionError(
        f"configure visual auth with: lumen config set-visual-auth <repository> <credential>, "
        f"or provide a storage state file in {state_env}"
    )


def doctor(workspace_root: Path) -> int:
    repositories = read_json(repos_config(workspace_root), {}).get("repositories", [])
    configured = [item for item in repositories if isinstance(item, dict) and isinstance(item.get("runtime"), dict)]
    if not configured:
        print("Visual Delivery: Not Configured")
        return 0
    failed = False
    for item in configured:
        name = str(item.get("name", "repository"))
        runtime = item["runtime"]
        platform = str(runtime.get("platform", ""))
        problems: list[str] = []
        manager = str(runtime.get("package_manager", ""))
        if not manager or not shutil.which(manager):
            problems.append(f"package manager '{manager or 'missing'}' is not available")
        if platform == "web":
            if not runtime.get("start_command"):
                problems.append("start_command is missing")
            if not runtime.get("ready_url"):
                problems.append("ready_url is missing")
            for key in ("base_url", "ready_url"):
                value = str(runtime.get(key, "")).strip()
                parsed = urllib.parse.urlparse(value)
                if value and parsed.scheme not in {"http", "https"}:
                    problems.append(f"{key} must be an http(s) URL")
            if not shutil.which("node"):
                problems.append("Node.js is not available")
            repo = Path(str(item.get("path", ""))).expanduser()
            if not repo.is_absolute():
                repo = (workspace_root / repo).resolve()
            mode = str(runtime.get("browser_mode", "managed")).strip().casefold()
            if mode not in {"managed", "cdp"}:
                problems.append("browser_mode must be managed or cdp")
            if mode == "cdp":
                cdp = str(runtime.get("browser_cdp_url", "")).strip()
                if not cdp:
                    problems.append("browser_cdp_url is missing for CDP mode")
                else:
                    try:
                        with urllib.request.urlopen(f"{cdp.rstrip('/')}/json/version", timeout=2) as response:
                            if response.status >= 500:
                                raise urllib.error.URLError("CDP endpoint returned an error")
                    except (OSError, urllib.error.URLError):
                        problems.append(f"Chrome CDP URL is not reachable: {cdp}")
            elif not (repo / "node_modules" / "playwright").is_dir():
                problems.append("Playwright is not installed in the repository; run the configured install command")
            if not web_auth_ready(runtime, dict(os.environ)):
                strategy = str(runtime.get("auth_strategy", "existing-session")).strip()
                if strategy in {"storage-state", "playwright-storage-state"}:
                    storage_env = str(runtime.get("auth_storage_state_env", "LUMEN_WEB_STORAGE_STATE"))
                    storage = web_auth_storage_path(runtime, dict(os.environ))
                    if not storage:
                        problems.append(f"authentication state environment variable '{storage_env}' is not set")
                    elif not Path(storage).is_file():
                        problems.append(f"authentication storage state file '{storage}' does not exist")
                elif strategy in {"login-endpoint", "fake-login"}:
                    problems.append(f"authentication variable {visual_auth_env_name(name, runtime)} is not set")
                elif strategy in {"existing-session", "saved-session"}:
                    problems.append("existing-session requires browser_mode=cdp and browser_cdp_url")
                else:
                    problems.append(f"unsupported authentication strategy: {strategy or 'missing'}")
            evidence = workspace_lumen_dir(workspace_root) / "results" / "web-session"
            try:
                evidence.mkdir(parents=True, exist_ok=True)
                probe = evidence / ".write-test"
                probe.write_text("", encoding="utf-8")
                probe.unlink()
            except OSError:
                problems.append(f"Web-session evidence directory is not writable: {evidence}")
        elif platform == "react-native":
            for tool in ("xcrun", "maestro"):
                if not shutil.which(tool):
                    problems.append(f"{tool} is not available")
            device = str((runtime.get("ios") or {}).get("device", ""))
            if not device:
                problems.append("iOS simulator device is missing")
            elif shutil.which("xcrun"):
                devices = subprocess.run(["xcrun", "simctl", "list", "devices", "available"], check=False, capture_output=True, text=True)
                if devices.returncode != 0 or device not in devices.stdout:
                    problems.append(f"configured simulator '{device}' was not found")
            if not runtime.get("metro_command"):
                problems.append("metro_command is missing")
            if not runtime.get("bundle_id"):
                problems.append("bundle_id is missing")
            if not runtime.get("deep_link_scheme"):
                problems.append("deep_link_scheme is missing")
            ios = runtime.get("ios") if isinstance(runtime.get("ios"), dict) else {}
            for key in ("build_command", "app_path"):
                if not ios.get(key):
                    problems.append(f"ios.{key} is missing")
            if not runtime.get("maestro_flow") and not runtime.get("settle_seconds"):
                problems.append("maestro_flow or an explicit settle_seconds fallback is missing")
        if not runtime.get("fixture_strategy"):
            problems.append("fixture_strategy is missing")
        elif runtime.get("fixture_strategy") in {"mock-server", "local-fixture-server", "seed-endpoint"} and not (
            runtime.get("fixture_command") or runtime.get("fixture_start_command")
        ):
            problems.append("configured fixture strategy has no fixture command")
        elif runtime.get("fixture_strategy") == "playwright-route":
            fixture_file = resolve_visual_fixture_file(workspace_root, workspace_root, repo, runtime)
            if not fixture_file or not fixture_file.is_file():
                problems.append("configured Playwright fixture file is missing")
        if not fixture_auth_ready(runtime, dict(os.environ)):
            problems.append(
                f"visual auth credential for '{name}' is not set; "
                f"run: lumen config set-visual-auth {name} <credential>"
            )
        status = "Not Ready" if problems or item.get("runtime_status") != "ready" else "Ready"
        print(f"\nVisual Delivery: {status}\nRepository: {name}\nPlatform: {platform or 'unknown'}")
        if problems:
            failed = True
            for problem in problems:
                print(f"✗ {problem}")
            print(f"Fix: update {repos_config(workspace_root)} for repository '{name}'.")
        else:
            print("✓ runtime configuration and local tooling are ready")
    return 1 if failed else 0


def run_owned(command: str, cwd: Path, env: dict[str, str], processes: list[subprocess.Popen[str]], runtime: dict[str, Any] | None = None) -> subprocess.Popen[str]:
    fd, log_path = tempfile.mkstemp(prefix="lumen-runtime-", suffix=".log")
    log = os.fdopen(fd, "w", encoding="utf-8")
    process = subprocess.Popen(
        runtime_command(cwd, runtime, command) if runtime else shlex.split(command), cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
        text=True, start_new_session=True,
    )
    process._lumen_runtime_log = log  # type: ignore[attr-defined]
    process._lumen_runtime_log_path = Path(log_path)  # type: ignore[attr-defined]
    processes.append(process)
    return process


def ensure_ios_app(repo: Path, runtime: dict[str, Any], env: dict[str, str]) -> None:
    ios = runtime.get("ios") if isinstance(runtime.get("ios"), dict) else {}
    device, bundle_id = str(ios.get("device", "")), str(runtime.get("bundle_id", ""))
    build, app_path = str(ios.get("build_command", "")), str(ios.get("app_path", ""))
    if not device or not bundle_id or not build or not app_path:
        raise EnvironmentError("iOS visual runtime requires device, bundle_id, ios.build_command, and ios.app_path")
    subprocess.run(["xcrun", "simctl", "boot", device], check=False, capture_output=True, text=True)
    boot = subprocess.run(["xcrun", "simctl", "bootstatus", device, "-b"], check=False, capture_output=True, text=True)
    if boot.returncode != 0:
        raise EnvironmentError(redact((boot.stderr or boot.stdout).strip(), env))
    installed = subprocess.run(["xcrun", "simctl", "get_app_container", device, bundle_id], check=False, capture_output=True, text=True)
    if installed.returncode == 0:
        return
    pods = str(ios.get("pod_install_command", "")).strip()
    if pods:
        prepared = subprocess.run(shlex.split(pods), cwd=repo, env=env, check=False, capture_output=True, text=True)
        if prepared.returncode != 0:
            raise EnvironmentError(redact((prepared.stderr or prepared.stdout or "pod install failed").strip(), env)[-500:])
    built = subprocess.run(shlex.split(build), cwd=repo, env=env, check=False, capture_output=True, text=True)
    if built.returncode != 0:
        raise EnvironmentError(redact((built.stderr or built.stdout or "iOS build failed").strip(), env)[-500:])
    app = repo / app_path
    if not app.is_dir():
        raise EnvironmentError(f"iOS build did not produce {app}")
    deployed = subprocess.run(["xcrun", "simctl", "install", device, str(app)], check=False, capture_output=True, text=True)
    if deployed.returncode != 0:
        raise EnvironmentError(redact((deployed.stderr or deployed.stdout).strip(), env))


def runtime_log_tail(process: subprocess.Popen[str], env: dict[str, str]) -> str:
    log = getattr(process, "_lumen_runtime_log", None)
    path = getattr(process, "_lumen_runtime_log_path", None)
    if log:
        log.flush()
    if not isinstance(path, Path) or not path.is_file():
        return ""
    return redact(path.read_text(encoding="utf-8", errors="ignore"), env)[-1000:].strip()


def wait_ready(url: str, timeout: int, process: subprocess.Popen[str] | None = None, env: dict[str, str] | None = None) -> None:
    parsed = urllib.parse.urlparse(url)
    context = ssl._create_unverified_context() if parsed.scheme == "https" and parsed.hostname in {"localhost", "127.0.0.1", "::1"} else None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process and process.poll() is not None:
            detail = runtime_log_tail(process, env or {})
            raise RuntimeError(f"configured runtime process exited before readiness{': ' + detail if detail else ''}")
        try:
            with urllib.request.urlopen(url, timeout=2, context=context) as response:
                if response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            time.sleep(0.5)
    detail = runtime_log_tail(process, env or {}) if process else ""
    raise TimeoutError(f"readiness URL did not respond within {timeout}s: {url}{': ' + detail if detail else ''}")


def web_capture(repo: Path, runtime: dict[str, Any], scenario: dict[str, Any], actual: Path, env: dict[str, str], fixture_file: Path | None = None) -> None:
    base = str(runtime.get("base_url", "")).rstrip("/")
    navigation = str(scenario.get("navigation", ""))
    url = navigation if navigation.startswith(("http://", "https://")) else f"{base}/{navigation.lstrip('/')}"
    marker = str(scenario.get("stable_marker", ""))
    state_env = str(runtime.get("auth_storage_state_env", "LUMEN_WEB_STORAGE_STATE"))
    storage = env.get(state_env, "") if str(runtime.get("auth_strategy", "")).strip().casefold() in {"playwright-storage-state", "storage-state", "login-endpoint", "fake-login"} else ""
    if str(runtime.get("auth_strategy", "")).strip().casefold() in {"playwright-storage-state", "storage-state", "login-endpoint", "fake-login"} and (not storage or not Path(storage).is_file()):
        raise PermissionError(
            f"storage state from {state_env} is unavailable; run visual verification after runtime startup prepares auth"
        )
    viewport = dict(runtime.get("viewport") or {}) if isinstance(runtime.get("viewport"), dict) else {"width": 1280, "height": 720}
    if match := re.fullmatch(r"\s*(\d+)\s*[x×]\s*(\d+)\s*", str(scenario.get("viewport", ""))):
        viewport = {"width": int(match.group(1)), "height": int(match.group(2))}
    script = """
const { chromium } = require('playwright');
(async () => { const [url,out,marker,storage,width,height,cdpUrl,testIdAttribute] = process.argv.slice(1);
 const browser = cdpUrl ? await chromium.connectOverCDP(cdpUrl) : await chromium.launch({headless:true});
 const context = cdpUrl ? browser.contexts()[0] : await browser.newContext({viewport:{width:+width,height:+height}, locale:'en-US', timezoneId:'UTC', ...(storage?{storageState:storage}:{})});
 const page = await context.newPage(); if(cdpUrl) { await page.setViewportSize({width:+width,height:+height}); await (await context.newCDPSession(page)).send('Security.setIgnoreCertificateErrors',{ignore:true}); }
 const fixtureFile = process.argv[9] || ''; if(fixtureFile) { const { installPlaywrightFixtures } = require(process.argv[10]); await installPlaywrightFixtures(page, fixtureFile); }
 await page.goto(url,{waitUntil:'networkidle'});
 if(marker) await (testIdAttribute === 'data-testid' ? page.getByTestId(marker) : page.locator(`[${testIdAttribute}="${marker}"]`)).waitFor({state:'visible'});
 await page.addStyleTag({content:'*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}'});
 await page.screenshot({path:out,fullPage:false}); await browser.close();
})().catch(e=>{console.error(e.message);process.exit(1)});
"""
    completed = subprocess.run(
        ["node", "-e", script, url, str(actual), marker, storage, str(viewport.get("width", 1280)), str(viewport.get("height", 720)), str(runtime.get("browser_cdp_url", "")), str(runtime.get("test_id_attribute", "data-testid")), str(fixture_file or ""), str(Path(__file__).with_name("playwright_fixtures.js"))],
        cwd=repo, env=env, check=False, capture_output=True, text=True,
    )
    if completed.returncode != 0:
        detail = redact((completed.stderr or completed.stdout or "Playwright screenshot failed").strip(), env)
        if "waiting for getByTestId" in detail or "Timeout" in detail:
            raise TimeoutError(detail[-500:])
        if "Cannot find module 'playwright'" in detail:
            raise ModuleNotFoundError("Playwright is not installed in the repository")
        raise RuntimeError(detail[-500:])


def png_pixels(path: Path) -> tuple[int, int, int, bytes]:
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"not a PNG image: {path}")
    offset, width, height, channels, compressed = 8, 0, 0, 0, bytearray()
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind, chunk = data[offset + 4:offset + 8], data[offset + 8:offset + 8 + length]
        offset += length + 12
        if kind == b"IHDR":
            width, height, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
            if depth != 8 or color not in {2, 6} or interlace:
                raise ValueError("Visual Delivery supports non-interlaced 8-bit RGB/RGBA PNG references")
            channels = 3 if color == 2 else 4
        elif kind == b"IDAT":
            compressed.extend(chunk)
        elif kind == b"IEND":
            break
    raw, stride, rows, previous = zlib.decompress(bytes(compressed)), width * channels, bytearray(), bytearray(width * channels)
    pos = 0
    for _ in range(height):
        mode, row = raw[pos], bytearray(raw[pos + 1:pos + 1 + stride]); pos += stride + 1
        for index in range(stride):
            left = row[index - channels] if index >= channels else 0
            up = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if mode == 1: row[index] = (row[index] + left) & 255
            elif mode == 2: row[index] = (row[index] + up) & 255
            elif mode == 3: row[index] = (row[index] + ((left + up) // 2)) & 255
            elif mode == 4:
                p = left + up - upper_left; pa, pb, pc = abs(p-left), abs(p-up), abs(p-upper_left)
                row[index] = (row[index] + (left if pa <= pb and pa <= pc else up if pb <= pc else upper_left)) & 255
            elif mode != 0: raise ValueError(f"unsupported PNG filter {mode}")
        rows.extend(row); previous = row
    return width, height, channels, bytes(rows)


def write_diff(path: Path, width: int, height: int, pixels: bytes) -> None:
    raw = b"".join(b"\0" + pixels[row * width * 3:(row + 1) * width * 3] for row in range(height))
    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def compare_png(expected: Path, actual: Path, diff: Path) -> float:
    ew, eh, ec, ep = png_pixels(expected); aw, ah, ac, ap = png_pixels(actual)
    if (ew, eh) != (aw, ah):
        raise ValueError(f"image dimensions differ: expected {ew}x{eh}, actual {aw}x{ah}")
    changed, out = 0, bytearray()
    for pixel in range(ew * eh):
        e = ep[pixel * ec:pixel * ec + 3]; a = ap[pixel * ac:pixel * ac + 3]
        different = e != a
        changed += different
        out.extend(b"\xff\x00\x00" if different else bytes(value // 3 for value in a))
    write_diff(diff, ew, eh, bytes(out))
    return changed / (ew * eh)


def stage_result(category: str, detail: str, scenario: dict[str, Any]) -> dict[str, Any]:
    stages = {key: "not_run" for key in ("environment", "runtime", "authentication", "fixture", "navigation", "stability", "capture", "visual_comparison", "cleanup")}
    mapping = {
        "environment_failed": "environment", "runtime_failed": "runtime", "authentication_failed": "authentication",
        "fixture_failed": "fixture", "navigation_failed": "navigation", "stability_failed": "stability",
        "capture_failed": "capture", "visual_difference": "visual_comparison", "cleanup_failed": "cleanup",
        "frontend_delivery_disabled": "environment",
    }
    stages[mapping[category]] = "failed"
    return {**scenario, "status": "failed", "failure_category": category, "summary": detail, "stages": stages}


def skipped_result(detail: str, scenario: dict[str, Any]) -> dict[str, Any]:
    stages = {key: "skipped" for key in ("environment", "runtime", "authentication", "fixture", "navigation", "stability", "capture", "visual_comparison", "cleanup")}
    return {**scenario, "status": "skipped", "failure_category": "frontend_delivery_disabled", "summary": detail, "stages": stages}


def execute(
    context: StoryContext,
    result_path: Path,
    scenarios: list[dict[str, Any]] | None = None,
    runtime_env: dict[str, str] | None = None,
    runtime_running: bool = False,
) -> list[dict[str, Any]]:
    disabled_reasons = frontend_delivery_disabled_reasons(context)
    contract = visual_contract(context.technical_plan)
    if not contract:
        return []
    if disabled_reasons:
        scenarios = scenarios if scenarios is not None else contract.get("scenarios", [])
        detail = "Frontend delivery skipped by policy: " + "; ".join(disabled_reasons)
        results = [skipped_result(detail, item) for item in scenarios]
        merge_visual_result(result_path, contract["runtime"].get("runtime_profile", ""), results)
        return results
    runtime_contract = contract["runtime"]
    repo_name = runtime_contract.get("repository", "")
    repo_target = next((repo for repo in context.repos if repo.name == repo_name), None)
    config_items = read_json(repos_config(context.workspace_root), {}).get("repositories", [])
    repo_config = next((item for item in config_items if isinstance(item, dict) and item.get("name") == repo_name), None)
    scenarios = scenarios if scenarios is not None else contract.get("scenarios", [])
    if not repo_target or not repo_config or not isinstance(repo_config.get("runtime"), dict):
        results = [stage_result("environment_failed", f"runtime configuration not found for {repo_name}", item) for item in scenarios]
        merge_visual_result(result_path, runtime_contract.get("runtime_profile", ""), results)
        return results
    runtime = repo_config["runtime"]
    fixture_file = resolve_visual_fixture_file(context.workspace_root, context.story_dir, repo_target.worktree_path, runtime)
    env = runtime_env if runtime_env is not None else dict(os.environ)
    processes: list[subprocess.Popen[str]] = []
    def cleanup() -> None:
        for process in reversed(processes):
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=5)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    if process.poll() is None:
                        try: os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                        process.wait()
            log = getattr(process, "_lumen_runtime_log", None)
            if log:
                log.close()
            path = getattr(process, "_lumen_runtime_log_path", None)
            if isinstance(path, Path):
                path.unlink(missing_ok=True)
    atexit.register(cleanup)
    results: list[dict[str, Any]] = []
    evidence = workspace_lumen_dir(context.workspace_root) / "results" / "visual" / time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    evidence.mkdir(parents=True, exist_ok=True)
    runtime_error = ""
    runtime_failure_category = "runtime_failed"
    try:
        if repo_config.get("runtime_status") != "ready":
            raise EnvironmentError("repository runtime_status is not ready; run lumen doctor")
        if not runtime_running:
            ensure_dependencies(repo_target.worktree_path, runtime, env)
            fixture_start = str(runtime.get("fixture_start_command", ""))
            if fixture_start:
                run_owned(fixture_start, repo_target.worktree_path, env, processes)
            platform = str(runtime.get("platform", ""))
            if platform == "web":
                ready_url = str(runtime.get("ready_url", ""))
                if local_runtime_port_in_use(ready_url):
                    raise EnvironmentError(f"configured local runtime port is already in use: {ready_url}")
                server = run_owned(str(runtime.get("start_command", "")), repo_target.worktree_path, env, processes, runtime)
                wait_ready(ready_url, int(runtime.get("ready_timeout_seconds", 60)), server, env)
                if str(runtime.get("auth_strategy", "")).strip().casefold() in {"playwright-storage-state", "storage-state", "login-endpoint", "fake-login"}:
                    prepare_web_auth_storage(repo_target.worktree_path, runtime, env, evidence / "web-auth-storage.json")
            elif platform == "react-native":
                ensure_ios_app(repo_target.worktree_path, runtime, env)
                metro_port = int(runtime.get("metro_port") or LUMEN_METRO_PORT)
                metro_env = dict(env)
                metro_env["RCT_METRO_PORT"] = str(metro_port)
                metro_env["METRO_PORT"] = str(metro_port)
                metro = run_owned(str(runtime.get("metro_command", "")), repo_target.worktree_path, metro_env, processes, runtime)
                wait_ready(
                    str(runtime.get("ready_url") or metro_ready_url(metro_port)),
                    int(runtime.get("ready_timeout_seconds", 120)),
                    metro,
                    metro_env,
                )
            else:
                raise EnvironmentError(f"unsupported visual platform: {platform}")
    except PermissionError as exc:
        runtime_error = str(exc)
        runtime_failure_category = "authentication_failed"
    except ModuleNotFoundError as exc:
        runtime_error = str(exc)
        runtime_failure_category = "environment_failed"
    except (OSError, ValueError, TimeoutError) as exc:
        runtime_error = str(exc)

    for index, scenario in enumerate(scenarios, 1):
        scenario = dict(scenario)
        scenario.update({"repository": repo_name, "platform": runtime_contract.get("platform", runtime.get("platform", ""))})
        scenario.setdefault("navigation", runtime_contract.get("navigation", ""))
        stem = re.sub(r"[^a-z0-9]+", "-", f"{scenario['screen']}-{scenario['state']}".lower()).strip("-") or f"scenario-{index}"
        reference = context.story_dir / str(scenario.get("reference", ""))
        expected, actual, diff = evidence / f"{stem}-expected.png", evidence / f"{stem}-actual.png", evidence / f"{stem}-diff.png"
        try:
            if runtime_error:
                raise RuntimeError(runtime_error)
            if not reference.is_file():
                raise FileNotFoundError(f"approved reference not found: {reference}")
            fixture_command = str(runtime.get("fixture_command", ""))
            if runtime.get("fixture_strategy") == "playwright-route" and (not fixture_file or not fixture_file.is_file()):
                raise ChildProcessError("configured Playwright fixture file is missing")
            if fixture_command:
                fixture_value = str(scenario.get("fixture", "")).strip()
                if not fixture_value or fixture_value.upper() == "TBD":
                    fixture_value = resolve_visual_auth_credential(runtime, env)
                command = fixture_command.replace("{fixture}", fixture_value)
                prepared = subprocess.run(shlex.split(command), cwd=repo_target.worktree_path, env=env, check=False, capture_output=True, text=True)
                if prepared.returncode != 0:
                    raise ChildProcessError(redact((prepared.stderr or prepared.stdout or "fixture command failed").strip(), env)[-500:])
            shutil.copy2(reference, expected)
            if runtime.get("platform") == "web":
                web_capture(repo_target.worktree_path, runtime, scenario, actual, env, fixture_file)
            else:
                device = str((runtime.get("ios") or {}).get("device", ""))
                subprocess.run(["xcrun", "simctl", "boot", device], check=False, capture_output=True, text=True)
                boot = subprocess.run(["xcrun", "simctl", "bootstatus", device, "-b"], check=False, capture_output=True, text=True)
                if boot.returncode != 0: raise EnvironmentError(redact((boot.stderr or boot.stdout).strip(), env))
                installed = subprocess.run(["xcrun", "simctl", "get_app_container", device, str(runtime.get("bundle_id", ""))], check=False, capture_output=True, text=True)
                if installed.returncode != 0: raise EnvironmentError("configured debug app is not installed on the simulator")
                opened = subprocess.run(["xcrun", "simctl", "openurl", device, str(scenario["navigation"])], check=False, capture_output=True, text=True)
                if opened.returncode != 0: raise ConnectionError(redact((opened.stderr or opened.stdout).strip(), env))
                flow = str(scenario.get("maestro_flow") or runtime.get("maestro_flow", ""))
                if flow:
                    checked = subprocess.run(["maestro", "test", flow], cwd=repo_target.worktree_path, check=False, capture_output=True, text=True)
                    if checked.returncode != 0: raise TimeoutError(redact((checked.stderr or checked.stdout).strip(), env))
                elif runtime.get("settle_seconds"):
                    time.sleep(float(runtime["settle_seconds"]))
                else:
                    raise TimeoutError("no Maestro stable-marker flow or explicit settle fallback is configured")
                captured = subprocess.run(["xcrun", "simctl", "io", device, "screenshot", str(actual)], check=False, capture_output=True, text=True)
                if captured.returncode != 0: raise RuntimeError(redact((captured.stderr or captured.stdout).strip(), env))
            ratio = compare_png(expected, actual, diff)
            threshold = scenario.get("maximum_difference_ratio")
            status = "needs_review" if threshold is None else "passed" if ratio <= threshold else "failed"
            result = {**scenario, "expected": str(expected), "actual": str(actual), "diff": str(diff), "difference_ratio": ratio, "status": status}
            result["stages"] = {key: "passed" for key in ("environment", "runtime", "authentication", "fixture", "navigation", "stability", "capture", "visual_comparison", "cleanup")}
            if status == "failed":
                result["failure_category"] = "visual_difference"
                result["stages"]["visual_comparison"] = "failed"
            elif status == "needs_review":
                result["summary"] = "Screenshot captured; no numerical visual threshold is configured."
                result["stages"]["visual_comparison"] = "needs_review"
            results.append(result)
        except PermissionError as exc: results.append(stage_result("authentication_failed", str(exc), scenario))
        except ChildProcessError as exc: results.append(stage_result("fixture_failed", str(exc), scenario))
        except FileNotFoundError as exc: results.append(stage_result("environment_failed", str(exc), scenario))
        except ModuleNotFoundError as exc: results.append(stage_result("environment_failed", str(exc), scenario))
        except ConnectionError as exc: results.append(stage_result("navigation_failed", str(exc), scenario))
        except TimeoutError as exc: results.append(stage_result("stability_failed", str(exc), scenario))
        except EnvironmentError as exc: results.append(stage_result("environment_failed", str(exc), scenario))
        except (RuntimeError, ValueError) as exc:
            category = runtime_failure_category if runtime_error else "capture_failed"
            results.append(stage_result(category, str(exc), scenario))
    cleanup()
    atexit.unregister(cleanup)
    merge_visual_result(result_path, runtime_contract.get("runtime_profile", ""), results)
    return results


def merge_visual_result(result_path: Path, profile: str, results: list[dict[str, Any]]) -> None:
    payload = read_json(result_path, {})
    statuses = {item.get("status") for item in results}
    status = (
        "passed" if results and statuses == {"passed"}
        else "skipped" if results and statuses == {"skipped"}
        else "needs_review" if results and statuses <= {"passed", "needs_review", "skipped"}
        else "failed"
    )
    payload["visual_verification"] = {"status": status, "runtime_profile": profile, "results": results}
    repositories = {str(item.get("repository", "")) for item in results}
    verification = [
        item for item in payload.get("verification_results", [])
        if not (isinstance(item, dict) and item.get("id") == "visual" and item.get("repository") in repositories)
    ]
    verification.extend({
        "repository": item.get("repository", ""), "id": "visual", "label": f"Visual: {item.get('screen', '')} / {item.get('state', '')}",
        "command": "internal visual delivery", "exit_code": 0 if item.get("status") in {"passed", "skipped"} else 1,
        "summary": item.get("summary") or (f"Difference {item.get('difference_ratio', 0):.2%}" if "difference_ratio" in item else item.get("failure_category", "")),
        "status": item.get("status", "failed"), "failure_category": item.get("failure_category", ""),
        "expected": item.get("expected", ""), "actual": item.get("actual", ""), "diff": item.get("diff", ""),
        "difference_ratio": item.get("difference_ratio"), "maximum_difference_ratio": item.get("maximum_difference_ratio"),
    } for item in results)
    payload["verification_results"] = verification
    write_json(result_path, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("detect", "doctor"):
        command = sub.add_parser(name); command.add_argument("--workspace-root", required=True)
    check = sub.add_parser("check", help="Capture and compare one visual contract state.")
    check.add_argument("--docs-dir", required=True)
    check.add_argument("--story", default="")
    check.add_argument("--screen", default="")
    check.add_argument("--state", default="")
    args = parser.parse_args()
    if args.command == "check":
        from delivery_workspace import load_story_context

        context = load_story_context(Path(args.docs_dir), args.story)
        scenarios = matching_scenarios(visual_contract(context.technical_plan), args.screen, args.state)
        if not scenarios:
            print("No matching Visual State Matrix scenario.", file=sys.stderr)
            return 2
        result_path = workspace_lumen_dir(context.workspace_root) / "results" / "visual" / "implement-check.json"
        if not result_path.is_file():
            write_json(result_path, {"delivery_status": "visual_check"})
        results = execute(context, result_path, scenarios)
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0 if all(item.get("status") in {"passed", "skipped"} for item in results) else 1
    root = Path(args.workspace_root).expanduser().resolve()
    if root.name in {"lumon", "lumen", ".lumen"}:
        root = root.parent
    if args.command == "detect":
        print(json.dumps({"repositories": enrich_repositories(root)}, indent=2, ensure_ascii=False)); return 0
    return doctor(root)


if __name__ == "__main__":
    raise SystemExit(main())
