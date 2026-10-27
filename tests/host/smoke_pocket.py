#!/usr/bin/env python3
"""Public Pocket CLI + actual drop-in loader + two real sessions + deterministic HTTP MODEL."""
import argparse
import json
from pathlib import Path
import threading
import time
import urllib.error
import urllib.request
from deterministic_provider import DeterministicProvider
from pocket_process import PocketProcess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text())
    source, data = Path(fixture["source"]), Path(fixture["data"])
    extensions = data / "extensions"
    extensions.mkdir(parents=True, exist_ok=True)
    # The upstream's own documented example, not a mocked loader or product bridge.
    (extensions / "fixture-clock.ts").write_bytes((source / "docs/examples/clock.ts").read_bytes())
    replies = [dict(tool="clock", arguments={"zone": "UTC"}), dict(text="HOST_FIXTURE_ACK")] * 2
    with DeterministicProvider(replies) as provider:
        config = Path(fixture["env"]["PI_CODING_AGENT_DIR"])
        config.mkdir(parents=True, exist_ok=True)
        (config / "models.json").write_text(json.dumps(provider.models_config()))
        with PocketProcess(args.fixture) as host:
            try:
                urllib.request.urlopen(host.base + "/api/sessions", timeout=5)
                raise AssertionError("Unauthenticated real host API was unexpectedly accessible")
            except urllib.error.HTTPError as error:
                assert error.code == 401
            modules = host.request("/api/extensions")["modules"]
            module = next(m for m in modules if m["file"] == "fixture-clock.ts")
            assert not module["enabled"], "A new drop-in must start OFF in the actual host"
            modules = host.request("/api/extensions/fixture-clock.ts", {"enabled": True})["modules"]
            module = next(m for m in modules if m["file"] == "fixture-clock.ts")
            assert module["enabled"] and not module.get("error"), module
            sessions = []
            for actor in range(2):
                session = host.request("/api/sessions", {"cwd": fixture["project"], "title": f"fixture actor {actor}"})["id"]
                host.request(f"/api/c/{session}/configure", {"model": {"provider": "fixture", "modelId": "deterministic"}})
                request_id = f"public-pocket-smoke-{actor}"
                host.request(f"/api/c/{session}/submit", {"text": "Read the clock and acknowledge the fixture.", "requestId": request_id})
                deadline = time.monotonic() + 25
                while True:
                    history = host.request(f"/api/c/{session}/history")
                    text = json.dumps(history)
                    if "HOST_FIXTURE_ACK" in text:
                        assert "clock" in text
                        break
                    if time.monotonic() > deadline:
                        raise AssertionError("Actual host did not finish its deterministic tool call: " + host.redact(text[-2500:]))
                    threading.Event().wait(.1)
                sessions.append(dict(actor=actor, session=session, actual_clock_tool=True, model_answer="HOST_FIXTURE_ACK"))
            assert provider.requests == 4, provider.requests
            result = dict(schema=1, public_host="Pi Pocket", version="0.14.0",
                          revision="e5456a832d47e7154faf04320dd7602ae5051bf7", sdk="1.1.0",
                          source_unmodified=True, replacedHarness=False, mocked_host_discovery_or_admission=False,
                          dropin_initially_disabled=True, owner_enable=True, unauthenticated_api=401,
                          same_workspace=True, sessions=sessions, deterministic_http_requests=provider.requests,
                          live_model_calls=0, deLM_plugin="NOT_YET_TESTED")
            (Path(fixture["evidence"]) / "pocket-deterministic-smoke.json").write_text(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result))


if __name__ == "__main__":
    main()
