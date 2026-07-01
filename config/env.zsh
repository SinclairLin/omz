# export TERM="xterm-kitty"

if [[ "$OSTYPE" == darwin* ]]; then
  [[ -d /opt/homebrew/bin ]] && path=(/opt/homebrew/bin $path)
  [[ -d /opt/homebrew/sbin ]] && path=(/opt/homebrew/sbin $path)
fi

[[ -d "$HOME/.config/rofi/scripts" ]] && path=($HOME/.config/rofi/scripts $path)
typeset -U path PATH

if [[ -z "${EDITOR:-}" ]]; then
  if (( $+commands[nvim] )); then
    EDITOR="$commands[nvim]"
  elif (( $+commands[vi] )); then
    EDITOR="$commands[vi]"
  else
    EDITOR="vi"
  fi
fi
export EDITOR
