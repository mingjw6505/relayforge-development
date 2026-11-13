"""Keep portable and legacy registration aligned and relocatable."""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_manifests_and_mcp_registration_are_aligned() -> None:
    """Prevent silently ignored cwd syntax and divergent compatibility metadata."""
    manifests = [
        json.loads((ROOT / path).read_text())
        for path in (
            "plugin.json",
            ".codex-plugin/plugin.json",
            ".claude-plugin/plugin.json",
        )
    ]
    assert len({manifest["version"] for manifest in manifests}) == 1
    assert len({manifest["name"] for manifest in manifests}) == 1
    portable = json.loads((ROOT / "mcp.json").read_text())
    legacy = json.loads((ROOT / ".mcp.json").read_text())
    server = portable["mcpServers"]["relayforge-progress"].copy()
    assert server.pop("type") == "stdio"
    assert server == legacy["mcpServers"]["relayforge-progress"]
    # Agent Plugins requires ./ (a bare dot is invalid and Codex ignores it).
    assert server["cwd"] == "./"
    assert server["command"] == "./scripts/start_progress"
    assert server["args"] == []
    assert (ROOT / "scripts/start_progress").is_file()
    if os.name != "nt":
        assert (ROOT / "scripts/start_progress").stat().st_mode & 0o111
    assert (ROOT / "scripts/start_progress.exe").is_file()
    assert manifests[0]["extensions"]["com.openai"]["mcpServers"] == "./.mcp.json"
    assert all(manifest["mcpServers"] == "./.mcp.json" for manifest in manifests[1:])
    assert (ROOT / "progress_panel/static/panel.html").is_file()
    assert (ROOT / "progress_panel/THIRD_PARTY_NOTICES.txt").is_file()
