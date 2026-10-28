[English](./README.md) | 中文

个人 Zsh 配置，保留 simple 提示符与原生降级能力，通用插件由固定提交的外部依赖提供。增强配置以 Zsh 5.8+ 为测试目标。

## 安装

```sh
curl -fsSL https://raw.githubusercontent.com/SinclairLin/omz/main/scripts/install_zsh_config.sh | sh
```

安装器可由 `/bin/sh` 启动：安装基础包，将源码克隆或快进更新到 `~/.config/zsh`，读取个人选项，准备配置档工具，执行插件管理器的 `install` 和 `verify`。这些步骤成功后，才向 `${ZDOTDIR:-$HOME}/.zshrc` 追加 source 行；保留原内容，追加前备份。安装器不更改登录 Shell，也不导入用户数据。

macOS 先准备 [Homebrew](https://brew.sh/) 与 Apple 命令行工具；安装器不会引导安装两者。Arch 路径采用 `pacman -Syu`，会执行系统升级；若要自行维护软件包，请先完成系统升级，再用 `OMZ_INSTALL_DEPS=0` 安装配置。

| 配置档 | 自动选择 | 基础工具之外请求安装的软件包 |
| --- | --- | --- |
| `desktop` | macOS | fd、fzf、zoxide、ouch、bat、eza |
| `server` | 其他 Linux | fd/fd-find、fzf、zoxide；其他工具按需安装 |
| `minimal` | OpenWrt | 无；原生补全、历史及 simple 提示符 |

只有显式选择 z.lua，或 `OMZ_JUMP=auto` 遇到尚未决定如何迁移的旧数据库时，才请求 Lua。可选包不可用时逐项警告并保留运行时降级；fzf 0.51.0+ 启用增强历史与补全，旧版保留原生行为。不自动编译 Rust、下载上游二进制、建立全局 fd 软链接，也不更新 `~/.fzf`。已有二进制仍可通过 PATH 使用。Python 3 仅用于显式迁移与开发检查，日常启动不需要。

需要永久选择配置档或后端时，安装前在 `${XDG_CONFIG_HOME:-$HOME/.config}/omz/local.zsh` 中设置，例如添加 `OMZ_PROFILE=minimal` 或 `OMZ_JUMP=zlua`；保留文件已有内容。它优先于旧 `config/env-self.zsh`。环境变量形式的 `OMZ_PROFILE=minimal` 只影响本次执行，安装器不会将其保存为永久配置。

### 手动准备软件包

```sh
# macOS desktop
brew install fd fzf zoxide ouch bat eza

# Debian / Ubuntu server，不需要创建 fd 软链接
sudo apt-get update
sudo apt-get install -y zsh git curl ca-certificates fd-find fzf zoxide

# Arch server，包含完整系统升级
sudo pacman -Syu --needed zsh git curl ca-certificates fd fzf zoxide

# OpenWrt minimal；/bin/sh 引导不依赖 Bash 或 Lua
if command -v apk >/dev/null 2>&1; then
  apk update
  apk add --no-cache zsh git git-http curl ca-bundle
else
  opkg update
  opkg install zsh git git-http curl ca-bundle
fi
```

随后使用同一安装器跳过包管理器；所需命令须已可用：

```sh
curl -fsSL https://raw.githubusercontent.com/SinclairLin/omz/main/scripts/install_zsh_config.sh |
  OMZ_INSTALL_DEPS=0 sh
```

`TARGET_DIR`、`ZSHRC_FILE` 支持自定义绝对路径，保留 `REPO_URL`、`SOURCE_LINE`。启动文件默认遵守 `ZDOTDIR`；XDG 变量独立控制个人配置、状态、依赖与缓存，不改变源码安装目录。完整选项见 `sh scripts/install_zsh_config.sh --help`。

### 升级、迁移与回滚

已有安装工作区干净时，重新运行安装器即可。源码或依赖有本地改动、目标为非空非 Git 目录、origin 与 `REPO_URL` 不同时会停止，不自动暂存或覆盖修改。仅在缺少完全相同的 source 行时追加；已有启动文件会备份为同目录的 `.omz-backup.*`。改变安装位置时，需核对已有的等价或自定义 source 行。

源码与软件包更新不是整体事务：插件准备失败时，源码可能已经快进，启动文件保持原样；旧加载缓存缺失或过期时，运行时降级为基础 Shell。修复依赖后重跑安装。升级前保存源码和状态备份；回滚时先恢复到独立目录比较，再决定切换，不用旧备份覆盖新历史。

```sh
# 在实际安装的源码目录执行；以下命令仅预览或诊断。
zsh -df scripts/migrate-state.zsh
zsh -df scripts/migrate-jump.zsh
zsh -df scripts/doctor.zsh

# 安装时附带状态迁移预览，需要 Python 3。
sh scripts/install_zsh_config.sh --migrate-state-preview
```

预览遇到冲突会非零退出，阻止追加 source 行。真实历史、查询记录、个人配置与跳转记录需等旧会话停止写入后另行决定迁移。操作与恢复步骤见 [迁移及回滚说明](docs/migration.zh-CN.md)。

### 插件归属与断网启动

Antidote 只管理固定提交的 Git 依赖：fzf-tab、自动建议、语法高亮，以及实际选中的 z.lua 兼容后端；二进制归系统包管理器。自动安装器已包含插件准备；后续手动维护使用：

```sh
zsh -df scripts/manage-plugins.zsh install
zsh -df scripts/manage-plugins.zsh verify
# 修改配置档、路径或禁用项后，利用已安装的固定版本重建：
zsh -df scripts/manage-plugins.zsh build
```

源码位于 `${XDG_DATA_HOME:-$HOME/.local/share}/omz/`，静态加载文件位于 `${XDG_CACHE_HOME:-$HOME/.cache}/omz/plugins.zsh`。搬迁配置源码后，必须在最终位置重新生成加载文件。日常启动不联网、不运行插件管理器；切换固定提交须用 `install`，minimal 不下载 Antidote。版本及许可证见 [第三方来源](docs/third-party.zh-CN.md)。

## 跳转与历史

增强配置优先使用 zoxide：`z` 跳转，`zi`、`zz`、`zf` 交互选择。已有非空 z.lua 数据库时保留兼容后端，直到明确导入或跳过；`OMZ_JUMP=zlua` 保留旧别名与语义。真实终端上的 Ctrl-R 使用 fzf 官方历史集成，Tab 由 fzf-tab 负责；缺工具、旧 fzf 或 minimal 使用原生历史与补全。用户 fzf 参数会保留。

## 验证范围

本机 macOS arm64 已验证三种配置档的隔离安装、重复执行、快进升级，以及插件固定提交、断网启动、迁移失败保护与真实 PTY 交互。CI 配置面向 Ubuntu、macOS 14 和 macOS latest；本轮没有新的远程 CI 结果。Debian/Arch 与 OpenWrt apk/opkg 包管理命令只在本机模拟，不能据此视作这些系统上的完整安装验收。Intel Mac 与 Kitty/iTerm2 的真实图片位置仍未验证。详细结果及人工待验项见 [验证报告](docs/verification.md)。仓库开发尚未切换日常安装或迁移真实用户数据。

## 目录结构

```text
config/       配置档、补全、历史、跳转、别名、插件固定提交
functions/    extract、randport、Docker 自有函数
lib/          路径、能力判断、插件、Git 提示符、预览适配
scripts/      安装器、插件管理、迁移、诊断、验证采集
tests/        隔离安装、运行时与 PTY 测试
docs/         迁移、结果与许可证
themes/       simple 提示符
omz.zsh       配置入口
```

## Plugins

- `extract` / `x`：项目自有的 ouch 薄封装。先安装 `ouch`（macOS：`brew install ouch`）；缺少时不注册这两个入口，可执行 `zsh -df scripts/doctor.zsh` 查看诊断。

```zsh
extract "a.tar.gz" "中文 文件.zip"
x -r -- "-archive.zip"
```

每个输入输出到同目录下的 `<完整文件名>.extracted/`；目标已存在则失败，不混入已有文件。仅在对应文件成功且指定 `-r` / `--remove` 后删除原包；任一输入失败则整体非零，工作目录保持不变。失败时保留非空的部分输出供检查。格式支持取决于实际 ouch 构建；本机 0.8.3 已测 ZIP、tar.gz、gzip、bzip2、xz、7z、RAR3 和 RAR5，不承诺所有平台一致。`.deb` / `.rpm` 的特殊展开改用平台原生工具，见 [M4 迁移说明](docs/migration.zh-CN.md#m4-解压预览与自有函数)。

- 文件预览：文本按 bat → batcat → head 降级，最多读取 1,000 行；目录按 eza → ls 降级，最多显示 200 行。图片交给已安装 fzf 的官方 `fzf-preview.sh`，仅在匹配的终端能力下调用；普通终端、SSH、tmux、关闭图片或缺少依赖时显示文件类型与尺寸。支持用导出的 `OMZ_FZF_PREVIEW_SCRIPT` 指定包内官方脚本路径。实际终端图像位置和 tmux 透传仍需人工验收。

- `randport` / `rp`：从 49152–65535 中选择当时探测为空闲的端口，不预留端口；缺少 ss、lsof、netstat 时失败。

- `dcupdate`：执行 `docker compose pull && docker compose up -d`；拉取失败则停止，不再先执行 down，服务重建仍可能中断。

- [z.lua](https://github.com/skywind3000/z.lua)

> 使用`z <dir>`会帮你跳转到所有的路径里 Frecent 值最高的那条路径去。
> 以下示例对应 `OMZ_JUMP=zlua` 兼容后端；zoxide 的选项和排序不同。

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
