#!/usr/bin/env bash
set -euo pipefail

LUMEN_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${LUMEN_LIB_DIR}/ensure-path.sh" ]]; then
  # shellcheck source=/dev/null
  source "${LUMEN_LIB_DIR}/ensure-path.sh"
  ensure_lumen_path ""
fi

load_env_file() {
  local file="$1"
  if [[ -f "${file}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${file}"
    set +a
  fi
}

RUNTIME_PY="${LUMEN_LIB_DIR}/delivery_runtime.py"
[[ -f "${RUNTIME_PY}" ]] || { printf 'Error: delivery runtime helper not found: %s\n' "${RUNTIME_PY}" >&2; exit 1; }
eval "$(python3 "${RUNTIME_PY}" "$@")"
COMMON_CONFIG="${WORKSPACE_DIR}/config/common.json"
RUN_ID="$(date -u '+%Y%m%d-%H%M%S')"
DELIVERY_STARTED_NS="$(python3 -c 'import time; print(time.monotonic_ns())')"
TRACE_DELIVERY_RECORDED="0"
LOG_DIR="${WORKSPACE_DIR}/logs/delivery"
LOG_FILE="${LOG_DIR}/run-${RUN_ID}.log"
RESULT_FILE="${WORKSPACE_DIR}/results/delivery-result.json"
STARTED_FILE="${WORKSPACE_DIR}/results/delivery-started.json"
PROGRESS_PY="${LUMEN_LIB_DIR}/delivery_progress.py"
ARCHIVE_PY="${LUMEN_LIB_DIR}/archive_delivery_run.py"
AGENT_TRACE_PY="${LUMEN_LIB_DIR}/agent_trace.py"
SECURE_AGENT_PY="${LUMEN_LIB_DIR}/run-agent-secure.py"
WORKFLOW_AGENT_PY="${LUMEN_LIB_DIR}/run-workflow-agent.py"
WEB_SESSION_PY="${LUMEN_LIB_DIR}/web_session.py"
WEB_SESSION_ROOT=""
WEB_SESSION_STATUS="completed"
WEB_SESSION_STOPPED="0"

mkdir -p "${LOG_DIR}" "${WORKSPACE_DIR}/results" "${WORKSPACE_DIR}/config" "${WORKSPACE_DIR}/worktrees"

# Feature worktrees are Story-isolated, but one docs workspace has one delivery
# control plane. Serializing agent runs prevents shared result/progress state,
# JIRA transitions, and expensive verification resources from colliding.
LOCK_DIR="${WORKSPACE_DIR}/locks/delivery-run"
mkdir -p "${WORKSPACE_DIR}/locks"
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  printf 'Error: another Lumen delivery run is already active for this docs workspace. Check `lumen delivery status %s`.\n' "${DOCS_DIR}" >&2
  exit 1
fi
printf '%s\n' "$$" > "${LOCK_DIR}/pid"
date -u '+%Y-%m-%dT%H:%M:%SZ' > "${LOCK_DIR}/started_at"
cleanup_web_sessions() {
  [[ "${WEB_SESSION_STOPPED}" == "0" ]] || return 0
  [[ -n "${WEB_SESSION_ROOT}" && -f "${WEB_SESSION_PY}" ]] || return 0
  WEB_SESSION_STOPPED="1"
  set +e
  python3 "${WEB_SESSION_PY}" stop --session-root "${WEB_SESSION_ROOT}" --result "${RESULT_FILE}" --status "${WEB_SESSION_STATUS}" 2>&1 | tee -a "${LOG_FILE}"
  set -e
}

cleanup_delivery_lock() {
  rm -f "${LOCK_DIR}/pid" "${LOCK_DIR}/started_at"
  rmdir "${LOCK_DIR}" 2>/dev/null || true
}

trap 'cleanup_web_sessions; cleanup_delivery_lock' EXIT

# Scan and delivery share the workspace-local environment. Root-level files are
# read only as a compatibility fallback for docs projects created before init
# became the unified initializer.
load_env_file "${DOCS_DIR}/${WORKSPACE_DIR_NAME}/.env.common"
load_env_file "${DOCS_DIR}/${WORKSPACE_DIR_NAME}/.env.local"
load_env_file "${DOCS_DIR}/.env.common"
load_env_file "${DOCS_DIR}/.env.local"
load_env_file "${LUMEN_HOME:-$HOME/.lumon}/.env.local"

if [[ -n "${CURSOR_API_KEY:-}" ]] || [[ ! -t 0 ]]; then
  export AGENT_CLI_CREDENTIAL_STORE=file
fi

fail() {
  local message="$1"
  WEB_SESSION_STATUS="failed"
  cleanup_web_sessions
  if [[ -f "${PROGRESS_PY}" ]]; then
    python3 "${PROGRESS_PY}" phase --workspace-root "${WORKSPACE_ROOT}" "${CURRENT_PHASE:-notify}" failed --detail "${message}" || true
    python3 "${PROGRESS_PY}" finish --workspace-root "${WORKSPACE_ROOT}" failed --detail "${message}" || true
    python3 "${PROGRESS_PY}" report --workspace-root "${WORKSPACE_ROOT}" || true
  fi
  local failure_py="${LUMEN_LIB_DIR}/write_delivery_failure.py"
  if [[ -f "${failure_py}" ]]; then
    python3 "${failure_py}" "${DOCS_DIR}" --story "${STORY_REF}" --result "${RESULT_FILE}" \
      --run-id "${RUN_ID}" --phase "${CURRENT_PHASE:-delivery}" --message "${message}" || true
    local render_py="${LUMEN_LIB_DIR}/render-delivery-and-notify.py"
    if [[ -f "${render_py}" ]]; then
      python3 "${render_py}" "${RESULT_FILE}" --event delivery.failed | tee -a "${LOG_FILE}" || true
    fi
  fi
  sync_delivery_docs_metadata
  record_delivery_span failed
  archive_delivery || true
  printf 'Error: %s\n' "${message}" >&2
  exit 1
}

record_trace_span() {
  local span_id="$1" name="$2" started_ns="$3" status="${4:-succeeded}"
  [[ -f "${AGENT_TRACE_PY}" ]] || return 0
  python3 "${AGENT_TRACE_PY}" span --workspace-root "${WORKSPACE_ROOT}" --run-id "${RUN_ID}" \
    --span-id "${span_id}" --name "${name}" --started-ns "${started_ns}" --status "${status}" || true
}

record_delivery_span() {
  local status="$1"
  [[ "${TRACE_DELIVERY_RECORDED}" == "0" ]] || return 0
  TRACE_DELIVERY_RECORDED="1"
  record_trace_span delivery delivery "${DELIVERY_STARTED_NS}" "${status}"
}

archive_delivery() {
  [[ -f "${ARCHIVE_PY}" ]] || return 0
  if [[ -f "${RESULT_FILE}" ]] && python3 - "${RESULT_FILE}" <<'PY'
import json, sys
try:
    status = json.load(open(sys.argv[1], encoding="utf-8")).get("delivery_status")
except Exception:
    status = ""
raise SystemExit(0 if status == "awaiting_deploy" else 1)
PY
  then
    return 0
  fi
  python3 "${ARCHIVE_PY}" \
    --workspace-root "${WORKSPACE_ROOT}" \
    --result "${RESULT_FILE}" \
    --progress "${WORKSPACE_DIR}/results/delivery-progress.json" \
    --log-file "${LOG_FILE}" >/dev/null
}

cleanup_completed_worktrees() {
  local cleanup_py="${LUMEN_LIB_DIR}/cleanup_delivery_worktrees.py"
  [[ -f "${cleanup_py}" ]] || return 0
  python3 "${cleanup_py}" "${DOCS_DIR}" --story "${STORY_REF}" | tee -a "${LOG_FILE}" || \
    printf 'Warning: completed delivery worktree cleanup failed. See log: %s\n' "${LOG_FILE}" >&2
}

sync_delivery_docs_metadata() {
  local sync_py="${LUMEN_LIB_DIR}/sync_delivery_docs.py"
  [[ -f "${sync_py}" ]] || return 0
  set +e
  python3 "${sync_py}" "${DOCS_DIR}" --story "${STORY_REF}" --include-config | tee -a "${LOG_FILE}"
  local sync_exit=${PIPESTATUS[0]}
  set -e
  if [[ "${sync_exit}" -ne 0 ]]; then
    progress_message "Warning: delivery metadata commit/push failed; see ${LOG_FILE}"
    printf 'Warning: delivery metadata commit/push failed. See log: %s\n' "${LOG_FILE}" >&2
  else
    progress_message "Delivery metadata committed and pushed to docs repository"
  fi
}

progress_phase() {
  local phase_id="$1"
  local status="$2"
  local detail="${3:-}"
  local step="${4:-}"
  CURRENT_PHASE="${phase_id}"
  [[ -f "${PROGRESS_PY}" ]] || return 0
  python3 "${PROGRESS_PY}" phase --workspace-root "${WORKSPACE_ROOT}" "${phase_id}" "${status}" \
    --detail "${detail}" --step "${step}" || true
}

progress_message() {
  local text="$1"
  [[ -f "${PROGRESS_PY}" ]] || return 0
  python3 "${PROGRESS_PY}" message --workspace-root "${WORKSPACE_ROOT}" "${text}" || true
}

init_delivery_progress() {
  [[ -f "${PROGRESS_PY}" ]] || return 0
  python3 "${PROGRESS_PY}" init \
    --workspace-root "${WORKSPACE_ROOT}" \
    --docs-dir "${DOCS_DIR}" \
    --story "${STORY_REF}" \
    --run-id "${RUN_ID}" \
    --log-file "${LOG_FILE}" || true
  python3 "${PROGRESS_PY}" report --workspace-root "${WORKSPACE_ROOT}" || true
}

finish_delivery_progress() {
  local status="$1"
  local detail="${2:-}"
  [[ -f "${PROGRESS_PY}" ]] || return 0
  python3 "${PROGRESS_PY}" finish --workspace-root "${WORKSPACE_ROOT}" "${status}" --detail "${detail}" || true
  python3 "${PROGRESS_PY}" report --workspace-root "${WORKSPACE_ROOT}" || true
}

model_from_config() {
  local config="${COMMON_CONFIG}"
  [[ -f "${config}" ]] || config="${DELIVERY_CONFIG}"
  if [[ ! -f "${config}" ]]; then
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 - "${config}" <<'PY' 2>/dev/null
import json, sys
try:
    with open(sys.argv[1], encoding='utf-8') as f:
        c = json.load(f)
    print(c.get('execution', {}).get('model', '') or '', end='')
except Exception:
    pass
PY
  fi
}

provider_from_config() {
  local config="${COMMON_CONFIG}"
  [[ -f "${config}" ]] || config="${DELIVERY_CONFIG}"
  if [[ ! -f "${config}" ]]; then
    return 0
  fi
  python3 - "${config}" <<'PY' 2>/dev/null
import json, sys
try:
    value = json.load(open(sys.argv[1], encoding="utf-8")).get("execution", {}).get("provider", "")
    print(value or "", end="")
except Exception:
    pass
PY
}

execution_seconds() {
  local key="$1" fallback="$2"
  [[ -f "${DELIVERY_CONFIG}" ]] || { printf '%s' "${fallback}"; return; }
  python3 - "${DELIVERY_CONFIG}" "${key}" "${fallback}" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        value = int(json.load(handle).get("execution", {}).get(sys.argv[2], sys.argv[3]))
    print(max(1, value), end="")
except Exception:
    print(sys.argv[3], end="")
PY
}

PROVIDER="${LUMON_WORKFLOW_PROVIDER:-$(provider_from_config)}"
PROVIDER="${PROVIDER:-cursor_cli}"
if [[ "${PROVIDER}" == "cursor" || "${PROVIDER}" == "cursor_cli" ]]; then
  MODEL="${CURSOR_AGENT_MODEL:-$(model_from_config)}"
else
  MODEL="$(model_from_config)"
fi
MODEL="${MODEL:-cursor-grok-4.5-medium}"
export LUMEN_MODEL="${MODEL}"
SANDBOX_MODE="${CURSOR_AGENT_SANDBOX:-enabled}"
OUTPUT_FORMAT="${CURSOR_AGENT_OUTPUT_FORMAT:-stream-json}"
STREAM_PARTIAL="${CURSOR_AGENT_STREAM_PARTIAL:-1}"
AGENT_TIMEOUT_SECONDS="${CURSOR_AGENT_TIMEOUT_SECONDS:-$(execution_seconds agent_timeout_seconds 3600)}"
AGENT_IDLE_TIMEOUT_SECONDS="${CURSOR_AGENT_IDLE_TIMEOUT_SECONDS:-$(execution_seconds agent_idle_timeout_seconds 900)}"

figma_mcp_approved() {
  [[ -f "${DELIVERY_CONFIG}" ]] || return 1
  python3 - "${DELIVERY_CONFIG}" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        print("1" if json.load(handle).get("execution", {}).get("approve_mcps") is True else "0", end="")
except Exception:
    print("0", end="")
PY
}

prepare_delivery() {
  local prepare_py="${LUMEN_LIB_DIR}/prepare_delivery_run.py"
  [[ -f "${prepare_py}" ]] || fail "prepare_delivery_run.py not found"
  local dry_flag=""
  [[ "${DRY_RUN}" == "1" ]] && dry_flag="--dry-run"
  python3 "${prepare_py}" "${DOCS_DIR}" --story "${STORY_REF}" --json ${dry_flag}
}

sync_delivery_references() {
  local sync_py="${LUMEN_LIB_DIR}/sync_delivery_workspace.py"
  [[ -f "${sync_py}" ]] || return 0
  python3 "${sync_py}" "${DOCS_DIR}" --story "${STORY_REF}"
}

run_sync_delivery() {
  set +e
  sync_delivery_references 2>&1 | tee -a "${LOG_FILE}"
  local sync_exit=${PIPESTATUS[0]}
  set -e
  if [[ "${sync_exit}" -ne 0 ]]; then
    fail "Delivery reference sync failed. See log: ${LOG_FILE}"
  fi
}

enrich_delivery_progress() {
  local prepare_json="$1"
  [[ -f "${PROGRESS_PY}" ]] || return 0
  python3 "${PROGRESS_PY}" enrich --workspace-root "${WORKSPACE_ROOT}" --prepare-json "${prepare_json}" || true
}

run_prepare_delivery() {
  local prepare_json
  set +e
  prepare_json="$(prepare_delivery 2>&1 | tee -a "${LOG_FILE}")"
  local prep_exit=${PIPESTATUS[0]}
  set -e
  if [[ "${prep_exit}" -ne 0 ]]; then
    progress_phase preflight failed "Story gates or worktree preparation failed"
    fail "${prepare_json##*$'\n'}"
  fi
  enrich_delivery_progress "${prepare_json}"
}

start_web_sessions() {
  [[ -f "${WEB_SESSION_PY}" ]] || return 0
  set +e
  python3 "${WEB_SESSION_PY}" start --docs-dir "${DOCS_DIR}" --story "${STORY_REF}" --run-id "${RUN_ID}" 2>&1 | tee -a "${LOG_FILE}"
  local session_exit=${PIPESTATUS[0]}
  set -e
  if [[ "${session_exit}" -ne 0 ]]; then
    fail "Authenticated Web session preparation failed. See log: ${LOG_FILE}"
  fi
  WEB_SESSION_ROOT="${WORKSPACE_DIR}/results/web-session/${RUN_ID}"
  if [[ ! -f "${WEB_SESSION_ROOT}/session-context.json" ]] || rg -q '"sessions": \[\]' "${WEB_SESSION_ROOT}/session-context.json" 2>/dev/null; then
    WEB_SESSION_ROOT=""
    progress_message "No configured Web runtime; authenticated Web session skipped"
  else
    progress_message "Authenticated Web session is ready for the implementation Agent"
  fi
}

send_started_notification() {
  local render_py="${LUMEN_LIB_DIR}/render-delivery-and-notify.py"
  local starter_py="${LUMEN_LIB_DIR}/write_delivery_started.py"
  if [[ ! -f "${render_py}" || ! -f "${starter_py}" ]]; then
    return 0
  fi
  local starter_result="${STARTED_FILE}"
  python3 "${starter_py}" "${DOCS_DIR}" "${starter_result}" --story "${STORY_REF}" || return 0
  python3 "${render_py}" "${starter_result}" --event delivery.started | tee -a "${LOG_FILE}" || true
}

capture_jira_context() {
  local capture_py="${LUMEN_LIB_DIR}/capture_jira_context.py"
  [[ -f "${capture_py}" ]] || return 0
  set +e
  python3 "${capture_py}" "${DOCS_DIR}" --story "${STORY_REF}" | tee -a "${LOG_FILE}"
  local capture_exit=${PIPESTATUS[0]}
  set -e
  if [[ "${capture_exit}" -ne 0 ]]; then
    printf 'Warning: JIRA context snapshot was not captured. The Story and approved plan remain authoritative.\n' >&2
  fi
}

load_delivery_prompt() {
  local compose_py="${LUMEN_LIB_DIR}/compose_delivery_prompt.py"
  [[ -f "${compose_py}" ]] || fail "compose_delivery_prompt.py not found"
  python3 "${compose_py}" "${DOCS_DIR}" "${STORY_REF}" "$@"
}

remediation_max_attempts() {
  [[ -f "${DELIVERY_CONFIG}" ]] || { printf '2'; return; }
  python3 - "${DELIVERY_CONFIG}" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        config = json.load(handle)
    remediation = config.get("verification", {}).get("remediation", {})
    if not isinstance(remediation, dict) or not remediation.get("enabled", True):
        print(0, end="")
    else:
        print(max(0, int(remediation.get("max_attempts", 2))), end="")
except Exception:
    print(2, end="")
PY
}

run_delivery_agent() {
  local prompt="$1"
  local stage="$2"
  local attempt="$3"
  local stage_label="$4"
  [[ "${SANDBOX_MODE}" == "enabled" ]] || fail "Auto Delivery requires the secure Agent sandbox to be enabled."
  local workflow_agent=(python3 "${WORKFLOW_AGENT_PY}"
    --workspace "${WORKSPACE_ROOT}"
    --workflow auto_delivery
    --agent-id mark
    --project "${STORY_REF}"
    --provider "${PROVIDER}"
    --model "${MODEL}"
    --sandbox "${SANDBOX_MODE}"
    --output-format "${OUTPUT_FORMAT}"
  )
  if [[ "${OUTPUT_FORMAT}" == "stream-json" && "${STREAM_PARTIAL}" == "1" ]]; then
    workflow_agent+=(--stream-partial-output)
  fi
  if [[ "${prompt}" == *"Figma MCP access is explicitly approved for this delivery."* ]] && [[ "$(figma_mcp_approved)" == "1" ]]; then
    workflow_agent+=(--approve-mcps)
  fi

  printf 'Starting %s at %s UTC...\n' "${stage_label}" "$(date -u '+%Y-%m-%d %H:%M:%S')"
  set +e
  if [[ -f "${AGENT_TRACE_PY}" ]]; then
    local lumen_version="" provider_version=""
    [[ -f "${LUMEN_LIB_DIR}/../../VERSION" ]] && lumen_version="$(tr -d '[:space:]' < "${LUMEN_LIB_DIR}/../../VERSION")"
    provider_version="${PROVIDER} API"
    if [[ "${PROVIDER}" == "cursor_cli" ]]; then
      provider_version="$(agent --version 2>/dev/null || true)"
    fi
    python3 "${AGENT_TRACE_PY}" run \
      --workspace-root "${WORKSPACE_ROOT}" --docs-dir "${DOCS_DIR}" --story "${STORY_REF}" \
      --run-id "${RUN_ID}" --stage "${stage}" --attempt "${attempt}" \
      --provider "${PROVIDER}" --model "${MODEL}" --output-format "${OUTPUT_FORMAT}" --sandbox "${SANDBOX_MODE}" \
      --lumen-version "${lumen_version}" --provider-version "${provider_version}" --timeout "${AGENT_TIMEOUT_SECONDS}" --idle-timeout "${AGENT_IDLE_TIMEOUT_SECONDS}" \
      -- "${workflow_agent[@]}" \
      < <(printf '%s' "${prompt}") > >(tee -a "${LOG_FILE}") 2> >(tee -a "${LOG_FILE}" >&2)
    local agent_exit=$?
  elif [[ "${OUTPUT_FORMAT}" == "stream-json" ]] && command -v python3 >/dev/null 2>&1 && [[ -f "${LUMEN_LIB_DIR}/format_scan_log.py" ]]; then
    "${workflow_agent[@]}" "${prompt}" 2>&1 | tee -a "${LOG_FILE}" | python3 "${LUMEN_LIB_DIR}/format_scan_log.py"
    local agent_exit=${PIPESTATUS[0]}
  else
    "${workflow_agent[@]}" "${prompt}" 2>&1 | tee -a "${LOG_FILE}"
    local agent_exit=${PIPESTATUS[0]}
  fi
  set -e
  return "${agent_exit}"
}

run_verification_profile() {
  local verify_py="${LUMEN_LIB_DIR}/run_delivery_verification.py"
  [[ -f "${verify_py}" ]] || return 0
  local started_ns
  started_ns="$(python3 -c 'import time; print(time.monotonic_ns())')"
  set +e
  python3 "${verify_py}" "${DOCS_DIR}" --story "${STORY_REF}" --result "${RESULT_FILE}" --workspace-root "${WORKSPACE_ROOT}" | tee -a "${LOG_FILE}"
  local verify_exit=${PIPESTATUS[0]}
  set -e
  VERIFY_RUN_COUNT=$((VERIFY_RUN_COUNT + 1))
  record_trace_span "verification-${VERIFY_RUN_COUNT}" code-verification "${started_ns}" "$([[ "${verify_exit}" -eq 0 ]] && printf succeeded || printf failed)"
  return "${verify_exit}"
}

visual_failure_is_remediable() {
  python3 - "${RESULT_FILE}" <<'PY'
import json
import sys

try:
    payload = json.load(open(sys.argv[1], encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    raise SystemExit(0)
visual = payload.get("visual_verification")
if not isinstance(visual, dict) or visual.get("status") != "failed":
    raise SystemExit(0)
categories = {
    item.get("failure_category")
    for item in visual.get("results", [])
    if isinstance(item, dict) and item.get("status") == "failed"
}
raise SystemExit(0 if categories == {"visual_difference"} else 1)
PY
}

run_remediation_loop() {
  local max_attempts
  max_attempts="$(remediation_max_attempts)"
  [[ "${max_attempts}" =~ ^[0-9]+$ ]] || max_attempts=2
  [[ "${max_attempts}" -gt 0 ]] || return 1

  local remediation_py="${LUMEN_LIB_DIR}/prepare_delivery_remediation.py"
  [[ -f "${remediation_py}" ]] || return 1
  local attempt remediation_prompt prompt_started_ns
  for ((attempt = 1; attempt <= max_attempts; attempt++)); do
    progress_message "Verification failed; starting bounded remediation attempt ${attempt}/${max_attempts}"
    progress_phase agent in_progress "Remediation attempt ${attempt}/${max_attempts}: diagnose and minimally fix verification failures"
    python3 "${remediation_py}" --result "${RESULT_FILE}" --attempt "${attempt}" --max-attempts "${max_attempts}" || return 1
    prompt_started_ns="$(python3 -c 'import time; print(time.monotonic_ns())')"
    remediation_prompt="$(load_delivery_prompt --remediation)" || return 1
    record_trace_span "remediation-prompt-${attempt}" prompt-composition "${prompt_started_ns}"
    if ! run_delivery_agent "${remediation_prompt}" remediation "${attempt}" "Lumen delivery remediation ${attempt}/${max_attempts}"; then
      progress_phase agent failed "Remediation agent exited during attempt ${attempt}/${max_attempts}"
      return 1
    fi
    [[ -f "${RESULT_FILE}" ]] || return 1
    python3 "${remediation_py}" --result "${RESULT_FILE}" --restore --docs-dir "${DOCS_DIR}" --story "${STORY_REF}" || return 1
    progress_phase agent completed "Remediation attempt ${attempt}/${max_attempts} finished; result updated"

    progress_phase verification in_progress "Verification after remediation attempt ${attempt}/${max_attempts}"
    printf '\n[delivery] Verification after remediation %s/%s\n' "${attempt}" "${max_attempts}"
    if run_verification_profile; then
      python3 "${remediation_py}" --result "${RESULT_FILE}" --complete || true
      progress_message "Verification passed after remediation attempt ${attempt}/${max_attempts}"
      return 0
    fi
    progress_phase verification failed "Verification failed after remediation attempt ${attempt}/${max_attempts}"
  done
  return 1
}

run_dry_delivery() {
  local dry_py="${LUMEN_LIB_DIR}/dry_run_delivery.py"
  [[ -f "${dry_py}" ]] || fail "dry_run_delivery.py not found"

  init_delivery_progress
  progress_phase preflight in_progress "Validate story gates and metadata"
  printf '\n[delivery] Phase 1/5 — Sync references and preflight\n'
  run_sync_delivery
  progress_phase worktrees in_progress "Prepare feature worktrees"
  printf '[delivery] Phase 2/5 — Feature worktrees\n'
  run_prepare_delivery
  progress_phase preflight completed "Gates passed"
  progress_phase worktrees completed "Worktrees ready"

  progress_phase agent skipped "Dry run — agent not started"
  progress_phase verification skipped "Dry run — verification not executed"
  progress_phase jira_start skipped "Dry run"
  progress_phase jira_done skipped "Dry run"

  printf '[delivery] Phase 3/5 — Dry-run result\n'
  python3 "${dry_py}" "${DOCS_DIR}" "${STORY_REF}" "${RUN_ID}" | tee -a "${LOG_FILE}"
  [[ -f "${RESULT_FILE}" ]] || fail "Dry run did not produce ${RESULT_FILE}"

  progress_phase notify in_progress "Dry-run notification preview"
  local render_py="${LUMEN_LIB_DIR}/render-delivery-and-notify.py"
  if [[ -f "${render_py}" ]]; then
    LUMEN_DRY_RUN=1 python3 "${render_py}" "${RESULT_FILE}" --event delivery.dev_done | tee -a "${LOG_FILE}" || true
  fi
  progress_phase notify completed "Dry-run notification preview sent"
  finish_delivery_progress completed "Dry run finished"
  archive_delivery
  printf '\nDry-run delivery finished. No Cursor agent, commits, or PRs were created.\n'
}

run_real_delivery() {
  if [[ "${PROVIDER}" == "cursor_cli" || "${PROVIDER}" == "cursor" ]]; then
    command -v agent >/dev/null 2>&1 || fail "Cursor CLI 'agent' was not found in PATH."
  fi

  local refresh_py="${LUMEN_LIB_DIR}/jira_sync.py"
  if [[ -f "${refresh_py}" ]] && command -v python3 >/dev/null 2>&1; then
    if ! python3 "${refresh_py}" refresh --delivery-workspace "${WORKSPACE_DIR}" 2>&1 | tee -a "${LOG_FILE}"; then
      printf 'Warning: TWG auth refresh failed. JIRA sync may fail during this delivery.\n' >&2
    fi
  fi

  init_delivery_progress

  progress_phase preflight in_progress "Validate story gates and metadata"
  printf '\n[delivery] Phase 1/8 — Sync references and preflight\n'
  run_sync_delivery
  local preflight_py="${LUMEN_LIB_DIR}/delivery_preflight.py"
  if [[ -f "${preflight_py}" ]] && ! python3 "${preflight_py}" "${DOCS_DIR}" --story "${STORY_REF}" | tee -a "${LOG_FILE}"; then
    fail "Delivery preflight failed. Fix the listed integrations before retrying."
  fi
  progress_phase worktrees in_progress "Create or refresh feature worktrees"
  printf '[delivery] Phase 2/8 — Feature worktrees\n'
  run_prepare_delivery
  start_web_sessions
  progress_phase preflight completed "Gates passed"
  progress_phase worktrees completed "Worktrees ready"

  progress_phase jira_start in_progress "Notify JIRA IN DEV"
  printf '[delivery] Phase 3/8 — JIRA IN DEV\n'
  capture_jira_context
  send_started_notification
  progress_phase jira_start completed "Started notification sent"

  local delivery_prompt prompt_started_ns
  prompt_started_ns="$(python3 -c 'import time; print(time.monotonic_ns())')"
  delivery_prompt="$(load_delivery_prompt)" || fail "Failed to compose delivery prompt."
  record_trace_span prompt-composition prompt-composition "${prompt_started_ns}"

  printf 'Docs repository: %s\n' "${DOCS_DIR}"
  printf 'Workspace root: %s\n' "${WORKSPACE_ROOT}"
  printf 'Cursor model: %s\n' "${MODEL}"
  printf 'Run log: %s\n' "${LOG_FILE}"
  progress_message "Model=${MODEL}; sandbox=${SANDBOX_MODE}"

  if [[ -z "${FEISHU_WEBHOOK_URL:-}" ]]; then
    printf 'Notice: FEISHU_WEBHOOK_URL is not set. Delivery Feishu notifications will be skipped.\n'
  fi
  if ! command -v gh >/dev/null 2>&1; then
    printf 'Notice: GitHub CLI (gh) is not installed. PR creation may be skipped by the agent.\n'
  elif ! gh auth status >/dev/null 2>&1; then
    printf 'Notice: GitHub CLI is not authenticated. PR creation may be skipped by the agent.\n'
  fi

  progress_phase agent in_progress "Cursor implementation agent"
  printf '\n[delivery] Phase 4/8 — Implementation agent\n'
  printf 'Starting Lumen delivery agent at %s UTC...\n' "$(date -u '+%Y-%m-%d %H:%M:%S')"

  if ! run_delivery_agent "${delivery_prompt}" implementation 1 "Lumen delivery implementation agent"; then
    progress_phase agent failed "Agent exited with a non-zero status"
    fail "Lumen delivery agent exited with a non-zero status. See log: ${LOG_FILE}"
  fi

  [[ -f "${RESULT_FILE}" ]] || fail "Delivery agent did not write ${RESULT_FILE}"
  progress_phase agent completed "Agent finished; result written"

  progress_phase verification in_progress "Configured repository verification checks"
  printf '\n[delivery] Phase 5/8 — Verification\n'
  if ! run_verification_profile; then
    progress_phase verification failed "Verification failed; bounded remediation required"
    if ! run_remediation_loop; then
      progress_phase verification failed "Verification failed after bounded remediation attempts"
      fail "Delivery verification failed after bounded remediation. See log: ${LOG_FILE}"
    fi
    progress_phase verification completed "All verification checks passed"
  else
    progress_phase verification completed "All verification checks passed"
  fi

  cleanup_web_sessions

  progress_phase finalize in_progress "Finalize verified changes"
  printf '\n[delivery] Phase 6/8 — Finalize verified changes\n'
  local merge_py="${LUMEN_LIB_DIR}/delivery_result_merge.py"
  if [[ -f "${merge_py}" ]]; then
    python3 "${merge_py}" --result "${RESULT_FILE}" --docs-dir "${DOCS_DIR}" --story "${STORY_REF}" | tee -a "${LOG_FILE}" || true
  fi
  local finalize_py="${LUMEN_LIB_DIR}/finalize_delivery.py"
  if [[ ! -f "${finalize_py}" ]]; then
    progress_phase finalize failed "Finalization runner not installed"
    fail "Delivery finalization runner not found: ${finalize_py}"
  fi
  set +e
  python3 "${finalize_py}" "${DOCS_DIR}" --story "${STORY_REF}" --result "${RESULT_FILE}" 2>&1 | tee -a "${LOG_FILE}"
  local finalize_exit=${PIPESTATUS[0]}
  set -e
  if [[ "${finalize_exit}" -ne 0 ]]; then
    local failure_detail
    failure_detail="$(
      python3 -c 'import json,sys
path=sys.argv[1]
try:
    data=json.load(open(path, encoding="utf-8"))
except Exception:
    print(sys.argv[2])
    raise SystemExit(0)
for item in reversed(data.get("failures") or []):
    if isinstance(item, dict):
        detail=str(item.get("detail") or "").strip()
        if detail:
            print(detail)
            raise SystemExit(0)
print(sys.argv[2])' "${RESULT_FILE}" "Delivery finalization failed. See log: ${LOG_FILE}"
    )"
    progress_phase finalize failed "${failure_detail}"
    fail "${failure_detail}"
  fi
  progress_phase finalize completed "Delivery finalization complete"

  progress_phase jira_done in_progress "Sync JIRA DEV DONE"
  progress_phase notify in_progress "Feishu and metadata updates"
  printf '[delivery] Phase 7/8 — JIRA DEV DONE\n'
  printf '[delivery] Phase 8/8 — Notifications\n'
  local render_py="${LUMEN_LIB_DIR}/render-delivery-and-notify.py"
  if [[ -f "${render_py}" ]]; then
    python3 "${render_py}" "${RESULT_FILE}" --event delivery.dev_done | tee -a "${LOG_FILE}" || \
      printf 'Warning: delivery notification step failed. See log for details.\n' >&2
  fi
  sync_delivery_docs_metadata
  local deployment_status
  deployment_status="$(python3 - "${RESULT_FILE}" <<'PY'
import json, sys
try:
    print(json.load(open(sys.argv[1], encoding="utf-8")).get("delivery_status", ""))
except Exception:
    print("")
PY
)"
  if [[ "${deployment_status}" == "awaiting_deploy" ]]; then
    progress_phase notify completed "Submitted deployment tracking update"
    progress_phase deployment in_progress "Published; waiting for CI/CD deployment result"
    finish_delivery_progress awaiting_deploy "Published; CI/CD deployment tracking is running"
    record_delivery_span succeeded
    cleanup_completed_worktrees
    printf '\nLumen delivery submitted; deployment tracking continues in the background.\n'
    return 0
  fi
  progress_phase jira_done completed "JIRA sync attempted"
  progress_phase notify completed "Notifications sent"
  finish_delivery_progress completed "Delivery run finished"
  record_delivery_span succeeded
  archive_delivery
  cleanup_completed_worktrees
  printf '\nLumen delivery run finished at %s UTC.\n' "$(date -u '+%Y-%m-%d %H:%M:%S')"
}

cd "${DOCS_DIR}"
VERIFY_RUN_COUNT=0

if [[ "${DRY_RUN}" == "1" || "${DRY_RUN}" == "true" || "${DRY_RUN}" == "yes" ]]; then
  run_dry_delivery
else
  run_real_delivery
fi
