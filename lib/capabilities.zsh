_omz_fzf_available() {
  if [[ -z ${_OMZ_FZF_CHECKED:-} ]]; then
    typeset -g _OMZ_FZF_CHECKED=true _OMZ_FZF_AVAILABLE=false
    local version
    if (( $+commands[fzf] )); then
      version=$(command fzf --version 2>/dev/null)
      version=${version%% *}
      autoload -Uz is-at-least
      if [[ $version == <->.<->* ]] && is-at-least 0.51.0 "$version"; then
        _OMZ_FZF_AVAILABLE=true
      fi
    fi
  fi
  [[ $_OMZ_FZF_AVAILABLE == true ]]
}

_omz_select_jump() {
  typeset -g _OMZ_JUMP_BACKEND=none _OMZ_JUMP_PENDING=false _OMZ_LUA=''
  [[ $OMZ_PROFILE != minimal && $OMZ_JUMP != none ]] || return 0
  local executable source=${_ZL_DATA:-$HOME/.zlua} decision=''
  if [[ -n ${ZLUA_EXEC:-} ]]; then
    executable=$(command -v -- "$ZLUA_EXEC")
    [[ -n $executable && -x $executable ]] && _OMZ_LUA=$executable
  else
    for executable in lua luajit lua5.4 lua5.3 lua5.2 lua5.1; do
      if (( $+commands[$executable] )); then
        _OMZ_LUA=$commands[$executable]
        break
      fi
    done
  fi
  source=${source:a}
  [[ ! -r "$OMZ_STATE_DIR/migrations/jump-v1" ]] ||
    decision=$(<"$OMZ_STATE_DIR/migrations/jump-v1")
  if [[ -s $source && $decision != "$source" ]]; then
    _OMZ_JUMP_PENDING=true
  fi
  if [[ $OMZ_JUMP == zlua ]]; then
    [[ -z $_OMZ_LUA ]] || _OMZ_JUMP_BACKEND=zlua
  elif (( $+commands[zoxide] )) && [[ $_OMZ_JUMP_PENDING == false ]]; then
    _OMZ_JUMP_BACKEND=zoxide
  elif [[ $OMZ_JUMP == auto && -n $_OMZ_LUA ]]; then
    _OMZ_JUMP_BACKEND=zlua
  fi
  return 0
}
