#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_TMP="$(mktemp -d)"
trap 'rm -rf "$TEST_TMP"' EXIT

fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
assert_contains() {
  case "$1" in *"$2"*) ;; *) fail "expected output to contain: $2" ;; esac
}
assert_not_contains() {
  case "$1" in *"$2"*) fail "unexpected output: $2" ;; esac
}

export OMZ_INSTALLER_SKIP_MAIN=1
# shellcheck disable=SC1091
source "$ROOT_DIR/scripts/install_zsh_config.sh"
unset OMZ_INSTALLER_SKIP_MAIN

version_ge 0.51.0 0.51.0 || fail "equal versions should pass"
version_ge 0.74.5 0.51.0 || fail "newer minor version should pass"
version_ge 10.0.0 8.0.0 || fail "newer major version should pass"
if version_ge 0.30.0 0.51.0; then fail "old fzf should fail threshold"; fi
if version_ge 7.9.9 8.0.0; then fail "old fd should fail threshold"; fi

uname() {
  case "${1:-}" in -s) printf '%s\n' Darwin ;; -m) printf '%s\n' arm64 ;; *) return 1 ;; esac
}
detect_os
[ "$OS_ID/$OS_ARCH" = macos/arm64 ] || fail "macOS detection failed"

BREW_LOG="$TEST_TMP/brew.log"
BREW_PREFIX="$TEST_TMP/homebrew"
mkdir -p "$BREW_PREFIX/bin" "$BREW_PREFIX/sbin"
cat >"$TEST_TMP/brew" <<'BREW'
#!/usr/bin/env sh
if [ "$1" = install ]; then
  printf '%s\n' "$*" >>"$BREW_LOG"
elif [ "$1" = --prefix ]; then
  printf '%s\n' "$BREW_PREFIX"
else
  exit 1
fi
BREW
chmod +x "$TEST_TMP/brew"
export BREW_LOG BREW_PREFIX
find_brew() { BREW_BIN="$TEST_TMP/brew"; }
install_macos
case "$PATH" in "$BREW_PREFIX/bin:$BREW_PREFIX/sbin:"*) ;; *) fail "missing brew PATH" ;; esac
INSTALL_PROFILE=desktop
INSTALL_LUA=none
install_profile_deps
assert_contains "$(cat "$BREW_LOG")" 'install zoxide'
assert_contains "$(cat "$BREW_LOG")" 'install ouch'
assert_contains "$(cat "$BREW_LOG")" 'install bat'
assert_contains "$(cat "$BREW_LOG")" 'install eza'
assert_not_contains "$(cat "$BREW_LOG")" 'lua'

: >"$BREW_LOG"
INSTALL_PROFILE=server
INSTALL_LUA=lua
install_profile_deps
assert_contains "$(cat "$BREW_LOG")" 'install lua'
assert_not_contains "$(cat "$BREW_LOG")" 'ouch'
: >"$BREW_LOG"
INSTALL_PROFILE=minimal
install_profile_deps
[ ! -s "$BREW_LOG" ] || fail "minimal installed enhanced tools"
find_brew() { return 1; }
if output="$(install_macos 2>&1)"; then fail "missing brew must fail"; fi
assert_contains "$output" 'https://brew.sh/'

PACKAGE_LOG="$TEST_TMP/packages.log"
as_root() { printf '%s\n' "$*" >>"$PACKAGE_LOG"; }
install_debian_like
INSTALL_PROFILE=server
INSTALL_LUA=lua
install_profile_deps
assert_contains "$(cat "$PACKAGE_LOG")" 'apt-get install -y zsh git curl ca-certificates'
assert_contains "$(cat "$PACKAGE_LOG")" 'apt-get install -y fd-find'
assert_contains "$(cat "$PACKAGE_LOG")" 'apt-get install -y lua5.4'
: >"$PACKAGE_LOG"
install_arch_like
assert_contains "$(cat "$PACKAGE_LOG")" 'pacman -Syu --needed --noconfirm'

mkdir -p "$TEST_TMP/pkg-bin"
for manager in apk opkg; do
  : >"$PACKAGE_LOG"
  printf '#!/bin/sh\nexit 0\n' >"$TEST_TMP/pkg-bin/$manager"
  chmod +x "$TEST_TMP/pkg-bin/$manager"
  (PATH="$TEST_TMP/pkg-bin:$PATH"; install_openwrt)
  assert_contains "$(cat "$PACKAGE_LOG")" "$manager update"
  assert_contains "$(cat "$PACKAGE_LOG")" 'zsh git git-http curl ca-bundle'
  assert_not_contains "$(cat "$PACKAGE_LOG")" 'bash'
  assert_not_contains "$(cat "$PACKAGE_LOG")" 'lua'
  rm "$TEST_TMP/pkg-bin/$manager"
done

# Optional packages fail independently; no fallback Git downloader is invoked.
PACKAGE_MANAGER=apt
as_root() { return 1; }
output="$(install_optional_package ouch 2>&1)"
assert_contains "$output" 'package unavailable: ouch'

SOURCE_LINE=''
TARGET_DIR="$HOME/.config/zsh"
ZSHRC_FILE="$TEST_TMP/zdot/.zshrc"
mkdir -p "$(dirname "$ZSHRC_FILE")"
printf 'export KEEP_ME=yes' >"$ZSHRC_FILE"
ensure_source_line
ensure_source_line
[ "$(grep -cFx 'source ~/.config/zsh/omz.zsh' "$ZSHRC_FILE")" -eq 1 ] || fail 'duplicate source line'
[ "$(head -n 1 "$ZSHRC_FILE")" = 'export KEEP_ME=yes' ] || fail 'old final line changed'
backups=("$ZSHRC_FILE".omz-backup.*)
[ "${#backups[@]}" -eq 1 ] || fail 'unexpected backup count'
[ "$(cat "${backups[0]}")" = 'export KEEP_ME=yes' ] || fail 'backup mismatch'
TARGET_DIR="$TEST_TMP/custom zsh"
ZSHRC_FILE="$TEST_TMP/custom.zshrc"
ensure_source_line
assert_contains "$(cat "$ZSHRC_FILE")" "source \"$TARGET_DIR/omz.zsh\""

TARGET_DIR="$TEST_TMP/non-git"
mkdir -p "$TARGET_DIR"
touch "$TARGET_DIR/file"
if output="$(check_repo_target 2>&1)"; then fail 'non-git target must fail'; fi
assert_contains "$output" 'exists but is not a git repo'

# Do not inherit this function-test shell's settings into isolated integration tests.
python3 "$ROOT_DIR/tests/test_installation.py"
printf 'installer tests passed\n'
