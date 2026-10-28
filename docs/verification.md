# 迁移验证记录

## M0：基线采集完成

- 日期：2026-10-27，Asia/Shanghai。
- 代码基线：`358bbd69e2ba81563401678f86df045b966d8e44`，分支 `main`。
- 环境：macOS 27.0.1，Apple Silicon / arm64。
- 原始记录：[baseline-m0.json](baseline-m0.json)。
- 采集入口：`scripts/collect-baseline.py`，Python 3 标准库，无新增依赖。
- 范围：记录现状、测量性能、验证备份；尚未修改 Shell 初始化、安装器或现有后端。

本段保存 M0 当时的基线，并非所有检查通过。19 项检查中 18 项通过，1 项发现已有图片脚本的语法错误，详见后文。M1-M5 的后续实现与验证分别记录在文末；旧图片脚本已删除，M5 已完成本机安装与文档收尾，跨平台与实际用户切换仍待验收。

## M0 命令入口与行为快照

| 入口 | 当前职责或行为 |
| --- | --- |
| `scripts/install_zsh_config.sh` | 可由 `/bin/sh` 启动；安装依赖、处理 fzf、获取配置、追加 source 行 |
| `omz.zsh` | 加载 init、别名、环境、个人配置、fzf、Git、钩子、七个内嵌插件及主题 |
| `lib/init.sh` | 实际为 Zsh 文件；负责 compinit、历史、快捷键、目录栈和 Git 提示符函数 |
| `config/env-self.zsh` | 仓库内旧个人配置；当前在 compinit 和别名之后读取 |
| `config/fzf.zsh` | 覆盖 `FZF_DEFAULT_OPTS`，手写历史搜索，配置 fzf-tab 样式及预览 |
| `plugins/z.lua/z.lua.plugin.zsh` | 通过 Lua 初始化跳转，注册 `z`、`zz`、`zf` 等入口 |
| `plugins/extract/extract.plugin.zsh` | 现有解压实现，含 `extract`、`x` |
| `plugins/randport/randport.plugin.zsh` | 探测空闲端口，别名 `rp` |
| `plugins/docker-tools/docker-tools.zsh` | `dcupdate`：pull、down、up；M4 前仍有停止容器步骤 |
| `themes/simple.zsh-theme` | 当前 simple 提示符及 Git 状态展示 |
| `lib/file_preview.sh` | 目录、文本、图片预览；图片可能调用旧 ueberzug 脚本 |
| `tests/test_installer.sh`、`tests/test_runtime.zsh` | 现有安装器模拟测试及局部运行时测试 |

隔离环境实测：

- 非交互加载返回 0、无启动输出，且保持 cwd；但仍初始化 compinit、ZLE 历史 widget、跳转及全部交互插件，不符合 M1 的交互保护目标。
- 交互加载后，Tab 为 `fzf-tab-complete`，Ctrl-R 为 `historybyfzf`；跳转、解压、小工具、建议和高亮函数均存在。
- 同一 Shell 重复 source 后，precmd/chpwd/preexec 钩子数量保持 `3/1/1`，Tab、Ctrl-R 绑定及 widget 总数保持一致。这仅证明上述可观察项稳定，不证明插件未重新执行或包装过程完全幂等。
- 本次未以伪终端实际按键，未验收 Tab 选择、Ctrl-R 取消、多行历史、建议接受、颜色和图片位置；函数存在及绑定检查不能代替这些验收。

## 依赖版本

| 工具 | 本机实际版本 | 解析路径 |
| --- | --- | --- |
| Zsh | 5.9，arm64-apple-darwin26.0 | `/bin/zsh` |
| Bash | 3.2.57(1)-release | `/bin/bash` |
| Git | 2.54.0，Apple Git-157 | `/usr/bin/git` |
| fzf | 0.74.5，Homebrew | `/opt/homebrew/bin/fzf` |
| fd | 10.5.0 | `/opt/homebrew/bin/fd` |
| Lua | 5.5.1 | `/opt/homebrew/bin/lua` |
| Python | 3.9.6 | `/usr/bin/python3` |

本机未找到 zoxide、ouch、bat/batcat、eza、ShellCheck。本次未安装或升级依赖。

内嵌版本标识：z.lua 自报 `1.8.25`，zsh-autosuggestions 文件头标注 `v0.6.4`，zsh-syntax-highlighting `.version` 为 `0.8.0-alpha2-dev`。fzf-tab 不以模块版本代替整个插件版本；四个主要入口文件的 SHA-256 保存在原始记录中。内嵌源码的版本标识不等于已核对上游提交；Antidote 与插件完整 pin 留待 M2 选择和验收。

## 自动化检查与已知问题

原有 `bash tests/test_installer.sh` 和 `zsh -df tests/test_runtime.zsh` 均通过。安装器测试中的 Homebrew/OpenWrt 是模拟，不表示本次在 OpenWrt 上安装或运行成功。安装器通过 `/bin/sh -n`；项目 Zsh 文件按 Zsh 解析，sh/bash 文件逐个解析。

新增的逐文件检查发现：

