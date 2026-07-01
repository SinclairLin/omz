#!/usr/bin/env zsh

ROOT_DIR=${0:A:h:h}
TEST_TMP=$(mktemp -d)
trap 'rm -rf "$TEST_TMP"' EXIT

fail() {
  print -u2 -- "FAIL: $*"
  exit 1
}

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

source "$ROOT_DIR/plugins/randport/randport.plugin.zsh"
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

mkdir -p "$TEST_TMP/home" "$TEST_TMP/zdot"
runtime_path="$PATH"
lua_found=false
for lua_bin in lua luajit lua5.4 lua5.3 lua5.2 lua5.1; do
  if (( $+commands[$lua_bin] )); then
    lua_found=true
    break
  fi
done

if [[ "$lua_found" == false ]]; then
  mkdir -p "$TEST_TMP/bin"
  cat >"$TEST_TMP/bin/lua" <<'EOF'
#!/usr/bin/env sh
exit 0
EOF
  chmod +x "$TEST_TMP/bin/lua"
  runtime_path="$TEST_TMP/bin:$runtime_path"
fi

HOME="$TEST_TMP/home" \
ZDOTDIR="$TEST_TMP/zdot" \
PATH="$runtime_path" \
TERM=xterm-256color \
zsh -dfc "source '$ROOT_DIR/omz.zsh'; whence -w randport >/dev/null"

print 'runtime tests passed'
