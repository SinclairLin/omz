#!/usr/bin/env python3
"""Exercise the complete /bin/sh installer against local real Git upstreams."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
from plugin_support import dependency_seed, isolated_env

ROOT = Path(__file__).resolve().parent.parent


class InstallationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="omz-install-seed-")
        cls.directory = Path(cls.temporary.name)
        cls.root = cls.directory / "source"
        shutil.copytree(ROOT, cls.root, ignore=shutil.ignore_patterns(
            ".git", "cache", "__pycache__", "env-self.zsh"))
        cls.seed = dependency_seed(ROOT, cls.directory / "seed")
        cls.git(["init", "--quiet", "-b", "main"], cls.root)
        cls.git(["add", "."], cls.root)
        cls.git(["commit", "--quiet", "-m", "Installer fixture"], cls.root)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    @staticmethod
    def git(args, directory):
        env = os.environ.copy()
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
                   GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.invalid",
                   GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="test@example.invalid")
        for key in list(env):
            if key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")) or key == "GIT_CONFIG_COUNT":
                del env[key]
        return subprocess.check_output(
            ["git"] + args, cwd=directory, env=env, stderr=subprocess.STDOUT, text=True)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="omz-install-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.env = isolated_env(self.directory)
        for key in ("TARGET_DIR", "ZSHRC_FILE", "SOURCE_LINE", "REPO_URL"):
            self.env.pop(key, None)
        self.upstream = self.directory / "upstream"
        self.git(["clone", "--quiet", str(self.root), str(self.upstream)], self.directory)
        self.target = self.directory / "installed source with spaces"
        self.zshrc = Path(self.env["ZDOTDIR"]) / ".zshrc"
        self.zshrc.parent.mkdir(parents=True)
        self.zshrc.write_text("export USER_SETTING=preserved")  # No final newline.
        self.env.update(REPO_URL=str(self.upstream), TARGET_DIR=str(self.target),
                        OMZ_INSTALL_DEPS="0", GIT_ALLOW_PROTOCOL="file",
                        GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1",
                        PYTHONDONTWRITEBYTECODE="1")
        repositories = {
            "mattmc3/antidote.git": self.seed / "antidote",
            "Aloxaf/fzf-tab": self.seed / "plugins/github.com/Aloxaf/fzf-tab",
            "zsh-users/zsh-autosuggestions":
                self.seed / "plugins/github.com/zsh-users/zsh-autosuggestions",
            "zsh-users/zsh-syntax-highlighting":
                self.seed / "plugins/github.com/zsh-users/zsh-syntax-highlighting",
            "skywind3000/z.lua": self.seed / "plugins/github.com/skywind3000/z.lua",
        }
        self.env["GIT_CONFIG_COUNT"] = str(len(repositories))
        for index, (name, path) in enumerate(repositories.items()):
            self.env["GIT_CONFIG_KEY_" + str(index)] = "url." + path.as_uri() + ".insteadOf"
            self.env["GIT_CONFIG_VALUE_" + str(index)] = "https://github.com/" + name

    def run_command(self, args, expected=0):
        result = subprocess.run(args, cwd=self.env["HOME"], env=self.env,
                                capture_output=True, text=True, timeout=90)
        if expected == 0:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def install(self, expected=0, arguments=()):
        return self.run_command(
            ["/bin/sh", str(ROOT / "scripts/install_zsh_config.sh"), *arguments], expected)

    def local(self, text):
        path = Path(self.env["XDG_CONFIG_HOME"]) / "omz/local.zsh"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def test_clean_install_repeat_and_fast_forward_upgrade_all_profiles(self):
        original = self.env.copy()
        for profile in ("desktop", "server", "minimal"):
            with self.subTest(profile=profile):
                self.env = original.copy()
                isolated = isolated_env(self.directory / profile)
                for name in ("HOME", "ZDOTDIR", "TMPPREFIX", "XDG_CONFIG_HOME",
                             "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
                    self.env[name] = isolated[name]
                self.target = self.directory / profile / "installed source with spaces"
                self.env["TARGET_DIR"] = str(self.target)
                self.zshrc = Path(self.env["ZDOTDIR"]) / ".zshrc"
                self.zshrc.parent.mkdir(parents=True)
                self.zshrc.write_text("export USER_SETTING=preserved")
                self.env["OMZ_PROFILE"] = profile
                self.install()
                static = Path(self.env["XDG_CACHE_HOME"]) / "omz/plugins.zsh"
                first = static.read_bytes()
                startup = self.zshrc.read_bytes()
                self.install()
                self.assertEqual(first, static.read_bytes())
                self.assertEqual(startup, self.zshrc.read_bytes())
                self.assertEqual(len(list(self.zshrc.parent.glob(".zshrc.omz-backup.*"))), 1)
                note = self.upstream / "upgrade.txt"
                note.write_text("upgrade " + profile + "\n")
                self.git(["add", "upgrade.txt"], self.upstream)
                self.git(["commit", "--quiet", "-m", "Upgrade " + profile], self.upstream)
                self.install()
                self.assertEqual((self.target / "upgrade.txt").read_bytes(), note.read_bytes())
                self.assertEqual(startup, self.zshrc.read_bytes())
                result = self.run_command(["zsh", "-dfi", "-c",
                    'source "$1"; [[ $USER_SETTING == preserved && $OMZ_PROFILE == "$2" ]]',
                    "--", str(self.zshrc), profile])
                self.assertEqual(result.stderr, "")
                self.assertEqual(self.git(["status", "--porcelain"], self.target), "")

    def test_minimal_has_no_antidote_or_fzf_side_effects(self):
        self.env["OMZ_PROFILE"] = "minimal"
        old = Path(self.env["HOME"]) / ".fzf/install"
        old.parent.mkdir()
        old.write_text("#!/bin/sh\nexit 97\n")
        old.chmod(0o755)
        self.install()
        self.assertFalse((Path(self.env["XDG_DATA_HOME"]) / "omz/antidote").exists())
        self.assertEqual(old.read_text(), "#!/bin/sh\nexit 97\n")

    def test_dirty_installation_is_rejected_before_activation(self):
        self.env["OMZ_PROFILE"] = "minimal"
        self.install()
        file = self.target / "omz.zsh"
        file.write_text(file.read_text() + "\n# user edit\n")
        before = self.zshrc.read_bytes()
        self.env["OMZ_INSTALL_DEPS"] = "1"
        result = self.install(expected=1)
        self.assertIn("local changes", result.stderr)
        self.assertNotIn("package manager:", result.stdout)
        self.assertEqual(before, self.zshrc.read_bytes())
        self.assertTrue(file.read_text().endswith("# user edit\n"))

    def test_non_git_nonempty_target_is_preserved(self):
        self.target.mkdir()
        note = self.target / "user data"
        note.write_text("keep")
        self.install(expected=1)
        self.assertEqual(note.read_text(), "keep")
        self.assertEqual(self.zshrc.read_text(), "export USER_SETTING=preserved")

    def test_failed_plugin_install_does_not_activate_or_leave_temporaries(self):
        self.env["GIT_CONFIG_KEY_0"] = "url.file:///nonexistent-omz-upstream.insteadOf"
        before = self.zshrc.read_bytes()
        self.install(expected=1)
        self.assertEqual(before, self.zshrc.read_bytes())
        self.assertFalse(list(self.zshrc.parent.glob(".zshrc.omz-backup.*")))
        data = Path(self.env["XDG_DATA_HOME"]) / "omz"
        self.assertFalse(list(data.glob(".antidote.*")))
        self.assertFalse((Path(self.env["XDG_CACHE_HOME"]) / "omz/plugins.zsh").exists())

    def test_dirty_dependency_preserves_existing_loader_and_startup(self):
        self.install()
        data = Path(self.env["XDG_DATA_HOME"]) / "omz"
        plugin = data / "plugins/github.com/zsh-users/zsh-autosuggestions/zsh-autosuggestions.zsh"
        plugin.write_text(plugin.read_text() + "\n# user edit\n")
        static = Path(self.env["XDG_CACHE_HOME"]) / "omz/plugins.zsh"
        before = (static.read_bytes(), self.zshrc.read_bytes())
        self.install(expected=1)
        self.assertEqual(before, (static.read_bytes(), self.zshrc.read_bytes()))
        self.assertTrue(plugin.read_text().endswith("# user edit\n"))

    def test_failed_pin_upgrade_keeps_loader_and_degrades_safely(self):
        self.install()
        static = Path(self.env["XDG_CACHE_HOME"]) / "omz/plugins.zsh"
        before = (static.read_bytes(), self.zshrc.read_bytes())
        bootstrap = self.upstream / "config/bootstrap.zsh"
        text = bootstrap.read_text()
        sha = text.split("OMZ_ANTIDOTE_SHA=", 1)[1].splitlines()[0]
        bootstrap.write_text(text.replace(sha, "0" * 40))
        self.git(["add", "config/bootstrap.zsh"], self.upstream)
        self.git(["commit", "--quiet", "-m", "Unavailable pin"], self.upstream)
        self.install(expected=1)
        self.assertEqual(before, (static.read_bytes(), self.zshrc.read_bytes()))
        self.assertEqual((self.target / "config/bootstrap.zsh").read_text(),
                         bootstrap.read_text())
        result = self.run_command(["zsh", "-dfi", "-c",
            'source "$1/omz.zsh"; (( $+functions[compdef] && ! $+functions[_zsh_highlight] ))',
            "--", str(self.target)])
        self.assertIn("plugins unavailable or stale", result.stderr)

    def test_doctor_is_read_only_without_installing(self):
        self.env["OMZ_PROFILE"] = "minimal"
        before = set(self.directory.rglob("*"))
        result = self.run_command(["zsh", "-df", str(ROOT / "scripts/doctor.zsh")])
        self.assertIn("profile: minimal", result.stdout)
        self.assertIn("plugins: no external plugins selected", result.stdout)
        self.assertIn("history/Tab: native (minimal)", result.stdout)
        self.assertEqual(before, set(self.directory.rglob("*")))

    def test_local_options_and_user_state_are_preserved_with_preview(self):
        local = self.local("OMZ_PROFILE=minimal\nOMZ_JUMP=none\n")
        state = Path(self.env["XDG_STATE_HOME"]) / "omz"
        state.mkdir(parents=True)
        history = state / "zsh_history"
        # A nonempty history merges; a symlinked target is still a conflict.
        (state / "elsewhere").write_text(": 100:0;preserve history\n")
        history.symlink_to(state / "elsewhere")
        legacy = Path(self.env["HOME"]) / ".config/zsh/cache"
        legacy.mkdir(parents=True)
        (legacy / "zshhistory").write_text(": 200:0;legacy history\n")
        jump = Path(self.env["HOME"]) / ".zlua"
        jump.write_text("/some path|3|100\n")
        before = [path.read_bytes() for path in (local, history, jump)]
        # Preview reports conflicts but never applies them; a conflict must not activate.
        self.install(expected=1, arguments=("--migrate-state-preview",))
        self.assertEqual(self.zshrc.read_text(), "export USER_SETTING=preserved")
        self.assertEqual(before, [path.read_bytes() for path in (local, history, jump)])
        history.unlink()
        self.install(arguments=("--migrate-state-preview",))
        self.assertEqual(local.read_text(), "OMZ_PROFILE=minimal\nOMZ_JUMP=none\n")
        self.assertFalse(history.exists())
        self.assertFalse((state / "migrations/state-v1.json").exists())

    def test_source_line_quotes_shell_metacharacters(self):
        self.env["OMZ_PROFILE"] = "minimal"
        self.target = self.directory / 'source "$HOME" `false` \\ folder'
        self.env["TARGET_DIR"] = str(self.target)
        self.install()
        self.run_command(["zsh", "-dfi", "-c",
            'source "$1"; [[ $OMZ == ${2:A} ]]', "--", str(self.zshrc), str(self.target)])

    def test_origin_mismatch_is_rejected(self):
        self.env["OMZ_PROFILE"] = "minimal"
        self.install()
        self.env["REPO_URL"] = str(self.directory / "other repo")
        before = self.zshrc.read_bytes()
        self.assertIn("origin differs", self.install(expected=1).stderr)
        self.assertEqual(before, self.zshrc.read_bytes())

    def test_invalid_options_do_not_create_installation(self):
        for settings, arguments in (
                ({"OMZ_INSTALL_DEPS": "invalid"}, ()),
                ({"TARGET_DIR": "relative"}, ()),
                ({}, ("--unknown",))):
            with self.subTest(settings=settings, arguments=arguments):
                original = self.env.copy()
                self.env.update(settings)
                self.install(expected=1, arguments=arguments)
                self.env = original
                self.assertFalse(self.target.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
