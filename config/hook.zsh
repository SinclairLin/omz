# auto update the terminal name
_apply_preexec_hook() {
    preexec_hook() { _cmd=($(echo $2)); print -n "\e]2;${(q)_cmd[1]}\a"; }
    add-zsh-hook -Uz preexec preexec_hook
}

_set_title() {
    print -Pn "\e]0;$1\a"
}

# set terminal title as user@host:cwd (use server ip for SSH sessions)
_apply_precmd_title_hook() {
    precmd_title_hook() {
        case "$TERM" in
            xterm*|rxvt*|screen*|tmux*) ;;
            *) return ;;
        esac

        if [[ -n "$SSH_CONNECTION" ]]; then
            local ip
            ip=$(echo "$SSH_CONNECTION" | awk '{print $3}')
            _set_title "%n@${ip}:%~"
        else
            _set_title "%n@%m:%~"
        fi
    }
    add-zsh-hook -Uz precmd precmd_title_hook
}

# auto to last pwd
_apply_chpwd_hook() {
    chpwd_hook() {
        (umask 077; print -r -- "$PWD" >| "$OMZ_STATE_DIR/last_directory")
        chmod 600 "$OMZ_STATE_DIR/last_directory"
    }
    add-zsh-hook -Uz chpwd chpwd_hook
    local currentdir
    if [[ -r "$OMZ_STATE_DIR/last_directory" ]]; then
        currentdir=$(<"$OMZ_STATE_DIR/last_directory")
        [[ -d "$currentdir" ]] && builtin cd -- "$currentdir"
    fi
    return 0
}

