#!/usr/bin/env sh
set -eu

REPO_URL="${REPO_URL:-https://github.com/SinclairLin/omz}"
TARGET_DIR="${TARGET_DIR:-$HOME/.config/zsh}"
ZSHRC_FILE="${ZSHRC_FILE:-${ZDOTDIR:-$HOME}/.zshrc}"
SOURCE_LINE="${SOURCE_LINE:-}"
OMZ_INSTALL_DEPS="${OMZ_INSTALL_DEPS:-1}"
MIN_FZF_VERSION="0.51.0"
MIN_FD_VERSION="8.0.0"
OS_NAME=""
OS_ID=""
OS_LIKE=""
OS_ARCH=""
BREW_BIN=""
PACKAGE_MANAGER=""
INSTALL_PROFILE=""
INSTALL_LUA=""
OPTIONS_FILE=""
MIGRATION_PREVIEW=0

log() { printf '[install] %s\n' "$*"; }
warn() { printf '[warn] %s\n' "$*" >&2; }
die() { printf '[error] %s\n' "$*" >&2; exit 1; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"; }

usage() {
  cat <<'HELP'
Usage: sh scripts/install_zsh_config.sh [--migrate-state-preview]
Install/update sources, install profile packages, verify pinned plugins, then
append one source line. --migrate-state-preview only previews legacy state.

Environment:
  TARGET_DIR       source checkout (default: ~/.config/zsh)
  ZSHRC_FILE       startup file (default: ${ZDOTDIR:-$HOME}/.zshrc)
  REPO_URL         source Git URL
  SOURCE_LINE      optional exact source line
  OMZ_INSTALL_DEPS 1: system package manager; 0: use installed commands only
  OMZ_PROFILE      auto/desktop/server/minimal (local.zsh takes precedence)
  OMZ_JUMP         auto/zoxide/zlua/none (Lua only for compatibility)
  XDG_*_HOME       absolute config/state/data/cache roots

Tools are owned by your package manager. No ~/.fzf updates, Rust compilation,
default-shell changes, or automatic history/jump imports.
HELP
}

version_ge() {
  awk -v current="$1" -v required="$2" 'BEGIN {
    n = split(current, a, "."); m = split(required, b, ".")
    for (i = 1; i <= (n > m ? n : m); i++) {
      sub(/[^0-9].*$/, "", a[i]); sub(/[^0-9].*$/, "", b[i])
      if (a[i] + 0 > b[i] + 0) exit 0
      if (a[i] + 0 < b[i] + 0) exit 1
    }
    exit 0
  }'
}

as_root() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    die "need root permission for: $*"
  fi
}

detect_os() {
  OS_NAME="$(uname -s)"
  OS_ARCH="$(uname -m)"
  OS_ID=""
  OS_LIKE=""
  if [ "$OS_NAME" = Darwin ]; then
    OS_ID=macos
  elif [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    OS_ID="${ID:-}"
    OS_LIKE="${ID_LIKE:-}"
  fi
}

find_brew() {
  if command -v brew >/dev/null 2>&1; then
    BREW_BIN="$(command -v brew)"
  elif [ -x /opt/homebrew/bin/brew ]; then
    BREW_BIN=/opt/homebrew/bin/brew
  elif [ -x /usr/local/bin/brew ]; then
    BREW_BIN=/usr/local/bin/brew
  else
    return 1
  fi
}

install_macos() {
  if ! find_brew; then
    die "Homebrew is required: install it from https://brew.sh/ and rerun, or set OMZ_INSTALL_DEPS=0 with dependencies already installed."
  fi
  # macOS provides zsh, git (Command Line Tools), and curl.
  brew_prefix="$("$BREW_BIN" --prefix)"
  PATH="$brew_prefix/bin:$brew_prefix/sbin:$PATH"
  export PATH
  PACKAGE_MANAGER=brew
  log "macOS $OS_ARCH; runtime validation scope is recorded in docs/verification.md"
}

install_debian_like() {
  PACKAGE_MANAGER=apt
  as_root apt-get update
  as_root apt-get install -y zsh git curl ca-certificates
}

install_arch_like() {
  PACKAGE_MANAGER=pacman
  # Never refresh Arch's database without upgrading installed packages.
  as_root pacman -Syu --needed --noconfirm zsh git curl ca-certificates
}

install_openwrt() {
  if command -v apk >/dev/null 2>&1; then
    PACKAGE_MANAGER=apk
    as_root apk update
    as_root apk add --no-cache zsh git git-http curl ca-bundle
  elif command -v opkg >/dev/null 2>&1; then
    PACKAGE_MANAGER=opkg
    as_root opkg update
    as_root opkg install zsh git git-http curl ca-bundle
  else
    die "missing OpenWrt package manager: apk or opkg"
  fi
}

install_base_deps() {
  [ "$OMZ_INSTALL_DEPS" = 1 ] || return 0
  case "$OS_ID" in
    macos) install_macos ;;
    debian|ubuntu|linuxmint|kali|raspbian) install_debian_like ;;
    arch|manjaro|endeavouros) install_arch_like ;;
    openwrt) install_openwrt ;;
    *)
      case "$OS_LIKE" in
        *debian*) install_debian_like ;;
        *arch*) install_arch_like ;;
        *) warn "no package mapping for $OS_ID; using installed tools only" ;;
      esac ;;
  esac
}

