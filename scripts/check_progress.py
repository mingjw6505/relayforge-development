#!/usr/bin/env python3
"""Optional stdio discovery probe; normal plugin startup needs no setup script."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {},
            "clientInfo": {"name": "relayforge-launch-check", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    try:
        portable = json.loads((ROOT / "mcp.json").read_text())["mcpServers"]["relayforge-progress"]
        legacy = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]["relayforge-progress"]
        if {key: value for key, value in portable.items() if key != "type"} != legacy:
            raise ValueError("MCP registrations differ")
        entry = ROOT / portable["command"]
        if os.name == "nt":
            entry = entry.with_suffix(".exe")
        with tempfile.TemporaryDirectory(prefix="relayforge-launch-") as directory:
            env = dict(os.environ, **portable.get("env", {}))
            env["RELAYFORGE_PROGRESS_DATA_DIR"] = directory
            result = subprocess.run(
                [str(entry), *portable.get("args", [])], cwd=ROOT, env=env,
                input="".join(json.dumps(request) + "\n" for request in requests),
                capture_output=True, text=True, encoding="utf-8", timeout=15,
            )
        if result.returncode:
            raise ValueError(f"MCP launch exited {result.returncode}: {result.stderr.strip()[:1000]}")
        responses = {value["id"]: value for line in result.stdout.splitlines()
                     if "id" in (value := json.loads(line))}
        tools = {tool["name"] for tool in responses[2]["result"]["tools"]}
        if responses[1]["result"]["serverInfo"]["name"] != "relayforge-progress" or not {
                "start_progress", "update_progress", "load_progress_skill"} <= tools:
            raise ValueError("Expected progress server and tools")
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f"RelayForge MCP check failed: {exc}", file=sys.stderr)
        return 1
    print("MCP startup and progress tool discovery passed. Inline rendering still requires a host check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
