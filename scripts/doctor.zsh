#!/usr/bin/env zsh
# Read-only capability report; do not load interactive configuration or install.
source "${0:A:h:h}/omz.zsh" || exit
source "$OMZ/lib/capabilities.zsh"
source "$OMZ/lib/plugins.zsh"
_omz_select_jump
print -r -- "profile: $OMZ_PROFILE"
print -r -- "source: $OMZ"
print -r -- "config: $OMZ_CONFIG_DIR"
print -r -- "state: $OMZ_STATE_DIR"
print -r -- "data: $OMZ_DATA_DIR"
print -r -- "cache: $OMZ_CACHE_DIR"
print -r -- "jump: requested=$OMZ_JUMP; effective=$_OMZ_JUMP_BACKEND; legacy decision pending=$_OMZ_JUMP_PENDING"
print -r -- "Lua: ${_OMZ_LUA:-not installed (only needed for z.lua)}"
if [[ $OMZ_PROFILE == minimal ]]; then
  print -r -- 'history/Tab: native (minimal)'
elif _omz_fzf_available; then
  print -r -- 'history: official fzf in a real terminal; Tab: fzf-tab when installed'
else
  print -r -- 'history/Tab: native; fzf >= 0.51.0 enables enhanced integration'
fi
if (( $+commands[ouch] )); then
  command ouch --version
  print -r -- "extract/x: available in an interactive shell"
else
  print -r -- "extract/x: disabled; install ouch with your package manager (macOS: brew install ouch)"
fi
for tool in git fzf fd fdfind zoxide bat batcat eza kitten python3; do
  print -r -- "$tool: ${commands[$tool]:-not installed}"
done
if _omz_select_plugins; then
  if (( ! $#_OMZ_PLUGIN_REPOS )); then
    print -r -- 'plugins: no external plugins selected'
  elif [[ -r "$OMZ_CACHE_DIR/plugins.zsh" ]] &&
       IFS= read -r header < "$OMZ_CACHE_DIR/plugins.zsh" &&
       [[ "$header" == "$(_omz_plugin_signature)" ]]; then
    print -r -- 'plugins: static header matches; run manage-plugins.zsh verify for Git/SHA checks'
  else
    print -r -- "plugins: missing/stale; run zsh -df ${(q)OMZ}/scripts/manage-plugins.zsh install"
  fi
fi
print -r -- "images: $OMZ_IMAGE_PREVIEW; auto requires an installed official fzf-preview.sh, supported terminal and fzf preview dimensions"
print -r -- 'images over SSH/tmux: metadata fallback'
print -r -- 'ownership: package manager owns binaries; manage-plugins.zsh owns pinned Git dependencies'
print -r -- 'migration: Python 3 required only for explicit state/jump migration; never applied at startup'
