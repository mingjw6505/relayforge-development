"""Isolated package health check. Does not read user task state or host logs."""

from __future__ import annotations

import json
from contextlib import closing
import sqlite3
import tempfile
from pathlib import Path


def main() -> None:
    """Check packaged protocol/UI and SQLite without claiming host rendering."""
    phase = "server_import"
    try:
        from progress_panel.server import RESOURCE_URI, ProgressServer

        with tempfile.TemporaryDirectory(prefix="relayforge-doctor-") as folder:
            directory = Path(folder)
            phase = "isolated_sqlite"
            with closing(sqlite3.connect(directory / "probe.sqlite")) as connection:
                connection.execute("CREATE TABLE probe (value INTEGER)")
                connection.execute("INSERT INTO probe VALUES (1)")
                assert connection.execute("SELECT value FROM probe").fetchone() == (1,)
            server = ProgressServer(directory / "state")
            phase = "tool_discovery"
            info = server.dispatch("initialize", {"protocolVersion": "2025-11-25"})
            tools = server.dispatch("tools/list", {})["tools"]
            phase = "bundled_ui"
            resource = server.dispatch("resources/read", {"uri": RESOURCE_URI})["contents"][0]
            assert resource["mimeType"] == "text/html;profile=mcp-app"
            assert len(resource["text"]) > 1000
            assert any(tool["name"] == "start_progress" for tool in tools)
        print(json.dumps({
            "status": "runtime_ready", "server": info["serverInfo"],
            "checks": ["server_import", "tool_discovery", "bundled_ui", "isolated_sqlite"],
            "host_tools": "unverified", "host_ui": "unverified", "state_directory": "unverified",
            "message": "Local runtime checks passed. Host tool loading, inline rendering and real state-directory permissions still require host verification.",
        }))
    except Exception:
        print(json.dumps({"status": "package_check_failed", "phase": phase}))
        raise SystemExit(70) from None


if __name__ == "__main__":
    main()
