# FORK FROM OH MY ZSH

SHORT_HOST=${HOST/.*/}
autoload -Uz add-zsh-hook
zmodload -i zsh/complist
unsetopt correct
setopt auto_pushd
setopt pushd_ignore_dups
setopt pushdminus

function d () {
  if [[ -n $1 ]]; then
    dirs "$@"
  else
    dirs -v | head -10
  fi
}
(( ! $+functions[compdef] )) || compdef _dirs d
ls --color=tty . &>/dev/null && alias ls='ls --color=tty' || alias ls='ls -G'

grep-flag-available() {
    echo | grep $1 "" >/dev/null 2>&1
}
GREP_OPTIONS=""
if grep-flag-available --color=auto; then
    GREP_OPTIONS+=" --color=auto"
fi
VCS_FOLDERS="{.bzr,CVS,.git,.hg,.svn}"

if grep-flag-available --exclude-dir=.cvs; then
    GREP_OPTIONS+=" --exclude-dir=$VCS_FOLDERS"
elif grep-flag-available --exclude=.cvs; then
    GREP_OPTIONS+=" --exclude=$VCS_FOLDERS"
fi
alias grep="grep $GREP_OPTIONS"
unset GREP_OPTIONS
unset VCS_FOLDERS
unfunction grep-flag-available
autoload -U colors && colors
setopt auto_cd
setopt multios
setopt prompt_subst
