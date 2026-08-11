#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="${1:?Usage: run-patch.sh <workspace> [--jira-key KEY] [--dry-run]}"
shift

load_env_file() {
  local file="$1"
  if [[ -f "${file}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${file}"
    set +a
  fi
}

load_env_file "${WORKSPACE_ROOT}/.env.common"
load_env_file "${WORKSPACE_ROOT}/.env.local"
WORKSPACE_LUMEN_DIR="${WORKSPACE_ROOT}/lumon"
[[ -d "${WORKSPACE_ROOT}/lumen" && ! -d "${WORKSPACE_LUMEN_DIR}" ]] && WORKSPACE_LUMEN_DIR="${WORKSPACE_ROOT}/lumen"
[[ -d "${WORKSPACE_ROOT}/.lumen" && ! -d "${WORKSPACE_LUMEN_DIR}" && ! -d "${WORKSPACE_ROOT}/lumen" ]] && WORKSPACE_LUMEN_DIR="${WORKSPACE_ROOT}/.lumen"
load_env_file "${WORKSPACE_LUMEN_DIR}/.env.common"
load_env_file "${WORKSPACE_LUMEN_DIR}/.env.local"

export AGENT_CLI_CREDENTIAL_STORE="${AGENT_CLI_CREDENTIAL_STORE:-file}"
exec python3 "${SCRIPT_DIR}/patch_scheduler.py" "${WORKSPACE_ROOT}" "$@"
