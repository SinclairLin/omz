#!/bin/sh
# Bound text/directory output here; leave image protocols to the installed fzf.
if [ "$#" -ne 1 ]; then
    printf '%s\n' 'Usage: file_preview.sh <path>' >&2
    exit 2
fi
case "$1" in
    /*) preview_path=$1 ;;
    *) preview_path=$PWD/$1 ;;
esac
if [ ! -r "$preview_path" ]; then
    printf 'preview: unreadable path: %s\n' "$preview_path" >&2
    exit 1
fi

if [ -d "$preview_path" ]; then
    # Avoid sorting the entire directory before displaying the first entries.
    if command -v eza >/dev/null 2>&1; then
        eza --all --oneline --sort=none --color=always -- "$preview_path" | head -n 200
    else
        # Display only; no filenames from ls output are parsed or executed.
        # shellcheck disable=SC2012
        ls -1f -- "$preview_path" | head -n 200
    fi
    exit
fi
if [ ! -f "$preview_path" ]; then
    printf 'preview: not a regular file: %s\n' "$preview_path"
    exit 0
fi

mime=$(file -bL --mime-type -- "$preview_path" 2>/dev/null)
case "$mime" in
    text/*|application/json|application/*+json|application/xml|application/*+xml|application/javascript|inode/x-empty)
        if command -v bat >/dev/null 2>&1; then
            head -n 1000 -- "$preview_path" |
                bat --paging=never --style=plain --color=always --file-name "$preview_path"
        elif command -v batcat >/dev/null 2>&1; then
            head -n 1000 -- "$preview_path" |
                batcat --paging=never --style=plain --color=always --file-name "$preview_path"
        else
            head -n 1000 -- "$preview_path"
        fi
        ;;
    image/*)
        preview_script=${OMZ_FZF_PREVIEW_SCRIPT:-}
        if [ -z "$preview_script" ]; then
            fzf_binary=$(command -v fzf 2>/dev/null)
            links=0
            while [ -L "$fzf_binary" ] && [ "$links" -lt 40 ]; do
                link=$(readlink "$fzf_binary") || break
                case "$link" in
                    /*) fzf_binary=$link ;;
                    *) fzf_binary=$(dirname "$fzf_binary")/$link ;;
                esac
                links=$((links + 1))
            done
            if [ -n "$fzf_binary" ]; then
                bin_dir=$(dirname "$fzf_binary")
                prefix=$(dirname "$bin_dir")
                for candidate in "$bin_dir/fzf-preview.sh" \
                    "$prefix/share/fzf/fzf-preview.sh" \
                    "$prefix/share/fzf/bin/fzf-preview.sh" \
                    "$prefix/share/doc/fzf/examples/fzf-preview.sh"; do
                    if [ -r "$candidate" ]; then
                        preview_script=$candidate
                        break
                    fi
                done
            fi
        fi
        image_capable=false
        if [ "${TERM:-dumb}" != dumb ] && [ -z "${TMUX:-}" ] &&
            [ -z "${SSH_CONNECTION:-}${SSH_TTY:-}${SSH_CLIENT:-}" ]; then
            if [ -n "${KITTY_WINDOW_ID:-}" ] && command -v kitten >/dev/null 2>&1; then
                image_capable=true
            elif [ "${TERM_PROGRAM:-}" = iTerm.app ] &&
                command -v imgcat >/dev/null 2>&1 &&
                ! command -v chafa >/dev/null 2>&1; then
                image_capable=true
            fi
        fi
        for dimension in "${FZF_PREVIEW_COLUMNS:-}" "${FZF_PREVIEW_LINES:-}"; do
            case "$dimension" in
                ''|*[!0-9]*|0*) image_capable=false ;;
            esac
        done
        if [ "${OMZ_IMAGE_PREVIEW:-auto}" != off ] &&
            [ "$image_capable" = true ] && [ -n "$preview_script" ] &&
            [ -r "$preview_script" ] && command -v bash >/dev/null 2>&1; then
            bash "$preview_script" "$preview_path" && exit 0
        fi
        printf '%s\n' 'Image preview unavailable or disabled; file information:'
        file -bL -- "$preview_path"
        ;;
    *)
        file -bL -- "$preview_path"
        ;;
esac
