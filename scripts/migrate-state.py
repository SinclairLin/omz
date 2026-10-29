#!/usr/bin/env python3
"""Preview or explicitly copy legacy omz state; Python 3 standard library only."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from datetime import datetime


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def private_directory(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def write_json(path, value):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write((json.dumps(value, indent=2, ensure_ascii=True) + "\n").encode())
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


# Line-oriented histories: legacy records first, then those the new shell already wrote.
MERGEABLE = ("zshhistory", "fzfhistory")


def merge_into(source, target, saved_source, saved_target, completed, marker):
    identity = {"target": str(target), "source_sha256": digest(saved_source)}
    record = completed.get(str(source), {})
    if target.is_symlink():
        raise RuntimeError("Target changed after preview: " + str(target))
    current = digest(target)
    if not (record.get("status") == "merging" and current == record.get("merged_sha256")):
        if current != digest(saved_target):
            raise RuntimeError("Target changed after backup: " + str(target))
        if digest(source) != identity["source_sha256"]:
            raise RuntimeError("Source changed after backup: " + str(source))
        legacy = saved_source.read_bytes()
        if legacy and not legacy.endswith(b"\n"):
            legacy += b"\n"
        merged = legacy + saved_target.read_bytes()
        expected = hashlib.sha256(merged).hexdigest()
        completed[str(source)] = dict(identity, status="merging", base_sha256=current,
                                      merged_sha256=expected)
        write_json(marker, completed)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(merged)
        try:
            if digest(temporary) != expected:
                raise RuntimeError("Merge verification failed: " + str(target))
            if digest(target) != current:
                raise RuntimeError("Target changed during merge: " + str(target))
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    completed[str(source)] = dict(identity, status="complete")
    write_json(marker, completed)
    print("Merged and verified: " + str(target))


def main():
    home = Path.home()
    repository = Path(__file__).resolve().parent.parent
    installed = home / ".config/zsh"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-root", type=Path,
                        default=installed if installed.is_dir() else repository)
    parser.add_argument("--zlua-data", type=Path,
                        default=Path(os.environ.get("_ZL_DATA", str(home / ".zlua"))),
                        help="Back up this jump database without importing it")
    parser.add_argument("--copy-local", action="store_true",
                        help="Also copy config/env-self.zsh into XDG local.zsh")
    parser.add_argument("--apply", action="store_true", help="Apply; default is preview only")
    parser.add_argument("--old-sessions-closed", action="store_true",
                        help="Assert old shells have exited and flushed their history")
    args = parser.parse_args()
    legacy = args.legacy_root.expanduser().absolute()
    def xdg(name, fallback):
        base = Path(os.environ.get(name) or fallback)
        return (base if base.is_absolute() else fallback) / "omz"

    state = xdg("XDG_STATE_HOME", home / ".local/state")
    config = xdg("XDG_CONFIG_HOME", home / ".config")
    pairs = [
        (legacy / "cache/zshhistory", state / "zsh_history"),
        (legacy / "cache/fzfhistory", state / "fzf_query_history"),
        (legacy / "cache/currentdir", state / "last_directory"),
    ]
    if args.copy_local:
        pairs.append((legacy / "config/env-self.zsh", config / "local.zsh"))
    marker = state / "migrations/state-v1.json"
    completed = json.loads(marker.read_text()) if marker.exists() else {}
    if not isinstance(completed, dict) or not all(
            isinstance(value, dict) for value in completed.values()):
        raise RuntimeError("Invalid migration record: " + str(marker))
    pending = []
    conflicts = []
    for source, target in pairs:
        key = str(source)
        if source == target or target.is_symlink():
            conflicts.append(str(target) + " is a symlink or the source itself")
            status = "conflict"
        elif not source.exists():
            status = "missing source"
        elif not source.is_file():
            conflicts.append(str(source) + " is not a regular file")
            status = "conflict"
        elif key in completed and target.is_file() and completed[key] == {
                "target": str(target), "source_sha256": digest(source), "status": "complete"}:
            status = "already migrated (new target records preserved)"
        elif (key in completed and target.is_file() and completed[key] == {
                "target": str(target), "source_sha256": digest(source), "status": "copying"}
                and digest(target) == digest(source)):
            status = "resume verified copy"
            pending.append((source, target, "copy"))
        elif (source.name in MERGEABLE and target.is_file()
                and completed.get(key, {}).get("status") == "merging"
                and completed[key].get("target") == str(target)
                and completed[key].get("source_sha256") == digest(source)
                and digest(target) in (completed[key].get("base_sha256"),
                                       completed[key].get("merged_sha256"))):
            status = "resume merge"
            pending.append((source, target, "merge"))
        elif target.exists() and target.stat().st_size and key not in completed:
            if source.name in MERGEABLE:
                status = "merge (legacy records first, new records kept)"
                pending.append((source, target, "merge"))
            elif source.name == "currentdir":
                status = "target kept (newer)"
            else:
                conflicts.append(str(target) + " is nonempty; merge manually, then re-run")
                status = "conflict"
        elif target.exists() and target.stat().st_size:
            conflicts.append(str(target) + " is nonempty; merge manually, then re-run")
            status = "conflict"
        else:
            status = "copy"
            pending.append((source, target, "copy"))
        print("{} -> {} [{}]".format(source, target, status))
    jump = args.zlua_data.expanduser().absolute()
    print("Jump database (backup only): {} [{}]".format(
        jump, "present" if jump.is_file() else "missing"))
    print("Legacy personal configuration is never executed by the migration tool.")
    if conflicts:
        raise RuntimeError("\n".join(conflicts))
    if any(mode == "merge" for _, _, mode in pending):
        print("Merging rewrites the new history; close every shell, including new ones, first.")
    if not args.apply:
        print("Preview only. Use --apply; history also requires --old-sessions-closed.")
        return
    if any(source.name == "zshhistory" for source, _, _ in pending):
        if not args.old_sessions_closed:
            raise RuntimeError("Close old shells to flush history, then pass --old-sessions-closed.")
    if not pending:
        print("No pending copies.")
        return

    private_directory(state)
    private_directory(state / "backups")
    private_directory(state / "migrations")
    # flock releases on process exit, so a crashed migration does not leave a stale lock.
    lock = state / "migrations/state-v1.lock"
    lock_stream = lock.open("a+b")
    try:
        fcntl.flock(lock_stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        current = json.loads(marker.read_text()) if marker.exists() else {}
        if current != completed:
            raise RuntimeError("Migration record changed; retry the preview.")
        backup = Path(tempfile.mkdtemp(
            prefix="m1-" + datetime.now().strftime("%Y%m%d-%H%M%S-"),
            dir=state / "backups"))
        candidates = [Path(os.environ.get("ZDOTDIR") or home) / ".zshrc",
                      legacy / "config/env-self.zsh", config / "local.zsh", jump]
        candidates += [file for pair in pairs for file in pair]
        snapshots = {}
        manifest = []
        for original in dict.fromkeys(candidates):
            if original.is_file():
                saved = backup / "{:03d}.data".format(len(manifest))
                shutil.copyfile(original, saved)
                saved.chmod(0o600)
                checksum = digest(saved)
                if checksum != digest(original):
                    raise RuntimeError("Source changed during backup: " + str(original))
                manifest.append({"source": str(original), "file": saved.name,
                                 "sha256": checksum})
                snapshots[original] = saved
        revision = subprocess.run(["git", "-C", str(legacy), "rev-parse", "HEAD"],
                                  capture_output=True, text=True, check=False)
        write_json(backup / "manifest.json", {
            "legacy_root": str(legacy), "repository_revision": revision.stdout.strip(),
            "files": manifest,
            "scope": "M1 state copies only; z.lua database is backed up, not imported.",
        })
        print("Verified backup: " + str(backup))
        for source, target, mode in pending:
            private_directory(target.parent)
            saved = snapshots[source]
            if mode == "merge":
                merge_into(source, target, saved, snapshots[target], completed, marker)
                continue
            resumable = completed.get(str(source)) == {
                "target": str(target), "source_sha256": digest(saved), "status": "copying"}
            if target.is_symlink() or (target.exists() and target.stat().st_size and not (
                    resumable and digest(target) == digest(saved))):
                raise RuntimeError("Target changed after preview: " + str(target))
            if digest(source) != digest(saved):
                raise RuntimeError("Source changed after backup: " + str(source))
            completed[str(source)] = {
                "target": str(target), "source_sha256": digest(saved), "status": "copying"}
            write_json(marker, completed)
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(saved.read_bytes())
            try:
                if digest(temporary) != digest(saved):
                    raise RuntimeError("Copy verification failed: " + str(target))
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
            completed[str(source)] = {
                "target": str(target), "source_sha256": digest(saved), "status": "complete"}
            write_json(marker, completed)
            print("Copied and verified: " + str(target))
    finally:
        lock_stream.close()


if __name__ == "__main__":
    os.umask(0o077)
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        raise SystemExit("omz migration: " + str(error))
