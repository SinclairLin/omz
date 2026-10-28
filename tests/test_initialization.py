#!/usr/bin/env python3
"""Exercise startup in isolated shells and paths, including a repository with spaces."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
from plugin_support import copy_dependencies, dependency_seed

ROOT = Path(__file__).resolve().parent.parent


class InitializationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checkout_tmp = tempfile.TemporaryDirectory(prefix="omz-source-")
        cls.root = Path(cls.checkout_tmp.name) / "source with spaces"
        shutil.copytree(ROOT, cls.root, ignore=shutil.ignore_patterns(
            ".git", "cache", "__pycache__", "env-self.zsh"))
        cls.seed = dependency_seed(ROOT, Path(cls.checkout_tmp.name) / "seed")

    @classmethod
    def tearDownClass(cls):
        cls.checkout_tmp.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="omz-runtime-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.home = self.directory / "home with spaces"
        self.home.mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("OMZ", "_OMZ", "XDG_", "_ZL", "_ZO", "ZLUA", "FZF_"))
                    and key not in ("HISTFILE", "ENV", "BASH_ENV")}
        self.env.update(HOME=str(self.home), ZDOTDIR=str(self.home / "zdot"),
                        TERM="xterm-256color", OMZ_TEST_ROOT=str(self.root))
        for kind in ("CONFIG", "STATE", "DATA", "CACHE"):
            self.env["XDG_" + kind + "_HOME"] = str(self.directory / (kind + " with spaces"))
        self.state = Path(self.env["XDG_STATE_HOME"]) / "omz"
        self.config = Path(self.env["XDG_CONFIG_HOME"]) / "omz"
        self.cache = Path(self.env["XDG_CACHE_HOME"]) / "omz"
        copy_dependencies(self.seed, self.env)

    def local(self, text):
        self.config.mkdir(parents=True, exist_ok=True)
        (self.config / "local.zsh").write_text(text)

    def shell(self, code="", interactive=True, expected=0):
        if interactive:
            build = subprocess.run(
                ["zsh", "-df", str(self.root / "scripts/manage-plugins.zsh"), "build"],
                env=self.env, cwd=self.home, capture_output=True, text=True, timeout=20)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
        result = subprocess.run(
            ["zsh", "-dfi" if interactive else "-df", "-c", code],
            env=self.env, cwd=self.home, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def clean_shell(self, code="", interactive=True):
        result = self.shell('source "$OMZ_TEST_ROOT/omz.zsh" || exit\n' + code, interactive)
        self.assertEqual(result.stderr, "")
        return result.stdout

    def test_noninteractive_only_environment(self):
        self.env.update(EDITOR="/chosen/editor", OMZ_PROFILE="minimal",
                        OMZ_RESTORE_DIRECTORY="true")
        self.assertEqual(self.clean_shell("""
[[ $EDITOR == /chosen/editor && $OMZ_PROFILE == minimal && $PWD == ${HOME:A} ]] || exit 1
(( ! $+functions[compdef] && ! $+functions[historybyfzf] &&
   ! $+functions[_zsh_highlight] && ! $+functions[randport] )) || exit 2
[[ -z ${HISTFILE:-} && -z ${_OMZ_INTERACTIVE_INITIALIZED:-} ]] || exit 3
""", interactive=False), "")
        for kind in ("CONFIG", "STATE", "CACHE"):
            self.assertFalse(Path(self.env["XDG_" + kind + "_HOME"]).exists())

    def test_local_overrides_before_interactive_setup_and_only_once(self):
        self.local("""
(( ${+functions[compdef]} )) && return 9
(( OMZ_TEST_READS += 1 ))
OMZ_PROFILE=minimal
OMZ_HISTORY_SEARCH=native
_OMZ_APPLY_PRECMD_TITLE_HOOK=false
EDITOR=/local/editor
""")
        self.assertEqual(self.clean_shell("""
source "$OMZ_TEST_ROOT/omz.zsh"
[[ $EDITOR == /local/editor && $OMZ_PROFILE == minimal && $OMZ_TEST_READS == 1 ]] || exit 1
(( ${precmd_functions[(Ie)precmd_title_hook]:-0} == 0 )) || exit 2
bindkey '^R'
"""), '"^R" history-incremental-search-backward\n')

    def test_legacy_configuration_fallback_and_new_file_priority(self):
        # Use a per-test checkout so a private legacy fixture cannot leak to other tests.
        legacy_root = self.directory / "legacy checkout"
        shutil.copytree(self.root, legacy_root)
        (legacy_root / "config/env-self.zsh").write_text(
            "EDITOR=/legacy/editor\nOMZ_PROFILE=minimal\n"
            "_OMZ_APPLY_HISTORYBYFZF=false\n_OMZ_APPLY_CHPWD_HOOK=true\n")
        self.env["OMZ_TEST_ROOT"] = str(legacy_root)
        self.clean_shell("""
