#!/usr/bin/env python3
"""Fetch an unmodified official public host snapshot into disposable test storage.

No package install, registry/Harness creation, private wrapper, host patch or model call.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile
import urllib.request

REVISION = "cd32f7725fdbddbaecdff5b1e68491563394e0ca"  # public stable v1.0.2
URL = f"https://codeload.github.com/earendil-works/pi/tar.gz/{REVISION}"
CATALOG_URL = "https://registry.npmjs.org/@earendil-works/pi-ai/-/pi-ai-1.0.2.tgz"
CATALOG_SHA256 = "8ac8e5fabd65e0f0ecb8538b6211824859f5997594005d7a03e1f70b38438a17"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dependency-root", action="append", default=[], type=Path,
                        help="Existing public node_modules; never installs or copies author host")
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    sandbox = Path(tempfile.mkdtemp(prefix="delm-public-host-"))
    home, project, source = (sandbox / name for name in ("home", "project", "upstream"))
    for directory in (home, project, source):
        directory.mkdir()
    with urllib.request.urlopen(URL, timeout=60) as response:
        archive = response.read(64 * 1024 * 1024 + 1)
    if len(archive) > 64 * 1024 * 1024:
        raise ValueError("public source archive exceeds bounded fixture download")
    paths = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        total = 0
        for member in tar:
            parts = PurePosixPath(member.name).parts[1:]
            if not parts or parts[0] not in {"packages", "tsconfig.json", "package.json", "LICENSE", "pi-test.sh"}:
                continue
            if ".." in parts or not (member.isfile() or member.isdir()):
                raise ValueError("unexpected unsafe source archive member")
            target = source.joinpath(*parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            total += member.size
            if total > 192 * 1024 * 1024:
                raise ValueError("public source fixture exceeds bounded extraction")
            body = tar.extractfile(member).read()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            target.chmod(member.mode & 0o755)
            paths["/".join(parts)] = hashlib.sha256(body).hexdigest()
    # Official source builds require generated model JSON, omitted from Git.
    # Hydrate only matching published JSON assets; no SDK code/dependency is installed.
    with urllib.request.urlopen(CATALOG_URL, timeout=45) as response:
        catalog = response.read(20 * 1024 * 1024 + 1)
    if hashlib.sha256(catalog).hexdigest() != CATALOG_SHA256:
        raise ValueError("pinned public model metadata archive changed")
    catalog_files = 0
    data = source / "packages/ai/src/providers/data"
    data.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(catalog), mode="r:gz") as tar:
        for member in tar:
            prefix = "package/dist/providers/data/"
            if member.isfile() and member.name.startswith(prefix):
                name = member.name[len(prefix):]
                if "/" in name or not name.endswith(".json"):
                    raise ValueError("unexpected generated metadata path")
                (data / name).write_bytes(tar.extractfile(member).read())
                catalog_files += 1
    roots = [str(p.resolve()) for p in args.dependency_root]
    fallback = Path(__file__).with_name("public-dependencies.mjs").resolve()
    env = {"PATH": os.pathsep.join(p for p in os.environ["PATH"].split(os.pathsep) if "delm-runs" not in p),
           "HOME": str(home), "LANG": "C.UTF-8",
           "TERM": "xterm-256color", "PI_OFFLINE": "1", "PI_EXPERIMENTAL": "1", "PI_TELEMETRY": "0",
           "PYTHONDONTWRITEBYTECODE": "1", "NODE_OPTIONS": "--import=" + fallback.as_uri(),
           "PI_CODING_AGENT_DIR": str(home / ".pi/agent"),
           "DELM_HOST_DEPENDENCY_ROOTS": os.pathsep.join(roots)}
    resolver = source / "packages/coding-agent/src/experimental/source-resolver.ts"
    cli = source / "packages/coding-agent/src/experimental/cli.ts"
    validated = subprocess.run(["node", str(source / "packages/ai/scripts/check-model-data.ts")],
                               cwd=project, env=env, text=True, capture_output=True, timeout=20)
    if validated.returncode:
        raise RuntimeError("official generated catalog validation failed")
    command = ["node", "--import", str(resolver), str(cli), "--version"]
    result = subprocess.run(command, cwd=project, env=env, text=True, capture_output=True, timeout=40)
    transcript = result.stdout + result.stderr
    for original, replacement in [(str(sandbox), "<SANDBOX>"),
            (str(Path(__file__).resolve().parents[2]), "<TARGET>"),
            *[(r, "<PUBLIC_DEPENDENCIES>") for r in roots]]:
        transcript = transcript.replace(original, replacement)
    (evidence / "public-cli-version.log").write_text(transcript)
    record = dict(schema=1, upstream="https://github.com/earendil-works/pi", tag="v1.0.2", revision=REVISION,
                  archive_sha256=hashlib.sha256(archive).hexdigest(), source_files=len(paths),
                  source_hashes={p: h for p, h in paths.items() if p.startswith("packages/coding-agent/src/experimental/")},
                  official_entry="packages/coding-agent/src/experimental/cli.ts",
                  catalog_json_files=catalog_files, catalog_archive_sha256=CATALOG_SHA256,
                  catalog_validation_exit=validated.returncode,
                  exit_code=result.returncode, plugin_discovery="NOT_YET_TESTED", real_model_calls=0,
                  replaced_host=False, source_patches=False, installed_dependencies=False)
    (evidence / "public-host-discovery.json").write_text(json.dumps(record, indent=2) + "\n")
    # Local locator contains no credentials; it is not included in published evidence.
    (sandbox / "fixture.json").write_text(json.dumps(dict(source=str(source), home=str(home),
        project=str(project), env=env, command=command, evidence=str(evidence))))
    print(json.dumps(dict(sandbox=str(sandbox), exit_code=result.returncode, source_files=len(paths),
                          archive_sha256=record["archive_sha256"], evidence=str(evidence))))


if __name__ == "__main__":
    main()
