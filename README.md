English | [中文](./README.zh-CN.md)

## Directory Structure
```text
./
├── cache/
├── config/
│   ├── aliases.zsh
│   ├── env.zsh
│   ├── fzf.zsh
│   ├── git.zsh
│   └── hook.zsh
├── lib/
│   ├── file_preview.sh
│   ├── get_cursor.sh
│   ├── img_preview.sh
│   └── init.sh
├── plugins/
│   ├── extract/
│   ├── fzf-tab/
│   ├── randport/
│   ├── z.lua/
│   ├── zsh-autosuggestions/
│   └── zsh-syntax-highlighting/
├── scripts/
│   └── install_zsh_config.sh
├── themes/
│   └── simple.zsh-theme
└── omz.zsh
```
## Installation

### Automatic Installation
Theoretically supports most distributions; please test it yourself. **Make sure to back up before running!**

```bash
curl -fsSL https://raw.githubusercontent.com/SinclairLin/omz/main/scripts/install_zsh_config.sh | bash
```

> Note: The automatic installation script prioritizes the system package manager. Some dependency versions on Debian stable/oldstable might be outdated.
> It is recommended to manually check versions after installation and upgrade key dependencies individually if necessary.

Quick check:

```bash
fzf --version
fd --version || fdfind --version
```

### Manual Installation
#### Requires
- `Zsh`,`lua`,`fd`
in Arch Linux:

```bash
sudo pacman -S zsh lua fd
```

in Debian:

```bash
sudo apt install zsh lua5.4 fd-find 
command -v fd >/dev/null 2>&1 || sudo ln -s /usr/bin/fdfind /usr/local/bin/fd
```

in OpenWrt:

```bash
opkg install zsh
sed -i 's|:/bin/ash|:/usr/bin/zsh|g' /etc/passwd    # Change default shell
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

#### source
Clone my configuration to `~/.config`:

```bash
git clone https://github.com/SinclairLin/omz ~/.config/zsh && echo 'source ~/.config/zsh/omz.zsh' >> ~/.zshrc
```

## Plugins

- [zsh-extract](https://github.com/SinclairLin/zsh-extract)

> Defines an `extract` function; simply execute `extract <filename>` or `x <filename>` to decompress an archive file.
> This way, you don't need to know the specific command for decompressing files. The function will create a new folder and extract the files into it.
> For specific files that can be decompressed: [SinclairLin/zsh-extract](https://github.com/SinclairLin/zsh-extract/blob/master/README.md#supported-file-extensions).

- [zsh-randport](https://github.com/SinclairLin/zsh-randport)

> Defines a `randport` function that randomly selects an available port between 49152 and 65535 and prints it to the screen.

- [z.lua](https://github.com/skywind3000/z.lua)

> Using `z <dir>` will jump to the path with the highest "Frecent" (Frequency + Recency) value among all paths.

**EXAMPLES:**

```bash
z foo       # Jump to the path containing foo with the highest weight (Frecent)
z foo bar   # Jump to the path containing both foo and bar with the highest weight
z -r foo    # Jump to the path containing foo with the highest access count
z -t foo    # Jump to the path containing foo that was accessed most recently
z -l foo    # Do not jump, just list all paths matching foo
z -c foo    # Jump to the path containing foo that is a subdirectory of the current path with the highest weight
z -e foo    # Do not jump, just print the path matching foo with the highest weight
z -i foo    # Enter interactive selection mode to let you choose where to go (if there are multiple results)
z -I foo    # Enter interactive selection mode, but use fzf for selection
z -b foo    # Jump to the parent directory level starting with foo
```

- [zsh-autosuggestions](https://github.com/zsh-users/zsh-autosuggestions)

> Suggests commands as you type based on history and completions.
> Use the `<right>` key to accept the current suggestion, and `<^ right>` to accept only one word.

- [zsh-syntax-highlighting](https://github.com/zsh-users/zsh-syntax-highlighting)

> Enables syntax highlighting in `Zsh` similar to `Fish shell`.

- [fzf-tab](https://github.com/Aloxaf/fzf-tab)

> Replaces `Zsh`'s default completion selection menu with [fzf](https://github.com/junegunn/fzf).
