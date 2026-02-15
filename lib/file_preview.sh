#! /usr/bin/env sh
mime=$(file -bL --mime-type "$1")
category=${mime%%/*}
if [ -d "$1" ]; then
    if command -v eza >/dev/null 2>&1; then
        eza -l --no-user --no-time --icons --no-permissions --no-filesize "$1" 2>/dev/null || ls --color=always "$1" 2>/dev/null || ls -G "$1"
    elif command -v exa >/dev/null 2>&1; then
        exa -l --no-user --no-time --icons --no-permissions --no-filesize "$1" 2>/dev/null || ls --color=always "$1" 2>/dev/null || ls -G "$1"
    else
        ls --color=always "$1" 2>/dev/null || ls -G "$1"
    fi
elif [ "$category" = text ]; then
    if command -v bat >/dev/null 2>&1; then
        bat -p --color=always "$1" 2>/dev/null | head -1000
    elif command -v batcat >/dev/null 2>&1; then
        batcat -p --color=always "$1" 2>/dev/null | head -1000
    else
        cat "$1" 2>/dev/null | head -1000
    fi
elif [ "$category" = image ]; then
    if command -v ueberzug >/dev/null 2>&1; then
        bash "$OMZ/lib/img_preview.sh" "$1"
    elif command -v img2txt >/dev/null 2>&1; then
        img2txt "$1"
    else
        echo "$1 is an image file"
    fi
else 
    echo "$1 is a $category file"
fi
