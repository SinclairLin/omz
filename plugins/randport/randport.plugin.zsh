# 快速获取随机可用端口
function randport() {
    local port
    while :; do
        port=$(shuf -i 49152-65535 -n 1)
        if ! ss -tuln | grep -q ":$port "; then
            echo $port
            break
        fi
    done
}
