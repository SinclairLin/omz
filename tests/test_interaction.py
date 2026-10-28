#!/usr/bin/env python3
"""M3 backend selection, migration safety, and actual ZLE interactions."""

import fcntl
import json
import os
from pathlib import Path
import pty
import select
import shlex
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
FZF = shutil.which("fzf")
ZOXIDE = shutil.which("zoxide")
MODERN_FZF = modern_fzf_available()
IMPORT_AVAILABLE = ZOXIDE and "z.lua" in subprocess.check_output(
    [ZOXIDE, "import", "--help"], text=True)


class Terminal:
    def __init__(self, env, directory):
        self.pending = b""
        self.pid, self.master = pty.fork()
        if self.pid == 0:
            os.chdir(directory)
            os.execvpe("zsh", ["zsh", "-di"], env)
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 120, 0, 0))

    def send(self, value):
        os.write(self.master, value)

    def expect(self, needle):
        deadline = time.monotonic() + 12
        while needle not in self.pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AssertionError("Missing {!r} in {!r}".format(needle, self.pending[-4000:]))
            if select.select([self.master], [], [], remaining)[0]:
                self.pending += os.read(self.master, 65536)
        before, self.pending = self.pending.split(needle, 1)
        return before

    def close(self):
        os.close(self.master)
        try:
            os.kill(self.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.waitpid(self.pid, 0)


class InteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="omz-m3-seed-")
        cls.seed = dependency_seed(ROOT, Path(cls.temporary.name) / "seed")

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="omz-m3-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.env = isolated_env(self.directory)
        self.env["_ZO_DATA_DIR"] = str(self.directory / "zoxide data")
        self.data = copy_dependencies(self.seed, self.env)
        self.home = Path(self.env["HOME"])
        self.state = Path(self.env["XDG_STATE_HOME"]) / "omz"

    def run_command(self, argv, expected=0):
        result = subprocess.run(argv, env=self.env, cwd=self.home,
                                capture_output=True, text=True, timeout=30)
        if expected == 0:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def build(self):
        return self.run_command(["zsh", "-df", str(ROOT / "scripts/manage-plugins.zsh"), "build"])

    def shell(self, code):
        self.build()
        return self.run_command(["zsh", "-dfi", "-c",
                                 'source "$1/omz.zsh"\n' + code, "--", str(ROOT)])

    def local(self, code):
        config = Path(self.env["XDG_CONFIG_HOME"]) / "omz"
        config.mkdir(parents=True, exist_ok=True)
        (config / "local.zsh").write_text(code)

    def terminal(self, setup=""):
        self.build()
        zdot = Path(self.env["ZDOTDIR"])
        zdot.mkdir(parents=True)
        (zdot / ".zshrc").write_text(
            'source "$OMZ_PTY_ROOT/omz.zsh"\n'
            "PROMPT='M3_READY> '\nRPROMPT=''\n" + setup)
        self.env["OMZ_PTY_ROOT"] = str(ROOT)
        terminal = Terminal(self.env, self.home)
        self.addCleanup(terminal.close)
        terminal.expect(b"M3_READY> ")
        return terminal

    @unittest.skipUnless(ZOXIDE, "zoxide required")
    def test_zoxide_default_aliases_and_single_hook(self):
        result = self.shell("""
[[ $_OMZ_JUMP_BACKEND == zoxide && $aliases[zz] == zi && $aliases[zf] == zi ]] || exit 1
(( $+functions[z] && $+functions[zi] && ! $+functions[_zlua] )) || exit 2
hooks=(${(M)chpwd_functions:#__zoxide_hook})
(( $#hooks == 1 )) || exit 3
(( ! ${+aliases[zb]} && ! ${+aliases[zc]} )) || exit 4
source "$1/omz.zsh"
hooks=(${(M)chpwd_functions:#__zoxide_hook})
(( $#hooks == 1 )) || exit 5
""")
        self.assertEqual(result.stderr, "")

    def test_zlua_compatibility_uses_external_source_and_custom_settings(self):
        source = self.home / "custom 跳转.data"
        destination = self.home / "legacy_target"
        destination.mkdir()
        source.write_text(str(destination) + "|10|" + str(int(time.time())) + "\n")
        self.local("OMZ_JUMP=zlua\n_ZL_DATA=" + "'" + str(source) + "'\n_ZL_CMD=j\n")
        result = self.shell("""
[[ $_OMZ_JUMP_BACKEND == zlua && $aliases[j] == _zlua &&
   $aliases[zc] == 'j -c' && $aliases[zbf] == 'j -b -I' ]] || exit 1
(( $+functions[_zlua] && ! $+functions[__zoxide_hook] )) || exit 2
[[ ${ZLUA_SCRIPT:A} == "${OMZ_DATA_DIR:A}/plugins/github.com/skywind3000/z.lua/z.lua" ]] || exit 3
[[ $_ZL_DATA == "$HOME/custom 跳转.data" ]] || exit 4
_zlua legacy_target
[[ ${PWD:A} == "${HOME:A}/legacy_target" ]] || exit 5
""")
        self.assertEqual(result.stderr, "")

    @unittest.skipUnless(ZOXIDE, "zoxide required")
    def test_legacy_data_blocks_switch_until_explicit_decision(self):
        (self.home / ".zlua").write_text(str(self.home) + "|10|1700000000\n")
        result = self.shell("""
[[ $_OMZ_JUMP_BACKEND == zlua ]] || exit 1
(( ! $+functions[__zoxide_hook] && $+functions[_zlua] )) || exit 2
""")
        self.assertIn("legacy jump data awaits a decision", result.stderr)
        self.env["OMZ_JUMP"] = "zoxide"
        self.assertIn("legacy jump data", self.shell(
            '[[ $_OMZ_JUMP_BACKEND == none ]] || exit 1').stderr)
        self.run_command(["zsh", "-df", str(ROOT / "scripts/migrate-jump.zsh"),
                          "--skip-import", "--apply", "--old-sessions-closed"])
        self.assertEqual(self.shell('[[ $_OMZ_JUMP_BACKEND == zoxide ]] || exit 1').stderr, "")

    def test_old_fzf_falls_back_without_sourcing_or_loading_fzf_tab(self):
        binaries = self.directory / "bin"
        binaries.mkdir()
        fake = binaries / "fzf"
        fake.write_text('#!/bin/sh\n[ "$1" = --version ] && { echo "0.30.0"; exit 0; }\nexit 91\n')
        fake.chmod(0o700)
        self.local("path=('" + str(binaries) + "' $path)\nOMZ_HISTORY_SEARCH=fzf\n")
        result = self.shell("""
[[ $(bindkey '^R') == *history-incremental-search-backward &&
   $(bindkey '^I') != *fzf-tab-complete ]] || exit 1
(( ! $+functions[fzf-history-widget] )) || exit 2
if [[ $_OMZ_JUMP_BACKEND == zoxide ]]; then
  zi 2>"$HOME/zi-error"
  [[ $? == 127 && $(<"$HOME/zi-error") == *'requires fzf >= 0.51.0'* ]] || exit 3
fi
""")
        self.assertIn("requires fzf >= 0.51.0", result.stderr)

    @unittest.skipUnless(MODERN_FZF, "fzf >= 0.51.0 required")
    def test_real_ctrl_r_cancel_selection_and_multiline_history(self):
        self.env["OMZ_JUMP"] = "none"
        terminal = self.terminal(
            "print -s 'print -r -- M3_HISTORY_SELECTED'\n"
            "print -s $'print -r -- M3_MULTI_ONE\\nprint -r -- M3_MULTI_TWO'\n"
            "m3_buffer() { print -rn -- \"$BUFFER\" > \"$HOME/captured-buffer\"; }\n"
            "zle -N m3_buffer\nbindkey '^Xb' m3_buffer\n")
        terminal.send(b"print -r -- CANCEL_KEEP\x12")
        terminal.expect(b"0/2")
        terminal.send(b"\x1b")
        terminal.expect(b"M3_READY> ")
        terminal.send(b"\x18b")
        deadline = time.monotonic() + 5
        capture = self.home / "captured-buffer"
        while not capture.exists() and time.monotonic() < deadline:
            select.select([], [], [], 0.01)
        self.assertEqual(capture.read_bytes(), b"print -r -- CANCEL_KEEP")
        terminal.send(b"\x15M3_HISTORY_SELECTED\x12")
        terminal.expect(b"1/2")
        terminal.send(b"\r")
        terminal.expect(b"M3_READY> ")
        terminal.send(b"\r")
        terminal.expect(b"\r\nM3_HISTORY_SELECTED\r\n")
        terminal.expect(b"M3_READY> ")
        terminal.send(b"M3_MULTI_ONE\x12")
        terminal.expect(b"1/")
        terminal.send(b"\r")
        terminal.expect(b"M3_READY> ")
        terminal.send(b"\r")
        terminal.expect(b"\r\nM3_MULTI_ONE\r\nM3_MULTI_TWO\r\n")

    @unittest.skipUnless(MODERN_FZF, "fzf >= 0.51.0 required")
    def test_history_keeps_native_tab_when_fzf_tab_disabled(self):
        binaries = self.directory / "bin"
        binaries.mkdir()
        wrapper = binaries / "fzf"
        wrapper.write_text(
            '#!/bin/sh\n[ "$1" != --zsh ] || touch "$HOME/used-official-fallback"\n'
            'exec ' + shlex.quote(FZF) + ' "$@"\n')
        wrapper.chmod(0o700)
        self.local("OMZ_JUMP=none\nOMZ_DISABLED_PLUGINS=(fzf-tab)\n"
                   "path=(" + shlex.quote(str(binaries)) + " $path)\n")
        terminal = self.terminal()
        self.assertTrue((self.home / "used-official-fallback").exists())
        terminal.send(b"bindkey '^I'; bindkey '^R'\r")
        terminal.expect(b'"^I" expand-or-complete')
        terminal.expect(b'"^R" fzf-history-widget')
        terminal.expect(b"M3_READY> ")
        terminal.send(b'before=$(bindkey -L); source "$OMZ_PTY_ROOT/omz.zsh"; '
                      b'[[ $before == "$(bindkey -L)" ]] && print M3_REPEAT_KEYS_OK\r')
        terminal.expect(b"\r\nM3_REPEAT_KEYS_OK\r\n")

    @unittest.skipUnless(ZOXIDE and MODERN_FZF, "zoxide and modern fzf required")
    def test_real_zoxide_jump_and_interactive_alias(self):
        target = self.home / "目录 with spaces"
        target.mkdir()
        self.run_command([ZOXIDE, "add", str(target)])
        terminal = self.terminal()
        terminal.send(b"z spaces; print -r -- M3_CWD:$PWD\r")
        terminal.expect(("M3_CWD:" + str(target)).encode())
        terminal.expect(b"M3_READY> ")
        terminal.send(b"cd; zz spaces\r")
        terminal.expect(str(target).encode())
        terminal.send(b"\r")
        terminal.expect(b"M3_READY> ")
        terminal.send(b"print -r -- M3_INTERACTIVE:$PWD\r")
        terminal.expect(("M3_INTERACTIVE:" + str(target)).encode())


class JumpMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="omz-jump-migration-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.env = isolated_env(self.directory)
        self.env["_ZO_DATA_DIR"] = str(self.directory / "zoxide data")
        self.home = Path(self.env["HOME"])
        self.source = self.home / "custom 跳转.db"
        self.env["_ZL_DATA"] = str(self.source)
        self.source.write_text(str(self.home) + "|10|1700000000\n")
        self.state = Path(self.env["XDG_STATE_HOME"]) / "omz"
        self.record = self.state / "migrations/jump-v1.json"
        self.decision = self.state / "migrations/jump-v1"
        self.target = Path(self.env["_ZO_DATA_DIR"]) / "db.zo"

    def migrate(self, *args, expected=0):
        result = subprocess.run(["zsh", "-df", str(ROOT / "scripts/migrate-jump.zsh"), *args],
                                env=self.env, capture_output=True, text=True, timeout=30)
        if expected == 0:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_preview_is_read_only_and_apply_requires_closed_sessions(self):
        self.assertIn(str(self.source), self.migrate().stdout)
        self.assertFalse(self.state.exists())
        self.assertFalse(self.target.exists())
        self.migrate("--apply", expected=1)
        self.assertFalse(self.state.exists())

    def test_explicit_skip_backs_up_and_preserves_both_databases(self):
        self.target.parent.mkdir()
        self.target.write_bytes(b"existing database")
        self.migrate("--apply", "--skip-import", "--old-sessions-closed")
        self.assertEqual(self.target.read_bytes(), b"existing database")
        self.assertEqual(self.decision.read_text(), str(self.source) + "\n")
        record = json.loads(self.record.read_text())
        self.assertEqual((Path(record["backup"]) / "zlua.data").read_bytes(), self.source.read_bytes())
        self.assertEqual((Path(record["backup"]) / "zoxide.db").read_bytes(), self.target.read_bytes())
        self.migrate("--apply", "--skip-import", "--old-sessions-closed")
        self.assertEqual(len(list((self.state / "backups").iterdir())), 1)
        self.assertEqual(self.record.stat().st_mode & 0o777, 0o600)

    @unittest.skipUnless(IMPORT_AVAILABLE, "zoxide import z.lua required")
    def test_import_merges_custom_database_and_preserves_later_records_on_rerun(self):
        destination = self.home / "中文 with spaces"
        destination.mkdir()
        self.source.write_text(str(destination) + "|100|1700000000\n")
        subprocess.run([ZOXIDE, "add", str(self.home)], env=self.env, check=True)
        self.migrate("--apply", "--old-sessions-closed")
        query = subprocess.check_output([ZOXIDE, "query", "--all", "--list"],
                                        env=self.env, text=True)
        self.assertIn(str(destination), query)
        self.assertIn(str(self.home), query)
        later = self.home / "later"
        later.mkdir()
        subprocess.run([ZOXIDE, "add", str(later)], env=self.env, check=True)
        before = self.target.read_bytes()
        self.migrate("--apply", "--old-sessions-closed")
        self.assertEqual(before, self.target.read_bytes())
        self.assertTrue(self.source.exists())

    def test_import_failure_has_no_decision_and_can_retry(self):
        binaries = self.directory / "bin"
        binaries.mkdir()
        fake = binaries / "zoxide"
        fake.write_text('#!/bin/sh\ncase "$*" in\n'
                        '"import --help") echo "z.lua"; exit 0;;\n'
                        '*) echo "fixture import failed" >&2; exit 7;;\nesac\n')
        fake.chmod(0o700)
        self.env["PATH"] = str(binaries) + ":" + self.env["PATH"]
        config = Path(self.env["XDG_CONFIG_HOME"]) / "omz"
        config.mkdir(parents=True)
        (config / "local.zsh").write_text("path=('" + str(binaries) + "' $path)\n")
        self.target.parent.mkdir()
        self.target.write_bytes(b"old database")
        self.migrate("--apply", "--old-sessions-closed", expected=1)
        self.assertEqual(self.target.read_bytes(), b"old database")
        self.assertFalse(self.decision.exists())
        self.assertFalse(self.record.exists())
        self.assertFalse(list(self.target.parent.glob(".omz-import-*")))
        self.migrate("--apply", "--old-sessions-closed", "--skip-import")
        self.assertTrue(self.decision.exists())

    @unittest.skipUnless(IMPORT_AVAILABLE, "zoxide import z.lua required")
    def test_interrupted_commit_recovers_without_duplicate_import(self):
        self.migrate("--apply", "--old-sessions-closed")
        before = self.target.read_bytes()
        record = json.loads(self.record.read_text())
        record["status"] = "prepared"
        self.record.write_text(json.dumps(record))
        self.decision.unlink()
        self.assertIn("Recovered verified import", self.migrate(
            "--apply", "--old-sessions-closed").stdout)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertTrue(self.decision.exists())

    def test_changed_source_and_concurrent_migration_are_rejected(self):
        self.migrate("--apply", "--old-sessions-closed", "--skip-import")
        self.source.write_text("new source\n")
        self.assertIn("Previous migration record differs", self.migrate(
            "--apply", "--old-sessions-closed", "--skip-import", expected=1).stderr)
        with (self.state / "migrations/jump-v1.lock").open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.migrate("--apply", "--old-sessions-closed", "--skip-import", expected=1)

    def test_invalid_migration_record_is_rejected_without_traceback(self):
        self.record.parent.mkdir(parents=True)
        self.record.write_text("[]")
        result = self.migrate("--apply", "--old-sessions-closed", "--skip-import", expected=1)
        self.assertIn("Invalid jump migration record", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(self.decision.exists())


if __name__ == "__main__":
    unittest.main()
