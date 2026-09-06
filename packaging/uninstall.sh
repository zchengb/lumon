#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'

install_root="${LUMON_INSTALL_ROOT:-${XDG_DATA_HOME:-$HOME/.local/share}/lumon}"
bin_dir="${LUMON_BIN_DIR:-$HOME/.local/bin}"
bin_path="$bin_dir/lumon"
expected_target="$install_root/venv/bin/lumon"

[[ -n "$install_root" && "$install_root" != "/" && "$install_root" != "$HOME" ]] || {
  printf 'lumon uninstaller: refusing broad installation directory: %s\n' "$install_root" >&2
  exit 1
}

if [[ -L "$bin_path" ]]; then
  if [[ "$(readlink "$bin_path")" == "$expected_target" ]]; then
    rm -f -- "$bin_path"
  else
    printf 'lumon uninstaller: leaving unrelated symlink %s\n' "$bin_path" >&2
  fi
elif [[ -e "$bin_path" ]]; then
  printf 'lumon uninstaller: leaving unrelated file %s\n' "$bin_path" >&2
fi

if [[ -e "$install_root" || -L "$install_root" ]]; then
  rm -rf -- "$install_root"
  printf 'Removed %s\n' "$install_root"
else
  printf 'Lumon Shell installation was not found at %s\n' "$install_root"
fi

printf 'Workspace directories and global Skills were not changed.\n'
