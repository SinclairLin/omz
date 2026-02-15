[中文](./README.zh-CN.md) | English

## Directory Structure
```text
./
├── cache/
├── config/
│   ├── aliases.zsh
│   ├── env.zsh
│   ├── fzf.zsh
│   ├── git.zsh
│   └── hook.zsh
├── lib/
│   ├── file_preview.sh
│   ├── get_cursor.sh
│   ├── img_preview.sh
│   └── init.sh
├── plugins/
│   ├── extract/
│   ├── fzf-tab/
│   ├── randport/
│   ├── z.lua/
│   ├── zsh-autosuggestions/
│   └── zsh-syntax-highlighting/
├── scripts/
│   └── install_zsh_config.sh
├── themes/
│   └── simple.zsh-theme
└── omz.zsh
```

## Installation

### Automatic Installation
In theory this should work on most Linux distributions. Please test in your environment and **back up first** before running.

```bash
curl -fsSL https://raw.githubusercontent.com/SinclairLin/omz/main/scripts/install_zsh_config.sh | bash
```

> Note: The installer prefers your system package manager. On Debian stable/oldstable, some dependency versions may be old.
> It is recommended to check versions after installation and upgrade key dependencies if needed.

Quick checks:

```bash
fzf --version
fd --version || fdfind --version
```

### Manual Installation
#### Requirements
- `zsh`, `lua`, `fd`

On Arch Linux:

```bash
sudo pacman -S zsh lua fd
```

On Debian:

```bash
sudo apt install zsh lua5.4 fd-find
command -v fd >/dev/null 2>&1 || sudo ln -s /usr/bin/fdfind /usr/local/bin/fd
```

On OpenWrt:

```bash
opkg install zsh
sed -i 's|:/bin/ash|:/usr/bin/zsh|g' /etc/passwd    # switch default shell
wget https://github.com/sharkdp/fd/releases/download/v10.3.0/fd-v10.3.0-aarch64-unknown-linux-musl.tar.gz
tar -zxvf fd-v10.3.0-aarch64-unknown-linux-musl.tar.gz
mv fd-v10.3.0-aarch64-unknown-linux-musl/fd /usr/bin
chmod +x /usr/bin/fd
fd --version
```

- fzf

```bash
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install
```

#### Source
Clone this config to `~/.config`:

```bash
git clone https://github.com/SinclairLin/omz ~/.config/zsh && echo 'source ~/.config/zsh/omz.zsh' >> ~/.zshrc
```

## Plugins

- [zsh-extract](https://github.com/SinclairLin/zsh-extract)

> Defines an `extract` function. Run `extract <filename>` or `x <filename>` to unpack archives.
> You do not need to remember exact extraction commands. It creates a new folder and extracts files into it.
> Supported archive types: [SinclairLin/zsh-extract](https://github.com/SinclairLin/zsh-extract/blob/master/README.md#supported-file-extensions).

- [zsh-randport](https://github.com/SinclairLin/zsh-randport)

> Defines a `randport` function that prints a random available port in the range `49152 - 65535`.

- [z.lua](https://github.com/skywind3000/z.lua)

> `z <dir>` jumps to the path with the highest frecent score among matched directories.

**EXAMPLES:**

```bash
z foo       # jump to the best matched path containing foo by frecent score
z foo bar   # jump to the best matched path containing both foo and bar
z -r foo    # jump to the most frequently visited path containing foo
z -t foo    # jump to the most recently visited path containing foo
z -l foo    # list matched paths only, do not jump
z -c foo    # jump to the best matched subdirectory under current path
z -e foo    # print the best matched path only, do not jump
z -i foo    # interactive selection mode when there are multiple matches
z -I foo    # interactive selection mode using fzf
z -b foo    # jump to parent directory level whose name starts with foo
```

- [zsh-autosuggestions](https://github.com/zsh-users/zsh-autosuggestions)

> Suggests commands from history and completions while typing.
> Use `<right>` to accept the full suggestion, `<^ right>` to accept one word.

- [zsh-syntax-highlighting](https://github.com/zsh-users/zsh-syntax-highlighting)

> Adds Fish-like syntax highlighting to Zsh.

- [fzf-tab](https://github.com/Aloxaf/fzf-tab)

> Replaces Zsh's default completion menu with [fzf](https://github.com/junegunn/fzf).
