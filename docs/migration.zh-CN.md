# 迁移进度与数据清单

依据：[维护与精简方案](maintenance-plan.zh-CN.md)。最新验证：[verification.md](verification.md)。

## 当前进度

| 阶段 | 状态 | 交付或下一步 |
| --- | --- | --- |
| M0 基线 | 已完成采集与备份校验 | 入口及版本清单、20 次稳定启动数据、提示符测量、可恢复快照；发现一个现有语法问题 |
| M1 初始化与数据路径 | 实现与本机自动化验证完成 | 个人配置提前读取、交互保护、三种配置档、XDG 目录、幂等初始化及显式迁移入口；未迁移真实数据 |
| M2 插件外移 | 实现与本机功能验证完成 | 完整 SHA、静态加载、install/build/verify、断网及 PTY 验收；三个内嵌副本已删除；历史绝对性能参考线未达到，同环境增量合格 |
| M3 交互替换 | 实现与本机功能验证完成 | zoxide、官方 Ctrl-R、外置 z.lua、显式数据导入及 PTY；真实跳转库尚未导入 |
| M4 解压与预览 | 实现与本机自动化验证完成 | ouch 薄封装、官方图片预览适配、自有函数整理；旧脚本已删除，真实终端图像及跨平台体验待验收 |
| M5 安装与文档收尾 | 仓库实现与本机自动化完成 | 包管理归属、三档隔离安装/升级、失败保护、诊断和中英文说明；跨平台实机/远程 CI 待验收 |

当前完成 M1-M5 仓库实现，历史和图片使用 fzf 官方组件，z.lua 已外置，解压交由 ouch。本机已通过 Homebrew 安装 ouch、bat、eza 和验证工具 ShellCheck；本仓库的外部依赖及加载文件已准备。日常使用的 `~/.config/zsh` 和 `.zshrc` 尚未切换，真实历史、查询记录、个人配置和跳转数据库没有复制、移动或合并。M5 本机安装与文档收尾已完成；跨平台和真实终端图像体验验收仍待完成。M1/M2 段落保留各阶段当时的行为，现行契约见下方 M3–M5。

## M0 数据位置快照

2026-10-27 本机只读取文件元数据并备份，没有合并、移动或删除真实用户数据。

| 数据 | 旧位置及本次观察 | 目标位置 | 迁移状态 |
| --- | --- | --- | --- |
| Shell 入口 | `~/.zshrc` 存在，仍引用 `~/.config/zsh` | 保留入口，按阶段调整加载实现 | 已备份，未修改 |
| 本项目个人配置 | `config/env-self.zsh` 不存在 | `${XDG_CONFIG_HOME:-$HOME/.config}/omz/local.zsh` | 未复制或创建 |
| 已安装配置的个人文件 | `~/.config/zsh/config/env-self.zsh` 不存在 | 同上；新文件优先，旧文件仅作兼容 | 待 M1 |
| 本项目命令历史 | `cache/zshhistory` 不存在，cache 中仅有 holder | `${XDG_STATE_HOME:-$HOME/.local/state}/omz/zsh_history` | 未创建 |
| 实际使用的旧命令历史 | `~/.config/zsh/cache/zshhistory` 存在，4,023 字节 | 同上 | 已备份，未导入 |
| 另一份用户历史 | `~/.zsh_history` 存在 | 必须先确认来源，不自动混入目标历史 | 已备份 |
| fzf 查询历史 | `~/.config/zsh/cache/fzfhistory` 存在，23 字节 | 同一状态目录的 `fzf_query_history` | 已备份，未导入 |
| 上次目录 | 两份配置的 `cache/currentdir` 均未发现 | 同一状态目录的 `last_directory` | 未创建；恢复目录默认关闭 |
| 旧光标状态 | `~/.config/zsh/cache/cursor` 存在，28 字节 | 不作为新预览协议的数据接口 | 已备份，待 M4 验收后处理 |
| z.lua 数据库 | `~/.zlua` 存在；采集环境未导出 `_ZL_DATA`，已检查的现有配置未发现该项 | zoxide 自身目录，或保留兼容后端 | 已备份，未导入，未切换后端 |
| 补全缓存 | 当前 compinit 使用其默认位置 | `${XDG_CACHE_HOME:-$HOME/.cache}/omz/` 下 | 只在临时 HOME 测量，未移动真实缓存 |
| 备份 | M0 新增的项目外快照，见验证报告 | 同一状态目录的 `backups/` | 恢复校验通过 |
| 插件及 Antidote | 当前插件仍在仓库 `plugins/` | `${XDG_DATA_HOME:-$HOME/.local/share}/omz/` 下 | 未下载、外移或删除 |

