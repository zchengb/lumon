#!/usr/bin/env bash
set -euo pipefail

# Builds a distributable Lumon CLI zip package.
# Usage: ./package.sh [output-dir]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(tr -d '[:space:]' < "${SCRIPT_DIR}/VERSION")"
OUT_DIR="${1:-${SCRIPT_DIR}/build}"
PKG_NAME="lumon-${VERSION}"
STAGE_DIR="$(mktemp -d)/${PKG_NAME}"

mkdir -p "${OUT_DIR}"
OUT_DIR="$(cd "${OUT_DIR}" && pwd)"
mkdir -p "${STAGE_DIR}"

cp -R "${SCRIPT_DIR}/bin" "${STAGE_DIR}/bin"
cp -R "${SCRIPT_DIR}/lib" "${STAGE_DIR}/lib"
cp "${SCRIPT_DIR}/install.sh" "${STAGE_DIR}/install.sh"
cp "${SCRIPT_DIR}/uninstall.sh" "${STAGE_DIR}/uninstall.sh"
cp "${SCRIPT_DIR}/VERSION" "${STAGE_DIR}/VERSION"
cp "${SCRIPT_DIR}/README.md" "${STAGE_DIR}/README.md"

chmod +x "${STAGE_DIR}/install.sh" "${STAGE_DIR}/uninstall.sh" "${STAGE_DIR}/bin/lumen" "${STAGE_DIR}/bin/lumon"
chmod +x "${STAGE_DIR}/lib/scripts/"*.sh 2>/dev/null || true

ZIP_PATH="${OUT_DIR}/${PKG_NAME}.zip"
rm -f "${ZIP_PATH}"

(cd "$(dirname "${STAGE_DIR}")" && zip -r -q "${ZIP_PATH}" "${PKG_NAME}")

rm -rf "$(dirname "${STAGE_DIR}")"

echo "Package created: ${ZIP_PATH}"
