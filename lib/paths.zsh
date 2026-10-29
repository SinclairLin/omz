# Resolve paths without creating files in noninteractive shells.
_omz_set_directory() {
  local base=$2
  [[ "$base" == /* ]] || base=$3
  export "$1=$base/omz"
}
_omz_set_directory OMZ_CONFIG_DIR "${XDG_CONFIG_HOME:-}" "$HOME/.config"
_omz_set_directory OMZ_STATE_DIR "${XDG_STATE_HOME:-}" "$HOME/.local/state"
_omz_set_directory OMZ_DATA_DIR "${XDG_DATA_HOME:-}" "$HOME/.local/share"
_omz_set_directory OMZ_CACHE_DIR "${XDG_CACHE_HOME:-}" "$HOME/.cache"
unfunction _omz_set_directory
ZSH_CACHE_DIR="$OMZ_CACHE_DIR"

# Glob qualifiers check existing modes without forking; repair only when needed.
_omz_prepare_directories() {
  emulate -L zsh
  local directory
  local -a ready
  for directory in "$OMZ_CONFIG_DIR" "$OMZ_STATE_DIR" "$OMZ_DATA_DIR" "$OMZ_CACHE_DIR"; do
    ready=( $directory(N/f700) )
    (( $#ready )) && continue
    (umask 077; mkdir -p -- "$directory" && chmod 700 "$directory") ||
      print -u2 -- "omz: cannot prepare private directory: $directory"
  done
  return 0
}

_omz_private_file() {
  emulate -L zsh
  local -a ready=( $1(N.f600) )
  (( $#ready )) && return 0
  (umask 077; touch -- "$1" && chmod 600 "$1") 2>/dev/null
}
