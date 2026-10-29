#!/usr/bin/env zsh

emulate -LR zsh
setopt pipe_fail
umask 077

export OMZ=${0:A:h:h}
source "$OMZ/lib/config.zsh"
# Personal shell configuration may contain optional probes returning nonzero.
setopt err_exit
source "$OMZ/config/bootstrap.zsh"
source "$OMZ/lib/capabilities.zsh"
source "$OMZ/lib/plugins.zsh"

usage() {
  print -u2 -- "Usage: zsh scripts/manage-plugins.zsh {install|build|verify}"
}
(( $# == 1 )) || { usage; exit 2; }
operation=$1
case "$operation" in
  install|build|verify) ;;
  *) usage; exit 2 ;;
esac

_omz_select_plugins
export ANTIDOTE_HOME="$OMZ_DATA_DIR/plugins"
# Do not inherit a user's Antidote configuration or Git update behavior.
export ANTIDOTE_CONFIG=/dev/null
export GIT_TERMINAL_PROMPT=0
[[ "$operation" == install ]] || export GIT_ALLOW_PROTOCOL=''
antidote_dir="$OMZ_DATA_DIR/antidote"
static_file="$OMZ_CACHE_DIR/plugins.zsh"
temporary=''
bootstrap_temporary=''
# Zsh can skip EXIT on ERR_EXIT inside a function; ZERR covers that path.
trap '[[ -z "$temporary" ]] || rm -f -- "$temporary"
      [[ -z "$bootstrap_temporary" ]] || rm -rf -- "$bootstrap_temporary"' EXIT ZERR
trap 'exit 130' INT
trap 'exit 143' HUP TERM

fail() {
  print -u2 -- "omz: $*"
  exit 1
}

check_checkout() {
  local directory=$1 expected=$2 actual dirty
  [[ -d "$directory/.git" ]] || fail "missing dependency: $directory; run install."
  actual=$(git -C "$directory" rev-parse HEAD) || fail "cannot read checkout: $directory"
  [[ "$actual" == "$expected" ]] ||
    fail "commit mismatch: $directory (expected $expected, found $actual); run install."
  dirty=$(git -C "$directory" status --porcelain --untracked-files=normal)
  [[ -z "$dirty" ]] || fail "local changes in $directory; preserve them before installation or build."
}

check_existing_clean() {
  local directory=$1 dirty
  [[ ! -e "$directory" ]] && return 0
  [[ -d "$directory/.git" ]] || fail "existing path is not a Git checkout: $directory"
  dirty=$(git -C "$directory" status --porcelain --untracked-files=normal)
  [[ -z "$dirty" ]] || fail "local changes in $directory; preserve them before installation."
}

