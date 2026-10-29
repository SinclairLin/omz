if [[ ${_OMZ_INTERACTIVE_INITIALIZED:-false} == true ]]; then
  # Re-sourcing during startup is common; only a manual reload needs the hint.
  [[ ${_OMZ_PROMPT_SHOWN:-false} != true ]] ||
    print -u2 -- "omz: already initialized; open a new shell to apply configuration changes."
  return 0
fi

export OMZ="${${(%):-%N}:A:h}"

if [[ ${_OMZ_ENV_INITIALIZED:-false} != true ]]; then
  source "$OMZ/lib/config.zsh"
  typeset -g _OMZ_ENV_INITIALIZED=true
fi

[[ -o interactive ]] || return 0
_omz_prepare_directories

source "$OMZ/config/history.zsh"
source "$OMZ/config/keybindings.zsh"
source "$OMZ/functions/extract.zsh"
source "$OMZ/functions/randport.zsh"
source "$OMZ/functions/docker.zsh"
source "$OMZ/lib/capabilities.zsh"

if [[ "$OMZ_PROFILE" != minimal ]] && _omz_fzf_available; then
  source "$OMZ/config/fzf.zsh"
fi
source "$OMZ/config/completion.zsh"
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

# Personal overrides of project aliases, bindings and history; widget plugins load after.
[[ ! -f "$OMZ_CONFIG_DIR/post.zsh" ]] || source "$OMZ_CONFIG_DIR/post.zsh"

if [[ "$OMZ_PROFILE" != minimal ]]; then
  source "$OMZ/lib/plugins.zsh"
  _omz_load_plugins
fi

_omz_mark_prompt_shown() {
  typeset -g _OMZ_PROMPT_SHOWN=true
  add-zsh-hook -d precmd _omz_mark_prompt_shown
}
add-zsh-hook precmd _omz_mark_prompt_shown

typeset -g _OMZ_INTERACTIVE_INITIALIZED=true
return 0
