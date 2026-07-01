#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/SinclairLin/omz}"
TARGET_DIR="${TARGET_DIR:-$HOME/.config/zsh}"
ZSHRC_FILE="${ZSHRC_FILE:-$HOME/.zshrc}"
SOURCE_LINE="source ~/.config/zsh/omz.zsh"

MIN_FZF_VERSION="0.30.0"
MIN_FD_VERSION="8.0.0"

OS_NAME=""
OS_ID=""
OS_LIKE=""
OS_ARCH=""
BREW_BIN=""

log() {
  printf "[install] %s\n" "$*"
}

warn() {
  printf "[warn] %s\n" "$*" >&2
}

die() {
  printf "[error] %s\n" "$*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing required command: $1"
}

need_lua() {
  local lua_bin

  for lua_bin in lua luajit lua5.4 lua5.3 lua5.2 lua5.1; do
    command -v "$lua_bin" >/dev/null 2>&1 && return
  done

  die "missing required command: lua"
}

version_ge() {
  awk -v current="$1" -v required="$2" 'BEGIN {
    current_count = split(current, current_parts, ".")
    required_count = split(required, required_parts, ".")
    count = current_count > required_count ? current_count : required_count

    for (i = 1; i <= count; i++) {
      sub(/[^0-9].*$/, "", current_parts[i])
      sub(/[^0-9].*$/, "", required_parts[i])
      current_part = current_parts[i] + 0
      required_part = required_parts[i] + 0

      if (current_part > required_part) exit 0
      if (current_part < required_part) exit 1
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
  OS_NAME="$(uname -s 2>/dev/null || true)"
  OS_ARCH="$(uname -m 2>/dev/null || true)"
  OS_ID=""
  OS_LIKE=""

  if [ "$OS_NAME" = "Darwin" ]; then
    OS_ID="macos"
    return
  fi

  if [ -f /etc/os-release ]; then
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
    BREW_BIN="/opt/homebrew/bin/brew"
  elif [ -x /usr/local/bin/brew ]; then
    BREW_BIN="/usr/local/bin/brew"
  else
    return 1
  fi
}

install_macos() {
  local brew_prefix

  if [ "$OS_ARCH" != "arm64" ]; then
    warn "macOS architecture $OS_ARCH is supported on a best-effort basis; CI covers Apple Silicon only"
  fi

  if ! find_brew; then
    warn "Homebrew is required on macOS and was not found."
    warn "Install it from https://brew.sh/ and rerun this script."
    warn 'Official command: /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    exit 1
  fi

  log "installing macOS dependencies via Homebrew"
  "$BREW_BIN" install lua fd fzf

  brew_prefix="$("$BREW_BIN" --prefix)"
  PATH="$brew_prefix/bin:$brew_prefix/sbin:$PATH"
  export PATH
}

install_debian_like() {
  log "installing base dependencies via apt"
  as_root apt-get update
  as_root apt-get install -y zsh git curl lua5.4 fd-find

  if ! command -v fd >/dev/null 2>&1 && command -v fdfind >/dev/null 2>&1; then
    log "linking fdfind to /usr/local/bin/fd"
    as_root ln -sf "$(command -v fdfind)" /usr/local/bin/fd
  fi
}

install_arch_like() {
  log "installing base dependencies via pacman"
  as_root pacman -Sy --noconfirm zsh git curl lua fd
}

install_openwrt() {
  log "installing base dependencies via opkg"
  as_root opkg update || true
  as_root opkg install zsh git curl lua || true
}

install_base_deps() {
  detect_os
  case "$OS_ID" in
    macos)
      install_macos
      ;;
    debian|ubuntu|linuxmint|kali|raspbian)
      install_debian_like
      ;;
    arch|manjaro|endeavouros)
      install_arch_like
      ;;
    openwrt)
      install_openwrt
      ;;
    *)
      case "$OS_LIKE" in
        *debian*) install_debian_like ;;
        *arch*) install_arch_like ;;
        *)
          warn "unsupported system: OS=$OS_NAME, ID=$OS_ID, ID_LIKE=$OS_LIKE"
          warn "please install manually: zsh git curl lua fd/fdfind"
          ;;
      esac
      ;;
  esac
}

install_or_update_fzf() {
  if [ -d "$HOME/.fzf/.git" ]; then
    log "updating fzf"
    git -C "$HOME/.fzf" pull --ff-only || warn "failed to update fzf, keep current version"
  elif ! command -v fzf >/dev/null 2>&1; then
    log "installing fzf from upstream"
    git clone --depth 1 https://github.com/junegunn/fzf.git "$HOME/.fzf"
  fi

  if [ -x "$HOME/.fzf/install" ]; then
    "$HOME/.fzf/install" --all --no-bash --no-fish >/dev/null
  fi
}

check_versions() {
  if command -v fzf >/dev/null 2>&1; then
    local fzf_ver
    fzf_ver="$(fzf --version | awk '{print $1}')"
    if ! version_ge "$fzf_ver" "$MIN_FZF_VERSION"; then
      warn "fzf version is old: $fzf_ver (recommended >= $MIN_FZF_VERSION)"
    fi
  else
    warn "fzf not found"
  fi

  if command -v fd >/dev/null 2>&1; then
    local fd_ver
    fd_ver="$(fd --version | awk '{print $2}')"
    if ! version_ge "$fd_ver" "$MIN_FD_VERSION"; then
      warn "fd version is old: $fd_ver (recommended >= $MIN_FD_VERSION)"
    fi
  elif command -v fdfind >/dev/null 2>&1; then
    local fdfind_ver
    fdfind_ver="$(fdfind --version | awk '{print $2}')"
    if ! version_ge "$fdfind_ver" "$MIN_FD_VERSION"; then
      warn "fdfind version is old: $fdfind_ver (recommended >= $MIN_FD_VERSION)"
    fi
  else
    warn "fd/fdfind not found"
  fi
}

install_repo() {
  mkdir -p "$(dirname "$TARGET_DIR")"
  if [ -d "$TARGET_DIR/.git" ]; then
    log "updating existing repo: $TARGET_DIR"
    git -C "$TARGET_DIR" pull --ff-only
  elif [ -d "$TARGET_DIR" ]; then
    warn "$TARGET_DIR exists but is not a git repo; skip clone"
  else
    log "cloning config to $TARGET_DIR"
    git clone "$REPO_URL" "$TARGET_DIR"
  fi
}

ensure_source_line() {
  touch "$ZSHRC_FILE"
  if ! grep -qxF "$SOURCE_LINE" "$ZSHRC_FILE"; then
    log "adding source line to $ZSHRC_FILE"
    printf "%s\n" "$SOURCE_LINE" >>"$ZSHRC_FILE"
  else
    log "source line already exists in $ZSHRC_FILE"
  fi
}

print_next_steps() {
  local zsh_path
  zsh_path="$(command -v zsh || true)"
  printf "\nDone.\n"
  printf "1) Reload: source %s/omz.zsh\n" "$TARGET_DIR"
  if [ -n "$zsh_path" ] && [ "${SHELL:-}" != "$zsh_path" ]; then
    printf "2) Optional: chsh -s %s\n" "$zsh_path"
  fi
}

main() {
  install_base_deps
  need_cmd zsh
  need_cmd git
  need_cmd curl
  need_lua
  install_or_update_fzf
  install_repo
  ensure_source_line
  check_versions
  print_next_steps
}

if [ "${OMZ_INSTALLER_SKIP_MAIN:-0}" != "1" ]; then
  main "$@"
fi
