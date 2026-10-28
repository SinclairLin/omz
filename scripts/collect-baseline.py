#!/usr/bin/env python3
"""Collect isolated runtime evidence without sourcing the user's shell configuration."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import tarfile
import tempfile
import time
from datetime import datetime


ROOT = Path(__file__).resolve().parent.parent


def run(argv, cwd, env=None):
    return subprocess.run(
        [str(arg) for arg in argv], cwd=str(cwd), env=env,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
    )


def require(argv, cwd, env=None):
    result = run(argv, cwd, env)
    if result.returncode:
        raise RuntimeError("{}: {}".format(argv, result.stderr.strip()))
    return result.stdout.strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary(values):
    return {
        "samples_ms": [round(value, 3) for value in values],
        "median_ms": round(statistics.median(values), 3),
        "p95_ms": round(sorted(values)[math.ceil(len(values) * 0.95) - 1], 3),
    }


def backup(destination, extra_state):
    destination = destination.resolve()
    records = []
    home = Path.home()
    candidates = [
        ROOT, home / ".zshrc", home / ".zshenv", home / ".zsh_history",
        home / ".zlua", home / ".config/zsh/config/env-self.zsh",
        home / ".config/zsh/cache",
        Path(os.environ.get("XDG_CONFIG_HOME", str(home / ".config"))) / "omz/local.zsh",
    ]
    if os.environ.get("ZDOTDIR"):
        candidates.extend(Path(os.environ["ZDOTDIR"]).expanduser() / name
                          for name in (".zshrc", ".zshenv"))
    if os.environ.get("_ZL_DATA"):
        candidates.append(Path(os.environ["_ZL_DATA"]).expanduser().absolute())
    candidates.extend(path.expanduser().absolute() for path in extra_state)
    for candidate in candidates:
        source = candidate.resolve()
        if candidate.is_dir() and (destination == source or source in destination.parents):
            raise ValueError("Backup must be outside source directories: {}".format(source))
    destination.mkdir(parents=True, mode=0o700, exist_ok=False)
    os.chmod(destination, 0o700)
    archive = destination / "files.tar.gz"
    # Store bytes rather than symlinks, so restoring does not depend on live targets.
    files = {}
    for candidate in candidates:
        if candidate.is_dir():
            for parent, dirs, names in os.walk(candidate, followlinks=False):
                dirs[:] = sorted(name for name in dirs if name != ".git")
                for name in sorted(names):
                    path = Path(parent) / name
                    if path.is_file():
                        files[str(path)] = path
        elif candidate.is_file():
            files[str(candidate)] = candidate
    with tarfile.open(str(archive), "w:gz", dereference=True) as tar:
        for index, path in enumerate(files.values()):
            before = digest(path)
            member = "files/{:05d}".format(index)
            tar.add(str(path), arcname=member, recursive=False)
            after = digest(path)
            if before != after:
                raise RuntimeError("File changed during backup; retry: {}".format(path))
            records.append({"source": str(path), "member": member, "sha256": after})
    os.chmod(archive, 0o600)
    # Restore into a disposable location and compare every byte with the manifest.
    with tempfile.TemporaryDirectory(prefix="omz-restore-") as directory:
        with tarfile.open(str(archive), "r:gz") as tar:
            for record in records:
                target = Path(directory) / record["member"]
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(record["member"]) as source:
                    target.write_bytes(source.read())
                if digest(target) != record["sha256"]:
                    raise RuntimeError("Backup verification failed")
    bundle = destination / "repository.bundle"
    require(["git", "bundle", "create", bundle, "--all"], ROOT)
    require(["git", "bundle", "verify", bundle], ROOT)
    with tempfile.TemporaryDirectory(prefix="omz-git-restore-") as directory:
        require(["git", "clone", "--quiet", bundle, directory], ROOT)
        restored = require(["git", "rev-parse", "HEAD"], Path(directory))
        if restored != require(["git", "rev-parse", "HEAD"], ROOT):
            raise RuntimeError("Restored Git HEAD differs")
    os.chmod(bundle, 0o600)
    manifest = {
        "created_at": datetime.now().astimezone().isoformat(),
        "head": require(["git", "rev-parse", "HEAD"], ROOT),
        "archive_sha256": digest(archive), "bundle_sha256": digest(bundle),
        "files": records, "restore_verified": True,
        "scope": "File snapshots only; active sessions may write newer history.",
        "symlinks": "File symlinks saved as bytes; nested directory symlinks not traversed.",
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    os.chmod(manifest_path, 0o600)
    return {"directory": str(destination), "file_count": len(records),
            "restore_verified": True, "head": manifest["head"]}


def collect(samples, profile=None, plugin_data=None):
    result = {
        "collected_at": datetime.now().astimezone().isoformat(),
        "head": require(["git", "rev-parse", "HEAD"], ROOT),
        "branch": require(["git", "branch", "--show-current"], ROOT),
        "platform": platform.platform(), "architecture": platform.machine(),
        "python": platform.python_version(),
        "path": os.environ["PATH"], "tools": {},
        "method": "Isolated repository copy, HOME/XDG; zsh -dfi -c; no PTY.",
        "requested_profile": profile or "auto",
    }
    for name in ("zsh", "bash", "git", "fzf", "fd", "fdfind", "lua", "luajit",
                 "lua5.4", "lua5.3", "zoxide", "ouch", "bat", "batcat", "eza",
                 "shellcheck"):
        binary = shutil.which(name)
        if binary:
            flag = "-v" if name.startswith("lua") else "--version"
            version = run([binary, flag], ROOT)
            result["tools"][name] = {
                "path": binary,
                "version": (version.stdout + version.stderr).splitlines()[0],
            }
        else:
            result["tools"][name] = None
    result["embedded"] = {
        str(path.relative_to(ROOT)): digest(path) for path in (
            ROOT / "plugins/fzf-tab/fzf-tab.zsh",
            ROOT / "plugins/zsh-autosuggestions/zsh-autosuggestions.zsh",
            ROOT / "plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh",
            ROOT / "plugins/z.lua/z.lua",
        ) if path.is_file()
    }
    result["plugin_manifest"] = (ROOT / "config/plugins.txt").read_text()
    result["plugin_bootstrap"] = (ROOT / "config/bootstrap.zsh").read_text()
    with tempfile.TemporaryDirectory(prefix="omz-baseline-") as directory:
        temporary = Path(directory)
        copy = temporary / "repo"
        shutil.copytree(str(ROOT), str(copy), ignore=shutil.ignore_patterns(
            ".git", "__pycache__", "env-self.zsh", "cache"))
        (copy / "cache").mkdir()
        home = temporary / "home"
        home.mkdir()
        env = {
            "HOME": str(home), "ZDOTDIR": str(home), "PATH": os.environ["PATH"],
            "TERM": "xterm-256color", "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8", "OMZ_BASELINE_ROOT": str(copy),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_STATE_HOME": str(home / ".local/state"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_DATA_HOME": str(home / ".local/share"),
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
        }
        if profile:
            env["OMZ_PROFILE"] = profile
        data = home / ".local/share/omz"
        if plugin_data:
            shutil.copytree(plugin_data, data, symlinks=True,
                            ignore=shutil.ignore_patterns(".plugins.lock"))
        setup = require(["zsh", "-df", copy / "scripts/manage-plugins.zsh",
                         "build" if plugin_data else "install"], copy, env)
        result["plugin_setup"] = setup.replace(str(temporary), "<TEMP>")
        result["plugin_verification"] = require(
            ["zsh", "-df", copy / "scripts/manage-plugins.zsh", "verify"],
            copy, env).replace(str(temporary), "<TEMP>")
        if (data / "antidote").is_dir():
            env["OMZ_TEST_PLUGIN_DATA"] = str(data)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        checks = [["sh", "-n", "scripts/install_zsh_config.sh"]]
        for name in ("scripts/install_zsh_config.sh", "tests/test_installer.sh",
                     "lib/file_preview.sh"):
            checks.append(["bash", "-n", name])
        # lib/init.sh uses Zsh syntax despite its suffix. Each parser takes ONE file.
        zsh_files = ["omz.zsh", "lib/init.sh"] + sorted(
            str(p.relative_to(copy)) for pattern in
            ("lib/*.zsh", "scripts/*.zsh", "config/*.zsh",
             "themes/*.zsh-theme", "tests/*.zsh",
             "functions/*.zsh")
            for p in copy.glob(pattern))
        checks.extend(["zsh", "-n", name] for name in zsh_files)
        checks.extend([["bash", "tests/test_installer.sh"],
                       ["zsh", "-df", "tests/test_runtime.zsh"]])
        result["checks"] = []
        for command in checks:
            check = run(command, copy, env)
            result["checks"].append({
                "command": command, "returncode": check.returncode,
                "stdout": check.stdout, "stderr": check.stderr,
            })
        # Existing tests can create a compdump; remove it before the first sample.
        for path in home.glob(".zcompdump*"):
            path.unlink()
        for path in (home / ".cache/omz").glob("zcompdump*"):
            path.unlink()
        normal = temporary / "ordinary"
        normal.mkdir()
        command = ["zsh", "-dfi", "-c",
                   'source "$OMZ_BASELINE_ROOT/omz.zsh"; exit 0']
        startup = []
        for _ in range(samples + 1):
            start = time.perf_counter()
            check = run(command, normal, env)
            startup.append((time.perf_counter() - start) * 1000)
            if check.returncode or check.stdout or check.stderr:
                raise RuntimeError("Startup was not clean: " + repr(
                    (check.returncode, check.stdout, check.stderr)))
        result["startup"] = {
            "first_without_compdump_ms": round(startup[0], 3),
            "warm": summary(startup[1:]),
            "note": "Process wall time including exit; OS filesystem caches not flushed.",
        }
        probe = r'''
original_directory=$PWD
source "$OMZ_BASELINE_ROOT/omz.zsh"
print -r -- "interactive=$options[interactive]"
[[ "$PWD" == "$original_directory" ]] && print "directory_unchanged=true"
print -r -- "history=$HISTFILE"
print -r -- "completion=${+functions[compdef]}"
print -r -- "history_widget=${+functions[fzf-history-widget]}"
print -r -- "suggestions=${+functions[_zsh_autosuggest_start]}"
print -r -- "highlighting=${+functions[_zsh_highlight]}"
print -r -- "jump_backend=${_OMZ_JUMP_BACKEND:-none}"
print -r -- "jump=$(( ${+functions[_zlua]} || ${+functions[__zoxide_z]} ))"
print -r -- "extract=${+functions[extract]}"
print -r -- "randport=${+functions[randport]}"
print -r -- "dcupdate=${+functions[dcupdate]}"
bindkey '^I'
bindkey '^R'
print -r -- "hooks_before=${#precmd_functions},${#chpwd_functions},${#preexec_functions}"
print -r -- "widgets_before=${#widgets}"
source "$OMZ_BASELINE_ROOT/omz.zsh"
print -r -- "hooks_after=${#precmd_functions},${#chpwd_functions},${#preexec_functions}"
print -r -- "widgets_after=${#widgets}"
bindkey '^I'
bindkey '^R'
'''
        result["probes"] = {}
        for kind, flags in (("noninteractive", "-df"), ("interactive", "-dfi")):
            check = run(["zsh", flags, "-c", probe], normal, env)
            result["probes"][kind] = {
                "returncode": check.returncode,
                "stdout": check.stdout.replace(str(temporary), "<TEMP>"),
                "stderr": check.stderr.replace(str(temporary), "<TEMP>"),
            }
        large = temporary / "large-git"
        large.mkdir()
        require(["git", "init", "-q", large], normal, env)
        for index in range(10000):
            parent = large / "dir{:03d}".format(index // 100)
            parent.mkdir(exist_ok=True)
            (parent / "file{:05d}.txt".format(index)).write_text("baseline\n")
        require(["git", "add", "."], large, env)
        require(["git", "-c", "user.name=Baseline", "-c",
                 "user.email=baseline@example.invalid", "-c", "commit.gpgsign=false",
                 "commit", "-qm", "Synthetic performance fixture"], large, env)
        prompt = '''
source "$OMZ_BASELINE_ROOT/omz.zsh"
zmodload zsh/datetime
git_prompt_info >/dev/null
repeat {samples}; do
  start=$EPOCHREALTIME
  git_prompt_info >/dev/null
  print -r -- $(( (EPOCHREALTIME - start) * 1000 ))
done
'''.replace("{samples}", str(samples))
        result["prompt"] = {}
        for name, cwd in (("ordinary", normal), ("git_10000_clean", large),
                          ("git_10000_dirty", large)):
            if name.endswith("dirty"):
                (large / "dir000/file00000.txt").write_text("changed\n")
            values = require(["zsh", "-dfi", "-c", prompt], cwd, env)
            result["prompt"][name] = summary([float(v) for v in values.splitlines()])
    return result


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--profile", choices=("desktop", "server", "minimal"),
                        help="Measure an explicit profile instead of auto detection")
    parser.add_argument("--plugin-data", type=Path,
                        help="Copy existing OMZ data into isolation and build offline")
    parser.add_argument("--backup", type=Path,
                        help="Create a private snapshot at a NEW directory")
    parser.add_argument("--state-file", type=Path, action="append", default=[],
                        help="Include a custom jump database or legacy state path")
    args = parser.parse_args()
    if args.samples < 20:
        parser.error("--samples must be at least 20")
    result = collect(args.samples, args.profile, args.plugin_data)
    if args.backup:
        result["backup"] = backup(args.backup.expanduser().absolute(), args.state_file)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n")
    print("Baseline written to {}".format(args.output))
    if any(check["returncode"] for check in result["checks"]):
        raise SystemExit("Existing checks failed; see the baseline report")


if __name__ == "__main__":
    main()
