#!/usr/bin/env python3
"""Check explicit migration, conflict handling, backups and interrupted-copy retry."""

import hashlib
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="omz-migration-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.legacy = self.home / ".config/zsh"
        (self.legacy / "cache").mkdir(parents=True)
        (self.legacy / "config").mkdir()
        self.state = self.root / "state with spaces/omz"
        self.config = self.root / "config with spaces/omz"
        self.jump = self.home / "custom jump database"
        self.jump.write_bytes(b"/legacy/path|2|1234\n")
        self.history = b": 1234:0;echo first\n: 1235:0;echo second\n"
        (self.legacy / "cache/zshhistory").write_bytes(self.history)
        (self.legacy / "cache/fzfhistory").write_bytes(b"query\n")
        (self.legacy / "cache/currentdir").write_bytes(b'/literal/$(not-code)\n')
        (self.legacy / "config/env-self.zsh").write_text(
            'touch "$HOME/should-not-execute"\n_ZL_DATA=/do/not/evaluate\n')
        (self.home / ".zshrc").write_text("# existing configuration\n")
        self.env = dict(os.environ, HOME=str(self.home),
                        XDG_STATE_HOME=str(self.state.parent),
                        XDG_CONFIG_HOME=str(self.config.parent),
                        _ZL_DATA=str(self.jump), ZDOTDIR=str(self.home))

    def run_migration(self, *args, expected=0):
        result = subprocess.run(["zsh", "-df", str(ROOT / "scripts/migrate-state.zsh"), *args],
                                env=self.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertFalse((self.home / "should-not-execute").exists())
        return result

    def apply(self, *args, expected=0):
        return self.run_migration("--apply", "--old-sessions-closed", *args, expected=expected)

    def test_preview_does_not_write(self):
        result = self.run_migration("--copy-local")
        self.assertIn(str(self.legacy / "cache/zshhistory"), result.stdout)
        self.assertIn(str(self.state / "zsh_history"), result.stdout)
        self.assertIn(str(self.jump), result.stdout)
        self.assertFalse(self.state.exists())
        self.assertFalse(self.config.exists())

    def test_history_requires_closed_session_assertion(self):
        result = self.run_migration("--apply", expected=1)
        self.assertIn("--old-sessions-closed", result.stderr)
        self.assertFalse(self.state.exists())

    def test_apply_backup_permissions_and_repeat(self):
        self.apply("--copy-local")
        self.assertEqual((self.state / "zsh_history").read_bytes(), self.history)
        self.assertEqual((self.legacy / "cache/zshhistory").read_bytes(), self.history)
        self.assertEqual((self.config / "local.zsh").read_bytes(),
                         (self.legacy / "config/env-self.zsh").read_bytes())
        backup = next((self.state / "backups").iterdir())
        manifest = json.loads((backup / "manifest.json").read_text())
        self.assertIn(str(self.jump), [item["source"] for item in manifest["files"]])
        self.assertIn(str(self.home / ".zshrc"), [item["source"] for item in manifest["files"]])
        for item in manifest["files"]:
            saved = backup / item["file"]
            self.assertEqual(hashlib.sha256(saved.read_bytes()).hexdigest(), item["sha256"])
            self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
        for directory in (self.state, backup, self.state / "backups", self.state / "migrations"):
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
        with (self.state / "zsh_history").open("ab") as stream:
            stream.write(b": 1236:0;new target record\n")
        result = self.apply("--copy-local")
        self.assertIn("already migrated", result.stdout)
        self.assertIn(b"new target record", (self.state / "zsh_history").read_bytes())
        self.assertEqual(len(list((self.state / "backups").iterdir())), 1)
        self.assertEqual((self.state / "zsh_history").stat().st_mode & 0o777, 0o600)

    def test_nonempty_target_stops_all_copies(self):
        self.state.mkdir(parents=True)
        (self.state / "zsh_history").write_bytes(b"existing target\n")
        self.apply(expected=1)
        self.assertEqual((self.state / "zsh_history").read_bytes(), b"existing target\n")
        self.assertFalse((self.state / "fzf_query_history").exists())
        self.assertFalse((self.state / "backups").exists())

    def test_empty_target_is_backed_up_and_populated(self):
        self.state.mkdir(parents=True)
        (self.state / "zsh_history").touch()
        self.apply()
        self.assertEqual((self.state / "zsh_history").read_bytes(), self.history)
        manifest = json.loads(next((self.state / "backups").glob("*/manifest.json")).read_text())
        entry = next(item for item in manifest["files"]
                     if item["source"] == str(self.state / "zsh_history"))
        self.assertEqual(entry["sha256"], hashlib.sha256(b"").hexdigest())

    def test_changed_legacy_history_after_migration_is_not_silently_skipped(self):
        self.apply()
        (self.legacy / "cache/zshhistory").write_bytes(self.history + b"late legacy record\n")
        result = self.apply(expected=1)
        self.assertIn("merge manually", result.stderr)
        self.assertEqual((self.state / "zsh_history").read_bytes(), self.history)

    def test_copy_local_is_opt_in(self):
        self.apply()
        self.assertFalse((self.config / "local.zsh").exists())

    def test_retry_interrupted_verified_copy(self):
        (self.state / "migrations").mkdir(parents=True)
        target = self.state / "zsh_history"
        target.write_bytes(self.history)
        source = self.legacy / "cache/zshhistory"
        marker = self.state / "migrations/state-v1.json"
        marker.write_text(json.dumps({str(source): {
            "target": str(target), "source_sha256": hashlib.sha256(self.history).hexdigest(),
            "status": "copying"}}))
        self.assertIn("resume verified copy", self.apply().stdout)
        self.assertEqual(json.loads(marker.read_text())[str(source)]["status"], "complete")

    def test_symlink_target_is_never_overwritten(self):
        other = self.home / "other-history"
        other.write_bytes(b"other records\n")
        self.state.mkdir(parents=True)
        (self.state / "zsh_history").symlink_to(other)
        self.apply(expected=1)
        self.assertEqual(other.read_bytes(), b"other records\n")

    def test_corrupt_record_fails_without_overwriting(self):
        (self.state / "migrations").mkdir(parents=True)
        (self.state / "migrations/state-v1.json").write_text("{broken")
        self.apply(expected=1)
        self.assertFalse((self.state / "zsh_history").exists())

    def test_locked_migration_can_retry_when_process_releases_lock(self):
        (self.state / "migrations").mkdir(parents=True)
        with (self.state / "migrations/state-v1.lock").open("a+b") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.apply(expected=1)
            self.assertFalse((self.state / "zsh_history").exists())
        self.apply()
        self.assertEqual((self.state / "zsh_history").read_bytes(), self.history)

    def test_changed_target_during_interrupted_copy_is_not_overwritten(self):
        (self.state / "migrations").mkdir(parents=True)
        target = self.state / "zsh_history"
        target.write_bytes(self.history + b"new target record\n")
        source = self.legacy / "cache/zshhistory"
        (self.state / "migrations/state-v1.json").write_text(json.dumps({str(source): {
            "target": str(target), "source_sha256": hashlib.sha256(self.history).hexdigest(),
            "status": "copying"}}))
        self.apply(expected=1)
        self.assertIn(b"new target record", target.read_bytes())


if __name__ == "__main__":
    unittest.main()