字节数为采集时的快照观察，其他 Shell 会话继续写入后会变化，不能作为迁移结束的校验值。

## M1 迁移入口与操作边界

迁移工具使用 Python 3 标准库；日常 Zsh 初始化不依赖 Python。默认只预览，不执行个人配置，不在 Shell 启动中自动迁移：

```sh
cd /Users/linzx6/Project/omz
zsh scripts/migrate-state.zsh
zsh scripts/migrate-state.zsh --legacy-root "$HOME/.config/zsh" --copy-local
```

默认优先选择已安装的 `~/.config/zsh`；该目录不存在时才选择本工具所在仓库。其他安装位置必须传 `--legacy-root`。迁移器读取导出的 `_ZL_DATA`，未导出的自定义值须显式提供，例如：

```sh
zsh scripts/migrate-state.zsh \
  --legacy-root "$HOME/.config/zsh" \
  --zlua-data "/实际路径/自定义跳转数据库"
```

先退出仍使用旧配置的 Shell，让它们完成历史落盘，再从没有加载旧配置的终端执行：

```sh
zsh -df scripts/migrate-state.zsh \
  --legacy-root "$HOME/.config/zsh" \
  --apply --old-sessions-closed
```

上面的命令是操作指引，本次没有对真实数据执行 `--apply`。`--old-sessions-closed` 是操作者对旧会话已结束的声明，工具不自动关闭终端，也不能独立证明其他会话停止写入。

- 需要复制旧个人配置时加 `--copy-local`；默认保留旧文件并仅兼容读取。
- 目标历史、查询记录、目录记录或个人配置非空且未有本工具的成功记录时，整个预检停止，保留两边数据，报告人工合并入口；空目标先备份再复制。
- 每次有待执行复制时，在状态目录的 `backups/m1-*/` 保存原 `.zshrc`、旧/新个人配置、旧/新状态、跳转数据库，写入含源路径和 SHA-256 的 `manifest.json`；备份校验后才复制。
- `migrations/state-v1.json` 记录逐项复制状态。成功重跑不覆盖目标后来新增的记录；旧源若继续增长，会报告冲突。中断且内容仍一致的复制可恢复，失败不能冒充完成。
- 使用自动随进程退出释放的文件锁。并发迁移会失败并提示，锁释放后可重试；不需要删除残留锁文件。
- 不导入或切换 z.lua 数据库；只备份导出的 `_ZL_DATA`、`--zlua-data` 指定位置或默认 `~/.zlua`。跳转后端切换属于 M3。
- XDG 根目录未设置、为空或为相对路径时使用用户目录下的默认位置。状态和备份目录为 0700，历史、复制结果和备份文件为 0600。

M1 的个人覆盖文件为 `${XDG_CONFIG_HOME:-$HOME/.config}/omz/local.zsh`，存在时优先于仓库 `config/env-self.zsh`，两者不同时执行。个人配置在历史、快捷键、补全、钩子及插件初始化前读取；重复 source 不重新执行个人文件或交互初始化，选项变化通过新 Shell 生效。

```zsh
OMZ_PROFILE=auto
OMZ_JUMP=auto
OMZ_HISTORY_SEARCH=auto
OMZ_IMAGE_PREVIEW=auto
OMZ_RESTORE_DIRECTORY=false
OMZ_DISABLED_PLUGINS=()
```

`auto` 配置档在 macOS 选 desktop、OpenWrt 选 minimal、其他系统选 server。minimal 使用原生补全/历史、simple 主题和自有函数，跳过 z.lua、fzf 配置及三个增强插件；server 关闭图片预览。M1 的 `OMZ_JUMP=auto` 继续使用已有 z.lua，有 Lua 才初始化；显式 `zoxide` 只提示 M3 尚未实现，不提前改变旧用户行为。`OMZ_HISTORY_SEARCH=native` 使用原生 Ctrl-R，其他可用 fzf 的增强配置仍用旧 `historybyfzf`，官方替换留待 M3。

