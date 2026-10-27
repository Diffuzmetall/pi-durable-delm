#!/usr/bin/env python3
"""Real patched PUBLIC Native host loads byte-identical released DeLM product files via its OWN bundler."""
import argparse
import hashlib
import json
from pathlib import Path
from deterministic_provider import DeterministicProvider
from native_process import NativeProcess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text())
    source, evidence = Path(fixture["source"]), Path(fixture["evidence"])
    patch = json.loads((evidence / "api-patch.json").read_text())
    for path, expected in patch["postimages"].items():
        assert hashlib.sha256((source / path).read_bytes()).hexdigest() == expected, path
    target = Path(__file__).resolve().parents[2]
    product_files = ["package.json", "extensions/delm/session-facet.js", "extensions/delm/control.js", "extensions/delm/index.js",
                     "extensions/delm/protocol.js", "skills/delm/Tools/NativeInput.mjs"]
    hashes = {name: hashlib.sha256((target / name).read_bytes()).hexdigest() for name in product_files}
    candidate = dict(product_sha256=hashes, producer_handoff_sequence=660,
                     loader_metadata="Actual Native-only product package.json; no fixture-generated replacement",
                     installed_archive="NOT_YET_TESTED", api_patch_sha256=patch["patch_sha256"])
    (evidence / "delm-package-candidate.json").write_text(json.dumps(candidate, indent=2) + "\n")
    host = NativeProcess(args.fixture, plugins=[target], log="delm-plugin-server.log")
    with DeterministicProvider() as provider:
        agent = Path(host.env["PI_CODING_AGENT_DIR"])
        agent.mkdir(parents=True, exist_ok=True)
        (agent / "models.json").write_text(json.dumps(provider.models_config()))
        with host:
            client = host.probe(Path(__file__).with_name("probe_native_delm.mjs"), {
                "DELM_NATIVE_EXPECTED_WORKSPACE": fixture["project"], "DELM_NATIVE_EXPECTED_SESSIONS": str(host.sessions)})
            (evidence / "delm-plugin-client.log").write_text(host.redact(client.stdout + client.stderr))
            assert client.returncode == 0, "Actual patched Native DeLM failed; see delm-plugin-client.log"
            result = json.loads(client.stdout)
        assert host.process.returncode == 0
        assert all(hashlib.sha256((target / name).read_bytes()).hexdigest() == expected for name, expected in hashes.items()), "Producer changed candidate during verification"
        assert provider.requests == 2, provider.requests
        result.update(public_native_revision=patch["source_revision"], source_variant=patch["source_variant"],
                      api_patch_sha256=patch["patch_sha256"], live_model_calls=0, deterministic_http_requests=provider.requests,
                      native_sigint_exit=0, product_source_sha256=hashes, final_package_acceptance="NOT_YET_TESTED")
        (evidence / "delm-plugin-result.json").write_text(host.redact(json.dumps(result, indent=2)) + "\n")
        print(host.redact(json.dumps(result)))


if __name__ == "__main__":
    main()
