#!/usr/bin/env zsh

ROOT_DIR=${0:A:h:h}
TEST_TMP=$(mktemp -d)
trap 'rm -rf "$TEST_TMP"' EXIT

fail() {
  print -u2 -- "FAIL: $*"
  exit 1
}

export HOME="$TEST_TMP/home"
export ZDOTDIR="$TEST_TMP/zdot"
export XDG_CONFIG_HOME="$TEST_TMP/config"
export XDG_STATE_HOME="$TEST_TMP/state"
export XDG_DATA_HOME="$TEST_TMP/data"
export XDG_CACHE_HOME="$TEST_TMP/cache"
export OMZ_STATE_DIR="$XDG_STATE_HOME/omz"
mkdir -p "$HOME" "$ZDOTDIR" "$OMZ_STATE_DIR"

EDITOR=/custom/editor
source "$ROOT_DIR/config/env.zsh"
[[ "$EDITOR" == /custom/editor ]] || fail "config/env.zsh overwrote EDITOR"

unset EDITOR
source "$ROOT_DIR/config/env.zsh"
[[ -n "$EDITOR" ]] || fail "config/env.zsh did not select an editor"
if [[ -d /opt/homebrew/bin ]]; then
  (( ${path[(Ie)/opt/homebrew/bin]} )) || fail "Homebrew bin is missing from PATH"
fi

export OMZ="$ROOT_DIR"
OSTYPE=darwin24.0
source "$ROOT_DIR/config/fzf.zsh"
zstyle -s ':fzf-tab:complete:kill:argument-rest' fzf-preview process_preview
[[ "$process_preview" == *'ps -p "$word" -o command='* ]] || fail "Darwin process preview is not using BSD ps"

OSTYPE=linux-gnu
source "$ROOT_DIR/config/fzf.zsh"
zstyle -s ':fzf-tab:complete:kill:argument-rest' fzf-preview process_preview
[[ "$process_preview" == *'ps --pid="$word"'* ]] || fail "Linux process preview lost GNU ps support"

source "$ROOT_DIR/functions/randport.zsh"
typeset -gi first_checked_port=0
_omz_port_in_use() {
  if (( first_checked_port == 0 )); then
    first_checked_port=$1
    return 0
  fi

  local expected_port=$((49152 + (first_checked_port - 49152 + 1) % 16384))
  (( $1 == expected_port )) || return 2
  return 1
}

port=$(randport) || fail "randport did not return a port"
[[ "$port" == <49152-65535> ]] || fail "randport returned an invalid port: $port"

_omz_port_in_use() {
  return 2
}
if randport >/dev/null 2>&1; then
  fail "randport should fail without a port inspection tool"
fi

HOME="$TEST_TMP/home" \
ZDOTDIR="$TEST_TMP/zdot" \
TERM=xterm-256color \
zsh -dfc 'source "$1/omz.zsh"; (( ! $+functions[randport] && ! $+functions[compdef] ))' -- "$ROOT_DIR" ||
  fail "noninteractive startup loaded interactive functions"

if [[ -z "${OMZ_TEST_PLUGIN_DATA:-}" ]]; then
  OMZ_PROFILE=desktop OMZ_JUMP=zlua zsh -df "$ROOT_DIR/scripts/manage-plugins.zsh" install ||
    fail "plugin test dependency installation failed"
  export OMZ_TEST_PLUGIN_DATA="$XDG_DATA_HOME/omz"
fi
python3 "$ROOT_DIR/tests/test_plugins.py" || fail "plugin tests failed"
python3 "$ROOT_DIR/tests/test_initialization.py" || fail "initialization tests failed"
python3 "$ROOT_DIR/tests/test_migration.py" || fail "migration tests failed"
python3 "$ROOT_DIR/tests/test_interaction.py" || fail "interaction tests failed"
python3 "$ROOT_DIR/tests/test_tools.py" || fail "M4 tool tests failed"

print 'runtime tests passed'