`_OMZ_APPLY_CHPWD_HOOK` 映射到 `OMZ_RESTORE_DIRECTORY`，`_OMZ_APPLY_HISTORYBYFZF=false` 映射到原生历史搜索；显式新选项优先。无旧值时恢复目录默认关闭，目录状态作为纯文本读取。终端标题继续沿用原开关。

M1 对旧光标脚本只调整 XDG 缓存路径和纯文本读写；旧图片实现和已知 Bash 解析问题仍待 M4，不属于本阶段图片体验保证。

- 使用隔离 HOME/XDG 验证初始化和迁移入口，继续保留当前 z.lua、手写历史及内嵌插件。
- 按实际正在使用的 `~/.config/zsh` 定位旧数据，不能只检查本项目的空 cache 后判定“无历史”。
- 实际迁移前重新确认 `_ZL_DATA`、配置路径和旧会话写入情况；目标存在且非空时停止自动覆盖。
- 为每次真实迁移单独建立新快照。M0 快照只保护采集时刻，不覆盖后来产生的记录。
- 新的状态文件按数据读取，尤其是上次目录，不能 source 旧状态文件。
- 先提供旧/新路径预览、重复执行与失败重试验证，再运行实际数据迁移。

## M2 外置插件的安装与重建

M2 固定版本见 [来源与许可证](third-party.zh-CN.md)。三个通用插件已从本仓库 `plugins/` 删除；z.lua、自有函数和历史后端保留到各自后续阶段。

在要使用的配置源码目录执行：

```sh
zsh -df scripts/manage-plugins.zsh install
zsh -df scripts/manage-plugins.zsh verify
```

- `install` 是唯一允许 Git 联网的操作：引导固定 Antidote，将有效插件交给 Antidote 的 `pin:` 安装，全部核对后原子替换静态文件。重复执行不跟随分支更新；已有依赖中的本地修改会阻止安装，不自动覆盖。
- `build` 只使用已安装且 SHA 一致、工作区干净的依赖重新生成静态文件，Git 网络协议被禁用；缺文件或版本不符会失败并保留旧缓存。改变清单中的版本后必须用 `install`。
- `verify` 核对本配置实际启用的依赖 HEAD、工作区和静态文件标识、语法；不联网、不拉取、不修复，也不初始化真实用户状态。
- `minimal` 和全部禁用三个插件的配置不需要下载 Antidote。未安装 fzf 时不安装或加载 fzf-tab；稍后装好 fzf，需要再次 `install`。禁用插件不会删除它已有的源码。
- 管理入口读取同一份个人配置和配置档。插件配置发生变化后，通过新 Shell 生效；仍需在相同配置下执行 `build`。

默认路径：

```text
~/.local/share/omz/antidote/
~/.local/share/omz/plugins/github.com/Aloxaf/fzf-tab/
~/.local/share/omz/plugins/github.com/zsh-users/zsh-autosuggestions/
~/.local/share/omz/plugins/github.com/zsh-users/zsh-syntax-highlighting/
~/.cache/omz/plugins.zsh
```

分别受 `XDG_DATA_HOME` 和 `XDG_CACHE_HOME` 控制。静态文件记录源码绝对路径、数据及缓存路径、配置档、有效插件、清单和引导文件内容。搬迁源码/数据/缓存、修改清单、改变禁用项或 fzf 可用性后，旧标识不再匹配；启动仅提示执行入口，继续保留原生补全和基础 Shell，不自动下载或重建。同一缓存路径只保存一个配置组合，切换配置须重建。

运行时不加载 Antidote、不调用插件管理 Git 命令，只读取匹配的静态文件。该文件先检查所有插件入口，再按 fzf-tab、自动建议、语法高亮顺序加载，避免缺少最后一个依赖时前面插件已部分启用。`verify` 是版本检查入口，普通启动不逐次运行 Git 检查源码是否被手工修改。

本次已在默认用户数据目录执行 `install` 和 `verify`，缓存对应 `/Users/linzx6/Project/omz`，不是旧 `~/.config/zsh` 副本。没有修改日常 `.zshrc`、历史、个人配置或跳转库。若之后改为从其他源码位置加载，先在该位置重新生成缓存。

