#!/usr/bin/env zsh
# Keep migration separate from startup and never evaluate legacy personal data.
emulate -LR zsh
if (( ! $+commands[python3] )); then
  print -u2 -- "omz migration requires Python 3; normal shell startup does not."
  exit 127
fi
python3 "${0:A:h}/migrate-state.py" "$@"
