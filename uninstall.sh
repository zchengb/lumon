#!/usr/bin/env bash
set -euo pipefail

LUMON_HOME="${LUMON_HOME:-${LUMEN_HOME:-$HOME/.lumon}}"
BIN_DIR="${LUMON_BIN_DIR:-${LUMEN_BIN_DIR:-$HOME/.local/bin}}"

echo "Removing ${BIN_DIR}/lumon..."
rm -f "${BIN_DIR}/lumon"
rm -f "${BIN_DIR}/lumen"

echo "Removing ${LUMON_HOME}..."
rm -rf "${LUMON_HOME}"

echo "Done. Any initialized scan workspaces (created via 'lumon init') were not touched."
