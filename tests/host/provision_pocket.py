#!/usr/bin/env python3
"""Provision unmodified PUBLIC Pi Pocket v0.14.0, isolated from the owner's running app."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import tarfile
import tempfile
import urllib.request

REVISION = "e5456a832d47e7154faf04320dd7602ae5051bf7"
URL = f"https://codeload.github.com/TannerMidd/pi-pocket/tar.gz/{REVISION}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-dependencies", required=True, type=Path,
                        help="Existing public Pocket 0.14 node_modules, read-only reuse; no installation")
    parser.add_argument("--evidence-dir", required=True, type=Path)
    args = parser.parse_args()
    dependencies = args.public_dependencies.resolve()
    peers = {}
    for name in ("pi-durable", "pi-ai", "chord"):
        peer = "@earendil-works/" + name
        peers[peer] = json.loads((dependencies / peer / "package.json").read_text())["version"]
        if peers[peer] != "1.1.0":
            raise ValueError(f"Public Pocket 0.14 requires {peer} 1.1.0, got {peers[peer]}")
    sandbox = Path(tempfile.mkdtemp(prefix="delm-clean-pocket-"))
    source, home, project, data = (sandbox / name for name in ("upstream", "home", "project", "data"))
    for path in (source, home, project, data):
        path.mkdir()
    with urllib.request.urlopen(URL, timeout=60) as response:
        archive = response.read(64 * 1024 * 1024 + 1)
    if len(archive) > 64 * 1024 * 1024:
        raise ValueError("public source archive exceeds fixture download bound")
    hashes = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        total = 0
        for member in tar:
            parts = PurePosixPath(member.name).parts[1:]
            if not parts:
                continue
            if ".." in parts or not (member.isfile() or member.isdir()):
                raise ValueError("unexpected source archive member")
            path = source.joinpath(*parts)
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
                continue
            total += member.size
            if total > 192 * 1024 * 1024:
                raise ValueError("public source fixture exceeds extraction bound")
            body = tar.extractfile(member).read()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            path.chmod(member.mode & 0o755)
            hashes["/".join(parts)] = hashlib.sha256(body).hexdigest()
    (source / "node_modules").symlink_to(dependencies, target_is_directory=True)
    env = dict(PATH=os.pathsep.join(p for p in os.environ["PATH"].split(os.pathsep) if "delm-runs" not in p),
               HOME=str(home), LANG="C.UTF-8", TERM="xterm-256color", PI_OFFLINE="1", PI_TELEMETRY="0",
               PI_CODING_AGENT_DIR=str(home / ".pi/agent"), PI_POCKET_DIR=str(data), PYTHONDONTWRITEBYTECODE="1")
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    record = dict(schema=1, repository="https://github.com/TannerMidd/pi-pocket", tag="v0.14.0", revision=REVISION,
                  archive_sha256=hashlib.sha256(archive).hexdigest(), source_files=len(hashes),
                  peers=peers, source_hashes=hashes, source_patched=False, new_harness=False,
                  dependency_install=False, private_author_settings=False)
    (evidence / "pocket-source.json").write_text(json.dumps(record, indent=2) + "\n")
    (sandbox / "fixture.json").write_text(json.dumps(dict(source=str(source), home=str(home), data=str(data),
        project=str(project), env=env, evidence=str(evidence), source_record=record)))
    print(json.dumps(dict(fixture=str(sandbox / "fixture.json"), revision=REVISION,
                         source_files=len(hashes), archive_sha256=record["archive_sha256"])))


if __name__ == "__main__":
    main()
