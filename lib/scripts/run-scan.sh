#!/usr/bin/env bash
set -euo pipefail

# Usage: run-scan.sh <workspace-dir>
WORKSPACE_ROOT="${1:?Usage: run-scan.sh <workspace-dir>}"
LUMEN_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LUMEN_HOME="${LUMEN_HOME:-$HOME/.lumon}"

if [[ -f "${LUMEN_LIB_DIR}/ensure-path.sh" ]]; then
  # shellcheck source=/dev/null
  source "${LUMEN_LIB_DIR}/ensure-path.sh"
  lumen_bin_hint=""
  if [[ -n "${LUMEN_CLI_BIN:-}" && -x "${LUMEN_CLI_BIN}" ]]; then
    lumen_bin_hint="${LUMEN_CLI_BIN}"
  elif command -v lumen >/dev/null 2>&1; then
    lumen_bin_hint="$(command -v lumen)"
  elif [[ -n "${HOME:-}" && -x "${HOME}/.local/bin/lumen" ]]; then
    lumen_bin_hint="${HOME}/.local/bin/lumen"
  fi
  ensure_lumen_path "${lumen_bin_hint}"
fi

PROMPT_FILE="${WORKSPACE_ROOT}/config/scan-prompt.md"
COMPOSE_PROMPT_SCRIPT="${LUMEN_LIB_DIR}/compose_scan_prompt.py"
COMMON_CONFIG="${WORKSPACE_ROOT}/config/common.json"
SECURE_AGENT_PY="${LUMEN_LIB_DIR}/run-agent-secure.py"
WORKFLOW_AGENT_PY="${LUMEN_LIB_DIR}/run-workflow-agent.py"

model_from_config() {
  if [[ ! -f "${COMMON_CONFIG}" ]]; then
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import json
try:
    with open('${COMMON_CONFIG}') as f:
        c = json.load(f)
    print(c.get('execution', {}).get('model', '') or '', end='')
except Exception:
    pass" 2>/dev/null
  fi
}

provider_from_config() {
  if [[ ! -f "${COMMON_CONFIG}" ]]; then
    return 0
  fi
  python3 - "${COMMON_CONFIG}" <<'PY' 2>/dev/null
import json, sys
try:
    value = json.load(open(sys.argv[1], encoding="utf-8")).get("execution", {}).get("provider", "")
    print(value or "", end="")
except Exception:
    pass
PY
}

project_name_from_config() {
  if [[ ! -f "${COMMON_CONFIG}" ]]; then
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -c "import json
try:
    with open('${COMMON_CONFIG}') as f:
        c = json.load(f)
    print(c.get('project', {}).get('display_name', '') or '', end='')
except Exception:
    pass" 2>/dev/null
  fi
}

notify_system() {
  local notify_script="${LUMEN_LIB_DIR}/notify.sh"
  if [[ -f "${notify_script}" ]]; then
    bash "${notify_script}" "$1" "$2" >/dev/null 2>&1 || true
  fi
}

PROVIDER="${LUMON_WORKFLOW_PROVIDER:-$(provider_from_config)}"
PROVIDER="${PROVIDER:-cursor_cli}"
if [[ "${PROVIDER}" == "cursor" || "${PROVIDER}" == "cursor_cli" ]]; then
  MODEL="${CURSOR_AGENT_MODEL:-$(model_from_config)}"
else
  MODEL="$(model_from_config)"
fi
if [[ "${PROVIDER}" == "codex" || "${PROVIDER}" == "codex_cli" || "${PROVIDER}" == "codex-cli" ]]; then
  MODEL="${MODEL:-gpt-5.6-luna}"
else
  MODEL="${MODEL:-cursor-grok-4.5-medium}"
