#!/usr/bin/env python3
"""Actual public Native server restart + exact session/history reattachment; no model/host mocking."""
import argparse
import json
from pathlib import Path
import uuid
from deterministic_provider import DeterministicProvider
from native_process import NativeProcess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args()
    server_id = str(uuid.uuid4())
    phases = []
    with DeterministicProvider() as provider:
        for phase in ("create", "resume"):
            host = NativeProcess(args.fixture, server_id=server_id,
                session_directory=args.fixture.resolve().parent / "native-lifecycle-sessions", log=f"native-lifecycle/{phase}-server.log")
            host.assert_original_source()
            output = host.evidence / "native-lifecycle"
            output.mkdir(exist_ok=True)
            agent = Path(host.env["PI_CODING_AGENT_DIR"])
            agent.mkdir(parents=True, exist_ok=True)
            (agent / "models.json").write_text(json.dumps(provider.models_config()))
            with host:
                client = host.probe(Path(__file__).with_name("probe_native_lifecycle.mjs"), {
                    "DELM_NATIVE_LIFECYCLE_PHASE": phase,
                    "DELM_NATIVE_LIFECYCLE_STATE": str(host.sandbox / "native-lifecycle-state.json")})
                (output / f"{phase}-client.log").write_text(host.redact(client.stdout + client.stderr))
                assert client.returncode == 0, f"Native {phase} failed; see {phase}-client.log"
                phases.append(json.loads(client.stdout))
            assert host.process.returncode == 0, host.process.returncode
        assert provider.requests == 2, "Restart duplicated model work: " + str(provider.requests)
        assert [r["sessionId"] for r in phases[0]["sessions"]] == [r["sessionId"] for r in phases[1]["sessions"]]
        result = dict(schema=1, public_host="Native Pi Durable experimental server", version="1.0.2",
            revision="cd32f7725fdbddbaecdff5b1e68491563394e0ca", source_modified=False,
            same_server_identity_after_restart=True, exact_sessions_and_histories_preserved=True,
            other_actor_history_leak=False, model_reenqueue_on_restart=False, official_sigint_exit=0,
            deterministic_http_requests=provider.requests, live_model_calls=0, phases=phases,
            delm_plugin="NOT_YET_TESTED", editor_draft="NOT_YET_TESTED")
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))


if __name__ == "__main__":
    main()
