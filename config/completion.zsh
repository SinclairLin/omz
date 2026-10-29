autoload -Uz compaudit compinit
# compdef and _comps are installed by compinit; reuse external initialization.
if (( ! $+functions[compdef] || ! ${+_comps} )); then
  # A declined compaudit prompt leaves compsys off; the rest of startup still loads.
  compinit -d "$OMZ_CACHE_DIR/zcompdump-$ZSH_VERSION" ||
    print -u2 -- "omz: compinit failed; completion is unavailable."
fi
if (( $+functions[compdef] && $+functions[extract] )); then
  _omz_complete_extract() {
    _arguments '(-r --remove)'{-r,--remove}'[Remove archive after successful extraction]' \
      '*:archive:_files'
  }
  compdef _omz_complete_extract extract
fi
