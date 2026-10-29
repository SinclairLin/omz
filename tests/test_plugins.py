#!/usr/bin/env python3
"""Verify real Antidote pins, offline operation, stale caches, and safe failure."""

import fcntl
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest

sys.dont_write_bytecode = True
from plugin_support import copy_dependencies, dependency_seed, isolated_env, modern_fzf_available


ROOT = Path(__file__).resolve().parent.parent


class PluginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="omz-plugins-seed-")
        cls.directory = Path(cls.temporary.name)
        cls.root = cls.directory / "source with spaces"
        shutil.copytree(ROOT, cls.root, ignore=shutil.ignore_patterns(
            ".git", "cache", "__pycache__", "env-self.zsh"))
        cls.seed = dependency_seed(ROOT, cls.directory / "seed")

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="omz-plugin-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.env = isolated_env(self.directory)
        self.data = copy_dependencies(self.seed, self.env)
        self.cache = Path(self.env["XDG_CACHE_HOME"]) / "omz"
        self.static = self.cache / "plugins.zsh"
        self.manager = self.root / "scripts/manage-plugins.zsh"

    def run_command(self, argv, expected=0):
        result = subprocess.run(argv, env=self.env, cwd=self.env["HOME"],
                                capture_output=True, text=True, timeout=60)
        if expected == 0:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def manage(self, operation, expected=0):
        return self.run_command(["zsh", "-df", str(self.manager), operation], expected)

    def startup(self, code="", prelude=""):
        return self.run_command([
            "zsh", "-dfi", "-c", prelude + '\nsource "$1/omz.zsh" || exit\n' + code,
            "--", str(self.root)])

    def local(self, text):
        config = Path(self.env["XDG_CONFIG_HOME"]) / "omz"
        config.mkdir(parents=True, exist_ok=True)
        (config / "local.zsh").write_text(text)

    def prohibit_network_commands(self):
        binaries = self.directory / "guard"
        binaries.mkdir()
        log = self.directory / "forbidden.log"
        git = shutil.which("git")
        (binaries / "git").write_text(
            '#!/bin/sh\ncase " $* " in\n'
            '  *" clone "*|*" fetch "*|*" pull "*|*" ls-remote "*)\n'
            '    printf "%s\\n" "$*" >> "$OMZ_FORBIDDEN_LOG"; exit 97;;\nesac\n'
            'exec "' + git + '" "$@"\n')
        for name in ("curl", "wget", "antidote"):
            (binaries / name).write_text(
                '#!/bin/sh\nprintf "%s\\n" "$0 $*" >> "$OMZ_FORBIDDEN_LOG"\nexit 97\n')
        for path in binaries.iterdir():
            path.chmod(0o755)
        self.env["PATH"] = str(binaries) + os.pathsep + self.env["PATH"]
        self.env["OMZ_FORBIDDEN_LOG"] = str(log)
        # env.zsh adds Homebrew paths; a local override keeps guards first.
        self.local('path=("$OMZ_GUARD_BIN" $path)\n')
        self.env["OMZ_GUARD_BIN"] = str(binaries)
        return log

    def test_install_from_local_upstreams_and_idempotence(self):
        shutil.rmtree(self.data)
        repositories = {
            "mattmc3/antidote": self.seed / "antidote",
            "Aloxaf/fzf-tab": self.seed / "plugins/github.com/Aloxaf/fzf-tab",
            "zsh-users/zsh-autosuggestions":
                self.seed / "plugins/github.com/zsh-users/zsh-autosuggestions",
            "zsh-users/zsh-syntax-highlighting":
                self.seed / "plugins/github.com/zsh-users/zsh-syntax-highlighting",
            "skywind3000/z.lua": self.seed / "plugins/github.com/skywind3000/z.lua",
        }
        self.env["GIT_CONFIG_COUNT"] = str(len(repositories))
        self.env["GIT_ALLOW_PROTOCOL"] = "file"
        for index, (repo, path) in enumerate(repositories.items()):
            self.env["GIT_CONFIG_KEY_" + str(index)] = "url." + path.as_uri() + ".insteadOf"
            self.env["GIT_CONFIG_VALUE_" + str(index)] = (
                "https://github.com/" + repo + (".git" if repo == "mattmc3/antidote" else ""))
        self.manage("install")
        first = self.static.read_bytes()
        self.manage("verify")
        self.manage("install")
        self.assertEqual(first, self.static.read_bytes())
        self.assertEqual(self.static.stat().st_mode & 0o777, 0o600)
        self.assertFalse(list(self.cache.glob(".plugins.*")))
        self.assertFalse(list(self.data.glob(".antidote.*")))

    def test_offline_build_verify_and_static_startup(self):
        log = self.prohibit_network_commands()
        self.manage("build")
        self.manage("verify")
        shutil.rmtree(self.data / "antidote")
        result = self.startup("""
(( $+functions[_zsh_highlight] && $+functions[_zsh_autosuggest_start] )) || exit 1
if _omz_fzf_available; then
  [[ $(bindkey '^I') == *fzf-tab-complete ]] || exit 2
fi
""", prelude="""
git() { print -u2 -- 'startup invoked git'; return 97 }
antidote() { print -u2 -- 'startup invoked antidote'; return 97 }
""")
        self.assertEqual(result.stderr, "")
        self.assertFalse(log.exists())

    def test_optional_probes_in_local_configuration(self):
        self.local("false\nOMZ_PROFILE=server\n")
        self.manage("build")
        self.manage("verify")
        self.assertEqual(self.startup().stderr, "")

    def test_unresolved_zlua_exec_warns_without_aborting_tools(self):
        self.local("ZLUA_EXEC=omz-no-such-lua\n")
        self.assertIn("ZLUA_EXEC=omz-no-such-lua not found", self.manage("build").stderr)
        self.manage("verify")

    @unittest.skipUnless(modern_fzf_available(), "fzf >= 0.51.0 required")
    def test_fzf_change_after_build_needs_no_rebuild(self):
        old = self.directory / "old fzf"
        old.mkdir()
        (old / "fzf").write_text('#!/bin/sh\n[ "$1" = --version ] && echo 0.30.0\n')
        (old / "fzf").chmod(0o700)
        self.local('[[ -z ${OMZ_TEST_OLD_FZF:-} ]] || path=("$OMZ_TEST_OLD_FZF" $path)\n'
                   "OMZ_JUMP=none\n")
        check = """
if _omz_fzf_available; then
  (( $+functions[fzf-tab-complete] )) || exit 1
else
  (( ! $+functions[fzf-tab-complete] )) || exit 2
fi
(( $+functions[_zsh_highlight] && $+functions[_zsh_autosuggest_start] )) || exit 3
"""
        for build_old, start_old in ((True, False), (False, True)):
            with self.subTest(build_old=build_old):
                self.env["OMZ_TEST_OLD_FZF"] = str(old) if build_old else ""
                self.manage("build")
                self.env["OMZ_TEST_OLD_FZF"] = str(old) if start_old else ""
                self.assertNotIn("stale", self.startup(check).stderr)

    def test_missing_cache_degrades_once_without_installing(self):
        log = self.prohibit_network_commands()
        result = self.startup("""
source "$1/omz.zsh"
(( ! $+functions[_zsh_highlight] && $+functions[compdef] )) || exit 1
""")
        self.assertEqual(result.stderr.count("plugins unavailable or stale"), 1)
        self.assertFalse(self.static.exists())
        self.assertFalse(log.exists())

    def test_missing_dependency_does_not_partially_load_plugins(self):
        self.manage("build")
        shutil.rmtree(self.data / "plugins/github.com/zsh-users/zsh-syntax-highlighting")
        result = self.startup("""
(( ! $+functions[_zsh_highlight] && ! $+functions[_zsh_autosuggest_start] )) || exit 1
[[ $(bindkey '^I') != *fzf-tab-complete ]] || exit 2
""")
        self.assertEqual(result.stderr.count("plugins unavailable or stale"), 1)
        self.assertNotIn("no such file", result.stderr)
        self.manage("build", expected=1)

    def test_profile_and_disabled_changes_require_rebuild(self):
        self.manage("build")
        self.env["OMZ_PROFILE"] = "server"
        self.assertIn("plugins unavailable or stale", self.startup().stderr)
        self.manage("verify", expected=1)
        self.manage("build")
        self.assertEqual(self.startup().stderr, "")
        self.local("OMZ_DISABLED_PLUGINS=(zsh-autosuggestions)\n")
        self.assertIn("plugins unavailable or stale", self.startup().stderr)
        self.manage("build")
        self.assertEqual(self.startup("""
(( ! $+functions[_zsh_autosuggest_start] && $+functions[_zsh_highlight] )) || exit 1
""").stderr, "")

    def test_manifest_or_bootstrap_change_invalidates_cache(self):
        checkout = self.directory / "another checkout"
        shutil.copytree(self.root, checkout)
        self.root = checkout
        self.manager = checkout / "scripts/manage-plugins.zsh"
        self.manage("build")
        for name in ("config/plugins.txt", "config/bootstrap.zsh"):
            path = checkout / name
            original = path.read_text()
            path.write_text(original + "# changed\n")
            self.assertIn("plugins unavailable or stale", self.startup().stderr)
            path.write_text(original)
        manifest = checkout / "config/plugins.txt"
        manifest.write_text(manifest.read_text().replace("pin:", "pin:bad", 1))
        self.assertIn("invalid or duplicate", self.manage("build", expected=1).stderr)

    def test_moved_repository_data_and_cache_require_rebuild(self):
        self.manage("build")
        other = self.directory / "moved source"
        shutil.copytree(self.root, other)
        self.root = other
        self.manager = other / "scripts/manage-plugins.zsh"
        self.assertIn("plugins unavailable or stale", self.startup().stderr)
        self.manage("build")
        destination = self.directory / "new data"
        destination.mkdir()
        shutil.move(str(self.data), destination / "omz")
        self.env["XDG_DATA_HOME"] = str(destination)
        self.assertIn("plugins unavailable or stale", self.startup().stderr)
        self.manage("build")
        destination = self.directory / "new cache"
        destination.mkdir()
        shutil.move(str(self.cache), destination / "omz")
        self.env["XDG_CACHE_HOME"] = str(destination)
        self.assertIn("plugins unavailable or stale", self.startup().stderr)
        self.manage("build")
        self.assertEqual(self.startup().stderr, "")

    def test_commit_mismatch_and_dirty_checkout_preserve_static_file(self):
        self.manage("build")
        original = self.static.read_bytes()
        repo = self.data / "plugins/github.com/zsh-users/zsh-autosuggestions"
        self.run_command(["git", "-C", str(repo), "-c", "user.name=Test", "-c",
                          "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
                          "commit", "--allow-empty", "-qm", "Wrong HEAD"])
        self.assertIn("commit mismatch", self.manage("verify", expected=1).stderr)
        log = self.prohibit_network_commands()
        self.manage("build", expected=1)
        self.assertFalse(log.exists())
        self.assertEqual(self.static.read_bytes(), original)
        (repo / "user-file").write_text("preserve me")
        self.assertIn("local changes", self.manage("install", expected=1).stderr)
        self.assertEqual((repo / "user-file").read_text(), "preserve me")
        self.assertEqual(self.static.read_bytes(), original)

    def test_failed_install_leaves_previous_cache_and_cleans_temporary_files(self):
        self.manage("build")
        original = self.static.read_bytes()
        shutil.rmtree(self.data / "antidote")
        self.env["GIT_ALLOW_PROTOCOL"] = ""
        self.manage("install", expected=1)
        self.assertEqual(self.static.read_bytes(), original)
        self.assertFalse(list(self.data.glob(".antidote.*")))
        self.assertFalse(list(self.cache.glob(".plugins.*")))

    def test_failed_antidote_bundle_preserves_previous_static_file(self):
        self.manage("build")
        original = self.static.read_bytes()
        checkout = self.directory / "broken pin checkout"
        shutil.copytree(self.root, checkout)
        self.manager = checkout / "scripts/manage-plugins.zsh"
        manifest = checkout / "config/plugins.txt"
        manifest.write_text(manifest.read_text().replace(
            "e52ee8ca55bcc56a17c828767a3f98f22a68d4eb", "0" * 40))
        self.env["GIT_ALLOW_PROTOCOL"] = ""
        self.manage("install", expected=1)
        self.assertEqual(self.static.read_bytes(), original)
        self.assertFalse(list(self.cache.glob(".plugins.*")))

    def test_minimal_and_all_disabled_require_no_antidote(self):
        shutil.rmtree(self.data)
        self.env["OMZ_PROFILE"] = "minimal"
        self.env["GIT_ALLOW_PROTOCOL"] = ""
        self.manage("install")
        self.manage("verify")
        self.assertFalse((self.data / "antidote").exists())
        self.assertEqual(self.startup().stderr, "")
        self.env["OMZ_PROFILE"] = "desktop"
        self.local("OMZ_DISABLED_PLUGINS=(fzf-tab zsh-autosuggestions zsh-syntax-highlighting)\n")
        self.manage("build")
        self.assertEqual(self.startup().stderr, "")
        self.assertFalse((self.data / "antidote").exists())

    def test_concurrent_operation_is_rejected(self):
        self.data.mkdir(exist_ok=True)
        with (self.data / ".plugins.lock").open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertIn("another plugin operation", self.manage("build", expected=1).stderr)

    @unittest.skipUnless(modern_fzf_available(), "fzf >= 0.51.0 required for terminal selection")
    def test_real_terminal_completion_suggestion_and_highlighting(self):
        self.local("OMZ_JUMP=none\n_OMZ_APPLY_PRECMD_TITLE_HOOK=false\n")
        self.manage("build")
        home = Path(self.env["HOME"])
        for name in ("omz_choice_alpha", "omz_choice_beta"):
            (home / name).write_text("terminal fixture\n")
        zdot = Path(self.env["ZDOTDIR"])
        zdot.mkdir()
        (zdot / ".zshrc").write_text(
            'source "$OMZ_PTY_ROOT/omz.zsh"\n'
            "PROMPT='OMZ_PTY> '\nRPROMPT=''\n"
            "print -s 'print -r -- OMZ_SUGGEST_ACCEPTED'\n")
        self.env["OMZ_PTY_ROOT"] = str(self.root)
        pid, master = pty.fork()
        if pid == 0:
            os.chdir(home)
            os.execvpe("zsh", ["zsh", "-di"], self.env)
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 120, 0, 0))
        pending = b""

        def expect(needle):
            nonlocal pending
            deadline = time.monotonic() + 12
            while needle not in pending:
                remaining = deadline - time.monotonic()
                self.assertGreater(remaining, 0, repr(pending[-4000:]))
                if select.select([master], [], [], remaining)[0]:
                    chunk = os.read(master, 65536)
                    self.assertTrue(chunk, repr(pending))
                    pending += chunk
            before, pending = pending.split(needle, 1)
            return before

        try:
            expect(b"OMZ_PTY> ")
            os.write(master, b"print -r -- OMZ_SUGG")
            expect(b"EST_ACCEPTED")
            os.write(master, b"\x1b[C\r")
            expect(b"\r\nOMZ_SUGGEST_ACCEPTED\r\n")
            expect(b"OMZ_PTY> ")
            os.write(master, b"omz_no_such_command")
            expect(b"\x1b[31m")
            os.write(master, b"\x15")
            os.write(master, b"print -r -- ./omz_choice_\t")
            expect(b"beta")
            os.write(master, b"beta")
            expect(b"1/2")
            os.write(master, b"\r")
            # fzf returns to ZLE; Enter then executes the completed command.
            expect(b"OMZ_PTY> ")
            os.write(master, b"\r")
            expect(b"\r\n./omz_choice_beta\r\n")
        finally:
            os.close(master)
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)


if __name__ == "__main__":
    unittest.main()
