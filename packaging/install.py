#!/usr/bin/env python3
"""Local payload install/rollback/removal, NOT Native plugin registration.

Version trees are never overwritten. Only clean, hash-recorded trees are removed;
modified/unknown files and run data are retained. No global settings are touched.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile
import uuid

MARKER = ".delm-managed.json"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def files(root):
    result = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("installed payload contains a symlink; preserve and reconcile")
        if path.is_file() and path.relative_to(root).as_posix() != MARKER:
            result[path.relative_to(root).as_posix()] = digest(path.read_bytes())
    return result


def state(prefix, name="current"):
    if (prefix / "versions").is_symlink():
        raise ValueError("versions directory must not be a symlink")
    pointer = prefix / name
    if not pointer.exists() and not pointer.is_symlink():
        return None
    if not pointer.is_symlink() or not re.fullmatch(r"versions/[0-9a-f]{64}", os.readlink(pointer)):
        raise ValueError(f"{name} is not an installer-managed pointer; refusing overwrite")
    root = prefix / os.readlink(pointer)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("managed version is missing or replaced; reconcile before changing")
    record = json.loads((root / MARKER).read_text())
    if record.get("schema") != 1 or record.get("archive_sha256") != root.name:
        raise ValueError("invalid managed manifest")
    return root, record


def clean(entry):
    root, record = entry
    if files(root) != record["files"]:
        raise ValueError("managed files were modified or new files exist; preserve them before update/rollback")


def point(prefix, name, target):
    state(prefix, name)  # Refuse replacing an unrelated file/directory.
    temporary = prefix / (".pointer-" + uuid.uuid4().hex)
    try:
        temporary.symlink_to(target.relative_to(prefix))
        os.replace(temporary, prefix / name)
    finally:
        temporary.unlink(missing_ok=True)


def unpack(archive, target):
    total, seen = 0, set()
    with tarfile.open(archive, "r:gz") as source:
        for member in source:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "package":
                raise ValueError("archive path outside package")
            relative = PurePosixPath(*path.parts[1:])
            if str(relative) == ".":
                if not member.isdir():
                    raise ValueError("invalid archive root")
                continue
            if str(relative) == MARKER or not (member.isdir() or member.isfile()):
                raise ValueError("archive links/special files/managed marker are not allowed")
            destination = target.joinpath(*relative.parts)
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            if relative in seen:
                raise ValueError("duplicate archive file")
            seen.add(relative)
            total += member.size
            if total > 32 * 1024 * 1024 or len(seen) > 4000:
                raise ValueError("payload exceeds local installer safety bound")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source.extractfile(member) as reader, destination.open("xb") as writer:
                shutil.copyfileobj(reader, writer)
            destination.chmod(member.mode & 0o755)
    metadata = json.loads((target / "package.json").read_text())
    if metadata.get("name") != "pi-durable-delm":
        raise ValueError("archive is not a pi-durable-delm payload")
    return metadata


def install(archive, prefix):
    prefix = Path(prefix).resolve()
    prefix.mkdir(parents=True, exist_ok=True)
    old = state(prefix)
    state(prefix, "previous")
    if old:
        clean(old)
    identity = digest(Path(archive).read_bytes())
    versions = prefix / "versions"
    if versions.is_symlink():
        raise ValueError("versions directory must not be a symlink")
    versions.mkdir(exist_ok=True)
    root = versions / identity
    if root.exists() or root.is_symlink():
        if root.is_symlink():
            raise ValueError("version path is a symlink")
        record = json.loads((root / MARKER).read_text())
        if record.get("schema") != 1 or record.get("archive_sha256") != identity:
            raise ValueError("existing version is not managed")
        clean((root, record))
    else:
        with tempfile.TemporaryDirectory(prefix=".stage-", dir=prefix) as staging:
            payload = Path(staging) / "payload"
            payload.mkdir()
            metadata = unpack(archive, payload)
            record = dict(schema=1, archive_sha256=identity, version=metadata["version"], files=files(payload))
            (payload / MARKER).write_text(json.dumps(record, sort_keys=True, indent=2) + "\n")
            os.rename(payload, root)
    if old and old[0] == root:
        return dict(status="unchanged", root=str(root), native_registered=False)
    if old:
        point(prefix, "previous", old[0])
    point(prefix, "current", root)
    return dict(status="installed", root=str(root), command=str(prefix / "current/bin/delm"), native_registered=False)


def rollback(prefix):
    prefix = Path(prefix).resolve()
    current, previous = state(prefix), state(prefix, "previous")
    if not current or not previous:
        raise ValueError("rollback requires a current and previous managed version")
    clean(current)
    clean(previous)
    point(prefix, "current", previous[0])
    point(prefix, "previous", current[0])
    return dict(status="rolled-back", root=str(previous[0]), native_registered=False)


def uninstall(prefix):
    prefix = Path(prefix).resolve()
    current, previous = state(prefix), state(prefix, "previous")
    retained, removed = [], []
    if not current and not previous:
        return dict(status="not-installed", retained=[], removed=[], native_registered=False)
    for name in ("current", "previous"):
        (prefix / name).unlink(missing_ok=True)
    versions = prefix / "versions"
    if versions.is_symlink():
        raise ValueError("versions directory must not be a symlink")
    for root in versions.iterdir():
        if root.is_symlink() or not re.fullmatch("[0-9a-f]{64}", root.name):
            retained.append(str(root))
            continue
        try:
            record = json.loads((root / MARKER).read_text())
            if record.get("schema") != 1 or record.get("archive_sha256") != root.name:
                raise ValueError("not managed")
            clean((root, record))
        except (OSError, ValueError, KeyError):
            retained.append(str(root))
            continue
        shutil.rmtree(root)
        removed.append(str(root))
    return dict(status="uninstalled", removed=removed, retained=retained, native_registered=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    for action in ("install", "rollback", "uninstall"):
        command = actions.add_parser(action)
        if action == "install":
            command.add_argument("archive", type=Path)
        command.add_argument("--prefix", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = install(args.archive, args.prefix) if args.action == "install" else globals()[args.action](args.prefix)
    except (OSError, ValueError, KeyError, tarfile.TarError) as error:
        parser.exit(1, f"Payload operation refused: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
