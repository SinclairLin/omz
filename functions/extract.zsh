# Keep archive handling in ouch; only own the shell interface and output policy.
(( $+commands[ouch] )) || return 0

extract() {
  emulate -L zsh
  local remove=false archive destination result=0
  while (( $# )); do
    case "$1" in
      -r|--remove) remove=true; shift ;;
      --) shift; break ;;
      -*) print -u2 -- "extract: unknown option: $1 (use -- before filenames starting with -)"; return 2 ;;
      *) break ;;
    esac
  done
  if (( ! $# )); then
    print -u2 -- 'Usage: extract [-r|--remove] [--] <file...>'
    return 2
  fi
  for archive in "$@"; do
    archive=${archive:a}
    destination="$archive.extracted"
    if [[ ! -f $archive ]]; then
      print -u2 -- "extract: not a regular file: $archive"
      result=1
      continue
    fi
    # mkdir reserves a fresh destination and also rejects dangling symlinks.
    if ! command mkdir -- "$destination"; then
      print -u2 -- "extract: cannot create destination: $destination"
      result=1
      continue
    fi
    if command ouch decompress --no --dir "$destination" -- "$archive"; then
      if [[ $remove == true ]]; then
        command rm -- "$archive" || result=1
      fi
    else
      print -u2 -- "extract: failed; archive kept, inspect partial output: $destination"
      command rmdir -- "$destination" 2>/dev/null
      result=1
    fi
  done
  return "$result"
}

alias x=extract