## M3 跳转、历史与旧别名

增强配置的 `OMZ_JUMP=auto` 优先使用已安装的 zoxide；没有 zoxide 时使用外置 z.lua 与 Lua，否则保留普通 `cd`。minimal 不初始化跳转或增强历史。显式 `zoxide`、`zlua` 不可用时提示原因，不切到另一个后端。

旧 `_ZL_DATA`（默认 `~/.zlua`）非空且尚无迁移决定时，auto 继续选 z.lua；显式 zoxide 暂停跳转并提示迁移入口。不会仅因安装了 zoxide 就忽略旧记录。外置 z.lua 尚未安装时，运行 `zsh -df scripts/manage-plugins.zsh install`，不会重新加载旧内嵌副本。旧数据库的相对路径按执行目录解析，建议在个人配置中使用绝对路径。

| 入口 | zoxide 后端 | z.lua 后端 |
| --- | --- | --- |
| `z` | zoxide 关键词匹配、排序及普通路径跳转 | 保留原语义；支持 `_ZL_CMD` 自定义命令名 |
| `zi` | 官方交互选择 | 对应 `<_ZL_CMD> -I` |
| `zz`、`zf` | 均为 `zi` | 分别保留 `-i`、`-I` |
| `zb`、`zc`、`zbi`、`zbf`、`zh`、`zzc` | 不模拟旧语义 | 保留；`_ZL_NO_ALIASES` 可关闭项目别名 |

两个后端不同时注册目录记录钩子。z.lua 使用本项目外置清单固定提交，保留 `_ZL_*` 和 `ZLUA_EXEC` 配置；zoxide 保留 `_ZO_*` 配置及自身数据目录规则。对未导出的个人配置变量，初始化适配层会导出对应标量，使子进程读取相同设置。`zi`/`zz`/`zf` 的 zoxide 交互选择要求 fzf 0.51.0+；缺少该工具仍可使用 `z` 的普通跳转。

### 显式导入或跳过

```sh
# 默认只预览；会读取与启动相同的个人配置。
zsh -df scripts/migrate-jump.zsh
zsh -df scripts/migrate-jump.zsh --zlua-data "/实际路径/自定义数据库"

# 停止所有向两个后端数据库写入的会话后执行。
zsh -df scripts/migrate-jump.zsh --apply --old-sessions-closed

# 明确决定不导入旧记录时，使用这一条代替上一条。
zsh -df scripts/migrate-jump.zsh --skip-import --apply --old-sessions-closed

# 决定后按新后端重新生成加载文件，再打开新 Shell。
zsh -df scripts/manage-plugins.zsh build
```

导入器本轮实测 zoxide 0.10.0，要求提供 `zoxide import z.lua` 子命令的版本；旧 CLI 不会被套用新语法。运行时普通跳转不要求用户升级到该导入版本，可继续明确选择 z.lua。

- 导入读取 `_ZL_DATA`，或 `--zlua-data` 指定的同一源文件；命令行指定自定义源时，也要让个人配置的 `_ZL_DATA` 指向它，启动才能识别该决定。
- 先在状态目录 `backups/m3-*/` 备份两边现存数据库并核对 SHA-256，生成路径映射与动作记录；缺失的目标不伪造原始备份。
- 使用 zoxide 官方 `import z.lua --merge`，在目标目录下的临时数据库副本中导入；上游读取校验后检查原始文件未变化，再替换目标。失败保留原库，不写成功决定，临时目录自动清理。
- `migrations/jump-v1.json` 保存备份、源与目标校验值和进度；`migrations/jump-v1` 为只按文本读取的后端决定。进程锁阻止两个迁移器并发。会话停止声明仍由操作者保证，不能防止未关闭的其他程序继续写库。
- 同一源的成功重跑不再导入，也不覆盖目标后来新增的记录；旧源改变或已有记录指向不同路径时停止，要求先保留并核对记录。替换后、写决定前的中断可按校验值恢复，避免再次加权导入。
- 跳过导入仍先备份并记录明确决定，保留两边数据库。真实数据库本次没有执行以上任何 `--apply`。
- macOS 默认 zoxide 目标为 `~/Library/Application Support/zoxide/db.zo`；Linux 默认 `${XDG_DATA_HOME:-$HOME/.local/share}/zoxide/db.zo`；`_ZO_DATA_DIR` 可覆盖目录。项目不把它重定向到自己的状态目录。

