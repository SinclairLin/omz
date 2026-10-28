[[ ${_OMZ_INTERACTIVE_INITIALIZED:-false} == true ]] && return 0

export OMZ="${${(%):-%N}:A:h}"

if [[ ${_OMZ_ENV_INITIALIZED:-false} != true ]]; then
  source "$OMZ/lib/paths.zsh"
  source "$OMZ/config/defaults.zsh"
  source "$OMZ/config/env.zsh"
  if [[ -f "$OMZ_CONFIG_DIR/local.zsh" ]]; then
    source "$OMZ_CONFIG_DIR/local.zsh"
  elif [[ -f "$OMZ/config/env-self.zsh" ]]; then
    source "$OMZ/config/env-self.zsh"
  fi
  _omz_resolve_options
  typeset -g _OMZ_ENV_INITIALIZED=true
fi

[[ -o interactive ]] || return 0
_omz_prepare_directories || return 1

source "$OMZ/config/history.zsh" || return
source "$OMZ/config/keybindings.zsh"
source "$OMZ/functions/extract.zsh"
source "$OMZ/functions/randport.zsh"
source "$OMZ/functions/docker.zsh"
source "$OMZ/lib/capabilities.zsh"

if [[ "$OMZ_PROFILE" != minimal ]] && _omz_fzf_available; then
  source "$OMZ/config/fzf.zsh"
fi
source "$OMZ/config/completion.zsh" || return
source "$OMZ/lib/init.sh"
source "$OMZ/lib/git-prompt.zsh"

if [[ "$OMZ_PROFILE" != minimal ]]; then
  source "$OMZ/config/fzf-history.zsh"
  _omz_init_fzf_history
  source "$OMZ/config/jump.zsh"
  _omz_init_jump
fi

source "$OMZ/config/aliases.zsh"
source "$OMZ/config/git.zsh"
source "$OMZ/config/hook.zsh"
source "$OMZ/themes/simple.zsh-theme"
[[ "${_OMZ_APPLY_PREEXEC_HOOK:-false}" == true ]] && _apply_preexec_hook
[[ "${_OMZ_APPLY_PRECMD_TITLE_HOOK:-true}" == false ]] || _apply_precmd_title_hook
[[ "$OMZ_RESTORE_DIRECTORY" == true ]] && _apply_chpwd_hook

if [[ "$OMZ_PROFILE" != minimal ]]; then
  source "$OMZ/lib/plugins.zsh"
  _omz_load_plugins
fi

typeset -g _OMZ_INTERACTIVE_INITIALIZED=true
return 0