install_optional_package() {
  optional_package="$1"
  log "package manager: $optional_package"
  case "$PACKAGE_MANAGER" in
    brew) "$BREW_BIN" install "$optional_package" ;;
    apt) as_root apt-get install -y "$optional_package" ;;
    pacman) as_root pacman -S --needed --noconfirm "$optional_package" ;;
    apk) as_root apk add --no-cache "$optional_package" ;;
    opkg) as_root opkg install "$optional_package" ;;
    *) return 0 ;;
  esac || warn "package unavailable: $optional_package; keeping the documented runtime fallback"
}

read_install_options() {
  # Share runtime option resolution, including local.zsh and legacy jump data.
  # Use a separate file so personal configuration output cannot corrupt results.
  OPTIONS_FILE="$(mktemp)"
  zsh -dfc '
    source "$1/omz.zsh" || exit
    source "$1/lib/capabilities.zsh"
    _omz_select_jump
    print -r -- "$OMZ_PROFILE" > "$2"
    if [[ $OMZ_JUMP == zlua ||
          ( $OMZ_JUMP == auto && $_OMZ_JUMP_PENDING == true ) ]]; then
      print -r -- lua >> "$2"
    else
      print -r -- none >> "$2"
    fi
  ' -- "$TARGET_DIR" "$OPTIONS_FILE"
  INSTALL_PROFILE="$(sed -n '1p' "$OPTIONS_FILE")"
  INSTALL_LUA="$(sed -n '2p' "$OPTIONS_FILE")"
  rm -f "$OPTIONS_FILE"
  OPTIONS_FILE=""
  log "resolved profile: $INSTALL_PROFILE; Lua requirement: $INSTALL_LUA"
}

install_profile_deps() {
  [ "$OMZ_INSTALL_DEPS" = 1 ] || return 0
  [ "$INSTALL_PROFILE" != minimal ] || return 0
  fd_package=fd
  lua_package=lua
  if [ "$PACKAGE_MANAGER" = apt ]; then
    fd_package=fd-find
    lua_package=lua5.4
  elif [ "$PACKAGE_MANAGER" = apk ]; then
    lua_package=lua5.4
  fi
  install_optional_package "$fd_package"
  install_optional_package fzf
  install_optional_package zoxide
  if [ "$INSTALL_PROFILE" = desktop ]; then
    install_optional_package ouch
    install_optional_package bat
    install_optional_package eza
  fi
  if [ "$INSTALL_LUA" = lua ]; then
    install_optional_package "$lua_package"
  fi
}

check_versions() {
  [ "$INSTALL_PROFILE" != minimal ] || return 0
  if command -v fzf >/dev/null 2>&1; then
    fzf_ver="$(fzf --version | awk '{print $1}')"
    if ! version_ge "$fzf_ver" "$MIN_FZF_VERSION"; then
      warn "fzf $fzf_ver < $MIN_FZF_VERSION: native history/completion; upgrade with its package manager"
    fi
  else
    warn "fzf not found: native history/completion"
  fi
  for fd_bin in fd fdfind; do
    if command -v "$fd_bin" >/dev/null 2>&1; then
      fd_ver="$("$fd_bin" --version | awk '{print $2}')"
      version_ge "$fd_ver" "$MIN_FD_VERSION" || warn "$fd_bin is older than $MIN_FD_VERSION"
      break
    fi
  done
}

check_repo_target() {
  if [ -e "$TARGET_DIR/.git" ]; then
    repo_status="$(git -C "$TARGET_DIR" status --porcelain --untracked-files=normal)" ||
      die "cannot inspect Git checkout: $TARGET_DIR"
    [ -z "$repo_status" ] ||
      die "local changes in $TARGET_DIR; preserve them before updating"
    remote="$(git -C "$TARGET_DIR" remote get-url origin)"
    [ "${remote%.git}" = "${REPO_URL%.git}" ] ||
      die "origin differs from REPO_URL in $TARGET_DIR; set REPO_URL to the existing origin"
  elif [ -d "$TARGET_DIR" ]; then
    [ -z "$(find "$TARGET_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ] ||
      die "$TARGET_DIR exists but is not a git repo; move it away or set TARGET_DIR"
  elif [ -e "$TARGET_DIR" ] || [ -L "$TARGET_DIR" ]; then
    die "TARGET_DIR is not a directory: $TARGET_DIR"
  fi
}

