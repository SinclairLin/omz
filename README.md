English | [中文](./README.zh-CN.md)

Personal Zsh configuration with native fallbacks, a simple prompt, and pinned external plugins. Zsh 5.8+ is the enhanced-profile test target.

## Installation

```sh
curl -fsSL https://raw.githubusercontent.com/SinclairLin/omz/main/scripts/install_zsh_config.sh | sh
```

The `/bin/sh` installer installs base packages, clones or fast-forwards `~/.config/zsh`, reads your local options, prepares profile tools, and runs the plugin manager's `install` and `verify`. It appends a source line to `${ZDOTDIR:-$HOME}/.zshrc` only after these steps succeed. Existing startup content is preserved and backed up before an append. It never changes your login shell or imports user data.

On macOS, install [Homebrew](https://brew.sh/) and Apple's Command Line Tools first. The installer does not bootstrap either. On Arch, installation uses `pacman -Syu` and therefore performs a system upgrade; update the system yourself and use `OMZ_INSTALL_DEPS=0` to manage packages separately.

| Profile | Automatic selection | Packages requested after the base tools |
| --- | --- | --- |
| `desktop` | macOS | fd, fzf, zoxide, ouch, bat, eza |
| `server` | Other Linux | fd/fd-find, fzf, zoxide; other tools optional |
| `minimal` | OpenWrt | None; native completion/history and the simple prompt |

Lua is requested only for an explicit z.lua backend or a pending legacy database under `OMZ_JUMP=auto`. Missing optional packages produce warnings and use the runtime fallbacks. fzf 0.51.0+ enables enhanced history/completion; older versions retain native behavior. No Rust builds, upstream binary downloads, global fd symlinks, or `~/.fzf` updates are performed. Existing binaries remain usable through your PATH. Python 3 is needed for explicit migrations and development checks, not everyday startup.

For a persistent profile/backend choice, put it in `${XDG_CONFIG_HOME:-$HOME/.config}/omz/local.zsh` before installing. Preserve existing content; for example, add `OMZ_PROFILE=minimal` or `OMZ_JUMP=zlua`. This file takes precedence over the legacy `config/env-self.zsh`. Environment overrides such as `OMZ_PROFILE=minimal` affect that invocation only and are not saved by the installer.

### Manual Packages And Installation

```sh
# macOS desktop
brew install fd fzf zoxide ouch bat eza

# Debian / Ubuntu server (no fd symlink required)
sudo apt-get update
sudo apt-get install -y zsh git curl ca-certificates fd-find fzf zoxide

# Arch server; full system upgrade
sudo pacman -Syu --needed zsh git curl ca-certificates fd fzf zoxide

# OpenWrt minimal; /bin/sh works without Bash or Lua
if command -v apk >/dev/null 2>&1; then
  apk update
  apk add --no-cache zsh git git-http curl ca-bundle
else
  opkg update
  opkg install zsh git git-http curl ca-bundle
fi
```

Then use the same installer with package changes disabled; required commands must already be available:

```sh
curl -fsSL https://raw.githubusercontent.com/SinclairLin/omz/main/scripts/install_zsh_config.sh |
  OMZ_INSTALL_DEPS=0 sh
```

Custom absolute paths are supported via `TARGET_DIR` and `ZSHRC_FILE`. `REPO_URL` and `SOURCE_LINE` remain supported. `ZSHRC_FILE` defaults to the active `ZDOTDIR`; XDG variables control personal settings, state, dependencies, and cache, independently of the source checkout. See `sh scripts/install_zsh_config.sh --help` for all options.

### Upgrade, Migration And Rollback

For an existing clean installation, rerun the installer. It refuses dirty source/dependency checkouts, a nonempty non-Git target, and an origin different from `REPO_URL`. It does not stash or overwrite edits. Only a missing exact source line is appended, with a sibling `.omz-backup.*` file containing the previous startup file. Review existing equivalent/custom source lines when changing the installation path.

Source/package updates are not one transaction: a later plugin failure can leave an updated source checkout. The startup file stays unchanged; a stale or missing loader falls back to the base shell. Fix the dependency and rerun installation. Preserve a source/state backup before upgrading; restore into a separate directory and compare before selecting a rollback. Never overwrite new history with an old backup.

```sh
# From the actual installed source directory; previews do not apply changes.
zsh -df scripts/migrate-state.zsh
zsh -df scripts/migrate-jump.zsh
zsh -df scripts/doctor.zsh

# Installer option to include the state preview; requires Python 3.
sh scripts/install_zsh_config.sh --migrate-state-preview
```

A preview conflict returns nonzero and prevents a source-line append. Real history, query history, personal configuration, and jump records require a separate migration decision after old sessions have stopped writing. See the [migration and rollback guide](docs/migration.zh-CN.md).

### Plugin Ownership And Offline Startup

Antidote owns only pinned Git dependencies: fzf-tab, autosuggestions, syntax highlighting, and the selected z.lua compatibility backend. Binaries belong to the system package manager. The automatic installer prepares plugins; manual maintenance is:

```sh
zsh -df scripts/manage-plugins.zsh install
zsh -df scripts/manage-plugins.zsh verify
# Rebuild from installed pins after profile/path/disabled-plugin changes:
zsh -df scripts/manage-plugins.zsh build
```

Sources live in `${XDG_DATA_HOME:-$HOME/.local/share}/omz/`; the static loader lives in `${XDG_CACHE_HOME:-$HOME/.cache}/omz/plugins.zsh`. Moving the source checkout requires rebuilding the loader at its final path. Startup stays offline and runs no plugin manager. Changing pins requires `install`; minimal needs no Antidote downloads. Versions and licenses are in [third-party notices](docs/third-party.zh-CN.md).

## Navigation And History

Enhanced profiles prefer zoxide: `z` jumps; `zi`, `zz`, and `zf` select interactively. A nonempty legacy z.lua database keeps the compatibility backend until an explicit import or skip decision. `OMZ_JUMP=zlua` retains its old aliases and semantics. In a real terminal, Ctrl-R uses official fzf history integration while fzf-tab owns Tab. Missing tools, old fzf, and minimal profiles keep native history/completion. User fzf options are preserved.

## Validation Scope

Local macOS arm64 checks cover isolated install/reinstall/fast-forward upgrade for all three profiles, pinned plugins, offline startup, migration failures, and real PTY interaction. The CI workflow targets Ubuntu, macOS 14, and macOS latest; this work does not include a new remote CI result. Debian/Arch and OpenWrt apk/opkg package commands are simulated locally, not validated as complete installations on those systems. Intel Mac and actual Kitty/iTerm2 image placement remain unverified. Exact results and outstanding manual checks are in the [verification report](docs/verification.md). The everyday installed configuration and real user data have not been switched by repository development.

## Directory Structure

```text
config/       profiles, completion, history, jump, aliases, plugin pins
functions/    extract, randport, docker helpers
lib/          paths, capabilities, plugins, Git prompt, preview adapter
scripts/      installer, plugin manager, migrations, diagnostics, verification
tests/        isolated installation, runtime and PTY tests
docs/         migration, results and licenses
themes/       simple prompt
omz.zsh       source entry point
```

## Plugins

- `extract` / `x`: a thin project wrapper around ouch. Install `ouch` first (`brew install ouch` on macOS). Neither entry is registered without it; run `zsh -df scripts/doctor.zsh` for diagnostics.

```zsh
extract "a.tar.gz" "archive with spaces.zip"
x -r -- "-archive.zip"
```

Each input gets a sibling `<full-filename>.extracted/` directory. Existing destinations are rejected. Only a successful input is removed with `-r` / `--remove`; any failure makes the aggregate status nonzero without changing cwd. Nonempty partial output is retained for inspection. Formats depend on the installed ouch build; local 0.8.3 passed ZIP, tar.gz, gzip, bzip2, xz, 7z, RAR3 and RAR5. Special `.deb` / `.rpm` unpacking now uses native platform tools; see the [M4 migration guide](docs/migration.zh-CN.md#m4-解压预览与自有函数).

- File previews: bat → batcat → head for at most 1,000 text lines; eza → ls for at most 200 directory lines. Images use the installed official fzf-preview.sh only with matching terminal capabilities. Plain terminals, SSH, tmux, disabled images or missing dependencies show file metadata. Export `OMZ_FZF_PREVIEW_SCRIPT` to select an official script in a custom package location. Actual image placement and tmux passthrough still need manual verification.

- `randport` / `rp`: prints a currently free port in 49152–65535 without reserving it; fails if ss, lsof and netstat are unavailable.

- `dcupdate`: runs `docker compose pull && docker compose up -d`, stopping on pull failure without an unconditional down. Rebuilding services may still interrupt them.

- [z.lua](https://github.com/skywind3000/z.lua)

> Using `z <dir>` will jump to the path with the highest "Frecent" (Frequency + Recency) value among all paths.
> These examples apply to the `OMZ_JUMP=zlua` compatibility backend; zoxide has different options and ranking.

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
