# Keep startup independent of Antidote, Git, and network access.
# The signature avoids PATH probes, so a build from `zsh -df` matches later shells:
# fzf-tab is checked when sourcing, and z.lua (a clone that jump.zsh checks) is excluded.
_omz_select_plugins() {
  emulate -L zsh
  setopt extendedglob
  typeset -ga _OMZ_PLUGIN_LINES=() _OMZ_PLUGIN_REPOS=() _OMZ_PLUGIN_SHAS=()
  local line repo sha
  local -a fields seen
  while IFS= read -r line || [[ -n "$line" ]]; do
    line=${line%%\#*}
    fields=(${(z)line})
    (( $#fields )) || continue
    repo=$fields[1]
    sha=${fields[2]#pin:}
    if [[ $repo == skywind3000/z.lua ]]; then
      [[ $#fields == 3 && $fields[3] == kind:clone ]] || {
        print -u2 -- "omz: z.lua requires kind:clone in config/plugins.txt"
        return 1
      }
    elif (( $#fields != 2 )); then
      print -u2 -- "omz: invalid entry in config/plugins.txt: $line"
      return 1
    fi
    if [[ $repo != (Aloxaf/fzf-tab|zsh-users/zsh-autosuggestions|zsh-users/zsh-syntax-highlighting|skywind3000/z.lua) ||
          $fields[2] != pin:* || $sha != [0-9a-f](#c40) ]] ||
       (( ${seen[(Ie)$repo]} )); then
      print -u2 -- "omz: invalid or duplicate entry in config/plugins.txt: $line"
      return 1
    fi
    seen+=("$repo")
    [[ "$OMZ_PROFILE" != minimal ]] || continue
    _omz_plugin_enabled "${repo:t}" || continue
    if [[ "$repo" == skywind3000/z.lua ]]; then
      [[ -n ${_OMZ_JUMP_BACKEND:-} ]] || _omz_select_jump
      [[ $_OMZ_JUMP_BACKEND == zlua ]] || continue
    fi
    _OMZ_PLUGIN_LINES+=("${(j: :)fields}")
    _OMZ_PLUGIN_REPOS+=("$repo")
    _OMZ_PLUGIN_SHAS+=("$sha")
  done < "$OMZ/config/plugins.txt"
}

_omz_plugin_signature() {
  emulate -L zsh
  local -a identity=(
    v2 "$OMZ" "$OMZ_DATA_DIR" "$OMZ_CACHE_DIR" "$OMZ_PROFILE"
    "$(<"$OMZ/config/bootstrap.zsh")" "$(<"$OMZ/config/plugins.txt")"
    "${(@)_OMZ_PLUGIN_LINES:#skywind3000/z.lua *}"
  )
  # One literal line, including when a path or manifest contains newlines.
  print -r -- "# omz-static ${(j: :)${(@qqqq)identity}}"
}

_omz_plugin_hint() {
  print -u2 -- "omz: plugins unavailable or stale; run: zsh ${(q)OMZ}/scripts/manage-plugins.zsh install (or build for installed dependencies)."
}

_omz_load_plugins() {
  _omz_select_plugins || return 0
  (( ${#${(@)_OMZ_PLUGIN_REPOS:#skywind3000/z.lua}} )) || return 0
  local file="$OMZ_CACHE_DIR/plugins.zsh" header
  if [[ -r "$file" ]] &&
     IFS= read -r header < "$file" &&
     [[ "$header" == "$(_omz_plugin_signature)" ]]; then
    source "$file" && return 0
  fi
  _omz_plugin_hint
  return 0
}