fi
export LUMEN_MODEL="${MODEL}"
SANDBOX_MODE="${CURSOR_AGENT_SANDBOX:-unrestricted}"
OUTPUT_FORMAT="${CURSOR_AGENT_OUTPUT_FORMAT:-stream-json}"
STREAM_PARTIAL="${CURSOR_AGENT_STREAM_PARTIAL:-1}"
LOCK_DIR="${WORKSPACE_ROOT}/state/run.lock"
RUN_ID="$(date -u '+%Y%m%d-%H%M%S')"
LOG_FILE="${WORKSPACE_ROOT}/logs/run-${RUN_ID}.log"
DRY_RUN="${LUMEN_DRY_RUN:-0}"
PROJECT_NAME="$(project_name_from_config)"
PROJECT_NAME="${PROJECT_NAME:-$(basename "${WORKSPACE_ROOT}")}"
SCAN_LABEL="Scan"
if [[ "${DRY_RUN}" == "1" || "${DRY_RUN}" == "true" || "${DRY_RUN}" == "yes" ]]; then
  SCAN_LABEL="Dry-run scan"
fi

cd "${WORKSPACE_ROOT}"

load_env_file() {
  local file="$1"
  if [[ -f "${file}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${file}"
    set +a
  fi
}

fail() {
  printf 'Error: %s\n' "$1" >&2
  exit 1
}

is_pid_alive() {
  local pid="$1"
  [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

clear_stale_lock() {
  if [[ ! -d "${LOCK_DIR}" ]]; then
    return 0
  fi

  local old_pid=""
  if [[ -f "${LOCK_DIR}/pid" ]]; then
    old_pid="$(tr -d '[:space:]' < "${LOCK_DIR}/pid")"
  fi

  if is_pid_alive "${old_pid}"; then
    local started_at="unknown"
    if [[ -f "${LOCK_DIR}/started_at" ]]; then
      started_at="$(tr -d '[:space:]' < "${LOCK_DIR}/started_at")"
    fi
    printf 'Another Lumen scan is already running.\n' >&2
    printf '  PID: %s\n' "${old_pid}" >&2
    printf '  Started: %s\n' "${started_at}" >&2
    printf '  Lock: %s\n' "${LOCK_DIR}" >&2
    printf 'If this is stale, stop the process or remove the lock after confirming no scan is active.\n' >&2
    exit 2
  fi

  printf 'Removing stale run lock at %s\n' "${LOCK_DIR}" >&2
  rm -rf "${LOCK_DIR}"
}

latest_scan_result_file() {
  local results_dir="${WORKSPACE_ROOT}/results"
  local fixed_path="${results_dir}/scan-result.json"
  if [[ -f "${fixed_path}" ]]; then
    printf '%s' "${fixed_path}"
    return 0
  fi
  find "${results_dir}" -maxdepth 1 -name 'scan-result-*.json' -type f -print0 2>/dev/null \
    | xargs -0 ls -t 2>/dev/null \
    | head -n1
}

run_report_and_notify() {
  local result_file
  result_file="$(latest_scan_result_file)"
  if [[ -z "${result_file}" ]]; then
    printf 'Warning: no scan-result.json was found under %s/results. Skipping report generation and Feishu notification.\n' "${WORKSPACE_ROOT}" >&2
    return 1
  fi

  local report_script="${LUMEN_LIB_DIR}/render-report-and-notify.py"
  if [[ ! -f "${report_script}" ]]; then
    printf 'Warning: report script not found: %s\n' "${report_script}" >&2
    return 1
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    printf 'Warning: python3 not found; skipped HTML/PDF generation and Feishu notification.\n' >&2
    return 1
  fi

  printf '\nGenerating report and sending Feishu notification from %s ...\n' "${result_file}"
  local report_output
  report_output="$(
    LUMEN_WORKSPACE="${WORKSPACE_ROOT}" python3 "${report_script}" "${result_file}" 2>&1
  )" || {
    printf '%s\n' "${report_output}" | tee -a "${LOG_FILE}" >&2
    printf 'Warning: report/notification step failed. See log for details.\n' >&2
    return 1
  }

  if [[ -f "${LUMEN_LIB_DIR}/format_scan_log.py" ]] && command -v python3 >/dev/null 2>&1; then
    while IFS= read -r report_line; do
      if [[ "${report_line}" == "{"* ]]; then
        python3 "${LUMEN_LIB_DIR}/format_scan_log.py" --report-json "${report_line}"
      else
        printf '%s\n' "${report_line}"
      fi
    done <<< "${report_output}" | tee -a "${LOG_FILE}"
  else
    printf '%s\n' "${report_output}" | tee -a "${LOG_FILE}"
  fi
}

refresh_dashboard() {
  local dashboard_script="${LUMEN_LIB_DIR}/render-dashboard.sh"
  if [[ -f "${dashboard_script}" ]]; then
    if LUMEN_WORKSPACE="${WORKSPACE_ROOT}" bash "${dashboard_script}" "${WORKSPACE_ROOT}"; then
      printf 'Dashboard data refreshed: %s/dashboard-data.js\n' "${WORKSPACE_ROOT}"
    else
      printf 'Warning: dashboard-data.js was not refreshed. Open dashboard.html after fixing the renderer.\n' >&2
    fi
  fi
}

run_dry_scan() {
  command -v python3 >/dev/null 2>&1 || fail "Python 3 is required for dry-run mode."
  [[ -f "${WORKSPACE_ROOT}/config/common.json" ]] || fail "Workspace config not found. Run 'lumen init' first."

  printf 'Lumen workspace: %s\n' "${WORKSPACE_ROOT}"
  printf 'Mode: DRY-RUN (Cursor agent will not run)\n'
  printf 'Run log: %s\n' "${LOG_FILE}"

  local dry_run_script="${LUMEN_LIB_DIR}/dry_run_scan.py"
  [[ -f "${dry_run_script}" ]] || fail "Dry-run script not found: ${dry_run_script}"

  printf '\nGenerating mock scan result at %s UTC...\n' "$(date -u '+%Y-%m-%d %H:%M:%S')"
  {
    printf '[dry-run] started_at=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    printf '[dry-run] generating mock scan-result.json\n'
    python3 "${dry_run_script}" "${WORKSPACE_ROOT}" "${RUN_ID}"
    printf '[dry-run] mock scan-result.json written\n'
  } 2>&1 | tee "${LOG_FILE}"

  local result_file="${WORKSPACE_ROOT}/results/scan-result.json"
  [[ -f "${result_file}" ]] || fail "Dry-run did not produce ${result_file}"

  local report_script="${LUMEN_LIB_DIR}/render-report-and-notify.py"
  if [[ -f "${report_script}" ]]; then
    printf '\n[dry-run] generating HTML report\n'
    if command -v python3 >/dev/null 2>&1; then
      LUMEN_DRY_RUN=1 LUMEN_WORKSPACE="${WORKSPACE_ROOT}" python3 "${report_script}" "${result_file}" | tee -a "${LOG_FILE}" || \
        printf 'Warning: report generation step failed. See log for details.\n' >&2
    else
      printf 'Warning: python3 not found; skipped HTML/PDF post-processing.\n' >&2
    fi
  fi

  refresh_dashboard

  printf '\nDry-run finished at %s UTC.\n' "$(date -u '+%Y-%m-%d %H:%M:%S')"
  printf 'No Cursor agent, git worktrees, PRs, or Feishu messages were sent.\n'
  printf 'Open %s/dashboard.html to review the mock result.\n' "${WORKSPACE_ROOT}"
}

load_scan_prompt() {
  if [[ -f "${COMPOSE_PROMPT_SCRIPT}" ]] && command -v python3 >/dev/null 2>&1; then
    python3 "${COMPOSE_PROMPT_SCRIPT}" "${WORKSPACE_ROOT}"
    return $?
  fi
  if [[ -f "${PROMPT_FILE}" ]]; then
    cat "${PROMPT_FILE}"
    return 0
  fi
  return 1
}

refresh_scan_worktrees() {
  local mode="${1:-refresh}"
  local script="${LUMEN_LIB_DIR}/prepare_scan_worktrees.py"
  [[ -f "${script}" ]] || return 0
  command -v python3 >/dev/null 2>&1 || return 0
  printf '\n[scan] %s scan worktrees...\n' "${mode}"
  python3 "${script}" "${mode}" "${WORKSPACE_ROOT}" 2>&1 | tee -a "${LOG_FILE}" || {
    printf 'Warning: scan worktree %s failed. See log for details.\n' "${mode}" >&2
    return 1
  }
}

run_secure_agent() {
  python3 "${SECURE_AGENT_PY}" --agent-id dylan --project "${PROJECT_NAME}" -- "$@"
}

refresh_twg_auth() {
  local refresh_py="${LUMEN_LIB_DIR}/jira_sync.py"
  [[ -f "${refresh_py}" ]] || return 0
  command -v python3 >/dev/null 2>&1 || return 0
  if ! python3 "${refresh_py}" refresh --scan-workspace "${WORKSPACE_ROOT}" 2>&1 | tee -a "${LOG_FILE}"; then
    printf 'Warning: TWG auth refresh failed. JIRA sync may fail after this scan.\n' >&2
  fi
}

run_real_scan() {
  if [[ "${PROVIDER}" == "cursor_cli" || "${PROVIDER}" == "cursor" ]]; then
    command -v agent >/dev/null 2>&1 || fail "Cursor CLI 'agent' was not found in PATH. Install it from https://cursor.com/cli before running a scan."
    if [[ -z "${CURSOR_API_KEY:-}" ]] && ! agent status >/dev/null 2>&1; then
      fail "Cursor agent is not authenticated for non-interactive runs. Add CURSOR_API_KEY to ${WORKSPACE_ROOT}/.env.local (Cursor Settings > API Keys), then re-run the scan."
    fi
    if [[ -z "${CURSOR_API_KEY:-}" && ! -t 0 ]]; then
      fail "Scheduled scans require CURSOR_API_KEY in ${WORKSPACE_ROOT}/.env.local. Interactive 'agent login' tokens are not available to cron. Add the key from Cursor Settings > API Keys."
    fi
  fi
  local scan_prompt
  scan_prompt="$(load_scan_prompt)" || fail "Scan prompt not found. Run 'lumen init' or 'lumen upgrade --project <slug>' in this workspace first."

  refresh_twg_auth

  refresh_scan_worktrees refresh || true

  printf 'Lumen workspace: %s\n' "${WORKSPACE_ROOT}"
  if [[ -f "${WORKSPACE_ROOT}/prompts/scan/manifest.json" ]]; then
    printf 'Prompt source: prompts/scan/manifest.json (composed snippets)\n'
  elif [[ -f "${WORKSPACE_ROOT}/config/prompts/manifest.json" ]]; then
    printf 'Prompt source: config/prompts/manifest.json (legacy composed snippets)\n'
  else
    printf 'Prompt file: %s\n' "${PROMPT_FILE}"
  fi
  printf 'AI provider: %s\n' "${PROVIDER}"
  printf 'AI model: %s\n' "${MODEL}"
  printf 'Sandbox mode: %s\n' "${SANDBOX_MODE}"
  printf 'Output format: %s\n' "${OUTPUT_FORMAT}"
  printf 'Run log: %s\n' "${LOG_FILE}"

  if [[ -z "${FEISHU_WEBHOOK_URL:-}" ]]; then
    printf 'Notice: FEISHU_WEBHOOK_URL is not set. The Feishu notification step will be skipped after this scan.\n'
  fi

  if ! command -v gh >/dev/null 2>&1; then
    printf 'Notice: GitHub CLI (gh) is not installed. Scanning can continue, but post-scan PR creation will be skipped.\n'
  elif command -v python3 >/dev/null 2>&1 && [[ -f "${LUMEN_LIB_DIR}/github_auth_context.py" ]]; then
    python3 "${LUMEN_LIB_DIR}/github_auth_context.py" preflight "${WORKSPACE_ROOT}" 2>&1 | tee -a "${LOG_FILE}" || true
  elif ! gh auth status >/dev/null 2>&1; then
    printf 'Notice: GitHub CLI is installed but not authenticated. Scanning can continue, but post-scan PR creation will be skipped.\n'
  fi

  printf '\nStarting Lumen scan agent at %s UTC...\n' "$(date -u '+%Y-%m-%d %H:%M:%S')"
  printf 'A full scan often takes 15-45 minutes across all repositories.\n'
  printf 'The agent may stay quiet for several minutes before the first visible output.\n'
  printf 'Watch live progress in another terminal:\n'
  printf '  lumen watch --project <slug>\n\n'

  local agent_args=(
    --workspace "${WORKSPACE_ROOT}"
    --workflow auto_scan
    --agent-id dylan
    --project "${PROJECT_NAME}"
    --provider "${PROVIDER}"
    --model "${MODEL}"
    --sandbox "${SANDBOX_MODE}"
    --output-format "${OUTPUT_FORMAT}"
  )

  if [[ "${OUTPUT_FORMAT}" == "stream-json" && "${STREAM_PARTIAL}" == "1" ]]; then
    agent_args+=(--stream-partial-output)
  fi

  set +e
  if [[ "${OUTPUT_FORMAT}" == "stream-json" ]] && command -v python3 >/dev/null 2>&1 && [[ -f "${LUMEN_LIB_DIR}/format_scan_log.py" ]]; then
    python3 "${WORKFLOW_AGENT_PY}" "${agent_args[@]}" "${scan_prompt}" 2>&1 | tee "${LOG_FILE}" | python3 "${LUMEN_LIB_DIR}/format_scan_log.py"
  else
    python3 "${WORKFLOW_AGENT_PY}" "${agent_args[@]}" "${scan_prompt}" 2>&1 | tee "${LOG_FILE}"
  fi
  local agent_exit=${PIPESTATUS[0]}
  set -e

  if [[ "${agent_exit}" -ne 0 ]]; then
    printf '\nLumen scan agent exited with status %s. See log: %s\n' "${agent_exit}" "${LOG_FILE}" >&2
    exit "${agent_exit}"
  fi

  printf '\nLumen scan agent finished at %s UTC.\n' "$(date -u '+%Y-%m-%d %H:%M:%S')"
  run_report_and_notify || true
  refresh_scan_worktrees refresh || true
  refresh_dashboard
}

mkdir -p "${WORKSPACE_ROOT}/state" "${WORKSPACE_ROOT}/logs" "${WORKSPACE_ROOT}/results" "${WORKSPACE_ROOT}/reports"

clear_stale_lock
mkdir "${LOCK_DIR}"

on_scan_exit() {
  local exit_code=$?
  rm -rf "${LOCK_DIR}" 2>/dev/null || true
  if [[ "${exit_code}" -eq 0 ]]; then
    notify_system "Lumen" "${SCAN_LABEL} finished: ${PROJECT_NAME}"
  else
    notify_system "Lumen" "${SCAN_LABEL} failed: ${PROJECT_NAME} (exit ${exit_code})"
  fi
  return "${exit_code}"
}
trap on_scan_exit EXIT

printf '%s\n' "$$" > "${LOCK_DIR}/pid"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "${LOCK_DIR}/started_at"

load_env_file "${WORKSPACE_ROOT}/.env.common"
load_env_file "${WORKSPACE_ROOT}/.env.local"
load_env_file "${LUMEN_HOME}/.env.local"

if [[ -n "${CURSOR_API_KEY:-}" ]] || [[ ! -t 0 ]]; then
  export AGENT_CLI_CREDENTIAL_STORE=file
fi

notify_system "Lumen" "${SCAN_LABEL} started: ${PROJECT_NAME}"

if [[ "${DRY_RUN}" == "1" || "${DRY_RUN}" == "true" || "${DRY_RUN}" == "yes" ]]; then
  run_dry_scan
else
  run_real_scan
fi
