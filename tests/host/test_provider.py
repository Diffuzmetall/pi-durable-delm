"""Small checks of the model-only fixture; real host evidence comes from smoke_pocket.py."""
import json
import unittest
import urllib.error
import urllib.request
from deterministic_provider import DeterministicProvider


class ModelFixtureTest(unittest.TestCase):
    def request(self, provider, body):
        request = urllib.request.Request(f"http://127.0.0.1:{provider.server.server_port}/v1/chat/completions",
            data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        return urllib.request.urlopen(request, timeout=5)

    def test_scripted_tool_is_sent_only_when_actual_host_advertises_it(self):
        with DeterministicProvider([{"tool": "clock", "arguments": {"zone": "UTC"}}]) as provider:
            with self.request(provider, {"tools": [{"function": {"name": "clock"}}]}) as response:
                stream = response.read().decode()
            frame = json.loads(stream.splitlines()[0].removeprefix("data: "))
            self.assertEqual(frame["choices"][0]["delta"]["tool_calls"][0]["function"]["name"], "clock")
            self.assertIn("data: [DONE]", stream)
            self.assertEqual(provider.requests, 1)

    def test_cannot_fabricate_a_tool_missing_from_host(self):
        with DeterministicProvider([{"tool": "missing", "arguments": {}}]) as provider:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                self.request(provider, {"tools": []})
            self.assertEqual(caught.exception.code, 422)

    def test_default_is_plain_ack_and_model_endpoint_is_local(self):
        with DeterministicProvider() as provider:
            with self.request(provider, {"tools": []}) as response:
                self.assertIn("HOST_FIXTURE_ACK", response.read().decode())
            self.assertEqual(provider.server.server_address[0], "127.0.0.1")
            self.assertTrue(provider.models_config()["providers"]["fixture"]["baseUrl"].startswith("http://127.0.0.1:"))


if __name__ == "__main__":
    unittest.main()
