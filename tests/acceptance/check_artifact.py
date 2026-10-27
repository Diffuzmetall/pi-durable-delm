#!/usr/bin/env python3
"""Verify the assembled local payload in a disposable HOME; never install dependencies."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tarfile
import tempfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    archive = args.archive.resolve()
    evidence = args.evidence_dir.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    sandbox = Path(tempfile.mkdtemp(prefix="delm-artifact-accept-"))
    home = sandbox / "home"
    home.mkdir()
    env = {"PATH": os.pathsep.join(p for p in os.environ["PATH"].split(os.pathsep)
                                  if "delm-runs" not in p),
           "HOME": str(home), "PYTHONDONTWRITEBYTECODE": "1", "LANG": "C.UTF-8",
           "TERM": "xterm-256color", "TMPDIR": str(sandbox), "PI_OFFLINE": "1", "PI_TELEMETRY": "0"}
    if os.environ.get("DELM_TEST_NODE_MODULES"):
        env["DELM_TEST_NODE_MODULES"] = os.environ["DELM_TEST_NODE_MODULES"]
    checks = []

    def redact(value):
        text = str(value).replace(str(sandbox), "<SANDBOX>")
        if os.environ.get("DELM_TEST_PI_MODULES"):
            probe_uri = (Path(os.environ["DELM_TEST_PI_MODULES"]).resolve().parent / "__public_skill_probe__.mjs").as_uri()
            text = text.replace(probe_uri, "file://<PUBLIC_SKILL_PROBE>")
        roots = env.get("DELM_TEST_NODE_MODULES", "").split(os.pathsep)
        roots.append(os.environ.get("DELM_TEST_PI_MODULES", ""))
        roots.append(os.environ.get("DELM_TEST_NATIVE_SOURCE", ""))
        for dependency_root in filter(None, roots):
            text = text.replace(str(Path(dependency_root).resolve()), "<PUBLIC_DEPENDENCIES>")
        return text

    def command(label, argv, cwd=sandbox, expected=0, extra_env=None):
        result = subprocess.run(argv, cwd=cwd, env=env | (extra_env or {}), text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
        text = redact(result.stdout)
        (evidence / (label + ".log")).write_text(text)
        checks.append(dict(check=label, exit_code=result.returncode, expected=expected,
                           passed=result.returncode == expected,
                           argv=[redact(a) for a in argv]))
        assert result.returncode == expected, f"{label} failed; see {evidence / (label + '.log')}"
        return result.stdout

    with tarfile.open(archive, "r:gz") as tar:
        members = [m for m in tar if m.isfile()]
        payload = {m.name.removeprefix("package/"): tar.extractfile(m).read() for m in members}
        assert all(m.name.startswith("package/") and not m.issym() and not m.islnk() for m in members)
        bootstrap = tar.extractfile("package/packaging/install.py").read()
    assert all(not any(part in {".local", ".git", "__pycache__", "node_modules"}
                       for part in Path(name).parts) for name in payload)
    assert not [name for name in payload if name.endswith((".sqlite", ".sqlite-wal", ".pyc"))
                or Path(name).name.lower() == "config.json"]
    # Negative assertions are deny-list literals, not dependencies on those directories.
    home_path = re.compile(rb"/home/[A-Za-z0-9._-]+/")
    def unmasked(line):
        # Only an explicitly redacted sandbox path may contain a nested home/.pi subtree.
        return re.sub(rb"<SANDBOX>/[A-Za-z0-9._%+@~/-]+", b"<REDACTED_PATH>", line)
    assert home_path.search(unmasked(b"/" + b"home/example/private"))
    assert not home_path.search(unmasked(b"<SANDBOX>/child/home/.pi/server"))
    assert home_path.search(unmasked(b"<SANDBOX>/child; /" + b"home/example/private"))
    assert home_path.search(unmasked(b"<SANDBOX>/child,/" + b"home/example/private"))
    assert home_path.search(unmasked(b"<SANDBOX>/child=/" + b"home/example/private"))
    private_lane = re.compile(rb"(?:host|extensions)-lane/")
    guard_literals = [name for name, body in payload.items()
                      if any(b"assertNotIn(" in line and home_path.search(unmasked(line)) for line in body.splitlines())]
    private_hits = [name for name, body in payload.items()
                    if any((home_path.search(unmasked(line)) and b"assertNotIn(" not in line)
                           or private_lane.search(unmasked(line))
                           for line in body.splitlines())]
    assert not private_hits, f"private installation roots in artifact: {private_hits}"
    provenance = json.loads(payload["provenance.json"])
    for entry in provenance["files"]:
        assert sha(payload[entry["target"]]) == entry["packaged_sha256"], entry["target"]
    metadata = json.loads(payload["package.json"])
    assert metadata["private"] and metadata["license"] == "MIT"
    assert payload["LICENSE"].startswith(b"MIT License\n")
    assert metadata["pi"]["extensions"] == [] and metadata["pi"]["skills"] == ["./skills/delm"]
    (sandbox / "install.py").write_bytes(bootstrap)
    prefix = sandbox / "installed"
    manager = [sys.executable, "-B", str(sandbox / "install.py")]
    first = json.loads(command("install", manager + ["install", str(archive), "--prefix", str(prefix)]))
    assert first["status"] == "installed" and first["native_registered"] is False
    root = (prefix / "current").resolve()
    assert root.is_relative_to(prefix)
    assert all(sha((root / name).read_bytes()) == sha(body) for name, body in payload.items())
    dependency_roots = [Path(p) for p in env.get("DELM_TEST_NODE_MODULES", "").split(os.pathsep) if p]
    dependency_versions, dependency_locations = {}, {}
    source_peer = {"@earendil-works/pi-client":"client", "@earendil-works/pi-durable":"durable",
                   "@earendil-works/pi-ai":"ai", "@earendil-works/chord":"chord"}
    for peer, expected in metadata["peerDependencies"].items():
        allowed = expected.split(" || ")
        assert all(re.fullmatch(r"\d+\.\d+\.\d+", version) for version in allowed), expected
        manifests = [p / peer / "package.json" for p in [root / "node_modules", *dependency_roots]]
        source_manifest = None
        if peer in source_peer and os.environ.get("DELM_TEST_NATIVE_SOURCE"):
            source_manifest = Path(os.environ["DELM_TEST_NATIVE_SOURCE"]) / "packages" / source_peer[peer] / "package.json"
            manifests.insert(0, source_manifest)
        manifest = next((p for p in manifests if p.is_file() and json.loads(p.read_text())["version"] in allowed), None)
        assert manifest, f"Missing compatible declared PUBLIC test dependency {peer} {expected}; no installation attempted"
        dependency_versions[peer] = json.loads(manifest.read_text())["version"]
        dependency_locations[peer] = dict(manifest=redact(manifest), public_test_source=manifest==source_manifest)

    repeat = json.loads(command("repeat-install", manager + ["install", str(archive), "--prefix", str(prefix)]))
    assert repeat["status"] == "unchanged"
    command("installed-bin", [str(root / "bin/delm"), "--help"])
    command("python", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"], root)
    command("packaging", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests/packaging", "-v"], root)
    command("launcher-python", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests/launcher", "-v"], root)
    command("demo", [sys.executable, "-B", "-m", "unittest", "discover", "-s", "examples/slugify", "-v"], root)
    assert command("demo-cli", [sys.executable, "examples/slugify/slugify.py", "Привет, мир!"], root).strip() == "привет-мир"
    node_files = ["tests/delm-durable.test.mjs", "tests/delm-reload.test.mjs", "tests/delm-first-slice.test.mjs",
                  "tests/delm-native-v2.test.mjs", "tests/delm-remaining-integration.test.mjs",
                  "tests/launcher/input-sdk.test.mjs"]
    if os.environ.get("DELM_TEST_NATIVE_SOURCE"):
        source_resolver = Path(os.environ["DELM_TEST_NATIVE_SOURCE"]) / "packages/coding-agent/src/experimental/source-resolver.ts"
        command("native-sdk-faux", ["node", "--import", str(root / "tests/host/public-dependencies.mjs"),
                "--import", str(source_resolver), "--test", *node_files], root,
                extra_env={"DELM_HOST_DEPENDENCY_ROOTS": env.get("DELM_TEST_NODE_MODULES", "")})
    else:
        command("native-sdk-faux", ["node", "--import", "./tests/native/sdk-loader.mjs", "--test", *node_files], root)
    # Ordinary Pi and Durable SDK may use different dependency trees; do not mix them with a hook.
    pi_modules = Path(os.environ.get("DELM_TEST_PI_MODULES", str(root / "node_modules"))).resolve()
    pi_parent = (pi_modules.parent / "__public_skill_probe__.mjs").as_uri()
    skill_probe = (f"const entry=import.meta.resolve('@earendil-works/pi-coding-agent',{json.dumps(pi_parent)});"
                   "const {loadSkillsFromDir}=await import(entry);"
                   "const r=loadSkillsFromDir({dir:'./skills/delm',source:'artifact-acceptance'});"
                   "if(r.skills.length!==1||r.skills[0].name!=='delm'||r.diagnostics.length)"
                   "throw Error(JSON.stringify(r));console.log('ordinary Pi skill parser: delm discovered; NOT Native host discovery');")
    command("skill-discovery", ["node", "--experimental-import-meta-resolve", "--input-type=module", "-e", skill_probe], root)
    location_probe = ("import sys,pathlib;sys.path.insert(0,'scripts');import delm_local,delm_domain,delm_delivery,delm_leases;"
                      "root=pathlib.Path.cwd();mods=[m for n,m in sys.modules.items() if n.startswith(('delm_','board','runtime')) and getattr(m,'__file__',None)];"
                      "assert mods;assert all(pathlib.Path(m.__file__).resolve().is_relative_to(root) for m in mods);"
                      "print('import closure entirely inside installed payload:',len(mods),'modules')")
    command("import-closure", [sys.executable, "-B", "-c", location_probe], root)
    # A doc-only successor exercises real full-payload update without changing tested executable bytes.
    successor = sandbox / "doc-update.tgz"
    with tarfile.open(successor, "w:gz") as target, tarfile.open(archive, "r:gz") as source:
        for member in source:
            if member.isfile():
                body = source.extractfile(member).read()
                if member.name == "package/README.md":
                    body += b"\nLocal acceptance update fixture; not another published version.\n"
                member.size = len(body)
                target.addfile(member, io.BytesIO(body))
            else:
                target.addfile(member)
    retained = prefix / "user-run"
    retained.mkdir()
    (retained / "history.txt").write_text("unmanaged history must survive")
    command("update", manager + ["install", str(successor), "--prefix", str(prefix)])
    assert (prefix / "current").resolve() != root
    command("rollback", manager + ["rollback", "--prefix", str(prefix)])
    assert (prefix / "current").resolve() == root
    assert all(sha((root / name).read_bytes()) == sha(body) for name, body in payload.items())
    (root / "user-notes.txt").write_text("unmanaged edits must survive")
    command("refuse-edited-update", manager + ["install", str(successor), "--prefix", str(prefix)], expected=1)
    removed = json.loads(command("uninstall", manager + ["uninstall", "--prefix", str(prefix)]))
    assert str(root) in removed["retained"]
    assert (root / "user-notes.txt").read_text() == "unmanaged edits must survive"
    assert (retained / "history.txt").read_text() == "unmanaged history must survive"
    report = dict(schema=2, verdict="LOCAL_ARTIFACT_COMPONENT_PASS_INSTALLED_NATIVE_CHECK_SEPARATE",
                  archive_sha256=sha(archive.read_bytes()), files=len(payload),
                  runtime_hashes={e["target"]: e["packaged_sha256"] for e in provenance["files"]},
                  environment=dict(python=platform.python_version(), platform=platform.system(), architecture=platform.machine(),
                                   node=command("node-version", ["node", "--version"]).strip(), public_dependencies=dependency_versions,
                                   ordinary_pi=json.loads((pi_modules / "@earendil-works/pi-coding-agent/package.json").read_text())["version"],
                                   dependency_manifests=dependency_locations),
                  checks=checks, private_root_hits=private_hits, negative_test_guard_literals=guard_literals,
                  source_imports=dict(product_checkout=False, public_sdk_test_source=bool(os.environ.get("DELM_TEST_NATIVE_SOURCE"))), real_model_calls=0,
                  log_hashes={p.name: sha(p.read_bytes()) for p in evidence.glob("*.log")},
                  limits=["ordinary Pi skill parsing is not stock Native registry/protected-admission discovery",
                          "Native SDK/faux is not live model or editor draft verification",
                          "payload rollback tested; actual downgrade to older Native work-unaware runtime NOT_TESTED",
                          "product import closure is installed payload; explicitly selected public SDK source may supply TEST platform dependencies", 
                          "existing public Node dependencies supplied explicitly; none installed"])
    (evidence / "acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(verdict=report["verdict"], archive_sha256=report["archive_sha256"],
                          checks=len(checks), evidence=str(evidence), sandbox=str(sandbox), installed_root=str(root))))


if __name__ == "__main__":
    main()
