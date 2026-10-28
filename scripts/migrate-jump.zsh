#!/usr/bin/env zsh
# Read the same trusted configuration as startup; the Python worker never evaluates data.
emulate -LR zsh
export OMZ=${0:A:h:h}
source "$OMZ/lib/paths.zsh"
source "$OMZ/config/env.zsh"
if [[ -f "$OMZ_CONFIG_DIR/local.zsh" ]]; then
  source "$OMZ_CONFIG_DIR/local.zsh"
elif [[ -f "$OMZ/config/env-self.zsh" ]]; then
  source "$OMZ/config/env-self.zsh"
fi
(( $+commands[python3] )) || {
  print -u2 -- "omz jump migration requires Python 3."
  exit 127
}
(( ! ${+_ZL_DATA} )) || export _ZL_DATA
for name in ${(k)parameters[(I)_ZO_*]}; do
  [[ ${(tP)name} == *scalar* ]] && export "$name"
done
python3 "$OMZ/scripts/migrate-jump.py" "$@"
