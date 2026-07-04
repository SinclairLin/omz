[English](./README.md) | 中文

## 目录结构
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

### 自动安装
支持 Debian、Arch Linux、OpenWrt 等现有 Linux 安装路径，并正式支持 macOS 14 及以上的 Apple Silicon Mac。Intel Mac 会尽力兼容，但目前不在 CI 保证范围内。**运行前务必备份！**

```bash
curl -fsSL https://raw.githubusercontent.com/SinclairLin/omz/main/scripts/install_zsh_config.sh | sh
```

> 注意：自动安装脚本会优先使用系统包管理器，Debian stable/oldstable 上部分依赖版本可能偏旧。
> 建议安装后手动检查版本，必要时再单独升级关键依赖。
>
> macOS 需要预先安装并配置好 [Homebrew](https://brew.sh/)。为避免未经确认的权限和系统改动，本脚本不会自动安装 Homebrew；缺少 Homebrew 时会显示安装指引并退出。
>
> 安装器可以用 `/bin/sh` 启动，因此 OpenWrt 在尚未安装 `bash` 时也能完成 bootstrap。OpenWrt 分支仍会安装 `bash`，因为上游 `fzf` 安装器需要它。

快速检查：

```bash
zsh --version
lua -v
fzf --version
fd --version || fdfind --version
```

### 手动安装
#### Requires
- `Zsh`,`lua`,`fd`

在 macOS 14+（Apple Silicon）中，使用系统自带的 Zsh、Git、curl，并通过 Homebrew 安装其余依赖：

```bash
brew install lua fd fzf
```

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
if command -v apk >/dev/null 2>&1; then
  apk update
  apk add --no-cache bash zsh git git-http curl lua5.4
else
  opkg update
  opkg install bash zsh git git-http curl lua
fi
sed -i 's|:/bin/ash|:/usr/bin/zsh|g' /etc/passwd    # 更换默认shell
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
clone 我的配置到`~/.config`：

```bash
git clone https://github.com/SinclairLin/omz ~/.config/zsh && echo 'source ~/.config/zsh/omz.zsh' >> ~/.zshrc
```

## Plugins

- [zsh-extract](https://github.com/SinclairLin/zsh-extract)

> 定义一个`extract`函数，只需执行`extract <filename>`或`x <filename>`即可解压一个压缩文件。
> 这样就可以不必知道解压文件的具体命令，该函数会建立一个新的文件夹，然后将文件提取到新的文件夹中。
> 具体可以解压那些文件：[SinclairLin/zsh-extract](https://github.com/SinclairLin/zsh-extract/blob/master/README.md#supported-file-extensions)。

- [zsh-randport](https://github.com/SinclairLin/zsh-randport)

> 定义一个`randport`函数，使其可以在49152 - 65535之间随机挑选一个空闲端口打印到屏幕上。

- [z.lua](https://github.com/skywind3000/z.lua)

> 使用`z <dir>`会帮你跳转到所有的路径里 Frecent 值最高的那条路径去。

**EXAMPLES:**

```bash
z foo       # 跳转到包含 foo 并且权重（Frecent）最高的路径
z foo bar   # 跳转到同时包含 foo 和 bar 并且权重最高的路径
z -r foo    # 跳转到包含 foo 并且访问次数最高的路径
z -t foo    # 跳转到包含 foo 并且最近访问过的路径
z -l foo    # 不跳转，只是列出所有匹配 foo 的路径
z -c foo    # 跳转到包含 foo 并且是当前路径的子路径的权重最高的路径
z -e foo    # 不跳转，只是打印出匹配 foo 并且权重最高的路径
z -i foo    # 进入交互式选择模式，让你自己挑选去哪里（多个结果的话）
z -I foo    # 进入交互式选择模式，但是使用 fzf 来选择
z -b foo    # 跳转到父目录中名称以 foo 开头的那一级
```

- [zsh-autosuggestions](https://github.com/zsh-users/zsh-autosuggestions)

> 根据历史记录和完成情况在输入时建议命令。
> 使用快捷键`<right>`接受当前建议，`<^ right>`只接受一个word。

- [zsh-syntax-highlighting](https://github.com/zsh-users/zsh-syntax-highlighting)

> 让`Zsh`可以实现类似`Fish shell`的语法高亮。

- [fzf-tab](https://github.com/Aloxaf/fzf-tab)

> 将`Zsh`的默认补全选择菜单替换为[fzf](https://github.com/junegunn/fzf)。
