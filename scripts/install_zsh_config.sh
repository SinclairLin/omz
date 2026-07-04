#!/usr/bin/env sh
set -eu
if (set -o pipefail) 2>/dev/null; then
  set -o pipefail
fi

REPO_URL="${REPO_URL:-https://github.com/SinclairLin/omz}"
TARGET_DIR="${TARGET_DIR:-$HOME/.config/zsh}"
ZSHRC_FILE="${ZSHRC_FILE:-$HOME/.zshrc}"
SOURCE_LINE="${SOURCE_LINE:-}"

MIN_FZF_VERSION="0.30.0"
MIN_FD_VERSION="8.0.0"
FD_RELEASE_VERSION="${FD_RELEASE_VERSION:-10.3.0}"

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

install_openwrt_fd() {
  fd_arch=""
  case "$(uname -m 2>/dev/null || true)" in
    x86_64|amd64)
      fd_arch="x86_64-unknown-linux-musl"
      ;;
    aarch64|arm64)
      fd_arch="aarch64-unknown-linux-musl"
      ;;
    *)
      warn "fd is not available from OpenWrt packages and no bundled fd release is configured for $(uname -m 2>/dev/null || echo unknown)"
      return
      ;;
  esac

  fd_archive="fd-v${FD_RELEASE_VERSION}-${fd_arch}"
  fd_tmp_dir="$(mktemp -d)"
  fd_url="https://github.com/sharkdp/fd/releases/download/v${FD_RELEASE_VERSION}/${fd_archive}.tar.gz"

  log "installing fd from upstream release"
  if curl -fsSL "$fd_url" -o "$fd_tmp_dir/fd.tar.gz" &&
    tar -xzf "$fd_tmp_dir/fd.tar.gz" -C "$fd_tmp_dir" &&
    [ -x "$fd_tmp_dir/$fd_archive/fd" ] &&
    as_root cp "$fd_tmp_dir/$fd_archive/fd" /usr/bin/fd &&
    as_root chmod +x /usr/bin/fd; then
    log "installed fd to /usr/bin/fd"
  else
    warn "failed to install fd from $fd_url"
  fi

  rm -rf "$fd_tmp_dir"
}

install_openwrt() {
  if command -v apk >/dev/null 2>&1; then
    log "installing base dependencies via apk"
    as_root apk update
    as_root apk add --no-cache bash zsh git git-http curl lua5.4
  elif command -v opkg >/dev/null 2>&1; then
    log "installing base dependencies via opkg"
    as_root opkg update
    as_root opkg install bash zsh git git-http curl lua
  else
    die "missing OpenWrt package manager: apk or opkg"
  fi

  if ! command -v fd >/dev/null 2>&1 && ! command -v fdfind >/dev/null 2>&1; then
    install_openwrt_fd
  fi
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
          warn "please install manually: bash zsh git curl lua fd/fdfind"
          ;;
      esac
      ;;
  esac
}

prepend_path() {
  case ":$PATH:" in
    *":$1:"*) ;;
    *)
      PATH="$1:$PATH"
      export PATH
      ;;
  esac
}

add_fzf_path() {
  if [ -d "$HOME/.fzf/bin" ]; then
    prepend_path "$HOME/.fzf/bin"
  fi
}

install_or_update_fzf() {
  add_fzf_path

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

  add_fzf_path
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
    if [ -z "$(find "$TARGET_DIR" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
      log "cloning config to empty directory: $TARGET_DIR"
      git clone "$REPO_URL" "$TARGET_DIR"
    else
      die "$TARGET_DIR exists but is not a git repo; move it away or set TARGET_DIR to another path"
    fi
  else
    log "cloning config to $TARGET_DIR"
    git clone "$REPO_URL" "$TARGET_DIR"
  fi
}

default_source_line() {
  if [ "$TARGET_DIR" = "$HOME/.config/zsh" ]; then
    printf '%s\n' "source ~/.config/zsh/omz.zsh"
  else
    printf 'source "%s/omz.zsh"\n' "$(printf '%s' "$TARGET_DIR" | sed 's/["\`$\\]/\\&/g')"
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
  touch "$ZSHRC_FILE"
  if ! grep -qxF "$current_source_line" "$ZSHRC_FILE"; then
    log "adding source line to $ZSHRC_FILE"
    printf "%s\n" "$current_source_line" >>"$ZSHRC_FILE"
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
