#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_TMP="$(mktemp -d)"
trap 'rm -rf "$TEST_TMP"' EXIT

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  case "$1" in
    *"$2"*) ;;
    *) fail "expected output to contain: $2" ;;
  esac
}

export OMZ_INSTALLER_SKIP_MAIN=1
# shellcheck disable=SC1091
source "$ROOT_DIR/scripts/install_zsh_config.sh"
unset OMZ_INSTALLER_SKIP_MAIN

version_ge 0.30.0 0.30.0 || fail "equal versions should pass"
version_ge 0.31.0 0.30.0 || fail "newer minor version should pass"
version_ge 10.0.0 8.0.0 || fail "newer major version should pass"
if version_ge 0.29.0 0.30.0; then
  fail "older minor version should fail"
fi
if version_ge 7.9.9 8.0.0; then
  fail "older major version should fail"
fi

uname() {
  case "${1:-}" in
    -s) printf '%s\n' Darwin ;;
    -m) printf '%s\n' arm64 ;;
    *) return 1 ;;
  esac
}

detect_os
[ "$OS_NAME" = "Darwin" ] || fail "Darwin was not detected"
[ "$OS_ID" = "macos" ] || fail "Darwin did not map to macos"
[ "$OS_ARCH" = "arm64" ] || fail "Apple Silicon architecture was not detected"

BREW_LOG="$TEST_TMP/brew.log"
BREW_PREFIX="$TEST_TMP/homebrew"
mkdir -p "$BREW_PREFIX/bin" "$BREW_PREFIX/sbin"
cat >"$TEST_TMP/brew" <<'EOF'
#!/usr/bin/env sh
if [ "$1" = "install" ]; then
  printf '%s\n' "$*" >>"$BREW_LOG"
elif [ "$1" = "--prefix" ]; then
  printf '%s\n' "$BREW_PREFIX"
else
  exit 1
fi
EOF
chmod +x "$TEST_TMP/brew"
export BREW_LOG BREW_PREFIX

find_brew() {
  BREW_BIN="$TEST_TMP/brew"
}

install_macos
assert_contains "$(cat "$BREW_LOG")" "install lua fd fzf"
case "$PATH" in
  "$BREW_PREFIX/bin:$BREW_PREFIX/sbin:"*) ;;
  *) fail "Homebrew prefix was not added to PATH" ;;
esac

find_brew() {
  return 1
}

if missing_brew_output="$(install_macos 2>&1)"; then
  fail "missing Homebrew should stop installation"
fi
assert_contains "$missing_brew_output" "Homebrew is required"
assert_contains "$missing_brew_output" "https://brew.sh/"

ZSHRC_FILE="$TEST_TMP/.zshrc"
SOURCE_LINE="source ~/.config/zsh/omz.zsh"
ensure_source_line
ensure_source_line
[ "$(grep -cFx "$SOURCE_LINE" "$ZSHRC_FILE")" -eq 1 ] || fail "source line should be idempotent"

printf 'installer tests passed\n'
