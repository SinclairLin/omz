: ${OMZ_PROFILE:=auto}
: ${OMZ_JUMP:=auto}
: ${OMZ_IMAGE_PREVIEW:=auto}
(( ${+OMZ_DISABLED_PLUGINS} )) || typeset -ga OMZ_DISABLED_PLUGINS=()

_omz_resolve_options() {
  # Delay legacy mappings until after local.zsh so explicit new options win.
  : ${OMZ_RESTORE_DIRECTORY:=${_OMZ_APPLY_CHPWD_HOOK:-false}}
  if [[ -z "${OMZ_HISTORY_SEARCH:-}" ]]; then
    if [[ "${_OMZ_APPLY_HISTORYBYFZF:-}" == false ]]; then
      OMZ_HISTORY_SEARCH=native
    else
      OMZ_HISTORY_SEARCH=auto
    fi
  fi
  if [[ "$OMZ_PROFILE" == auto ]]; then
    if [[ -f /etc/openwrt_release || "$OSTYPE" == *openwrt* ]]; then
      OMZ_PROFILE=minimal
    elif [[ "$OSTYPE" == darwin* ]]; then
      OMZ_PROFILE=desktop
    else
      OMZ_PROFILE=server
    fi
  fi
  case "$OMZ_PROFILE" in
    desktop|server|minimal) ;;
    *)
      [[ -o interactive ]] && print -u2 -- "omz: invalid OMZ_PROFILE; using minimal."
      OMZ_PROFILE=minimal ;;
  esac
  case "$OMZ_JUMP" in
    auto|zoxide|zlua|none) ;;
    *)
      [[ -o interactive ]] && print -u2 -- "omz: invalid OMZ_JUMP; directory jumping is disabled."
      OMZ_JUMP=none ;;
  esac
  case "$OMZ_HISTORY_SEARCH" in
    auto|fzf|native) ;;
    *)
      [[ -o interactive ]] && print -u2 -- "omz: invalid OMZ_HISTORY_SEARCH; using native Ctrl-R."
      OMZ_HISTORY_SEARCH=native ;;
  esac
  [[ "$OMZ_RESTORE_DIRECTORY" == true ]] || OMZ_RESTORE_DIRECTORY=false
  [[ "$OMZ_IMAGE_PREVIEW" == auto ]] || OMZ_IMAGE_PREVIEW=off
  [[ "$OMZ_PROFILE" == desktop ]] || OMZ_IMAGE_PREVIEW=off
  export OMZ_IMAGE_PREVIEW
}

_omz_plugin_enabled() {
  (( ! ${OMZ_DISABLED_PLUGINS[(Ie)$1]} ))
}
