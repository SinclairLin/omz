#!/usr/bin/env python3
"""Preview, import, or explicitly skip legacy jump data. Never runs during startup."""

import argparse
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile


HELPERS = runpy.run_path(str(Path(__file__).with_name("migrate-state.py")))
private_directory = HELPERS["private_directory"]
write_json = HELPERS["write_json"]
digest = HELPERS["digest"]


def checksum(path):
    return digest(path) if path.is_file() else None


def write_decision(path, source):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write((str(source) + "\n").encode())
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zlua-data", type=Path,
                        default=Path(os.environ.get("_ZL_DATA") or str(Path.home() / ".zlua")))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--skip-import", action="store_true",
                        help="Keep both databases and explicitly permit switching without import")
    parser.add_argument("--old-sessions-closed", action="store_true",
                        help="Assert sessions writing either jump database have stopped")
    args = parser.parse_args()
    home = Path.home()
    state_base = Path(os.environ.get("XDG_STATE_HOME") or home / ".local/state")
    if not state_base.is_absolute():
        state_base = home / ".local/state"
    state = state_base / "omz"
    source = Path(os.path.abspath(args.zlua_data.expanduser()))
    if "\n" in str(source):
        raise RuntimeError("Jump database paths containing newlines are unsupported.")
    data_base = Path(os.environ.get("XDG_DATA_HOME") or home / ".local/share")
    default_data = (home / "Library/Application Support/zoxide" if sys.platform == "darwin"
                    else data_base / "zoxide")
    data = Path(os.environ.get("_ZO_DATA_DIR") or default_data)
    if not data.is_absolute():
        raise RuntimeError("_ZO_DATA_DIR must be absolute.")
    target = data / "db.zo"
    decision = state / "migrations/jump-v1"
    record = state / "migrations/jump-v1.json"
    print("z.lua source: {} [{}]".format(source, "present" if source.is_file() else "missing"))
    print("zoxide target: {} [{}]".format(target, "present" if target.is_file() else "missing"))
    action = "skip import" if args.skip_import else "import and merge"
    print("Action: " + action)
    if not args.apply:
        print("Preview only. Use --apply --old-sessions-closed; --skip-import is explicit opt-out.")
        return
    if not args.old_sessions_closed:
        raise RuntimeError("Stop shells writing either database, then pass --old-sessions-closed.")
    if not args.skip_import and not source.is_file():
        raise RuntimeError("Missing source database; use --skip-import only to opt out explicitly.")
    if source.is_symlink() or target.is_symlink() or decision.is_symlink() or record.is_symlink():
        raise RuntimeError("Migration paths must not be symlinks.")
    private_directory(state / "migrations")
    private_directory(state / "backups")
    with (state / "migrations/jump-v1.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original = checksum(source)
        before = checksum(target)
        completed = json.loads(record.read_text()) if record.exists() else {}
        if not isinstance(completed, dict):
            raise RuntimeError("Invalid jump migration record: " + str(record))
        same_source = (completed.get("source") == str(source) and
                       completed.get("source_sha256") == original and
                       completed.get("target") == str(target))
        if same_source:
            if (completed.get("status") == "complete" and decision.is_file() and
                    decision.read_text().rstrip("\n") == str(source)):
                print("Already decided; later records in either database are preserved.")
                return
            if (completed.get("status") in ("prepared", "complete") and
                    completed.get("target_sha256") == before):
                completed["status"] = "complete"
                write_json(record, completed)
                write_decision(decision, source)
                print("Recovered verified import; no records imported twice.")
                return
            if (completed.get("status") == "prepared" and
                    completed.get("before_sha256") == before):
                completed = {}
        if completed:
            raise RuntimeError("Previous migration record differs; preserve it and review before re-importing.")
        binary = shutil.which("zoxide")
        if not args.skip_import:
            if not binary:
                raise RuntimeError("Install zoxide before importing.")
            help_result = subprocess.run([binary, "import", "--help"], capture_output=True,
                                         text=True, check=True)
            if "z.lua" not in help_result.stdout:
                raise RuntimeError("This importer requires zoxide 0.10.0+ with 'import z.lua'.")
        backup = Path(tempfile.mkdtemp(
            prefix="m3-" + datetime.now().strftime("%Y%m%d-%H%M%S-"), dir=state / "backups"))
        manifest = []
        for name, path in (("zlua.data", source), ("zoxide.db", target)):
            if path.is_file():
                saved = backup / name
                shutil.copyfile(path, saved)
                saved.chmod(0o600)
                if digest(saved) != digest(path):
                    raise RuntimeError("Database changed during backup: " + str(path))
                manifest.append({"source": str(path), "file": name, "sha256": digest(saved)})
        write_json(backup / "manifest.json", {"files": manifest, "action": action})
        print("Verified backup: " + str(backup))
        if not args.skip_import:
            # Upstream imports into a staged copy. Failure leaves the live database intact.
            private_directory(data)
            with tempfile.TemporaryDirectory(prefix=".omz-import-", dir=data) as directory:
                stage = Path(directory)
                if target.exists():
                    shutil.copyfile(backup / "zoxide.db", stage / "db.zo")
                env = dict(os.environ, _ZO_DATA_DIR=str(stage), _ZL_DATA=str(backup / "zlua.data"))
                result = subprocess.run([binary, "import", "z.lua", "--merge"],
                                        env=env, capture_output=True, text=True)
                if result.returncode:
                    raise RuntimeError("zoxide import failed: " + result.stderr.strip())
                # Decode the resulting database through the upstream reader before committing it.
                result = subprocess.run([binary, "query", "--all", "--list"], env=env,
                                        capture_output=True, text=True)
                if (result.returncode not in (0, 1) or
                        (result.returncode == 1 and "no match found" not in result.stderr) or
                        not (stage / "db.zo").is_file()):
                    raise RuntimeError("Imported database could not be verified.")
                if checksum(source) != original or checksum(target) != before:
                    raise RuntimeError("A database changed during import; stop old sessions and retry.")
                write_json(record, {
                    "source": str(source), "source_sha256": original, "target": str(target),
                    "before_sha256": before, "target_sha256": digest(stage / "db.zo"),
                    "backup": str(backup), "action": action, "status": "prepared"})
                (stage / "db.zo").chmod(0o600)
                (stage / "db.zo").replace(target)
        elif checksum(source) != original or checksum(target) != before:
            raise RuntimeError("A database changed during backup; stop old sessions and retry.")
        # Keep a recoverable record if interrupted before enabling the backend.
        write_json(record, {"source": str(source), "source_sha256": original,
                            "target": str(target), "target_sha256": checksum(target),
                            "backup": str(backup), "action": action, "status": "complete"})
        write_decision(decision, source)
        print("Decision recorded. Rebuild plugins for the chosen backend, then open a new shell.")


if __name__ == "__main__":
    os.umask(0o077)
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit("omz jump migration: " + str(error))