[[ $EDITOR == /legacy/editor && $OMZ_HISTORY_SEARCH == native &&
   $OMZ_RESTORE_DIRECTORY == true ]] || exit 1
""")
        self.local("EDITOR=/new/editor\nOMZ_PROFILE=minimal\n"
                   "OMZ_RESTORE_DIRECTORY=false\nOMZ_HISTORY_SEARCH=auto\n")
        self.env["_OMZ_APPLY_CHPWD_HOOK"] = "true"
        self.env["_OMZ_APPLY_HISTORYBYFZF"] = "false"
        self.clean_shell("""
[[ $EDITOR == /new/editor && $OMZ_RESTORE_DIRECTORY == false &&
   $OMZ_HISTORY_SEARCH == auto ]] || exit 1
""")

    def test_profiles_and_plugin_order_bindings(self):
        for profile in ("desktop", "server", "minimal"):
            with self.subTest(profile=profile):
                self.env["OMZ_PROFILE"] = profile
                self.clean_shell("""
(( $+functions[compdef] && $+functions[randport] && $+functions[dcupdate] )) || exit 1
if (( $+commands[ouch] )); then
  (( $+functions[extract] && $+aliases[x] )) || exit 7
else
  (( ! $+functions[extract] && ! $+aliases[x] )) || exit 8
fi
if [[ $OMZ_PROFILE == minimal ]]; then
  (( ! $+functions[_zlua] && ! $+functions[_zsh_highlight] &&
     ! $+functions[_zsh_autosuggest_start] && ! $+functions[historybyfzf] )) || exit 2
  [[ $(bindkey '^R') == *history-incremental-search-backward ]] || exit 3
else
  (( $+functions[_zsh_highlight] && $+functions[_zsh_autosuggest_start] )) || exit 4
  if _omz_fzf_available; then
    [[ $(bindkey '^I') == *fzf-tab-complete &&
       $(bindkey '^R') == *history-incremental-search-backward ]] || exit 5
  fi
fi
[[ $OMZ_PROFILE == desktop || $OMZ_IMAGE_PREVIEW == off ]] || exit 6
""")

    def test_auto_profile_detection(self):
        for ostype, profile in (("darwin24.0", "desktop"),
                                ("linux-gnu", "server"), ("linux-openwrt", "minimal")):
            with self.subTest(ostype=ostype):
                self.assertEqual(self.shell(
                    'OSTYPE=' + ostype + '\nsource "$OMZ_TEST_ROOT/omz.zsh"\n'
                    'print -r -- "$OMZ_PROFILE"', interactive=False).stdout, profile + "\n")

    def test_repeat_source_preserves_hooks_widgets_bindings_and_options(self):
        self.env.update(OMZ_RESTORE_DIRECTORY="true", _OMZ_APPLY_PREEXEC_HOOK="true")
        self.clean_shell("""
before_hooks="${precmd_functions[*]}|${chpwd_functions[*]}|${preexec_functions[*]}"
before_widgets="${(kv)widgets}"
before_keys=$(bindkey -L)
before_options=$FZF_DEFAULT_OPTS
source "$OMZ_TEST_ROOT/omz.zsh"
[[ $before_hooks == "${precmd_functions[*]}|${chpwd_functions[*]}|${preexec_functions[*]}" &&
   $before_widgets == "${(kv)widgets}" && $before_keys == "$(bindkey -L)" &&
   $before_options == "$FZF_DEFAULT_OPTS" ]] || exit 1
""")

    def test_external_compinit_is_reused(self):
        self.env["OMZ_PROFILE"] = "minimal"
        self.assertEqual(self.shell("""
autoload -Uz compinit
compinit -d "$HOME/external-dump"
compinit() { print -u2 -- 'compinit repeated'; return 1 }
source "$OMZ_TEST_ROOT/omz.zsh" || exit
(( $+functions[compdef] )) || exit 2
""").stderr, "")
        self.assertTrue((self.home / "external-dump").exists())
        self.assertFalse(list(self.cache.glob("zcompdump*")))

    def test_xdg_state_permissions_and_no_repository_writes(self):
        self.env["OMZ_PROFILE"] = "minimal"
        self.clean_shell("""
