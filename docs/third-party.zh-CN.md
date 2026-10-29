# 外置插件来源与许可证

M2 使用下面的发行标签选择版本，并在实际配置中固定完整提交。版本变更须修改清单、重新安装和验收；运行时不跟随上游分支。

| 组件 | 上游仓库 | 选择版本 | 完整提交 | 许可证副本 |
| --- | --- | --- | --- | --- |
| Antidote | `https://github.com/mattmc3/antidote` | v2.3.0 | `9bb69ab99c6f05d6e6ae237f7ce222eeeb5b4a14` | [MIT](licenses/antidote.MIT) |
| fzf-tab | `https://github.com/Aloxaf/fzf-tab` | v1.3.0 | `d7e0234614dbe5369fdd760907d12c0e05a4dccc` | [MIT](licenses/fzf-tab.MIT) |
| zsh-autosuggestions | `https://github.com/zsh-users/zsh-autosuggestions` | v0.7.1 | `e52ee8ca55bcc56a17c828767a3f98f22a68d4eb` | [MIT](licenses/zsh-autosuggestions.MIT) |
| zsh-syntax-highlighting | `https://github.com/zsh-users/zsh-syntax-highlighting` | 0.8.0 | `db085e4661f6aafd24e5acb5b2e17e4dd5dddf3e` | [BSD-3-Clause](licenses/zsh-syntax-highlighting.BSD) |
| z.lua（M3 兼容后端） | `https://github.com/skywind3000/z.lua` | 源码自报 1.8.25，2026-10-27 固定 HEAD | `86a9fc5b308b66197720811d295e3812b1c73325` | [MIT](licenses/z.lua.MIT) |

Antidote 本体来源保存在 `config/bootstrap.zsh`，三个插件使用 `config/plugins.txt` 中的 Antidote 原生 `pin:`。源码由上游 Git 获取，安装位置保留上游原有版权和许可证文件；本项目不再分发这三个插件的源码副本。fzf-tab 随上游携带的组件继续由其安装目录中的许可证约束，不另行复制或改写其实现。

删除旧内嵌目录后，额外保留原 fzf-tab 的 [MIT 声明](licenses/legacy-fzf-tab.MIT)，以及其内嵌 zsh-ls-colors 的 [MIT 声明](licenses/legacy-zsh-ls-colors.MIT)。旧版语法高亮与所选版本的 BSD 声明一致；旧自动建议源码文件头中的 MIT 作者同样包含在所保留的 MIT 声明中。旧源码仍可从 M0 Git 基线与项目外备份恢复。

M3 将 z.lua 交给同一份清单的 `kind:clone` 声明，仅在有效后端为 zlua 时选入；项目的 `config/jump.zsh` 负责初始化。该提交不是发行标签，文件自报版本不能代替固定 SHA。外置兼容适配验收后删除内嵌副本，保留 MIT 声明。

M3 本机二进制验收版本为 Homebrew zoxide 0.10.0 与 fzf 0.74.5。它们由包管理器维护，不由 Antidote 管理或 vendoring。fzf 优先加载所选安装包内的官方 `key-bindings.zsh`；没有配套脚本时使用该二进制的 `fzf --zsh`。没有复制或改写上游历史组件。参考对应版本的 `zoxide import --help`、`zoxide import z.lua --help` 及官方按键脚本。

M4 将 extract 替换为调用 ouch 的项目函数，将 randport 和 docker-tools 移至 `functions/`，删除旧插件目录和自管图片脚本。本机二进制验收版本为 Homebrew ouch 0.8.3（MIT）、bat 0.26.1（MIT 或 Apache-2.0）、eza 0.23.5（EUPL-1.2）、fzf 0.74.5（MIT）；许可证按本机 Homebrew 元数据核对。它们仍归包管理器维护，不复制其源码或预览脚本。开发验证使用 ShellCheck 0.11.0（GPL-3.0-or-later）。

解压适配以已安装 `ouch decompress --help`、`ouch --help` 和 0.8.3 上游仓库为依据：`https://github.com/ouch-org/ouch/tree/0.8.3`。RAR3/RAR5 使用该标签对应提交 `433c05d21ffd3a59a213930e256ce4b4ad863d79` 的 `tests/data/testfile.rar3.rar.gz`、`testfile.rar5.rar` 临时样本；文件随临时目录清理，来源和哈希保存在本地生成的 `verification-m4-formats.json`（已忽略，不随仓库分发）。

图片预览调用所选 fzf 包的 `bin/fzf-preview.sh` 等官方安装位置；本机读取 `/opt/homebrew/Cellar/fzf/0.74.5/bin/fzf-preview.sh`，未修改或复制该脚本。终端协议与清理行为由 fzf 和官方脚本负责，本项目只做路径、能力判断及元数据降级。

M5 没有更换上述固定提交或二进制验收版本。安装器仅调用 Homebrew/apt/pacman/apk/opkg 维护二进制，逐项处理不可用的可选包；不再更新或执行用户 `~/.fzf` 安装器、不再下载 OpenWrt fd 发行包，不新增源码编译流程。Antidote 继续只负责固定 Git 插件。系统包的实际版本取决于所选软件源，不能把本机 Homebrew 版本当作其他平台的安装保证；可用 `doctor.zsh` 和各工具 `--version` 复核。