```text
bash -n lib/img_preview.sh
lib/img_preview.sh: line 33: syntax error near unexpected token `('
```

本机 Bash 3.2 无法解析该脚本的 `declare -A -p cmd=(...)` 行。当前预览入口在 macOS 不走 ueberzug 分支，因此普通启动通过并不能证明此脚本可用。只核实了本机解析失败，未验证其他 Bash 版本。该问题记录到 M4 的旧图片路径替换清单，本阶段保留原实现。

现有 CI 把多个文件名一起传给 `bash -n` 或 `zsh -n`，只有第一个文件被作为脚本解析，其余是脚本参数，因此原有语法检查覆盖不完整。采集脚本已逐个文件检查；CI 修正仍待后续实施，不把原有 CI 结果视为全文件语法通过。

## 性能基线

测试使用临时仓库副本、独立 HOME、ZDOTDIR 和 XDG 目录，排除个人 `env-self.zsh` 及旧 cache 内容。PATH 继承采集时的命令搜索路径，记录于 JSON；TERM 固定为 `xterm-256color`，LANG/LC_ALL 为 `en_US.UTF-8`。不读取真实用户启动文件，不写入真实历史。

启动测量命令为 `zsh -dfi -c 'source "$OMZ_BASELINE_ROOT/omz.zsh"; exit 0'`。计时包含进程创建、初始化和退出，不包含首个可见提示符或真实 ZLE 交互；没有 PTY，也没有清空操作系统文件缓存。

| 场景 | 样本数 | 中位数 | P95 |
| --- | --- | --- | --- |
| 无 compdump 的首次启动 | 1 | 173.033 ms | 不适用 |
| 有 compdump 的稳定启动 | 20 | 52.833 ms | 54.182 ms |
| 普通非 Git 目录 `git_prompt_info` | 20 | 15.386 ms | 16.043 ms |
| 合成 Git 仓库：10,000 个已跟踪文件，干净 | 20 | 27.412 ms | 27.919 ms |
| 同一 Git 仓库：修改一个已跟踪文件 | 20 | 31.186 ms | 34.233 ms |

P95 使用 nearest-rank：20 个样本中升序第 19 项。提示符先预热一次，再在同一 Zsh 内逐次测量 `git_prompt_info`；未测完整终端绘制、标题钩子或 z.lua 的目录记录耗时。合成仓库共 100 个目录，每目录 100 个小文本文件，不代表所有大型真实项目。

按方案预算，此机器及相同测量条件下，后续增强配置的稳定启动中位数暂以 `52.833 + max(5.2833, 20) = 72.833 ms` 为回归上限。当前没有 minimal 配置，未声称测得 minimal 性能。后续应复用测量方法，并补充真实终端及大型实际仓库验收。

## 备份与恢复校验

已保存到项目之外：

```text
/Users/linzx6/.local/state/omz/backups/m0-20261027-omz-358bbd6-verified/
  files.tar.gz
  repository.bundle
  manifest.json
```

- 共 527 个文件快照，包括本项目工作区（排除 `.git`）、当时已有的方案与采集文件、真实 `.zshrc`、`.zsh_history`、`.zlua` 和已安装配置的旧 cache。备份不含本报告完成后的文档修订。
- `manifest.json` 保存每个源路径、归档成员名和 SHA-256，以及归档、Git bundle 的 SHA-256。未把用户历史内容写入项目文档。
- 将全部归档文件还原到临时目录后，逐文件 SHA-256 一致；Git bundle 通过 verify，并实际 clone 到临时仓库，恢复 HEAD 与基线一致。
- 备份目录权限为 0700，备份文件为 0600；恢复演练目录及测量生成物已清理。
- 文件符号链接按内容快照，不保留链接语义；不遍历嵌套目录符号链接。有此类外置配置时须通过 `--state-file` 额外列出，不宣称备份任意自定义布局。
- 这是文件快照，未结束其他 Shell 会话；之后写入的历史不在快照内，也未声称用户数据已迁移完成。

当前实际安装仍位于 `/Users/linzx6/.config/zsh`，其 HEAD 同为 `358bbd6`，`omz.zsh` 内容哈希与项目一致；本次没有切换 `.zshrc` 的 source 目标。该快照足以核对基线并演练恢复，不直接覆盖正在使用的配置。

## 复测方法

在仓库根目录运行：

```sh
python3 scripts/collect-baseline.py --output /tmp/omz-baseline.json
```

需要新的可恢复快照时，再增加一个尚不存在的项目外目录：

```sh
python3 scripts/collect-baseline.py \
  --output /tmp/omz-baseline.json \
  --backup "$HOME/.local/state/omz/backups/m0-new-snapshot"
```

自定义跳转数据库或其他旧状态使用 `--state-file "/实际路径"`；导出的 `_ZL_DATA` 自动纳入备份。采集器不执行个人配置来猜测未导出的变量，迁移前仍须核对实际路径。

原始检查有失败时，采集器仍写出报告和已校验的备份，再以非零状态退出，便于保留失败证据；当前基线会因旧图片脚本解析错误而返回 1。未提供 `--backup` 时只采集，不创建真实配置备份。重复备份必须使用新目录，避免覆盖前次快照。

## M1：初始化、交互保护与 XDG 数据路径

- 日期：2026-10-27，Asia/Shanghai；本机 macOS 27.0.1 / arm64、Zsh 5.9。
- 工作位置：`main` 工作区，HEAD 仍为 M0 基线 `358bbd6`；本阶段改动尚未提交。
- 原始记录：[desktop](verification-m1-desktop.json)、[minimal](verification-m1-minimal.json)。两次采集依次进行，每档独立使用临时源码、HOME、ZDOTDIR 与四个 XDG 根目录。
- 真实数据只执行了默认迁移预览：正确定位 `~/.config/zsh/cache/zshhistory`、`fzfhistory` 和 `~/.zlua`，上次目录源文件缺失；没有执行真实 `--apply`，没有修改 `.zshrc` 或日常安装目录。

实现：

- `omz.zsh` 先设置 XDG 路径、默认值和环境，再读取新个人文件或兼容旧文件；非交互直接返回，不初始化历史、提示符、补全、跳转或插件。
- 历史、基础快捷键和 compinit 分离为 `config/history.zsh`、`keybindings.zsh`、`completion.zsh`；compinit 使用 XDG 缓存，并复用外部已初始化的 compsys。
- 新增 desktop/server/minimal 配置档及禁用插件数组。minimal 跳过增强插件和跳转，server 关闭图片；既有后端与 simple 主题保留。新旧开关映射及当前阶段限制见迁移文档。
- 交互初始化成功后重复 source 直接返回，个人文件只执行一次，钩子、widgets、Tab/Ctrl-R 和 fzf 参数不重复设置。
- 命令历史、查询历史和目录记录写入 XDG 状态目录；源码目录不再保存运行状态。敏感目录权限 0700，历史及迁移文件 0600。旧光标脚本仅调整为 XDG 缓存的纯文本读写，图片替换继续留待 M4。
- `scripts/migrate-state.zsh` 调用 Python 3 标准库实现显式迁移。默认只预览；历史复制要求声明旧会话结束。提供备份哈希校验、非空目标冲突保护、个人配置选择复制、自定义跳转库备份、逐项完成记录、中断重试及进程锁；不执行旧个人配置。
- CI 改为逐个文件做语法解析，按 Zsh 解析 `lib/init.sh` 和新增 Zsh 文件；旧图片脚本已知解析问题显式保留在 M4 清单，完整采集仍报告该失败。

### M1 自动化结果

`zsh -df tests/test_runtime.zsh` 通过，包含原有局部断言、新增 13 个初始化测试和 12 个迁移测试；`bash tests/test_installer.sh` 通过。安装器的 `/bin/sh -n` 通过。

关键覆盖：

| 检查 | 实际结果 |
| --- | --- |
| 非交互加载 | stdout/stderr 均为空，不改变 cwd，不创建 XDG 目录，不加载交互函数或设置 HISTFILE |
| 新旧个人配置与选项优先级 | 新文件优先，缺失时读取旧文件；初始化前可覆盖选项，显式新开关优先，重复 source 不重复执行 |
| 三种配置档 | desktop/server/minimal 行为通过；Darwin/Linux/OpenWrt 的 auto 分派用 OSTYPE 模拟，仅验证分派逻辑 |
| 重复 source 与外部补全 | 钩子、widgets、按键、fzf 参数均保持一致；已有 compinit 不重新执行、不生成项目 compdump |
| 状态路径与权限 | 含空格的源码、HOME/XDG 路径可用；中文及空格目录可恢复；目录状态中的命令文本不执行；空/相对 XDG 回退默认位置 |
| 可选依赖缺失 | 隔离 PATH 不提供 Lua/fzf 时安静启动，回退原生历史/补全；禁用三个插件时不加载 |
| fzf 参数 | 用户参数保留在项目默认值之后；真实 fzf `--filter` 验证含空格的查询历史参数可解析 |
| 迁移预览和冲突 | 默认预览零写入；未声明旧会话结束时拒绝复制历史；非空目标或符号链接目标均不覆盖 |
| 备份和重跑 | 快照 SHA-256、私有权限及自定义 `_ZL_DATA` 备份通过；旧文件保留，目标新增历史不被重跑覆盖 |
| 失败恢复 | 旧源迁移后继续增长会报冲突；复制中断可校验后重试；目标新增内容阻止恢复覆盖；损坏记录清晰失败；锁释放后可重试 |

两份完整采集各有 26 个检查，其中 25 项通过，唯一失败仍为 M0 已发现的 `bash -n lib/img_preview.sh`，当前行号为 36。因此采集命令按设计返回 1，不能把本阶段写成“全仓库语法检查通过”。

### M1 性能

沿用 M0 的 Shell 进程计时条件：每档 1 次无 compdump 启动、20 次稳定启动；不使用 PTY，不清空操作系统缓存。测量包含进程创建、初始化和退出，不代表首屏绘制或真实按键延迟。

| 配置 | 首次启动 | 稳定中位数 | 稳定 P95 |
| --- | --- | --- | --- |
| M0 原配置基线 | 173.033 ms | 52.833 ms | 54.182 ms |
| M1 desktop | 169.483 ms | 60.117 ms | 61.397 ms |
| M1 minimal | 140.045 ms | 31.285 ms | 31.695 ms |

desktop 稳定中位数比 M0 增加 7.284 ms，低于本机 20 ms 的回归预算，上限为 72.833 ms。minimal 未承担增强插件的初始化成本；这里比较的是本机的配置差异，不代表 OpenWrt 设备性能。

desktop 的 `git_prompt_info` 中位数/P95：普通目录 15.958/16.449 ms、10,000 文件干净仓库 28.528/29.633 ms、修改一个文件的仓库 28.047/28.777 ms。minimal 对应为 15.362/15.831、27.446/30.278、27.485/30.166 ms。提示符函数本阶段没有替换，波动不作优化收益解释。

复测：

```sh
python3 scripts/collect-baseline.py --profile desktop --output /tmp/omz-m1-desktop.json
python3 scripts/collect-baseline.py --profile minimal --output /tmp/omz-m1-minimal.json
```

本阶段完成定义限于 M1 仓库实现和本机自动化。Linux/macOS CI 配置已更新，但本次没有远程运行结果；没有 Linux/OpenWrt 真机验收，也未用真实终端或 PTY 验收 Tab 选择、Ctrl-R 取消、多行历史、自动建议接受、高亮和图片。这些交互体验与后端替换仍在 M2-M5 的验收范围，旧图片问题继续登记在 M4。

## M2：插件外移与固定提交

- 日期：2026-10-27，Asia/Shanghai；本机 macOS 27.0.1 / arm64，Zsh 5.9、fzf 0.74.5。
- 工作位置：`main`；HEAD 仍为 `358bbd6`，保留 M1 未提交工作，没有创建分支或提交。
- 原始记录：[desktop](verification-m2-desktop.json)、[minimal](verification-m2-minimal.json)、[同环境交错对照](verification-m2-comparison.json)。
- Antidote v2.3.0、fzf-tab v1.3.0、zsh-autosuggestions v0.7.1、zsh-syntax-highlighting 0.8.0；完整提交及许可证见 [第三方来源](third-party.zh-CN.md)，实际固定值位于 `config/bootstrap.zsh` 和 `config/plugins.txt`。

### M2 实现与实际安装

`scripts/manage-plugins.zsh` 提供 `install`、`build`、`verify`。仅引导 Antidote 本体需要项目执行 Git 获取固定提交；插件克隆、pin 检出和静态脚本生成由 Antidote 完成。没有实现另一套插件下载器或版本锁格式。

`install` 拒绝覆盖依赖中的本地修改，用进程锁保护共用数据目录；引导和加载文件先写临时位置，全部核对后发布。失败和中断会清理本次临时文件，保留已有静态文件。`build` 先验证本地提交和工作区，禁止 Git 网络协议，只重建缓存。`verify` 核对当前启用的依赖提交、工作区及缓存标识和语法，不更新版本。

运行时在项目按键、补全、主题和钩子之后读取静态文件，不加载 Antidote。标识包含源码、数据和缓存路径、配置档、清单、引导声明及有效插件。标识不符时提示一次并保留基础 Shell，不自动安装或重建；加载前检查所有入口，缺失依赖时不部分启用插件。顺序保持 fzf-tab、自动建议、语法高亮。

本次实际执行 `install` 和 `verify`，默认安装到：

```text
/Users/linzx6/.local/share/omz/antidote/
/Users/linzx6/.local/share/omz/plugins/github.com/
/Users/linzx6/.cache/omz/plugins.zsh
```

三个内嵌源码目录已在外置加载通过验收后删除，保留来源、许可证及 M0 可恢复备份。z.lua 和原历史搜索继续保留；外置 z.lua 的 `kind:clone` 声明及兼容适配在 M3 处理。

日常 `.zshrc` 和旧 `~/.config/zsh` 安装副本没有切换；真实历史、查询记录、个人配置及跳转库没有迁移。管理命令只准备依赖和缓存目录；交互测试与测量使用临时 HOME、ZDOTDIR 和 XDG，测试生成物会清理。

### M2 自动化和终端结果

`zsh -df tests/test_runtime.zsh` 通过：14 个插件测试、13 个初始化测试、12 个迁移测试，共 39 个 Python 测试，以及原有局部断言。`bash tests/test_installer.sh` 通过。

| 检查 | 实际结果 |
| --- | --- |
| 固定提交与重复安装 | 实际 Antidote 安装，全部启用的 HEAD 等于完整 pin；重复 install 的静态文件逐字节一致 |
| 无网络安装演练 | 把四个上游 URL 重定向到本地真实 Git 仓库，仅允许 file 协议，完整安装和重复执行通过 |
| 断网构建与启动 | build/verify 禁止 Git 网络协议，额外拦截 clone/fetch/pull/ls-remote、curl、wget；没有触发拦截。删除 Antidote 本体后静态启动仍通过 |
| 缓存与路径变化 | 清单、引导声明、配置档、禁用项或源码/数据/缓存位置变化，旧缓存被拒绝；显式 build 后恢复 |
| 缺少依赖 | 缺缓存或最后一个插件时只提示一次，保留 compsys，不部分加载前面的插件；minimal 和全部禁用时不需要 Antidote |
| 失败保护 | 错误 pin、提交不符、本地修改、引导下载失败、Antidote bundle 失败和并发操作均正确失败，旧缓存保留，临时文件清理 |
| 个人配置 | 管理入口和启动使用同一配置；可选探测命令返回非零不提前中止读取后续配置 |
| 真实 PTY | 临时 Shell 中输入命令前缀、右方向键接受历史建议并执行；无效命令触发红色高亮；Tab 打开真实 fzf 候选列表，筛选 beta、接受并实际执行所选路径 |
| M1 回归 | 非交互保护、重复 source、三种配置档、缺少 Lua/fzf、含空格路径、历史迁移和状态权限测试继续通过 |

两份完整采集各有 29 项检查，28 项通过；唯一失败仍是已登记到 M4 的 `bash -n lib/img_preview.sh`。因此完整采集按设计返回 1，不能称“全仓库检查全部通过”。CI 已覆盖新脚本语法和插件测试，本次没有远程 Linux/macOS CI 结果。

### M2 性能与对照

复用 M0/M1 的进程墙钟计时方法，每档一次无 compdump 启动和至少 20 次稳定启动；没有 PTY、没有清空 OS 文件缓存。两档依次采集，不并行测量。

| 配置 | 首次启动 | 稳定中位数 | 稳定 P95 |
| --- | --- | --- | --- |
| M2 desktop | 223.592 ms | 85.159 ms | 119.255 ms |
| M2 minimal | 178.221 ms | 41.843 ms | 44.831 ms |

原 M0 的历史绝对参考线为 72.833 ms，本次 desktop 高出 12.326 ms，**该历史绝对阈值未达到**。P95 包含本轮较慢样本，未剔除。M1 的旧记录不能直接视为当时同等负载下的对照。

为区分外移增量与不同时段的共同变化，另做一次同环境交错对照：M0 从 `358bbd6` 归档恢复；M1 用现有 M1 初始化恢复旧加载段和 Git 基线中的三个内嵌插件；M2 使用外置实现。每个配置单独隔离 HOME/XDG，同一 PATH、TERM、locale，固定随机种子交错测量，每档 20 次稳定启动。

| 对照配置 | 中位数 | P95 |
| --- | --- | --- |
| M0 desktop | 71.767 ms | 76.074 ms |
| M1 desktop | 81.151 ms | 87.755 ms |
| M2 desktop | 82.595 ms | 85.295 ms |
| M1 minimal | 41.880 ms | 45.381 ms |
| M2 minimal | 41.854 ms | 43.989 ms |

该轮 M2 相比 M1 增加 1.444 ms，相比 M0 增加 10.828 ms，低于同环境 20 ms 增量预算；minimal 未增加外置插件初始化成本。该结果没有撤销 72.833 ms 历史阈值未达到的记录，也不证明升级插件会加速启动。

最后完整采集中的 `git_prompt_info` 中位数/P95：desktop 普通目录 27.356/35.930 ms、10,000 文件干净仓库 38.670/40.887 ms、修改一个文件 39.044/52.320 ms；minimal 对应为 26.270/34.847、35.473/41.390、37.678/41.096 ms。M2 没有修改 Git 提示符实现，不作提示符优化收益解释。

复测：

```sh
python3 scripts/collect-baseline.py --profile desktop \
  --plugin-data "$HOME/.local/share/omz" \
  --output /tmp/omz-m2-desktop.json
python3 scripts/collect-baseline.py --profile minimal \
  --plugin-data "$HOME/.local/share/omz" \
  --output /tmp/omz-m2-minimal.json
```

`--plugin-data` 只把依赖复制进临时目录并离线构建，不修改原依赖；不传时在隔离目录显式安装。非默认 XDG 数据目录应传实际的 `omz/` 路径。

M2 完成边界为外置实现、本机依赖安装、功能及隔离 PTY 验证。Kitty/SSH/tmux 的人工体验、Ctrl-R 取消与多行历史、图片、Linux/OpenWrt 真机和完整升级切换仍待后续阶段；历史绝对性能参考线也仍有上述未达项。

## M3：交互替换的本机实现与功能验收

- 日期：2026-10-27，Asia/Shanghai；继续在 `main` 工作，保留原有 M1/M2 改动，没有创建分支或 Git 提交。
- 本机版本：Zsh 5.9、Homebrew fzf 0.74.5、zoxide 0.10.0、Lua 5.5.1。
- 原始记录：[功能检查](verification-m3.json)、[启动测量](verification-m3-performance.json)。
- 用户本轮调整性能要求：“忽略性能，只要不是太离谱就没事”。下方原始数据及旧预算对照继续保留，细微差异不阻塞 M3，未宣称每一档均满足此前的 20 ms 预算。

### M3 实现

`config/jump.zsh` 初始化单一跳转后端。新配置的 auto 优先 zoxide，保留 `z`，以 `zi`、`zz`、`zf` 交互选择；不模拟 z.lua 的特殊选项。缺少交互所需的 fzf 0.51.0+ 时，`z` 仍工作，`zi` 明确提示所缺能力。显式选择不可用后端时给出原因，不偷偷切换。

非空旧 `_ZL_DATA`、默认 `~/.zlua` 在没有迁移决定时阻止自动切换；auto 继续选择 z.lua，显式 zoxide 则提示迁移。兼容后端使用 Antidote `kind:clone` 与完整 SHA，由项目适配层初始化，保留 `_ZL_*`、自定义命令名和旧别名。插件管理入口支持该类依赖的安装、构建和核对。

新增 `scripts/migrate-jump.zsh` 与标准库 Python worker。默认预览；apply 需要声明旧会话已停止，先备份两边数据库并校验，通过官方 `zoxide import z.lua --merge` 在临时数据库副本中导入，验证及源/目标变更检查后替换。可明确 `--skip-import`，保留旧库。成功重跑保留新增记录；失败不写切换决定，中断提交可按校验记录恢复。

`config/fzf-history.zsh` 优先加载所选安装包的官方按键脚本；没有配套脚本时使用同一二进制的 `fzf --zsh`，恢复其临时改动的 Tab 入口。项目只启用官方历史绑定，先初始化 compsys，再加载历史/跳转，最后加载 fzf-tab、自动建议、高亮。手写 `historybyfzf` 管道和无人消费的 `FZF_PREVIEW_COMMAND` 已删除。用户通用及历史专有 fzf 参数保留，查询记录仅通过 `FZF_CTRL_R_OPTS` 配置。

旧版 fzf、工具缺失、minimal 采用原生搜索/补全；旧版官方独立脚本未验收，因此不启用。无 TTY 的 `zsh -i -c` 检查也使用原生历史，避免官方脚本恢复 ZLE 选项时的报错；这类检查不代表实际 Ctrl-R，后者通过真实 PTY 验收。

内嵌 z.lua 在外置兼容跳转通过验收后删除，MIT 声明保留于 `docs/licenses/z.lua.MIT`。删除前额外创建并逐文件 SHA-256 核对了源码备份：

```text
/Users/linzx6/.local/state/omz/backups/m3-vendored-zlua-20261027-x5rvprcm/
  zlua.tar.gz
  manifest.json
```

该备份是源码快照，不是一次真实跳转数据库迁移。M0 的 Git 基线及恢复备份也继续保留。

### M3 功能检查

完整 `zsh -df tests/test_runtime.zsh` 通过：14 项插件、13 项初始化、12 项状态迁移、14 项 M3 交互/跳转迁移，共 53 项 Python 测试，加原有运行时断言。安装器测试、插件 verify、Zsh/Python 语法和差异空白检查通过。

| 场景 | 本机结果 |
| --- | --- |
| 官方 Ctrl-R | 真实 PTY 中搜索、选择后回填、执行；取消后通过 ZLE 读取 BUFFER，确认原输入逐字保留 |
| 多行历史 | 官方组件选中一条含两行命令的历史，回填后实际执行，两行输出均正确 |
| 加载顺序 | Tab 真实 fzf 选择、自动建议右方向键接受、高亮继续通过；禁用 fzf-tab 后 Tab 为 `expand-or-complete`，Ctrl-R 仍为 `fzf-history-widget` |
| 完整官方集成回退 | 包装实际二进制以模拟无配套脚本安装，确实调用 `--zsh`，Tab 保持原生；真实 TTY 重复 source 后全部绑定不变 |
| zoxide | 真实 PTY 的关键词跳转和 `zz` 交互选择通过，目标含中文、空格；目录钩子只注册一次 |
| 外置 z.lua | 自定义非导出 `_ZL_DATA`、`_ZL_CMD=j` 生效；兼容别名正确，实际从自定义数据库按关键词跳转 |
| 防止提前切换 | 非空旧库保持兼容后端；显式 zoxide 等待决定，临时 HOME 中明确跳过后再使用 zoxide |
| 降级 | 0.30.0 版本替身不加载官方历史或 fzf-tab；Ctrl-R 保留原生，交互跳转明确提示版本要求；缺工具和 minimal 回归通过 |
| 数据导入 | 自定义源、已有目标合并、两边备份、成功后新增目标记录及重复执行、失败后重试、提交中断恢复、锁冲突及损坏记录均覆盖 |
| M1/M2 回归 | 非交互安静、XDG/空格路径、私有权限、幂等初始化、固定提交、断网加载和安装失败保护继续通过 |

### M3 性能观察

同 PATH、TERM、locale，分别隔离 HOME、XDG 与已存在的 ZDOTDIR；M0 由 `git archive 358bbd6` 恢复。每档首次启动一次，稳定启动 20 次，以固定随机顺序交错采集。TTY 档使用带控制终端的 `pty.fork`，确认实际 Ctrl-R 绑定为官方 widget；计时覆盖 `zsh -dfi -c source`，不包含提示符绘制或按键选择，也没有清空操作系统文件缓存。

| 配置 | 首次启动 | 稳定中位数 | P95 |
| --- | --- | --- | --- |
| M0 desktop，无 TTY | 225.435 ms | 63.945 ms | 78.676 ms |
| M3 默认 desktop，无 TTY | 191.715 ms | 62.647 ms | 82.034 ms |
| M3 z.lua 兼容，无 TTY | 220.679 ms | 81.633 ms | 104.385 ms |
| M3 minimal，无 TTY | 177.757 ms | 47.221 ms | 51.814 ms |
| M0 desktop，TTY | 204.442 ms | 64.466 ms | 76.375 ms |
| M3 默认 desktop，TTY | 221.364 ms | 69.239 ms | 83.421 ms |
| M3 z.lua 兼容，TTY | 223.791 ms | 89.090 ms | 103.308 ms |
| M3 minimal，TTY | 180.359 ms | 46.501 ms | 53.867 ms |

默认 desktop TTY 相比同轮 M0 增加 4.773 ms；z.lua 兼容 TTY 增加 24.624 ms，超过旧 20 ms 预算 4.624 ms。按用户本轮调整后的标准，这不作为阻塞；保留全部样本，不继续追逐毫秒差异。数据没有显示明显启动异常，也不构成其他机器或平台的速度保证。M2 的历史性能记录没有被改写。

### M3 完成边界

本机实现、外部依赖准备、功能回归及真实 PTY 完成。安装了 Homebrew zoxide，并为本仓库核对了含外置 z.lua 的四项插件依赖；没有修改日常 `.zshrc`、旧 `~/.config/zsh` 或对真实历史/跳转库执行 apply。

M4 解压与图片预览、M5 安装和平台收尾尚未开始；旧 `bash -n lib/img_preview.sh` 解析失败仍按 M4 已知问题保留。没有 Linux/OpenWrt 真机、远程 CI、Kitty/SSH/tmux 的人工体验或真实用户数据导入结果。因此这里只宣告 M3 本机功能完成，不宣称 M0-M5 全部完成或全仓库所有旧检查均通过。

## M4 解压、预览与自有函数（2026-10-28）

本阶段完成仓库实现和本机自动化验收。`extract` 交给 ouch；文件预览保留一层 POSIX sh 适配，图片协议调用安装包内的官方脚本。randport、dcupdate 移到 `functions/`，Git 提示符函数移到 `lib/git-prompt.zsh`。simple 主题的颜色和信息结构保持原样。

已安装并使用本机 Homebrew ouch 0.8.3、bat 0.26.1、eza 0.23.5，开发检查使用 ShellCheck 0.11.0；fzf 继续为 0.74.5。这些二进制由 Homebrew 维护，不加入 Antidote 清单。安装器的依赖统一继续留到 M5。

### 实际行为与测试

| 项目 | 结果与证据 |
| --- | --- |
| 正常解压 | ZIP、tar.gz、gzip、bzip2、xz、7z 的真实 ouch 调用通过，含中文、空格、前导连字符路径 |
| RAR 构建支持 | 固定上游 0.8.3 对应提交的 RAR3/RAR5 样本都解出 `testfile.txt`；来源、SHA-256 与输出见 `verification-m4-formats.json` |
| 输出与删除 | 输出为旁边的 `<完整文件名>.extracted/`；已有目录和悬空符号链接拒绝；成功 `-r` 删除对应原包，损坏与缺失输入返回失败 |
| 多输入与失败 | 失败不删原包且继续后续输入；整体非零；成功和失败均不改变调用者 cwd；非空部分输出保留供检查 |
| 无 ouch | 不注册 extract/x；无参、仅选项和非法选项返回 2；doctor 提示安装方式 |
| 文本与目录 | bat/batcat/head 选择及 eza/ls 降级通过；真实 bat 只输出 1,000 行，真实 eza 只输出 200 行，见 `verification-m4-preview.json` |
| 图片调用 | 通过 PATH 所选安装包定位官方脚本；本机真实官方脚本调用替身 kitten，核对 `icat`、`--place=60x10@0x0` 及完整中文文件路径 |
| 图片降级 | off、普通终端、缺脚本、官方脚本失败、SSH、tmux、缺失或非法尺寸均返回 PNG 类型和尺寸；不是依赖 uname 判断终端 |
| 取消清理 | 真实 fzf 在 PTY 启动预览并收到 Ctrl-C 后退出；慢预览和真实官方脚本的 kitten/sed 管道各自的监测进程均结束 |
| 小工具 | dcupdate 仅 pull → up -d，pull 失败不 up；randport 检测工具失败不误报可用端口；缺命令不注册 tree/lg |
| 提示符 | 清洁、修改、隐藏 Git 状态输出通过；函数拆分不改变 simple 主题 |

新增 `tests/test_tools.py` 最终为 20 项，全部通过。测试使用隔离 HOME、XDG、临时输入和依赖替身；另对真实 ouch、bat、eza、fzf 包进行调用。图像测试中的 kitten 是替身，因此没有向用户终端发送图像。

完整采集：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/collect-baseline.py \
  --output docs/verification-m4-desktop.json --profile desktop \
  --plugin-data "$HOME/.local/share/omz" --samples 20
PYTHONDONTWRITEBYTECODE=1 python3 scripts/collect-baseline.py \
  --output docs/verification-m4-minimal.json --profile minimal \
  --plugin-data "$HOME/.local/share/omz" --samples 20
```

两份完整采集各有 33 项检查，全部返回 0；这两次采集中的 M4 测试为 19 项。之后增加真实官方脚本取消时 kitten 管道退出检查，M4 最终扩展至 20 项，并重新执行完整 runtime 套件：插件 14、初始化 13、迁移 12、交互 14、M4 工具 20，共 73 项全部通过。所有逐文件 Zsh/POSIX 解析、ShellCheck 和 `git diff --check` 通过。CI 配置已更新为新函数目录和 macOS ouch/bat/eza/ShellCheck 依赖，本次没有触发或读取远程 CI 结果。

### 资源观察

按既定方法在独立进程中采集，稳定启动各 20 次；毫秒级预算仍按用户的 M3 调整不作为交付门槛。

| 配置档 | 首次启动（无补全缓存） | 稳定中位数 | 稳定 P95 |
| --- | --- | --- | --- |
| desktop | 159.854 ms | 50.893 ms | 52.250 ms |
| minimal | 141.592 ms | 32.234 ms | 36.316 ms |

desktop 的 Git 提示符中位数/P95：普通目录 16.049/16.783 ms、10,000 文件干净仓库 28.715/29.564 ms、修改一个文件 29.115/33.741 ms。minimal 对应 16.260/16.830、29.127/33.669、34.770/36.102 ms。M4 仅迁移提示符函数位置，不把本机波动解释为优化收益。

### 清理和未验收范围

验证后已删除旧 extract、randport、docker-tools 插件目录，以及 `lib/img_preview.sh`、`lib/get_cursor.sh`；移除相应加载入口和旧光标缓存依赖。M0–M3 的旧失败记录保留作历史，当前源码中不再存在该 Bash 解析问题。测试压缩包、下载样本、FIFO、预览进程和临时 HOME 随测试清理；项目不保留截图、下载包或测试历史。用户 XDG 依赖及旧安装中的 cursor 数据仍保留。

真实 Kitty/iTerm2 的图像位置、尺寸、视觉效果尚未人工验收；SSH/tmux 验证的是元数据降级，未承诺图片透传。加密、分卷等格式未穷尽，RAR 成功仅代表本机 ouch 构建。没有 Linux/OpenWrt 真机或远程 CI 结果。本次没有切换 `.zshrc`、替换日常安装目录或迁移真实用户数据；M5 尚未开始。

## M5：安装与文档收尾（2026-10-28）

在 `main` 延续已有 M1–M4 工作区完成本阶段，没有新分支、提交或推送。原始机器记录为 [verification-m5.json](verification-m5.json)。本阶段交付范围是仓库安装器、文档和本机隔离验收；日常安装、真实数据与跨平台实机体验仍分开标记。

### 安装与诊断

- `/bin/sh` 安装器按有效配置档准备软件包，使用与运行时一致的个人配置优先级；desktop 请求 fd/fzf/zoxide/ouch/bat/eza，server 请求 fd/fzf/zoxide，minimal 不装增强工具。Lua 仅用于明确或保留旧数据库的 z.lua 场景。
- 二进制统一由包管理器维护，可选包逐个失败降级；删除 `~/.fzf` pull/install、OpenWrt 未校验 fd 下载、全局 fd 软链接及无条件 Lua/Bash 依赖。Arch 使用完整 `pacman -Syu`，文档明确该行为并给出独立维护软件包的入口。
- 源码 clone/快进后执行固定插件 install/verify，成功后才向启动文件添加精确 source 行。已有启动文件追加前备份为同目录 `.omz-backup.*`，权限 600；支持 ZDOTDIR、自定义路径、空格、Shell 元字符和无末尾换行。
- 本地源码改动、依赖改动、非空非 Git 目标和远端不符会阻止覆盖。源码脏检查先于任何软件包操作。`OMZ_INSTALL_DEPS=0` 跳过包管理器；`--migrate-state-preview` 只预览，冲突时不添加入口，永不自动 apply。
- `doctor.zsh` 扩展为只读配置/路径/工具/跳转/缓存诊断；完整 SHA 检查继续交给插件 verify。

### 本机验证结果

| 检查 | 结果与范围 |
| --- | --- |
| 安装器函数测试 | Homebrew、apt、pacman、OpenWrt apk/opkg 命令分支；desktop/server/minimal 包选择；Lua 条件安装；可选包失败；source 行幂等与备份均通过。包管理器以替身记录调用，没有执行真实系统包安装 |
| 完整安装集成 | 12 项通过；真实 `/bin/sh`、Git 仓库、Antidote/插件固定源码；上游重定向至本地真实 Git，仅允许 file 协议 |
| 三档全流程 | desktop/server/minimal 均完成干净目标安装、重跑、快进升级及安装后交互 Shell 加载；source 行只出现一次，备份内容保持 |
| 升级失败 | 脏源码在包操作前停止；脏依赖和无法取得的固定 SHA 保留旧加载缓存与启动文件；源码已快进但 pin 安装失败时，启动确认进入可用的原生补全降级 |
| 用户状态与只读预览 | 隔离的历史、local.zsh、旧跳转库逐字节保留；冲突预览不添加 source 行；无冲突预览也不复制历史或写迁移完成标记 |
| 诊断和路径 | doctor 不创建状态目录；含空格、引号、美元符号、反引号和反斜线的安装路径可按字面 source |
| 运行时回归 | 插件 14、初始化 13、状态迁移 12、交互/跳转 14、工具 20，共 73 项 Python 测试及原有 Zsh 断言通过，包含真实 PTY |
| 语法与静态检查 | 逐文件 sh/bash/Zsh 解析、Python AST、安装器与预览适配 ShellCheck、受跟踪与未跟踪文件空白检查通过 |
| 真实用户文件 | 检查前后 `.zshrc`、`.zshenv`、`.zlua`、旧个人文件和旧安装 cache 下现有文件的 SHA-256 完全相同；原始路径/校验值记录于 JSON |

安装集成与运行时共 **85 项 Python 测试通过**，没有跳过项。完整采集包含 34 个命令检查。初次额外扫描未跟踪文件时发现此前 `config/history.zsh`、`config/keybindings.zsh` 末尾各有一个多余空行；仅修剪这两个空行后重新检查语法和空白，结果通过。未因这次非功能整理重复运行完整套件。源码/依赖升级不是整体事务，失败保护不等于自动回滚源码；该边界已同步到两份 README 和迁移说明。

本阶段没有修改交互初始化逻辑，不重新采集毫秒级启动基准；保留 M0–M4 原始性能记录，73 项运行时回归作为此次兼容检查。

### 文档、清理与尚未验收项

中英文 README 已统一安装档位、包归属、环境变量、升级失败、迁移、回滚及平台证据。迁移清单与计划顶端更新为 M0–M5 仓库实现/本机自动化完成，历史阶段报告保留原貌，不能把旧“未开始”段落当作当前状态。第三方说明继续保留所选提交及许可证，没有更换 pins。

M2–M4 已替换的通用插件与图片实现继续保持删除；M5 删除无消费者的 `cache/holder` 和空目录，保留旧 cache 的忽略规则。测试 HOME/XDG、上游仓库、下载样本与临时缓存均随测试结束清理。项目最终扫描未发现 `__pycache__`、`.pyc`、临时日志、FIFO 或下载包；用户目录中的依赖、备份和状态保留。

CI 工作流增加安装器 ShellCheck 和三档安装/升级测试入口，Ubuntu 增加 bat/ShellCheck 测试依赖；当前没有远程 CI 运行结果。Debian/Ubuntu、Arch、OpenWrt 的完整包安装与首次启动没有实机验证；本机模拟 apk/opkg 不代表 OpenWrt 运行验收。Intel Mac、Kitty/iTerm2 真实图像位置、SSH/tmux 人工体验、日常安装切换和真实历史/跳转库导入仍未完成。因此本轮完成 M5 仓库与本机收尾，不宣称全部跨平台与用户迁移验收结束。
