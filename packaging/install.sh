#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'

readonly DEFAULT_REPOSITORY="zchengb/lumon"
readonly DEFAULT_VERSION="latest"

repository="${LUMON_REPOSITORY:-$DEFAULT_REPOSITORY}"
version="${LUMON_VERSION:-$DEFAULT_VERSION}"
install_root="${LUMON_INSTALL_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/lumon}"
bin_dir="${LUMON_BIN_DIR:-$HOME/.local/bin}"
force=false

die() {
  printf 'lumon installer: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: install.sh [OPTIONS]

Install Lumon without uv. The installer uses Python 3.12, a private virtual
environment, and pip. For a private GitHub repository, it first tries the
Release API with LUMON_GITHUB_TOKEN and then falls back to Git over SSH.

Options:
  --repository OWNER/REPOSITORY  GitHub repository (default: zchengb/lumon)
  --version latest|vX.Y.Z        Release tag (default: latest stable Release)
  --install-root PATH            Installation directory
  --bin-dir PATH                 Directory for the lumon executable
  --force                        Replace an existing Shell installation
  -h, --help                     Show this help
EOF
}

while (($# > 0)); do
  case "$1" in
    --repository)
      (($# >= 2)) || die "--repository requires a value."
      repository="$2"
      shift 2
      ;;
    --version)
      (($# >= 2)) || die "--version requires a value."
      version="$2"
      shift 2
      ;;
    --install-root)
      (($# >= 2)) || die "--install-root requires a value."
      install_root="$2"
      shift 2
      ;;
    --bin-dir)
      (($# >= 2)) || die "--bin-dir requires a value."
      bin_dir="$2"
      shift 2
      ;;
    --force)
      force=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1"
      ;;
  esac
done

[[ "$repository" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || \
  die "GitHub repository must use OWNER/REPOSITORY format."

normalize_version() {
  local requested="$1"
  local normalized="${requested#v}"

  if [[ "$requested" == "latest" ]]; then
    printf 'latest\n'
    return
  fi

  [[ "$normalized" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || \
    die "Version must use latest or vX.Y.Z format."
  printf 'v%s\n' "$normalized"
}

version="$(normalize_version "$version")"

[[ -n "$install_root" && "$install_root" != "/" && "$install_root" != "$HOME" ]] || \
  die "Refusing to use a broad installation directory: $install_root"
[[ -n "$bin_dir" && "$bin_dir" != "/" && "$bin_dir" != "$HOME" ]] || \
  die "Refusing to use a broad binary directory: $bin_dir"

if [[ "$install_root" == "$bin_dir" || "$install_root" == "$bin_dir"/* || \
  "$bin_dir" == "$install_root" || "$bin_dir" == "$install_root"/* ]]; then
  die "Installation and binary directories must not overlap."
fi

is_python_312() {
  local candidate="$1"
  "$candidate" -c \
    'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)' \
    >/dev/null 2>&1
}

resolve_python() {
  local candidate name

  if [[ -n "${LUMON_PYTHON:-}" ]]; then
    candidate="$LUMON_PYTHON"
    if [[ ! -x "$candidate" ]]; then
      candidate="$(command -v "$candidate" || true)"
    fi
    [[ -n "$candidate" ]] || die "LUMON_PYTHON does not point to an executable."
    is_python_312 "$candidate" || die "LUMON_PYTHON must be Python 3.12."
    printf '%s\n' "$candidate"
    return
  fi

  for name in python3.12 python3 python; do
    candidate="$(command -v "$name" || true)"
    if [[ -n "$candidate" ]] && is_python_312 "$candidate"; then
      printf '%s\n' "$candidate"
      return
    fi
  done

  if [[ "$(uname -s)" == "Darwin" ]] && command -v brew >/dev/null 2>&1; then
    printf 'Python 3.12 was not found; installing python@3.12 with Homebrew.\n' >&2
    brew list --formula python@3.12 >/dev/null 2>&1 || brew install python@3.12
    candidate="$(brew --prefix python@3.12)/bin/python3.12"
    is_python_312 "$candidate" || die "Homebrew did not provide a working Python 3.12."
    printf '%s\n' "$candidate"
    return
  fi

  die "Python 3.12 was not found. Install it or set LUMON_PYTHON to its path."
}

resolve_latest_version() {
  local resolved

  if resolved="$("$python_command" - "$repository" <<'PY'
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request


repository = sys.argv[1]
api_root = "https://api.github.com"
headers = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "lumon-installer",
    "X-GitHub-Api-Version": "2022-11-28",
}
token = os.environ.get("LUMON_GITHUB_TOKEN")
if token:
    headers["Authorization"] = f"Bearer {token}"


def request(url: str, accept: str) -> urllib.request.Request:
    request_headers = dict(headers)
    request_headers["Accept"] = accept
    return urllib.request.Request(url, headers=request_headers)


def stable_tag(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    if re.fullmatch(r"v?\d+\.\d+\.\d+", value) is None:
        return None
    return value if value.startswith("v") else f"v{value}"


try:
    with urllib.request.urlopen(
        request(f"{api_root}/repos/{repository}/releases/latest", headers["Accept"]),
        timeout=30,
    ) as response:
        payload = json.loads(response.read())
    tag = stable_tag(payload.get("tag_name"))
    if tag is None:
        raise ValueError("latest Release does not have a stable semantic-version tag")
    print(tag)
    raise SystemExit(0)
except (KeyError, TypeError, ValueError, json.JSONDecodeError, urllib.error.URLError) as exc:
    api_error = exc

# The HTML endpoint follows the GitHub redirect to /releases/tag/<tag>. This is
# useful for public repositories when the unauthenticated API is rate-limited.
try:
    with urllib.request.urlopen(
        request(f"https://github.com/{repository}/releases/latest", "text/html"),
        timeout=30,
    ) as response:
        match = re.search(r"/releases/tag/(v?\d+\.\d+\.\d+)$", response.geturl())
    tag = stable_tag(match.group(1) if match else None)
    if tag is None:
        raise ValueError("latest Release redirect does not have a stable semantic-version tag")
    print(tag)
except (ValueError, urllib.error.URLError) as exc:
    print(f"GitHub latest Release lookup unavailable: {api_error}; {exc}", file=sys.stderr)
    raise SystemExit(1) from exc
PY
  )"; then
    version="$(normalize_version "$resolved")"
    return
  fi

  if ! command -v git >/dev/null 2>&1; then
    die "Could not resolve the latest Release. Install Git or pass --version vX.Y.Z."
  fi

  printf 'GitHub Release lookup was unavailable; checking semantic-version tags over SSH.\n' >&2
  if ! resolved="$(git ls-remote --refs --tags "git@github.com:${repository}.git" | \
    "$python_command" -c '
import re
import sys


versions = []
for line in sys.stdin:
    fields = line.split()
    if len(fields) != 2:
        continue
    match = re.fullmatch(r"refs/tags/(v?)(\d+)\.(\d+)\.(\d+)", fields[1])
    if match is None:
        continue
    version = tuple(int(part) for part in match.groups()[1:])
    versions.append((version, f"v{version[0]}.{version[1]}.{version[2]}"))

if not versions:
    raise SystemExit("No stable semantic-version tags were found.")
print(max(versions)[1])
')"; then
    die "Could not resolve the latest Release over SSH. Pass --version vX.Y.Z."
  fi
  version="$(normalize_version "$resolved")"
}

download_release() {
  local output_dir="$1"

  "$python_command" - "$repository" "$version" "$output_dir" <<'PY'
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


repository, tag, output_directory = sys.argv[1:]
version = tag.removeprefix("v")
wheel_name = f"lumon-{version}-py3-none-any.whl"
api_root = "https://api.github.com"
headers = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "lumon-installer",
    "X-GitHub-Api-Version": "2022-11-28",
}
token = os.environ.get("LUMON_GITHUB_TOKEN")
if token:
    headers["Authorization"] = f"Bearer {token}"


def request_bytes(url: str, accept: str) -> bytes:
    request_headers = dict(headers)
    request_headers["Accept"] = accept
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


try:
    if token:
        release_payload = json.loads(
            request_bytes(
                f"{api_root}/repos/{repository}/releases/tags/{tag}",
                headers["Accept"],
            )
        )
        assets = {
            item["name"]: item
            for item in release_payload["assets"]
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        wheel_asset = assets[wheel_name]
        checksum_asset = assets["SHA256SUMS"]
        wheel_bytes = request_bytes(wheel_asset["url"], "application/octet-stream")
        checksum_bytes = request_bytes(checksum_asset["url"], "application/octet-stream")
    else:
        wheel_url = f"https://github.com/{repository}/releases/download/{tag}/{wheel_name}"
        checksum_url = f"https://github.com/{repository}/releases/download/{tag}/SHA256SUMS"
        wheel_bytes = request_bytes(wheel_url, "application/octet-stream")
        checksum_bytes = request_bytes(checksum_url, "application/octet-stream")
except (KeyError, TypeError, ValueError, json.JSONDecodeError, urllib.error.URLError) as exc:
    print(f"GitHub Release download unavailable: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc


expected = None
for line in checksum_bytes.decode("utf-8").splitlines():
    fields = line.split()
    if len(fields) >= 2 and fields[1].lstrip("*") == wheel_name:
        expected = fields[0].lower()
        break

actual = hashlib.sha256(wheel_bytes).hexdigest()
if expected is None or actual != expected:
    print("Release Wheel checksum verification failed.", file=sys.stderr)
    raise SystemExit(1)

wheel_path = Path(output_directory) / wheel_name
wheel_path.write_bytes(wheel_bytes)
print(wheel_path)
PY
}

install_from_source() {
  command -v git >/dev/null 2>&1 || die "Git is required for the private SSH fallback."
  printf 'Release API was not available; installing the fixed Git tag over SSH.\n' >&2
  "$venv_python" -m pip install \
    --disable-pip-version-check \
    --no-cache-dir \
    --force-reinstall \
    "git+ssh://git@github.com/${repository}.git@${version}"
}

python_command="$(resolve_python)"
python_version="$("$python_command" -c 'import platform; print(platform.python_version())')"
printf 'Using Python %s\n' "$python_version"

if [[ "$version" == "latest" ]]; then
  resolve_latest_version
fi
normalized_version="${version#v}"

parent_directory="$(dirname "$install_root")"
mkdir -p "$parent_directory" "$bin_dir"

if [[ -e "$install_root" || -L "$install_root" ]] && [[ "$force" != true ]]; then
  die "Installation already exists at $install_root; use --force to replace it."
fi

if [[ -e "$bin_dir/lumon" || -L "$bin_dir/lumon" ]] && [[ "$force" != true ]]; then
  die "$bin_dir/lumon already exists; use --force to replace it."
fi

download_root="$(mktemp -d "${parent_directory}/.lumon-download.XXXXXX")"
old_root=""
rollback_needed=true

cleanup() {
  if [[ -n "${download_root:-}" && -e "$download_root" ]]; then
    rm -rf -- "$download_root"
  fi
  if [[ "$rollback_needed" == true ]]; then
    if [[ -e "$install_root" || -L "$install_root" ]]; then
      rm -rf -- "$install_root"
    fi
    if [[ -n "$old_root" && -e "$old_root" ]]; then
      mv "$old_root" "$install_root"
    fi
  elif [[ -n "$old_root" && -e "$old_root" ]]; then
    rm -rf -- "$old_root"
  fi
}
trap cleanup EXIT

if [[ -e "$install_root" || -L "$install_root" ]]; then
  old_root="${install_root}.previous.$$"
  [[ ! -e "$old_root" && ! -L "$old_root" ]] || die "Temporary backup already exists: $old_root"
  mv "$install_root" "$old_root"
fi

mkdir -p "$install_root"
staging_venv="$install_root/venv"
venv_python="$staging_venv/bin/python"
"$python_command" -m venv "$staging_venv"

if ! wheel_path="$(download_release "$download_root")"; then
  install_from_source
else
  printf 'Installing verified Release Wheel.\n'
  "$venv_python" -m pip install \
    --disable-pip-version-check \
    --no-cache-dir \
    --force-reinstall \
    "$wheel_path"
fi

touch "$install_root/.lumon-shell-install"
"$install_root/venv/bin/lumon" --version
"$install_root/venv/bin/lumon" doctor --json

if [[ -e "$bin_dir/lumon" || -L "$bin_dir/lumon" ]]; then
  rm -f -- "$bin_dir/lumon"
fi
ln -s "$install_root/venv/bin/lumon" "$bin_dir/lumon"

rollback_needed=false

printf '\nLumon %s installed at %s\n' "$normalized_version" "$install_root"
if [[ ":$PATH:" != *":$bin_dir:"* ]]; then
  printf 'Add this directory to PATH before running lumon:\n  %s\n' "$bin_dir"
else
  printf 'Run: lumon doctor\n'
fi
