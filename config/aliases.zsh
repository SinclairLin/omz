alias tree='tree --dirsfirst -F'
alias c=clear
alias lsa='ls -lah'
alias l='ls -lah'
alias ll='ls -lh'
alias la='ls -lAh'
# alias vim=nvim
# alias vi=nvim
if command -v nvim >/dev/null 2>&1; then
  alias vim='nvim'
  alias vi='nvim'
fi
alias lg=lazygit
# alias rr=ranger

# kitty ssh
ssh() {
  if [ "${TERM:-}" = "xterm-kitty" ] && command -v kitten >/dev/null 2>&1; then
    kitten ssh "$@"
  else
    command ssh "$@"
  fi
}

# git alias
alias gco='git checkout'
alias gpo='git push origin $(git symbolic-ref --short -q HEAD)'
alias gpl='git pull origin $(git symbolic-ref --short -q HEAD) --ff-only'
alias gd='git --no-pager diff'
alias gs='git --no-pager status'
alias gss='git --no-pager status -s'
alias gpt='git push origin --tags'
alias glt='git tag -n --sort=taggerdate | tail -n ${1-10}'

alias rp=randport
