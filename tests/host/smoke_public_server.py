#!/usr/bin/env python3
"""Official unmodified public Native server/client/plugin with a deterministic MODEL only."""
import argparse
import json
from pathlib import Path
from deterministic_provider import DeterministicProvider
from native_process import NativeProcess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args()
    host = NativeProcess(args.fixture, session_directory=args.fixture.resolve().parent / "deterministic-sessions",
                         log="public-server-deterministic.log")
    host.assert_original_source()
    with DeterministicProvider() as provider:
        agent = Path(host.env["PI_CODING_AGENT_DIR"])
        agent.mkdir(parents=True, exist_ok=True)
        (agent / "models.json").write_text(json.dumps(provider.models_config()))
        with host:
            client = host.probe(Path(__file__).with_name("probe_public_client.mjs"))
            (host.evidence / "public-client-smoke.log").write_text(host.redact(client.stdout + client.stderr))
            if client.returncode:
                raise RuntimeError("Official host client probe failed; see public-client-smoke.log")
            result = json.loads(client.stdout)
            assert provider.requests == 2, provider.requests
        assert host.process.returncode == 0, host.process.returncode
        result.update(model_http_requests=provider.requests, revision="cd32f7725fdbddbaecdff5b1e68491563394e0ca",
                      replacedHost=False, modifiedHostSource=False, deLMPlugin="NOT_YET_TESTED", officialServerExitCode=0)
        (host.evidence / "public-host-smoke.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))


if __name__ == "__main__":
    main()