### Ctrl-R 与加载顺序

有真实 TTY 且 fzf 0.51.0+ 时，优先读取所选安装包的官方 `key-bindings.zsh`，不加载它的文件补全层；没有配套脚本时使用该二进制的 `--zsh` 输出。原生快捷键与 compinit 先完成，fzf 历史与跳转后端随后初始化，最后加载 fzf-tab、自动建议、语法高亮。回退到完整官方集成时，其 Tab 绑定会恢复为项目补全入口；Ctrl-T/Alt-C 不额外注册，禁用 fzf-tab 后仍使用 compsys。

`OMZ_HISTORY_SEARCH=native` 或旧开关 `_OMZ_APPLY_HISTORYBYFZF=false` 使用原生 Ctrl-R；工具缺失、旧版、minimal 也降级。旧版独立脚本本轮未验收，因此不加载。无 TTY 的 `zsh -i -c` 检查保留原生历史，避开官方脚本在这类环境恢复 ZLE 选项时的报错；真实交互由 PTY 验收。

`FZF_DEFAULT_OPTS` 的用户参数保留在项目视觉默认值之后；查询历史仅通过 `FZF_CTRL_R_OPTS` 设置，用户专有参数同样在项目默认值后。不再设置无人使用的 `FZF_PREVIEW_COMMAND`，也不设置另一套触发式文件补全入口。Ctrl-R 选择、取消后保留缓冲区、多行历史执行，以及与 Tab、建议和高亮并存已在本机真实 PTY 验证。

## M4 解压、预览与自有函数

2026-10-28 完成本机实现及自动化验证；这一步没有修改日常 `.zshrc` 或执行真实数据迁移。M5 已统一安装器依赖归属；macOS 也可显式安装：

```sh
brew install ouch bat eza
zsh -df scripts/doctor.zsh
```

`extract [-r|--remove] [--] <文件...>` 和 `x` 仅在 ouch 可用时注册。命令行为变化如下：

| 行为 | M4 契约 |
| --- | --- |
| 输出目录 | 每个原包旁的 `<完整文件名>.extracted/`，例如 `a.tar.gz.extracted/`，保留全部扩展名 |
| 已有目标 | 目录、文件、符号链接均拒绝，不合并或覆盖 |
| 删除原包 | 仅显式 `-r` / `--remove`，且对应输入成功后删除；失败的原包保留 |
| 多输入 | 逐个处理，失败后继续后续输入；任一失败则整体非零 |
| 无参数或非法选项 | 返回 2 并提示用法；前导连字符文件名用 `--` |
| 失败输出 | 空目录尝试删除；非空部分输出保留供检查，再次执行前须先处理该目录 |
| 调用者目录 | 成功、失败及多输入均不改变 cwd |
| `.deb` / `.rpm` | 不承诺旧脚本的 control/data 特殊展开；Debian 用 `dpkg-deb -x/-e`，RPM 用 `rpm2cpio` 与 `cpio` 在独立目录处理 |
| 格式范围 | 由 ouch 版本和构建决定；本机 0.8.3 已测 ZIP、tar.gz、gzip、bzip2、xz、7z、RAR3 和 RAR5，未穷尽加密或分卷格式 |

`lib/file_preview.sh` 通过 fzf-tab 的实际 `fzf-preview` 配置消费，不配置无人读取的全局预览变量。路径转为绝对路径并逐参数传递；文本通过 head 先读取最多 1,000 行，再交给 bat、batcat，缺少两者则输出文本。目录优先 eza，否则 ls，最多显示 200 行；不开启递归目录树。

图片从 PATH 所选 fzf 的安装位置查找官方 `fzf-preview.sh`（包含 Homebrew symlink 路径和常见 Linux 共享目录）。自定义安装位置可在个人配置中显式导出：

```zsh
export OMZ_FZF_PREVIEW_SCRIPT="/实际 fzf 包路径/bin/fzf-preview.sh"
# 或关闭图像，仅显示元数据
OMZ_IMAGE_PREVIEW=off
```

