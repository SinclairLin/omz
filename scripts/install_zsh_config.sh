#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/SinclairLin/omz}"
TARGET_DIR="${TARGET_DIR:-$HOME/.config/zsh}"
ZSHRC_FILE="${ZSHRC_FILE:-$HOME/.zshrc}"
SOURCE_LINE="source ~/.config/zsh/omz.zsh"

MIN_FZF_VERSION="0.30.0"
MIN_FD_VERSION="8.0.0"

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

version_ge() {
  [ "$(printf '%s\n' "$2" "$1" | sort -V | tail -n1)" = "$1" ]
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
  OS_ID=""
  OS_LIKE=""
  if [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    OS_ID="${ID:-}"
    OS_LIKE="${ID_LIKE:-}"
  fi
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
          warn "unsupported distro: ID=$OS_ID, ID_LIKE=$OS_LIKE"
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
  need_cmd git
  need_cmd curl

  install_base_deps
  install_or_update_fzf
  install_repo
  ensure_source_line
  check_versions
  print_next_steps
}

main "$@"