verify_dependencies() {
  (( $#_OMZ_PLUGIN_REPOS )) || return 0
  check_checkout "$antidote_dir" "$OMZ_ANTIDOTE_SHA"
  local index directory
  for (( index = 1; index <= $#_OMZ_PLUGIN_REPOS; index++ )); do
    directory="$ANTIDOTE_HOME/github.com/$_OMZ_PLUGIN_REPOS[$index]"
    check_checkout "$directory" "$_OMZ_PLUGIN_SHAS[$index]"
    if [[ $_OMZ_PLUGIN_REPOS[$index] == skywind3000/z.lua ]]; then
      [[ -r "$directory/z.lua" ]] || fail "missing z.lua entry: $directory"
      continue
    fi
    [[ -r "$directory/${directory:t}.plugin.zsh" &&
       -r "$directory/${directory:t}.zsh" ]] ||
      fail "missing plugin entry: $directory"
  done
}

bootstrap_antidote() {
  check_existing_clean "$antidote_dir"
  if [[ ! -d "$antidote_dir" ]]; then
    bootstrap_temporary=$(mktemp -d "$OMZ_DATA_DIR/.antidote.XXXXXXXX")
    git -C "$bootstrap_temporary" init --quiet
    git -C "$bootstrap_temporary" remote add origin "$OMZ_ANTIDOTE_URL"
    git -C "$bootstrap_temporary" fetch --quiet --depth=1 origin "$OMZ_ANTIDOTE_SHA"
    git -C "$bootstrap_temporary" checkout --quiet --detach "$OMZ_ANTIDOTE_SHA"
    check_checkout "$bootstrap_temporary" "$OMZ_ANTIDOTE_SHA"
    mv -- "$bootstrap_temporary" "$antidote_dir"
    bootstrap_temporary=''
  else
    if [[ "$(git -C "$antidote_dir" rev-parse HEAD)" != "$OMZ_ANTIDOTE_SHA" ]]; then
      git -C "$antidote_dir" fetch --quiet --depth=1 origin "$OMZ_ANTIDOTE_SHA"
      git -C "$antidote_dir" checkout --quiet --detach "$OMZ_ANTIDOTE_SHA"
    fi
  fi
  check_checkout "$antidote_dir" "$OMZ_ANTIDOTE_SHA"
}

if [[ "$operation" == verify ]]; then
  verify_dependencies
  [[ -r "$static_file" ]] || fail "static file is missing; run build."
  IFS= read -r header < "$static_file"
  [[ "$header" == "$(_omz_plugin_signature)" ]] || fail "static file is stale; run build."
  zsh -n "$static_file"
  print -- "omz: verified $OMZ_PROFILE ($#_OMZ_PLUGIN_REPOS plugins), Antidote $OMZ_ANTIDOTE_SHA."
  exit 0
fi

mkdir -p -- "$OMZ_DATA_DIR" "$OMZ_CACHE_DIR"
chmod 700 "$OMZ_DATA_DIR" "$OMZ_CACHE_DIR"
# One lock protects shared checkouts even if two callers use different caches.
zmodload zsh/system
touch "$OMZ_DATA_DIR/.plugins.lock"
zsystem flock -t 0 -f lock_fd "$OMZ_DATA_DIR/.plugins.lock" ||
  fail "another plugin operation is running; retry after it finishes."

if (( $#_OMZ_PLUGIN_REPOS )); then
  if [[ "$operation" == install ]]; then
    for repo in "${_OMZ_PLUGIN_REPOS[@]}"; do
      check_existing_clean "$ANTIDOTE_HOME/github.com/$repo"
    done
    bootstrap_antidote
  else
    verify_dependencies
  fi
fi

temporary=$(mktemp "$OMZ_CACHE_DIR/.plugins.XXXXXXXX")
_omz_plugin_signature > "$temporary"
if (( $#_OMZ_PLUGIN_REPOS )); then
  # Guard every entry before sourcing any plugin, so missing files degrade as a unit.
  # z.lua is a clone that jump.zsh checks; keeping it out keeps the file backend-neutral.
  for repo in "${(@)_OMZ_PLUGIN_REPOS:#skywind3000/z.lua}"; do
    directory="$ANTIDOTE_HOME/github.com/$repo"
    print -r -- "[[ -r ${(q)directory}/${repo:t}.plugin.zsh && -r ${(q)directory}/${repo:t}.zsh ]] || return 1" >> "$temporary"
  done
  source "$antidote_dir/antidote.zsh"
  zstyle ':antidote:bundle' path-style full
  zstyle ':antidote:bundle:*' shallow yes
  zstyle ':antidote:*' zcompile no
  # Antidote owns cloning, pin checkout, and static source generation.
  for line in "${_OMZ_PLUGIN_LINES[@]}"; do
    if [[ ${line%% *} == skywind3000/z.lua ]]; then
      print -r -- "$line" | antidote bundle >/dev/null
    elif [[ ${line%% *} == Aloxaf/fzf-tab ]]; then
      # fzf can be installed or removed after the build; check when sourcing.
      print -r -- 'if _omz_fzf_available && (( $+functions[compdef] )); then' >> "$temporary"
      print -r -- "$line" | antidote bundle >> "$temporary"
      print -r -- 'fi' >> "$temporary"
    else
      print -r -- "$line" | antidote bundle >> "$temporary"
    fi
  done
  verify_dependencies
fi
print -r -- 'return 0' >> "$temporary"
zsh -n "$temporary"
mv -f -- "$temporary" "$static_file"
temporary=''
print -- "omz: $operation complete: $static_file ($OMZ_PROFILE, $#_OMZ_PLUGIN_REPOS plugins)."
