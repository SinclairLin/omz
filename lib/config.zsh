# Shared by startup and tools. Source at top level: typeset in local.zsh stays global.
source "$OMZ/lib/paths.zsh"
source "$OMZ/config/defaults.zsh"
source "$OMZ/config/env.zsh"
if [[ -f "$OMZ_CONFIG_DIR/local.zsh" ]]; then
  source "$OMZ_CONFIG_DIR/local.zsh"
elif [[ -f "$OMZ/config/env-self.zsh" ]]; then
  source "$OMZ/config/env-self.zsh"
fi
_omz_resolve_options
