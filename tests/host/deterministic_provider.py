"""Loopback OpenAI-compatible deterministic MODEL provider; not a fake host or admission policy."""
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading


class DeterministicProvider:
    def __init__(self, replies=()):
        self.reply_for_request = replies if callable(replies) else None
        self.replies = deque() if self.reply_for_request else deque(replies)
        self.requests = 0
        self.tool_names = []
        self.lock = threading.Lock()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass  # Do not publish request bodies, headers, or credentials.

            def do_POST(self):
                if self.path != "/v1/chat/completions":
                    self.send_error(404)
                    return
                length = int(self.headers.get("content-length", "0"))
                if not 0 < length <= 2 * 1024 * 1024:
                    self.send_error(413)
                    return
                request = json.loads(self.rfile.read(length))
                with owner.lock:
                    owner.requests += 1
                    owner.tool_names = [t["function"]["name"] for t in request.get("tools", [])]
                    reply = owner.reply_for_request(request) if owner.reply_for_request else (
                        owner.replies.popleft() if owner.replies else {"text": "HOST_FIXTURE_ACK"})
                delta = {"role": "assistant"}
                if "tool" in reply:
                    if reply["tool"] not in owner.tool_names:
                        self.send_error(422, "requested fixture tool was not advertised by actual host")
                        return
                    delta["tool_calls"] = [{"index": 0, "id": f"fixture-call-{owner.requests}", "type": "function",
                        "function": {"name": reply["tool"], "arguments": json.dumps(reply["arguments"])}}]
                    finish = "tool_calls"
                else:
                    delta["content"] = reply["text"]
                    finish = "stop"
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.end_headers()
                for value in [dict(id="fixture-completion", object="chat.completion.chunk", created=0,
                                   model="deterministic", choices=[dict(index=0, delta=delta, finish_reason=None)]),
                              dict(id="fixture-completion", object="chat.completion.chunk", created=0,
                                   model="deterministic", choices=[dict(index=0, delta={}, finish_reason=finish)],
                                   usage=dict(prompt_tokens=1, completion_tokens=1, total_tokens=2))]:
                    self.wfile.write(("data: " + json.dumps(value) + "\n\n").encode())
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def models_config(self):
        return {"providers": {"fixture": {
            "baseUrl": f"http://127.0.0.1:{self.server.server_port}/v1", "api": "openai-completions",
            "apiKey": "fixture-only-not-a-credential", "models": [{"id": "deterministic", "name": "Deterministic fixture",
                "reasoning": False, "input": ["text"], "contextWindow": 32768, "maxTokens": 1024,
                "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}}]}}}
