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

_omz_prepare_directories() {
  (
    umask 077
    mkdir -p -- "$OMZ_CONFIG_DIR" "$OMZ_STATE_DIR" "$OMZ_DATA_DIR" "$OMZ_CACHE_DIR" &&
      chmod 700 "$OMZ_CONFIG_DIR" "$OMZ_STATE_DIR" "$OMZ_DATA_DIR" "$OMZ_CACHE_DIR"
  )
}
