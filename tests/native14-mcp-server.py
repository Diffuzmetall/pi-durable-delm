#!/usr/bin/env python3
"""Deterministic stdio MCP fixture. No network, user configuration, auth or Native storage."""
import json
import sys

for line in sys.stdin:
    request = json.loads(line)
    if "id" not in request:
        continue
    method = request["method"]
    if method == "initialize":
        result = dict(protocolVersion=request["params"]["protocolVersion"], capabilities={"tools": {}},
                      serverInfo={"name": "delm-mcp-fixture", "version": "1.0.0"})
    elif method == "tools/list":
        schema = dict(type="object", properties={"message": {"type": "string"}}, required=["message"])
        result = {"tools": [dict(name="echo", description="Return synthetic fixture text.", inputSchema=schema,
                                 outputSchema=schema, annotations={"readOnlyHint": True})]}
    elif method == "tools/call":
        assert request["params"]["name"] == "echo"
        value = request["params"]["arguments"]["message"]
        result = dict(content=[{"type": "text", "text": value}], structuredContent={"message": value})
    else:
        result = {}
    print(json.dumps(dict(jsonrpc="2.0", id=request["id"], result=result)), flush=True)
