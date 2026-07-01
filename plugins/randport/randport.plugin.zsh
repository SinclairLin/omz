# 快速获取随机可用端口
_omz_port_in_use() {
    local port="$1"

    if (( $+commands[ss] )); then
        ss -tuln 2>/dev/null | grep -Eq "[:.]${port}([[:space:]]|$)"
    elif (( $+commands[lsof] )); then
        lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1 || \
            lsof -nP -iUDP:"$port" >/dev/null 2>&1
    elif (( $+commands[netstat] )); then
        netstat -an 2>/dev/null | grep -Eq "[:.]${port}([[:space:]]|$)"
    else
        return 2
    fi
}

function randport() {
    local port
    local start=$((RANDOM % 16384))
    local attempt=0
    local check_status

    while (( attempt < 16384 )); do
        port=$((49152 + (start + attempt) % 16384))
        if _omz_port_in_use "$port"; then
            check_status=0
        else
            check_status=$?
        fi

        case "$check_status" in
            0) ;;
            1)
                print -r -- "$port"
                return 0
                ;;
            2)
                print -u2 -- "randport: neither ss, lsof, nor netstat is available"
                return 1
                ;;
        esac

        (( ++attempt ))
    done

    print -u2 -- "randport: no available port found in 49152-65535"
    return 1
}
