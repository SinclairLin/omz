"""Shared real dependencies; tests keep all installation and state in temporary paths."""

import os
from pathlib import Path
import shutil
import subprocess


def modern_fzf_available():
    binary = shutil.which("fzf")
    if not binary:
        return False
    version = subprocess.check_output([binary, "--version"], text=True).split()[0]
    try:
        return tuple(map(int, version.split(".")[:2])) >= (0, 51)
    except ValueError:
        return False


def isolated_env(directory):
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("OMZ", "_OMZ", "XDG_", "_ZL", "_ZO", "ZLUA", "FZF_", "ANTIDOTE"))
           and key not in ("HISTFILE", "ENV", "BASH_ENV")}
    home = directory / "home with spaces"
    home.mkdir(parents=True, exist_ok=True)
    env.update(HOME=str(home), ZDOTDIR=str(home / "zdot"), TERM="xterm-256color",
               OMZ_PROFILE="desktop", GIT_TERMINAL_PROMPT="0",
               TMPPREFIX=str(directory / "zsh"))
    for kind in ("CONFIG", "STATE", "DATA", "CACHE"):
        env["XDG_" + kind + "_HOME"] = str(directory / (kind + " with spaces"))
    return env


def dependency_seed(root, directory):
    supplied = os.environ.get("OMZ_TEST_PLUGIN_DATA")
    if supplied:
        return Path(supplied)
    env = isolated_env(directory)
    env["OMZ_JUMP"] = "zlua"
    result = subprocess.run(
        ["zsh", "-df", str(root / "scripts/manage-plugins.zsh"), "install"],
        env=env, capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise RuntimeError("Plugin fixture installation failed:\n" + result.stdout + result.stderr)
    return Path(env["XDG_DATA_HOME"]) / "omz"


def copy_dependencies(seed, env):
    target = Path(env["XDG_DATA_HOME"]) / "omz"
    shutil.copytree(seed, target, symlinks=True,
                    ignore=shutil.ignore_patterns(".plugins.lock"))
    return target