install_repo() {
  check_repo_target
  mkdir -p "$(dirname "$TARGET_DIR")"
  if [ -e "$TARGET_DIR/.git" ]; then
    log "updating existing repo: $TARGET_DIR"
    git -C "$TARGET_DIR" pull --ff-only
  else
    log "cloning config to $TARGET_DIR"
    git clone "$REPO_URL" "$TARGET_DIR"
  fi
  [ -f "$TARGET_DIR/omz.zsh" ] &&
    [ -f "$TARGET_DIR/scripts/manage-plugins.zsh" ] ||
    die "target lacks the current omz entry point or plugin manager"
}

default_source_line() {
  if [ "$TARGET_DIR" = "$HOME/.config/zsh" ]; then
    printf '%s\n' 'source ~/.config/zsh/omz.zsh'
  else
    printf 'source "%s/omz.zsh"\n' "$(printf '%s' "$TARGET_DIR" | sed 's/["`$\\]/\\&/g')"
  fi
}

source_line() {
  if [ -n "$SOURCE_LINE" ]; then
    printf '%s\n' "$SOURCE_LINE"
  else
    default_source_line
  fi
}

ensure_source_line() {
  current_source_line="$(source_line)"
  if [ -f "$ZSHRC_FILE" ] && grep -qxF "$current_source_line" "$ZSHRC_FILE"; then
    log "source line already exists in $ZSHRC_FILE"
    return 0
  fi
  mkdir -p "$(dirname "$ZSHRC_FILE")"
  if [ -e "$ZSHRC_FILE" ] || [ -L "$ZSHRC_FILE" ]; then
    [ -f "$ZSHRC_FILE" ] || die "startup path is not a regular file: $ZSHRC_FILE"
    backup="$(mktemp "$ZSHRC_FILE.omz-backup.XXXXXXXX")"
    cp -p "$ZSHRC_FILE" "$backup"
    chmod 600 "$backup"
    log "startup backup: $backup"
  fi
  # Separate a pre-existing final line even when it lacks a trailing newline.
  printf '\n%s\n' "$current_source_line" >> "$ZSHRC_FILE"
  log "added source line to $ZSHRC_FILE"
}

print_next_steps() {
  printf '\nDone. Open a new Zsh after closing old sessions and reviewing migration.\n'
  printf 'Configuration: %s\nProfile used for installation: %s\n' "$TARGET_DIR" "$INSTALL_PROFILE"
  printf '%s\n' 'Persist profile/backend overrides in your XDG omz/local.zsh.'
  printf 'State preview: zsh -df "%s/scripts/migrate-state.zsh"\n' "$TARGET_DIR"
  printf 'Jump preview:  zsh -df "%s/scripts/migrate-jump.zsh"\n' "$TARGET_DIR"
  printf 'Diagnostics:   zsh -df "%s/scripts/doctor.zsh"\n' "$TARGET_DIR"
}

main() {
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --help|-h) usage; return 0 ;;
      --migrate-state-preview) MIGRATION_PREVIEW=1 ;;
      *) die "unknown option: $1 (see --help)" ;;
    esac
    shift
  done
  case "$OMZ_INSTALL_DEPS" in 0|1) ;; *) die "OMZ_INSTALL_DEPS must be 0 or 1" ;; esac
  case "$TARGET_DIR" in /*) ;; *) die "TARGET_DIR must be absolute" ;; esac
  case "$ZSHRC_FILE" in /*) ;; *) die "ZSHRC_FILE must be absolute" ;; esac
  # Refuse a dirty installation before changing any packages.
  if [ -e "$TARGET_DIR" ] || [ -L "$TARGET_DIR" ]; then
    need_cmd git
    check_repo_target
  fi
  trap '[ -z "$OPTIONS_FILE" ] || rm -f "$OPTIONS_FILE"' EXIT
  trap 'exit 130' INT
  trap 'exit 143' HUP TERM
  detect_os
  install_base_deps
  need_cmd zsh
  need_cmd git
  need_cmd curl
  install_repo
  read_install_options
  install_profile_deps
  check_versions
  zsh -df "$TARGET_DIR/scripts/manage-plugins.zsh" install
  zsh -df "$TARGET_DIR/scripts/manage-plugins.zsh" verify
  if [ "$MIGRATION_PREVIEW" = 1 ]; then
    zsh -df "$TARGET_DIR/scripts/migrate-state.zsh"
  fi
  # Append the startup entry only after preparation and verification succeeded.
  ensure_source_line
  print_next_steps
}

if [ "${OMZ_INSTALLER_SKIP_MAIN:-0}" != 1 ]; then
  main "$@"
fi
