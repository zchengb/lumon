#!/usr/bin/env bash
set -euo pipefail

# Lumon installer.
# Usage:
#   ./install.sh                 Install the CLI only (lumon init later, anywhere)
#   ./install.sh <workspace-dir> Install the CLI AND initialize a scan workspace in one step

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LUMON_HOME="${LUMON_HOME:-${LUMEN_HOME:-$HOME/.lumon}}"
LUMEN_HOME="${LUMON_HOME}"
BIN_DIR="${LUMON_BIN_DIR:-${LUMEN_BIN_DIR:-$HOME/.local/bin}}"

BOLD="$(printf '\033[1m')"
GREEN="$(printf '\033[32m')"
YELLOW="$(printf '\033[33m')"
RESET="$(printf '\033[0m')"

echo "${BOLD}Installing Lumon...${RESET}"

# PDF plan replies are rendered locally before upload to Feishu.
pdf_python=""
for candidate in \
  /opt/homebrew/opt/python@*/bin/python3.* \
  /opt/homebrew/bin/python3 \
  /usr/local/opt/python@*/bin/python3.* \
  "$(command -v python3 2>/dev/null || true)"; do
  if [[ -x "${candidate}" ]]; then
    pdf_python="${candidate}"
    break
  fi
done
if [[ -z "${pdf_python}" ]]; then
  echo "${YELLOW}!${RESET} Python 3 is required for PDF plan replies." >&2
  exit 1
fi
if ! "${pdf_python}" -c 'import reportlab' >/dev/null 2>&1; then
  echo "${YELLOW}!${RESET} Installing the PDF export dependency (reportlab) into ${pdf_python}..."
  if ! "${pdf_python}" -m pip install --user reportlab >/dev/null 2>&1; then
    "${pdf_python}" -m pip install --user --break-system-packages reportlab >/dev/null
  fi
fi

GATEWAY_WAS_RUNNING=0
if [[ -f "${LUMON_HOME}/agents/gateway.pid" ]]; then
  gateway_pid="$(tr -d '[:space:]' < "${LUMON_HOME}/agents/gateway.pid" 2>/dev/null || true)"
  if [[ "${gateway_pid}" =~ ^[0-9]+$ ]] && kill -0 "${gateway_pid}" 2>/dev/null; then
    GATEWAY_WAS_RUNNING=1
    "${BIN_DIR}/lumon" agents stop >/dev/null 2>&1 || true
  fi
fi

mkdir -p "${LUMEN_HOME}/lib"
mkdir -p "${BIN_DIR}"

# Lumen owns these library directories. Remove them before copying so
# deleted templates from older versions do not survive upgrades.
rm -rf \
  "${LUMEN_HOME}/lib/scripts" \
  "${LUMEN_HOME}/lib/templates" \
  "${LUMEN_HOME}/lib/standards" \
  "${LUMEN_HOME}/lib/agents" \
  "${LUMEN_HOME}/lib/feishu" \
  "${LUMEN_HOME}/lib/notifications" \
  "${LUMEN_HOME}/lib/workflows" \
  "${LUMEN_HOME}/lib/risk" \
  "${LUMEN_HOME}/lib/skills"
cp -R "${SCRIPT_DIR}/lib/scripts" "${LUMEN_HOME}/lib/"
cp -R "${SCRIPT_DIR}/lib/templates" "${LUMEN_HOME}/lib/"
cp -R "${SCRIPT_DIR}/lib/standards" "${LUMEN_HOME}/lib/"
cp -R "${SCRIPT_DIR}/lib/agents" "${LUMEN_HOME}/lib/"
cp -R "${SCRIPT_DIR}/lib/feishu" "${LUMEN_HOME}/lib/"
cp -R "${SCRIPT_DIR}/lib/notifications" "${LUMEN_HOME}/lib/"
cp -R "${SCRIPT_DIR}/lib/workflows" "${LUMEN_HOME}/lib/"
cp -R "${SCRIPT_DIR}/lib/risk" "${LUMEN_HOME}/lib/"
if [[ -d "${SCRIPT_DIR}/lib/skills" ]]; then
  cp -R "${SCRIPT_DIR}/lib/skills" "${LUMEN_HOME}/lib/"
fi
cp "${SCRIPT_DIR}/VERSION" "${LUMEN_HOME}/VERSION"

chmod +x "${LUMEN_HOME}/lib/scripts/"*.sh 2>/dev/null || true
chmod +x "${LUMEN_HOME}/lib/scripts/"*.py 2>/dev/null || true

# Migrate the installed Agent registry without touching unrelated workspace data.
LUMON_HOME="${LUMEN_HOME}" python3 "${LUMEN_HOME}/lib/scripts/migrate_agent_runtime.py" "${LUMEN_HOME}/agents/config.json" --migrate-workspaces

install -m 0755 "${SCRIPT_DIR}/bin/lumen" "${BIN_DIR}/lumen" 2>/dev/null \
  || { cp "${SCRIPT_DIR}/bin/lumen" "${BIN_DIR}/lumen" && chmod +x "${BIN_DIR}/lumen"; }
install -m 0755 "${SCRIPT_DIR}/bin/lumon" "${BIN_DIR}/lumon" 2>/dev/null \
  || { cp "${SCRIPT_DIR}/bin/lumon" "${BIN_DIR}/lumon" && chmod +x "${BIN_DIR}/lumon"; }

echo "${GREEN}✓${RESET} Installed lumon to ${BIN_DIR}/lumon"
echo "${GREEN}✓${RESET} Installed Lumon library to ${LUMEN_HOME}"

case ":${PATH}:" in
  *":${BIN_DIR}:"*) ;;
  *)
    echo
    echo "${YELLOW}!${RESET} ${BIN_DIR} is not on your PATH."
    echo "  Add this to your ~/.zshrc or ~/.bashrc, then restart your shell:"
    echo
    echo "    export PATH=\"${BIN_DIR}:\$PATH\""
    echo
    ;;
esac

WORKSPACE_DIR="${1:-}"
if [[ -n "${WORKSPACE_DIR}" ]]; then
  echo
  echo "${BOLD}Initializing scan workspace at: ${WORKSPACE_DIR}${RESET}"
  mkdir -p "${WORKSPACE_DIR}"
  LUMEN_HOME="${LUMEN_HOME}" "${BIN_DIR}/lumen" init "${WORKSPACE_DIR}"
fi

echo
echo "${BOLD}Installation complete.${RESET}"
echo
echo "Next steps:"
if [[ -z "${WORKSPACE_DIR}" ]]; then
  echo "  1. Open a new terminal (or 'source ~/.zshrc') so 'lumon' is on your PATH."
  echo "  2. cd into (or create) a directory for your scan workspace."
  echo "  3. Run: lumon init"
else
  echo "  1. Open a new terminal (or 'source ~/.zshrc') so 'lumon' is on your PATH."
  echo "  2. cd \"${WORKSPACE_DIR}\""
fi
echo "  4. Run: lumon list          (see registered projects and IDs)"
echo "  5. Run: lumon doctor"
echo "  6. Run: lumon scan --project <slug>   (see slugs with: lumon list)"
echo "  7. Run: lumon dashboard --project <slug>   (opens the local interactive dashboard)"

if [[ "${GATEWAY_WAS_RUNNING}" -eq 1 ]]; then
  if "${BIN_DIR}/lumon" agents start >/dev/null 2>&1; then
    echo "${GREEN}✓${RESET} Restarted Agent Gateway with the newly installed code"
  else
    echo "${YELLOW}!${RESET} Agent Gateway was running before install but could not be restarted; run: lumon agents start"
  fi
fi
