_omz_port_in_use() {
  local port="$1" sockets
  if (( $+commands[ss] )); then
    sockets=$(command ss -tuln 2>/dev/null) || return 2
    print -r -- "$sockets" | command grep -Eq "[:.]${port}([[:space:]]|$)"
  elif (( $+commands[lsof] )); then
    command lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1 ||
      command lsof -nP -iUDP:"$port" >/dev/null 2>&1
  elif (( $+commands[netstat] )); then
    sockets=$(command netstat -an 2>/dev/null) || return 2
    print -r -- "$sockets" | command grep -Eq "[:.]${port}([[:space:]]|$)"
  else
    return 2
  fi
}

# This probes availability; it does not reserve the returned port.
randport() {
  emulate -L zsh
  local port check_status
  local start=$((RANDOM % 16384)) attempt=0
  while (( attempt < 16384 )); do
    port=$((49152 + (start + attempt) % 16384))
    _omz_port_in_use "$port"
    check_status=$?
    case "$check_status" in
      0) ;;
      1) print -r -- "$port"; return 0 ;;
      *) print -u2 -- "randport: port inspection unavailable or failed (ss, lsof, netstat)"; return 1 ;;
    esac
    (( ++attempt ))
  done
  print -u2 -- "randport: no available port found in 49152-65535"
  return 1
}
