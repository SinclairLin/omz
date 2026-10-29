_omz_init_fzf_history() {
  [[ $OMZ_HISTORY_SEARCH != native ]] || return 0
  if ! _omz_fzf_available; then
    [[ $OMZ_HISTORY_SEARCH != fzf ]] ||
      print -u2 -- "omz: official history search requires fzf >= 0.51.0; using native Ctrl-R."
    return 0
  fi
  # Upstream restores the ZLE option, which Zsh cannot set without a terminal.
  [[ -t 0 && -t 1 ]] || return 0
  local integration tab_binding script prefix=${commands[fzf]:A:h:h}
  local FZF_CTRL_T_COMMAND='' FZF_ALT_C_COMMAND=''
  # Prefer the selected package's official bindings, without its file-completion layer.
  for script in "$prefix/shell/key-bindings.zsh" \
                "$prefix/share/fzf/key-bindings.zsh" \
                "$prefix/share/doc/fzf/examples/key-bindings.zsh"; do
    if [[ -r $script ]]; then
      source "$script"
      return
    fi
  done
  integration=$(command fzf --zsh) || {
    print -u2 -- "omz: fzf --zsh failed; using native Ctrl-R."
    return 0
  }
  # The output concatenates key-bindings.zsh and completion.zsh; keep only the former.
  if [[ $integration == *$'\n### end: key-bindings.zsh ###'* ]]; then
    eval "${integration%%$'\n### end: key-bindings.zsh ###'*}"
    return
  fi
  # Unknown layout: use all of it, then restore the project Tab entry.
  tab_binding=$(bindkey '^I')
  eval "$integration"
  bindkey '^I' "${tab_binding##* }"
}
