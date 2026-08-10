#!/usr/bin/env bash
set -euo pipefail

# Cuts a new Lumon CLI release: bumps VERSION, commits, tags, and pushes.
# The push triggers .github/workflows/release.yml, which builds the zip
# package and publishes it as a GitHub Release asset.
#
# Usage: ./release.sh <new-version>
#   e.g. ./release.sh 1.6.1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEW_VERSION="${1:-}"

BOLD="$(printf '\033[1m')"
GREEN="$(printf '\033[32m')"
RED="$(printf '\033[31m')"
RESET="$(printf '\033[0m')"

fail() { printf '%sError:%s %s\n' "${RED}" "${RESET}" "$1" >&2; exit 1; }
ok()   { printf '%s✓%s %s\n' "${GREEN}" "${RESET}" "$1"; }

sync_dashboard_ui_version() {
  [[ -f "dashboard-ui/package.json" ]] || return 0
  command -v npm >/dev/null 2>&1 || fail "npm is required to build the Dashboard for a release."

  npm --prefix dashboard-ui version --no-git-tag-version "${NEW_VERSION}" >/dev/null
  npm --prefix dashboard-ui run build >/dev/null
  git add dashboard-ui/package.json dashboard-ui/package-lock.json lib/templates/dashboard-app
}

[[ -n "${NEW_VERSION}" ]] || fail "Usage: ./release.sh <new-version> (e.g. 1.6.1)"
[[ "${NEW_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "Version must look like X.Y.Z (got: ${NEW_VERSION})"

cd "${SCRIPT_DIR}"

if [[ -n "$(git status --porcelain)" ]]; then
  fail "Working tree is not clean. Commit or stash changes before releasing."
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "${CURRENT_BRANCH}" != "main" ]]; then
  fail "Releases must be cut from 'main' (current branch: ${CURRENT_BRANCH})."
fi

TAG="v${NEW_VERSION}"
if git rev-parse "${TAG}" >/dev/null 2>&1; then
  fail "Tag ${TAG} already exists."
fi

printf '%s' "${NEW_VERSION}" > VERSION
sync_dashboard_ui_version
git add VERSION
git commit -m "chore: release ${TAG}"
git tag -a "${TAG}" -m "Lumon ${TAG}"

ok "Committed VERSION bump and created tag ${TAG}."
printf 'Push with:\n'
printf '  git push origin main --follow-tags\n'
printf '\nThis triggers the "Release" GitHub Actions workflow, which builds\n'
printf 'the zip package and publishes it as a release asset.\n'