[[ $HISTFILE == "$OMZ_STATE_DIR/zsh_history" &&
   $ZSH_CACHE_DIR == "$OMZ_CACHE_DIR" ]] || exit 1
[[ $OMZ_RESTORE_DIRECTORY == false ]] || exit 2
""")
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.state / "zsh_history").stat().st_mode & 0o777, 0o600)
        self.assertTrue(list(self.cache.glob("zcompdump-*")))
        self.assertFalse(list(self.home.glob(".zcompdump*")))
        self.assertFalse((self.root / "cache").exists())

    def test_default_and_relative_xdg_paths(self):
        for value in ("", "relative/invalid"):
            for kind in ("CONFIG", "STATE", "DATA", "CACHE"):
                self.env["XDG_" + kind + "_HOME"] = value
            self.clean_shell("""
[[ $OMZ_STATE_DIR == "$HOME/.local/state/omz" &&
   $OMZ_CONFIG_DIR == "$HOME/.config/omz" &&
   $OMZ_DATA_DIR == "$HOME/.local/share/omz" &&
   $OMZ_CACHE_DIR == "$HOME/.cache/omz" ]] || exit 1
""", interactive=False)
        self.assertFalse((self.home / "relative").exists())

    def test_restore_directory_reads_literal_data_and_writes_private_state(self):
        destination = self.home / "目录 with spaces"
        destination.mkdir()
        self.state.mkdir(parents=True)
        (self.state / "last_directory").write_text(str(destination) + "\n")
        self.env.update(OMZ_PROFILE="minimal", OMZ_RESTORE_DIRECTORY="true")
        self.clean_shell("""
[[ $PWD == "$HOME/目录 with spaces" ]] || exit 1
cd -- "$HOME"
[[ $(<"$OMZ_STATE_DIR/last_directory") == $HOME ]] || exit 2
""")
        self.assertEqual((self.state / "last_directory").stat().st_mode & 0o777, 0o600)
        (self.state / "last_directory").write_text('$(touch "$HOME/executed")\n')
        self.clean_shell('[[ $PWD == ${HOME:A} ]] || exit 1')
        self.assertFalse((self.home / "executed").exists())

    def test_disabled_plugins_and_native_history(self):
        self.local("""
OMZ_DISABLED_PLUGINS=(fzf-tab zsh-autosuggestions zsh-syntax-highlighting)
OMZ_JUMP=none
OMZ_HISTORY_SEARCH=native
""")
        self.clean_shell("""
(( ! $+functions[_zsh_highlight] && ! $+functions[_zsh_autosuggest_start] &&
   ! $+functions[_zlua] )) || exit 1
[[ $(bindkey '^R') == *history-incremental-search-backward &&
   $(bindkey '^I') != *fzf-tab-complete ]] || exit 2
""")

    def test_missing_optional_tools(self):
        binaries = self.home / "base-bin"
        binaries.mkdir()
        for name in ("mkdir", "chmod", "touch", "ls", "grep", "head", "rm", "mv",
                     "cat", "env", "cut", "sed", "awk", "tail", "wc", "sort", "uname",
                     "git", "zsh", "mktemp"):
            executable = shutil.which(name)
            if executable:
                (binaries / name).symlink_to(executable)
        self.local('PATH="$HOME/base-bin"\nOMZ_PROFILE=server\n')
        self.clean_shell("""
(( ! $+commands[fzf] && ! $+functions[historybyfzf] && ! $+functions[_zlua] )) || exit 1
[[ $(bindkey '^R') == *history-incremental-search-backward ]] || exit 2
""")

    def test_fzf_options_preserve_user_settings_and_support_spaces(self):
        self.env["FZF_DEFAULT_OPTS"] = "--height=20 --border"
        self.env["FZF_CTRL_R_OPTS"] = "--height=18"
        self.clean_shell("""
[[ $FZF_DEFAULT_OPTS == *'--height=20 --border' ]] || exit 1
if _omz_fzf_available; then
  print -r -- sample | fzf --filter=sample >/dev/null || exit 2
  [[ $FZF_CTRL_R_OPTS == *'--height=18' ]] || exit 3
  print -r -- sample | FZF_DEFAULT_OPTS="$FZF_CTRL_R_OPTS" fzf --filter=sample >/dev/null || exit 4
  [[ -f "$OMZ_STATE_DIR/fzf_query_history" ]] || exit 5
fi
""")
        if (self.state / "fzf_query_history").exists():
            self.assertEqual((self.state / "fzf_query_history").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