当前自动调用要求 fzf 提供正数预览尺寸，且为本地 Kitty（`KITTY_WINDOW_ID` 和 kitten）或 iTerm2（imgcat 且没有抢先进入官方 chafa 分支）。普通终端、缺脚本或工具、关闭图片、SSH、tmux 均输出文件类型和可获得的尺寸。server/minimal 保持关闭图片。iTerm2 条件分支存在，但本次没有真实 iTerm2 验收；其他终端和 tmux 透传尚未启用为承诺功能。

本项目不创建图片常驻进程、FIFO 或光标缓存，不执行 `killall`。已删除仓库中的旧 `lib/img_preview.sh`、`lib/get_cursor.sh` 和旧 extract 源码；真实安装目录及其中的旧 cursor 数据仍保留。PTY 验收覆盖官方脚本加替身 kitten 的协议参数和取消清理，尚不等于真实终端中图片位置、尺寸和视觉效果验收。

`randport`、`dcupdate` 移至 `functions/`；randport 的返回值只表示探测当时空闲，不预留端口。dcupdate 改为 pull 成功后直接 up -d，不再无条件 down；服务重建仍可能中断。Git 状态函数移至 `lib/git-prompt.zsh`，simple 主题显示结构保持原样。tree、lazygit 缺失时不注册对应别名。

## M5 安装、升级与平台边界（2026-10-28）

安装器保持 `/bin/sh` 入口，自动读取与运行时相同的个人配置，按有效配置档安装依赖：desktop 请求 fd/fzf/zoxide/ouch/bat/eza，server 请求 fd/fzf/zoxide，minimal 不请求增强工具。Lua 只在显式 z.lua 或 auto 存在未决定迁移的旧跳转库时请求；minimal 仍不安装 Lua。Debian 的 fd-find、batcat 直接由运行时识别，不创建全局软链接。

二进制只交给包管理器：macOS 用 Homebrew，Debian 系用 apt，Arch 用 pacman，OpenWrt 优先 apk、否则 opkg。可选包逐个安装；不可用时提示降级，不尝试源码编译或下载没有校验的上游产物。Arch 的基础步骤使用 `pacman -Syu`，包含系统升级。已有 `~/.fzf` 完全保留；不再执行其 pull/install，也不为 OpenWrt 下载 fd tar 包或强制安装 Bash。macOS 安装器仍要求预先准备 Homebrew 与命令行工具；只使用已安装命令时可跳过包管理器。

```sh
# 默认克隆/快进更新 ~/.config/zsh，准备并核对插件后再添加 source 行。
sh scripts/install_zsh_config.sh

# 软件包由用户自行维护；仍执行源码与固定插件的安装/核对。
OMZ_INSTALL_DEPS=0 sh scripts/install_zsh_config.sh

# 附带只读状态预览，需要 Python 3；冲突时不追加 source 行。
sh scripts/install_zsh_config.sh --migrate-state-preview

sh scripts/install_zsh_config.sh --help
```

安装器选项：

| 选项 | 契约 |
| --- | --- |
| `TARGET_DIR` | 源码绝对路径，默认 `~/.config/zsh`，不随 XDG_CONFIG_HOME 改变 |
| `ZSHRC_FILE` | 启动文件绝对路径，默认 `${ZDOTDIR:-$HOME}/.zshrc` |
| `REPO_URL` | 源码远端；已有 origin 必须相同，允许 URL 末尾 `.git` 差异 |
| `SOURCE_LINE` | 自定义精确 source 行；等价但不同文本的旧行不自动重写 |
| `OMZ_INSTALL_DEPS=0` | 不运行包管理器；需要 zsh/git/curl 已可用，允许增强工具缺失 |
| `OMZ_PROFILE` / `OMZ_JUMP` | 环境值仅用于此次执行，个人文件中的设置优先；永久选项写入 local.zsh |
| `XDG_*_HOME` | 与运行时相同的绝对路径规则，分别控制配置/状态/依赖/缓存 |

新安装与升级会依次进行：目标检查、基础包准备、源码 clone/pull、读取个人选项、配置档包准备、插件 install/verify、可选迁移预览、追加 source 行。源码/依赖中有本地改动时拒绝覆盖；源码脏检查在任何包操作之前。非空非 Git 目录或 origin 不符也会拒绝。个人文件和旧 cache 内容不会由安装器复制、移动或清理。

