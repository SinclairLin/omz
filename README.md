## 目录结构
```
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
理论上可以支持大多数发行版，请自行测试，**运行前务必备份！**
```
curl -fsSL https://raw.githubusercontent.com/SinclairLin/omz/main/scripts/install_zsh_config.sh -o install_zsh_config.sh
chmod +x install_zsh_config.sh
./install_zsh_config.sh
```

> 注意：自动安装脚本会优先使用系统包管理器，Debian stable/oldstable 上部分依赖版本可能偏旧。
> 建议安装后手动检查版本，必要时再单独升级关键依赖。

快速检查：
```
zsh --version
lua -v
fzf --version
fd --version || fdfind --version
```

### 手动安装
#### Requires
- `Zsh`,`lua`,`fd`
in Arch Linux:
```
sudo pacman -S zsh lua fd
```

in Debian:
```
sudo apt install zsh lua5.4 fd-find 
command -v fd >/dev/null 2>&1 || sudo ln -s /usr/bin/fdfind /usr/local/bin/fd
```

in OpenWrt:
```
opkg install zsh
sed -i 's|:/bin/ash|:/usr/bin/zsh|g' /etc/passwd    # 更换默认shell
wget https://github.com/sharkdp/fd/releases/download/v10.3.0/fd-v10.3.0-aarch64-unknown-linux-musl.tar.gz
tar -zxvf fd-v10.3.0-aarch64-unknown-linux-musl.tar.gz
mv fd-v10.3.0-aarch64-unknown-linux-musl/fd /usr/bin
chmod +x /usr/bin/fd
fd --version
```

- fzf
```
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install
```

- 可选增强工具（版本过旧时建议自行升级）
`eza`/`bat`/`ueberzug`/`img2txt`/`lazygit`/`ranger`

#### source
clone 我的配置到`~/.config`：
```
git clone https://github.com/SinclairLin/omz ~/.config/zsh && \
echo 'source ~/.config/zsh/omz.zsh' >> ~/.zshrc
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
```
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
