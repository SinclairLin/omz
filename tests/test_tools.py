#!/usr/bin/env python3
"""M4 archive contracts, bounded previews, upstream image integration and tools."""

import base64
import bz2
import gzip
import io
import json
import lzma
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
import tarfile
import tempfile
import termios
import fcntl
import time
import unittest
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
OUCH = shutil.which("ouch")
FZF = shutil.which("fzf")
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1cAAAAASUVORK5CYII=")


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="omz-m4-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve()
        self.bin = self.directory / "bin"
        self.bin.mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(("OMZ", "_OMZ", "XDG_", "FZF_", "KITTY", "SSH_", "TMUX"))
                    and key not in ("ENV", "BASH_ENV", "TERM_PROGRAM", "GHOSTTY_RESOURCES_DIR")}
        self.env.update(HOME=str(self.directory), ZDOTDIR=str(self.directory / "zdot"),
                        TERM="xterm-256color", PATH=str(self.bin) + ":/usr/bin:/bin")
        for kind in ("CONFIG", "STATE", "DATA", "CACHE"):
            self.env["XDG_" + kind + "_HOME"] = str(self.directory / kind)

    def stub(self, name, code):
        target = self.bin / name
        target.write_text("#!/bin/sh\n" + code + "\n")
        target.chmod(0o755)
        return target

    def run_command(self, argv):
        return subprocess.run(argv, env=self.env, cwd=self.directory,
                              capture_output=True, text=True, timeout=15)

    def shell(self, code, *args):
        return self.run_command(["/bin/zsh", "-dfc", code, "--", str(ROOT), *map(str, args)])

    def archive(self, name):
        path = self.directory / name
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("payload.txt", "payload\n")
        return path

    def real_ouch(self):
        self.bin.joinpath("ouch").symlink_to(OUCH)

    def extract(self, *args):
        return self.shell("""
source "$1/functions/extract.zsh"
shift
before=$PWD
extract "$@"
result=$?
[[ $PWD == $before ]] || exit 99
exit $result
""", *args)

    def preview(self, path):
        return self.run_command(["/bin/sh", str(ROOT / "lib/file_preview.sh"), str(path)])

    def image(self):
        path = self.directory / "-中文 image.png"
        path.write_bytes(PNG)
        return path

    def image_environment(self):
        self.env.update(KITTY_WINDOW_ID="123", TERM="xterm-kitty",
                        FZF_PREVIEW_LINES="10", FZF_PREVIEW_COLUMNS="60")

    def fake_official(self, code='printf "official:%s\\n" "$1"'):
        package = self.directory / "fzf package"
        (package / "bin").mkdir(parents=True)
        (package / "bin/fzf").write_text("")
        (package / "bin/fzf").chmod(0o755)
        self.bin.joinpath("fzf").symlink_to(package / "bin/fzf")
        script = package / "bin/fzf-preview.sh"
        script.write_text("#!/bin/bash\n" + code + "\n")
        self.stub("kitten", "exit 0")
        self.image_environment()
        return script

    @unittest.skipUnless(OUCH, "real ouch required")
    def test_real_zip_spaces_unicode_and_leading_dash(self):
        self.real_ouch()
        for name in ("中文 空格.zip", "-leading.zip"):
            with self.subTest(name=name):
                path = self.archive(name)
                result = self.extract("--", path.name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(Path(str(path) + ".extracted/payload.txt").read_text(), "payload\n")
                self.assertTrue(path.exists())

    @unittest.skipUnless(OUCH, "real ouch required")
    def test_real_formats_and_successful_remove(self):
        self.real_ouch()
        for extension, encode in (("gz", gzip.compress), ("bz2", bz2.compress),
                                  ("xz", lzma.compress)):
            with self.subTest(extension=extension):
                path = self.directory / ("data." + extension)
                path.write_bytes(encode(b"payload\n"))
                result = self.extract("-r", path)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(path.exists())
                self.assertEqual(Path(str(path) + ".extracted/data").read_bytes(), b"payload\n")
        path = self.directory / "archive.tar.gz"
        with tarfile.open(path, "w:gz") as archive:
            item = tarfile.TarInfo("nested/payload.txt")
            item.size = 8
            archive.addfile(item, io.BytesIO(b"payload\n"))
        result = self.extract("--remove", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(path.exists())
        self.assertEqual(Path(str(path) + ".extracted/nested/payload.txt").read_bytes(), b"payload\n")

    @unittest.skipUnless(OUCH, "real ouch required")
    def test_real_seven_zip(self):
        self.real_ouch()
        source = self.directory / "payload.txt"
        source.write_text("payload\n")
        archive = self.directory / "archive.7z"
        result = self.run_command([OUCH, "compress", str(source), str(archive)])
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.extract(archive)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(str(archive) + ".extracted/payload.txt").read_text(), "payload\n")

    @unittest.skipUnless(OUCH, "real ouch required")
    def test_real_mixed_inputs_preserve_failed_archive(self):
        self.real_ouch()
        good = self.archive("good.zip")
        bad = self.directory / "broken.zip"
        bad.write_bytes(b"invalid archive")
        last = self.archive("last.zip")
        result = self.extract("-r", good, bad, "missing.zip", last)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertFalse(good.exists())
        self.assertFalse(last.exists())
        self.assertTrue(bad.exists())
        self.assertIn("archive kept", result.stderr)

    def test_existing_destination_and_dangling_symlink_are_not_used(self):
        self.stub("ouch", 'touch "$HOME/ouch-called"')
        for name, symlink in (("existing.zip", False), ("symlink.zip", True)):
            path = self.archive(name)
            destination = Path(str(path) + ".extracted")
            if symlink:
                destination.symlink_to(self.directory / "missing-target")
            else:
                destination.mkdir()
                (destination / "keep").write_text("keep")
            self.assertEqual(self.extract("-r", path).returncode, 1)
            self.assertTrue(path.exists())
        self.assertFalse((self.directory / "ouch-called").exists())

    def test_partial_failure_is_preserved_and_original_kept(self):
        self.stub("ouch", 'mkdir -p "$4"; printf partial > "$4/partial"; exit 1')
        path = self.archive("partial.zip")
        result = self.extract("-r", path)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(path.exists())
        self.assertEqual(Path(str(path) + ".extracted/partial").read_text(), "partial")

    def test_usage_and_no_ouch_do_not_register_extract(self):
        previous_path = self.env["PATH"]
        self.env["PATH"] = str(self.bin)
        result = self.shell('source "$1/functions/extract.zsh"; '
                            '(( ! $+functions[extract] && ! $+aliases[x] ))')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.env["PATH"] = previous_path
        self.stub("ouch", "exit 0")
        for args in ((), ("-r",), ("--unknown",)):
            self.assertEqual(self.extract(*args).returncode, 2)

    def test_text_and_directory_fallback_are_bounded(self):
        for name in ("中文 text.txt", "-file.txt"):
            path = self.directory / name
            path.write_text("hello\n" * 1200)
            result = self.preview(path.name)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), ["hello"] * 1000)
        folder = self.directory / "-目录 folder"
        folder.mkdir()
        for index in range(230):
            (folder / str(index)).touch()
        result = self.preview(folder.name)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 200)

    def test_bat_batcat_and_eza_selection(self):
        path = self.directory / "data.txt"
        path.write_text("hello\n")
        for tool in ("batcat", "bat"):
            self.stub(tool, 'printf "%s\\n" "$0" "$@"; cat')
            result = self.preview(path)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("/" + tool + "\n", result.stdout)
            self.assertIn("--paging=never", result.stdout)
            self.assertIn("hello", result.stdout)
        self.stub("eza", 'printf "%s\\n" "$@"')
        result = self.preview(self.directory)
        self.assertIn("--sort=none", result.stdout)

    def test_missing_binary_and_nonregular_paths(self):
        self.assertNotEqual(self.preview("missing").returncode, 0)
        data = self.directory / "-binary"
        data.write_bytes(bytes(range(256)))
        self.assertEqual(self.preview(data).returncode, 0)
        fifo = self.directory / "fifo"
        os.mkfifo(fifo)
        result = self.preview(fifo)
        self.assertEqual(result.returncode, 0)
        self.assertIn("not a regular file", result.stdout)

    def test_official_script_discovery_and_literal_image_path(self):
        self.fake_official()
        path = self.image()
        result = self.preview(path.name)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "official:" + str(path) + "\n")

    def test_images_fallback_for_disabled_ssh_tmux_plain_or_bad_dimensions(self):
        self.fake_official()
        path = self.image()
        baseline = self.env.copy()
        for override in ({"OMZ_IMAGE_PREVIEW": "off"}, {"SSH_CONNECTION": "a b c d"},
                         {"SSH_TTY": "/dev/ttys1"}, {"TMUX": "session"},
                         {"KITTY_WINDOW_ID": ""}, {"TERM": "dumb"},
                         {"FZF_PREVIEW_LINES": ""}, {"FZF_PREVIEW_COLUMNS": "1x2"},
                         {"FZF_PREVIEW_COLUMNS": "0"}):
            with self.subTest(override=override):
                self.env = dict(baseline, **override)
                result = self.preview(path)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("PNG image data", result.stdout)
                self.assertNotIn("official:", result.stdout)

    def test_missing_or_failed_official_script_falls_back(self):
        self.image_environment()
        self.stub("kitten", "exit 0")
        path = self.image()
        self.env["OMZ_FZF_PREVIEW_SCRIPT"] = str(self.directory / "missing-script")
        self.assertIn("PNG image data", self.preview(path).stdout)
        script = self.directory / "failed.sh"
        script.write_text("exit 1\n")
        self.env["OMZ_FZF_PREVIEW_SCRIPT"] = str(script)
        self.assertIn("PNG image data", self.preview(path).stdout)

    @unittest.skipUnless(FZF, "installed fzf required")
    def test_installed_official_script_with_recorded_kitten(self):
        self.bin.joinpath("fzf").symlink_to(FZF)
        self.image_environment()
        log = self.directory / "kitten.json"
        # Record upstream's protocol invocation without sending graphics to a user terminal.
        self.stub("kitten", shlex.quote(sys.executable) + " -c " + shlex.quote(
            "import json,sys; from pathlib import Path; "
            "Path(" + repr(str(log)) + ").write_text(json.dumps(sys.argv[1:]))") +
            ' "$@"\nprintf "image\\nreset\\n"')
        path = self.image()
        result = self.preview(path)
        if not log.exists():
            self.skipTest("installed fzf package has no official image script")
        self.assertEqual(result.returncode, 0, result.stderr)
        args = json.loads(log.read_text())
        self.assertIn("icat", args)
        self.assertIn("--place=60x10@0x0", args)
        self.assertEqual(args[-1], str(path))

    @unittest.skipUnless(FZF, "fzf required")
    def test_fzf_preview_cancellation_reaps_process_group(self):
        script = self.fake_official('printf "%s\\n" "$$" > "$HOME/image-pid"\n'
                                    'exec sleep 30')
        self.env["OMZ_FZF_PREVIEW_SCRIPT"] = str(script)
        self.check_preview_cancellation()

    @unittest.skipUnless(FZF, "installed fzf required")
    def test_installed_official_cancellation_reaps_kitten_pipeline(self):
        binary = Path(FZF).resolve()
        prefix = binary.parent.parent
        candidates = (binary.parent / "fzf-preview.sh",
                      prefix / "share/fzf/fzf-preview.sh",
                      prefix / "share/fzf/bin/fzf-preview.sh",
                      prefix / "share/doc/fzf/examples/fzf-preview.sh")
        script = next((path for path in candidates if path.is_file()), None)
        if script is None:
            self.skipTest("installed fzf package has no official image script")
        self.image_environment()
        self.env["OMZ_FZF_PREVIEW_SCRIPT"] = str(script)
        self.stub("kitten", 'printf "%s\\n" "$$" > "$HOME/image-pid"\nexec sleep 30')
        self.check_preview_cancellation()

    def check_preview_cancellation(self):
        image = self.image()
        command = [FZF, "--no-sort", "--preview",
                   "sh " + shlex.quote(str(ROOT / "lib/file_preview.sh")) + " {}",
                   "--preview-window=right:60%"]
        listing = self.directory / "listing"
        listing.write_text(str(image) + "\n")
        self.env["FZF_DEFAULT_COMMAND"] = "cat " + shlex.quote(str(listing))
        pid, master = pty.fork()
        if pid == 0:
            os.chdir(self.directory)
            os.execvpe(FZF, command, self.env)
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 120, 0, 0))
        waited = False
        preview_pid = None
        try:
            deadline = time.monotonic() + 10
            marker = self.directory / "image-pid"
            while not marker.exists() and time.monotonic() < deadline:
                if select.select([master], [], [], 0.05)[0]:
                    os.read(master, 65536)
            self.assertTrue(marker.exists(), "fzf did not launch image preview")
            preview_pid = int(marker.read_text())
            os.write(master, b"\x03")
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if select.select([master], [], [], 0.02)[0]:
                    try:
                        os.read(master, 65536)
                    except OSError:
                        pass
                child, _ = os.waitpid(pid, os.WNOHANG)
                if child:
                    waited = True
                    break
                time.sleep(0.02)
            self.assertTrue(waited, "fzf did not exit on Ctrl-C")
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                try:
                    os.kill(preview_pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.02)
            else:
                self.fail("preview process survived fzf cancellation")
        finally:
            os.close(master)
            if not waited:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            if preview_pid:
                try:
                    os.kill(preview_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_dcupdate_order_and_pull_failure(self):
        self.stub("docker", 'printf "%s\\n" "$*" >> "$HOME/docker.log"\n'
                  '[ "$*" != "compose pull" ] || exit "${PULL_STATUS:-0}"')
        for status, expected in (("0", ["compose pull", "compose up -d"]),
                                 ("1", ["compose pull"])):
            self.env["PULL_STATUS"] = status
            result = self.shell('source "$1/functions/docker.zsh"; dcupdate')
            self.assertEqual(result.returncode, int(status))
            log = self.directory / "docker.log"
            self.assertEqual(log.read_text().splitlines(), expected)
            log.unlink()

    def test_randport_rejects_inspection_failure(self):
        self.stub("ss", "exit 2")
        result = self.shell('source "$1/functions/randport.zsh"; randport')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("inspection unavailable or failed", result.stderr)

    def test_optional_aliases_require_commands(self):
        self.env["PATH"] = str(self.bin)
        result = self.shell('source "$1/config/aliases.zsh"; '
                            '(( ! $+aliases[tree] && ! $+aliases[lg] ))')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_git_prompt_preserves_clean_dirty_and_hidden_output(self):
        git = shutil.which("git")
        if not git:
            self.skipTest("git required")
        self.bin.joinpath("git").symlink_to(git)
        for args in (("init", "-q"), ("config", "user.name", "M4"),
                     ("config", "user.email", "m4@example.invalid"),
                     ("config", "status.showUntrackedFiles", "no")):
            self.assertEqual(self.run_command([git, *args]).returncode, 0)
        tracked = self.directory / "tracked"
        tracked.write_text("clean\n")
        self.run_command([git, "add", "tracked"])
        self.run_command([git, "-c", "commit.gpgsign=false", "commit", "-qm", "fixture"])
        result = self.shell('source "$1/lib/git-prompt.zsh"; '
                            'ZSH_THEME_GIT_PROMPT_PREFIX="["; ZSH_THEME_GIT_PROMPT_SUFFIX="]"; '
                            'ZSH_THEME_GIT_PROMPT_DIRTY="~"; git_prompt_info')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("~", result.stdout)
        tracked.write_text("dirty\n")
        result = self.shell('source "$1/lib/git-prompt.zsh"; '
                            'ZSH_THEME_GIT_PROMPT_DIRTY="~"; git_prompt_info')
        self.assertIn("~", result.stdout)
        self.run_command([git, "config", "oh-my-zsh.hide-status", "1"])
        self.assertEqual(self.shell(
            'source "$1/lib/git-prompt.zsh"; git_prompt_info').stdout, "")


if __name__ == "__main__":
    unittest.main()
