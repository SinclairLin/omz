export RUNEWIDTH_EASTASIAN=0
export FZF_DEFAULT_OPTS="--height 12 --scrollbar=▌▐ --info=inline-right --layout=reverse ${FZF_DEFAULT_OPTS:-}"
export FZF_CTRL_R_OPTS="--history=${(q)OMZ_STATE_DIR}/fzf_query_history ${FZF_CTRL_R_OPTS:-}"
if [[ -d "$OMZ_STATE_DIR" ]]; then
    (umask 077; touch -- "$OMZ_STATE_DIR/fzf_query_history")
    chmod 600 "$OMZ_STATE_DIR/fzf_query_history"
fi

if command -v fd >/dev/null 2>&1; then
    _OMZ_FD_BIN="fd"
elif command -v fdfind >/dev/null 2>&1; then
    _OMZ_FD_BIN="fdfind"
else
    _OMZ_FD_BIN=""
fi

if [[ -n "$_OMZ_FD_BIN" ]]; then
    export FZF_DEFAULT_COMMAND="${_OMZ_FD_BIN} --exclude={.git,.idea,.vscode,.sass-cache,node_modules,build,dist,vendor} --type f"
else
    export FZF_DEFAULT_COMMAND="find . -type f 2>/dev/null"
fi

unset _OMZ_FD_BIN

zstyle ':completion:complete:*:options' sort false
zstyle ':fzf-tab:complete:_zlua:*' query-string input
zstyle ':completion:*:descriptions' format "[%d]"
zstyle ':fzf-tab:*' group-colors $'\033[15m' $'\033[14m' $'\033[33m' $'\033[35m' $'\033[15m' $'\033[14m' $'\033[33m' $'\033[35m'
zstyle ':fzf-tab:*' prefix ''
if [[ "$OSTYPE" == darwin* ]]; then
    zstyle ':completion:*:*:*:*:processes' command "ps -U $USER -o pid,user,command"
    zstyle ':fzf-tab:complete:(kill|ps):argument-rest' fzf-preview '[ "$group" = "process ID" ] && ps -p "$word" -o command='
else
    zstyle ':completion:*:*:*:*:processes' command "ps -u $USER -o pid,user,comm -w -w"
    zstyle ':fzf-tab:complete:(kill|ps):argument-rest' fzf-preview '[ "$group" = "process ID" ] && ps --pid="$word" -o cmd --no-headers -w -w'
fi
zstyle ':fzf-tab:complete:(kill|ps):argument-rest' fzf-flags --preview-window=down:3:wrap
zstyle ':fzf-tab:complete:systemctl-*:*' fzf-preview 'SYSTEMD_COLORS=1 systemctl status $word'
zstyle ':fzf-tab:complete:yay:*' fzf-preview 'yay -Qi $word || yay -Si $word'
zstyle ':fzf-tab:complete:pacman:*' fzf-preview 'pacman -Qi $word || pacman -Si $word'
zstyle ':fzf-tab:complete:(\\|)run-help:*' fzf-preview 'run-help $word'
zstyle ':fzf-tab:complete:(\\|*/|)man:*' fzf-preview 'man $word'
zstyle ':fzf-tab:complete:git-(add|diff|restore):*' fzf-preview 'git diff --color=always $word'
zstyle ':fzf-tab:complete:git-log:*' fzf-preview 'git log --color=always $word'
zstyle ':fzf-tab:complete:git-show:*' fzf-preview 'git show --color=always $word'
zstyle ':fzf-tab:complete:git-checkout:*' fzf-preview '[ -f "$realpath" ] && git diff --color=always $word || git log --color=always $word'
zstyle ':fzf-tab:complete:*:*' fzf-preview 'sh "$OMZ/lib/file_preview.sh" "$realpath"'
zstyle ':fzf-tab:complete:*:*' fzf-flags --height=12