已有启动文件需要追加时，先生成同目录 `<启动文件>.omz-backup.XXXXXXXX` 内容备份，权限为 600。原文件没有末尾换行也能正确分隔；source 行已存在则不写文件、不再备份。自定义路径中的空格、美元符号、反引号、引号及反斜线按字面引用。安装器不会替换其他位置的旧 source 行，更换目标时需人工核对已有入口。

源码 pull、系统包更新和插件安装不是整体事务。插件失败时不追加启动入口，旧加载缓存保留，但源码可能已更新；缓存签名不匹配时新 Shell 降级并提示修复。已有 source 行仍指向原目标，不应将这种保护理解成源码自动回滚。修复包/网络/固定提交后重新安装；需要恢复时在独立目录取回此前源码，比较个人文件后切换入口，并在最终路径重建匹配的插件缓存。不要用旧状态覆盖新历史。

`doctor.zsh` 只报告有效配置、路径、跳转后端与旧库决定、工具位置、fzf 门槛、静态文件签名和图像降级；不下载、不创建状态。完整 Git/SHA 检查仍由 `manage-plugins.zsh verify` 完成。安装过程不会自动调用任何迁移 `--apply`，也不自动切换登录 Shell。

| 平台/场景 | 本轮证据 | 仍未验收 |
| --- | --- | --- |
| 本机 macOS arm64 | `/bin/sh` 完整隔离安装、重复执行、快进升级；三档；真实固定依赖、本地 Git 上游；运行时与 PTY 回归 | 日常安装切换、真实数据导入、图像人工体验 |
| Debian/Ubuntu | apt 包名和降级命令模拟；CI 工作流已配置 Ubuntu | 新一轮远程 CI、Linux 包管理器实际安装及首次启动 |
| Arch | 验证请求完整升级而非单独刷新数据库 | 真机完整安装/升级 |
| OpenWrt | apk/opkg 两条基础安装命令模拟；minimal 不装增强依赖 | 真机的包可用性、首次启动、后续启动和资源体验 |
| Intel Mac / SSH / tmux | 通用配置与降级逻辑覆盖；保留先前隔离验证 | Intel Mac 实机、远端人工体验和图片透传 |

旧 vendored 插件和图片实现已在 M2–M4 删除；M5 移除无消费者的 `cache/holder`，保留 cache 忽略规则保护旧安装中的用户数据。许可证与历史验收记录继续保留。测试与下载样本只存在临时目录，依赖缓存和用户状态不属于项目临时文件，不会清除。

## 回滚准备

已完成两类演练：归档文件恢复到临时目录并逐字节校验，以及从 Git bundle 恢复基线仓库。原始文件没有被恢复演练覆盖。

后续阶段回滚时，先把 bundle clone 到独立目录，再按备份 manifest 的路径映射取出需要的文件进行比较；确认 `.zshrc` 或个人配置没有新编辑后，再选择性恢复。不得整包覆盖用户目录，不得删除新增历史或跳转记录，不使用 `reset --hard`。

M1 回滚可先切回该阶段之前的源码，再从本次迁移备份的 manifest 定位所需文件，逐项比较后恢复。不要整包覆盖用户目录，不要删除 XDG 下新增的历史或个人配置。本次未切换日常 Shell、未执行真实迁移，因此没有需要恢复的真实状态；完整迁移与后端回滚仍需随后阶段验收。

M2 回滚可从 M0 快照或 Git 基线在独立目录取回三个内嵌插件及旧加载入口，或者恢复目标版本的清单/引导文件后重新 `install`。外部插件目录属于依赖，不是用户历史；普通项目清理不删除它们，也不删除新产生的 XDG 状态。

M3 需要恢复旧跳转体验时，在个人配置明确设 `OMZ_JUMP=zlua`，重新 `install`/`build` 并打开新 Shell；旧数据库仍在，zoxide 新记录也保留。若要撤销一次真实导入，先比较导入备份后的新增记录，再人工合并，不能直接用备份覆盖活跃数据库。旧内嵌 z.lua 可从 M0 备份或 Git 基线恢复到独立目录。

M4 旧 extract 和图片脚本仍可从 Git 基线或 M0 快照取回到独立目录比较；若确需回退，配套恢复该阶段的加载入口。回滚不删除已解压文件、原压缩包、新增状态或包管理器依赖。
