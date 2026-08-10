#!/usr/bin/env bash
set -euo pipefail

# One-command Lumon installer.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/zchengb/lumon-cli/main/get.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/zchengb/lumon/main/get.sh | bash -s -- ~/Projects/MyProject
#
# The optional argument is a workspace directory; if given, Lumon also runs
# 'lumon init' there after installing (same as install.sh <workspace-dir>).
#
# Env overrides:
#   LUMON_REPO      GitHub "owner/repo" to install from (default: zchengb/lumon)
#   LUMON_VERSION   Specific release tag to install (default: latest release)
#   LUMON_HOME      Lumon installation directory (default: ~/.lumon)
#   LUMON_BIN_DIR   Where to place the 'lumon' executable (default: ~/.local/bin)

REPO="${LUMON_REPO:-${LUMEN_REPO:-zchengb/lumon}}"
REQUESTED_VERSION="${LUMON_VERSION:-${LUMEN_VERSION:-}}"

BOLD="$(printf '\033[1m')"
GREEN="$(printf '\033[32m')"
YELLOW="$(printf '\033[33m')"
RED="$(printf '\033[31m')"
RESET="$(printf '\033[0m')"

info() { printf '%s\n' "$1" >&2; }
ok()   { printf '%s✓%s %s\n' "${GREEN}" "${RESET}" "$1" >&2; }
warn() { printf '%s!%s %s\n' "${YELLOW}" "${RESET}" "$1" >&2; }
fail() { printf '%sError:%s %s\n' "${RED}" "${RESET}" "$1" >&2; exit 1; }

command -v unzip >/dev/null 2>&1 || fail "'unzip' is required but was not found. Install it and re-run."

fetch() {
  local url="$1"
  local out="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${url}" -o "${out}"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "${url}" -O "${out}"
  else
    fail "Neither curl nor wget is available to download Lumon."
  fi
}

fetch_stdout() {
  local url="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${url}"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO- "${url}"
  else
    fail "Neither curl nor wget is available to download Lumon."
  fi
}

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "${WORK_DIR}"' EXIT

ZIP_PATH="${WORK_DIR}/lumon.zip"
EXTRACT_ROOT="${WORK_DIR}/extracted"
mkdir -p "${EXTRACT_ROOT}"

resolve_release_asset_url() {
  local api_url="https://api.github.com/repos/${REPO}/releases/latest"
  if [[ -n "${REQUESTED_VERSION}" ]]; then
    api_url="https://api.github.com/repos/${REPO}/releases/tags/${REQUESTED_VERSION}"
  fi

  local release_json
  release_json="$(fetch_stdout "${api_url}" 2>/dev/null || true)"
  [[ -z "${release_json}" ]] && return 1
  printf '%s' "${release_json}" | grep -o '"browser_download_url": *"[^"]*\.zip"' | head -n1 | sed -E 's/.*"(https:[^"]+)"/\1/'
}

install_from_release() {
  local asset_url="$1"
  info "Downloading Lumon release package..."
  fetch "${asset_url}" "${ZIP_PATH}"
  unzip -q "${ZIP_PATH}" -d "${EXTRACT_ROOT}"
  local pkg_dir
  pkg_dir="$(find "${EXTRACT_ROOT}" -maxdepth 1 -mindepth 1 -type d | head -n1)"
  [[ -n "${pkg_dir}" ]] || fail "Downloaded package looked empty."
  printf '%s' "${pkg_dir}"
}

install_from_branch() {
  local branch="${1:-main}"
  warn "No GitHub release found for ${REPO}. Falling back to the ${branch} branch source."
  local archive_url="https://github.com/${REPO}/archive/refs/heads/${branch}.zip"
  fetch "${archive_url}" "${ZIP_PATH}"
  unzip -q "${ZIP_PATH}" -d "${EXTRACT_ROOT}"
  local pkg_dir
  pkg_dir="$(find "${EXTRACT_ROOT}" -maxdepth 1 -mindepth 1 -type d | head -n1)"
  [[ -n "${pkg_dir}" ]] || fail "Downloaded source archive looked empty."
  printf '%s' "${pkg_dir}"
}

printf '%sInstalling Lumon from %s...%s\n' "${BOLD}" "${REPO}" "${RESET}"

ASSET_URL="$(resolve_release_asset_url || true)"

PKG_DIR=""
if [[ -n "${ASSET_URL}" ]]; then
  PKG_DIR="$(install_from_release "${ASSET_URL}")"
else
  PKG_DIR="$(install_from_branch "main")"
fi

[[ -f "${PKG_DIR}/install.sh" ]] || fail "install.sh not found in downloaded package: ${PKG_DIR}"
chmod +x "${PKG_DIR}/install.sh"

ok "Package downloaded."
bash "${PKG_DIR}/install.sh" "$@"
