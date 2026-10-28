_omz_init_jump() {
  _omz_select_jump
  local initialization script="$OMZ_DATA_DIR/plugins/github.com/skywind3000/z.lua/z.lua"
  case $_OMZ_JUMP_BACKEND in
    zoxide)
      local name
      for name in ${(k)parameters[(I)_ZO_*]}; do
        [[ ${(tP)name} == *scalar* ]] && export "$name"
      done
      initialization=$(command zoxide init zsh) || {
        print -u2 -- "omz: zoxide init failed; directory jumping is disabled."
        return 0
      }
      eval "$initialization"
      if ! _omz_fzf_available; then
        zi() {
          print -u2 -- "omz: interactive zoxide selection requires fzf >= 0.51.0; use z for keyword jumping."
          return 127
        }
      fi
      alias zz=zi zf=zi
      ;;
    zlua)
      if [[ -r $script ]]; then
        typeset -g ZLUA_SCRIPT=$script
        local -a flags=(zsh once enhanced)
        [[ -n ${_ZL_ZSH_NO_FZF:-} ]] || ! _omz_fzf_available || flags+=(fzf)
        export _ZL_FZF_FLAG=${_ZL_FZF_FLAG:-"-e"}
        # Lua reads its settings from the environment, including non-exported local.zsh values.
        local name
        for name in ${(k)parameters[(I)_ZL_*]}; do
          [[ ${(tP)name} == *scalar* ]] && export "$name"
        done
        initialization=$("$_OMZ_LUA" "$script" --init "${flags[@]}") || {
          print -u2 -- "omz: z.lua init failed; directory jumping is disabled."
          return 0
        }
        eval "$initialization"
        if [[ -z ${_ZL_NO_ALIASES:-} ]]; then
          alias zi="${_ZL_CMD:-z} -I" zz="${_ZL_CMD:-z} -i" zf="${_ZL_CMD:-z} -I"
          alias zc="${_ZL_CMD:-z} -c" zb="${_ZL_CMD:-z} -b"
          alias zbi="${_ZL_CMD:-z} -b -i" zbf="${_ZL_CMD:-z} -b -I"
          alias zh="${_ZL_CMD:-z} -I -t ." zzc='zz -c'
        fi
      else
        print -u2 -- "omz: z.lua is unavailable; run: zsh ${(q)OMZ}/scripts/manage-plugins.zsh install"
      fi
      ;;
    none)
      [[ $OMZ_JUMP != zlua ]] ||
        print -u2 -- "omz: OMZ_JUMP=zlua requires Lua; directory jumping is disabled."
      if [[ $OMZ_JUMP == zoxide && $_OMZ_JUMP_PENDING == false ]]; then
        print -u2 -- "omz: OMZ_JUMP=zoxide requires zoxide; directory jumping is disabled."
      fi
      ;;
  esac
  if [[ $_OMZ_JUMP_PENDING == true && $OMZ_JUMP != zlua ]]; then
    print -u2 -- "omz: legacy jump data awaits a decision; run: zsh ${(q)OMZ}/scripts/migrate-jump.zsh (or select OMZ_JUMP=zlua)."
  fi
  return 0
}
