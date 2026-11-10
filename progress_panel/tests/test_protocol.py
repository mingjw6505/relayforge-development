"""MCP wire behavior, packaging contract and privacy boundaries."""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from progress_panel.server import (
    MAX_REQUEST_BYTES,
    RESOURCE_URI,
    ProgressServer,
    data_directory,
)

ROOT = Path(__file__).resolve().parents[2]


def start_arguments() -> dict:
    return {"title": "开发任务", "steps": [{"label": "验证", "status": "active"}]}


def rpc(server: ProgressServer, value: object) -> list[dict]:
    source = io.BytesIO((json.dumps(value) + "\n").encode())
    output = io.BytesIO()
    server.serve(source, output)
    return [json.loads(line) for line in output.getvalue().splitlines()]


def test_render_and_data_tools_are_distinct_and_resource_is_inline(
    tmp_path: Path,
) -> None:
    server = ProgressServer(tmp_path / "state")
    definitions = {
        tool["name"]: tool for tool in server.dispatch("tools/list", {})["tools"]
    }
    assert definitions["start_progress"]["_meta"]["ui"]["resourceUri"] == RESOURCE_URI
    assert "resourceUri" not in definitions["update_progress"]["_meta"].get("ui", {})
    assert definitions["read_progress"]["_meta"]["ui"]["visibility"] == ["app"]
    assert "openai/ui" not in definitions["start_progress"]["_meta"]
    assert definitions["load_progress_skill"]["_meta"]["ui"]["visibility"] == ["model"]
    resource = server.dispatch("resources/read", {"uri": RESOURCE_URI})["contents"][0]
    assert resource["_meta"]["openai/ui"]["availableDisplayModes"] == ["inline"]
    assert resource["mimeType"] == "text/html;profile=mcp-app"
    assert "RelayForge" in resource["text"]
    assert not server.directory.exists(), "discovery must not create task state"


def test_stdio_lifecycle_and_scoped_reopen(tmp_path: Path) -> None:
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "progress_panel.server",
            "--data-dir",
            str(tmp_path / "state"),
        ],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )

    def call(identifier: int, method: str, params: dict) -> dict:
        process.stdin.write(
            json.dumps(
                {"jsonrpc": "2.0", "id": identifier, "method": method, "params": params}
            )
            + "\n"
        )
        process.stdin.flush()
        return json.loads(process.stdout.readline())

    try:
        initialized = call(1, "initialize", {"protocolVersion": "2025-11-25"})["result"]
        assert initialized["serverInfo"]["name"] == "relayforge-progress"
        started = call(
            2, "tools/call", {"name": "start_progress", "arguments": start_arguments()}
        )["result"]["structuredContent"]
        arguments = {
            "run_id": started["run_id"],
            "expected_revision": 1,
            "status": "completed",
            "steps": [{"label": "验证", "status": "done"}],
            "summary": "检查通过",
        }
        ended = call(
            3, "tools/call", {"name": "update_progress", "arguments": arguments}
        )["result"]["structuredContent"]
        reopened = call(
            4,
            "tools/call",
            {"name": "open_progress", "arguments": {"run_id": started["run_id"]}},
        )["result"]["structuredContent"]
        assert ended["status"] == reopened["status"] == "completed"
        assert "history" not in ended
        assert reopened["revision"] == 2
        process.stdin.close()
        assert process.wait(timeout=3) == 0
        assert process.stderr.read() == ""
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=3)


def test_errors_do_not_echo_inputs_and_oversized_lines_are_drained(
    tmp_path: Path,
) -> None:
    server = ProgressServer(tmp_path / "state")
    marker = "PRIVATE-CONTENT-DO-NOT-ECHO"
    result = server.call_tool("start_progress", {**start_arguments(), "prompt": marker})
    assert result["isError"]
    assert marker not in json.dumps(result)
    assert server.call_tool("no_such_tool", {})["isError"]
    assert server.call_tool("start_progress", [])["isError"]
    assert server.call_tool("start_progress", {})["isError"]
    assert not server.directory.exists()
    output = io.BytesIO()
    server.serve(
        io.BytesIO(
            b"x" * (MAX_REQUEST_BYTES + 10)
            + b'\n{"jsonrpc":"2.0","id":7,"method":"ping"}\n'
        ),
        output,
    )
    replies = [json.loads(line) for line in output.getvalue().splitlines()]
    assert replies[0]["error"]["message"] == "request_too_large"
    assert replies[1]["result"] == {}


@pytest.mark.parametrize("payload", [b'{"id":1,"id":2}\n', b'{"x":NaN}\n', b"\xff\n"])
def test_invalid_json_is_generic(tmp_path: Path, payload: bytes) -> None:
    output = io.BytesIO()
    ProgressServer(tmp_path / "state").serve(io.BytesIO(payload), output)
    assert json.loads(output.getvalue())["error"]["code"] == -32700


@pytest.mark.parametrize(
    "value",
    [
        [],
        {"id": 1},
        {"jsonrpc": "2.0", "id": True},
        {"jsonrpc": "2.0", "id": 1, "method": 4},
        {"jsonrpc": "2.0", "id": 1, "method": "ping", "params": []},
    ],
)
def test_malformed_rpc_is_rejected(tmp_path: Path, value: object) -> None:
    assert rpc(ProgressServer(tmp_path / "state"), value)[0]["error"]["code"] == -32600


def test_notifications_discovery_unknown_resources_and_conflicts(
    tmp_path: Path,
) -> None:
    server = ProgressServer(tmp_path / "state")
    assert rpc(server, {"jsonrpc": "2.0", "method": "notifications/initialized"}) == []
    assert server.dispatch("resources/templates/list", {}) == {"resourceTemplates": []}
    assert server.dispatch("resources/list", {})["resources"][0]["uri"] == RESOURCE_URI
    assert (
        server.dispatch("initialize", {"protocolVersion": "future-version"})[
            "protocolVersion"
        ]
        == "2025-11-25"
    )
    for method, params, code in [
        ("no_such_method", {}, -32601),
        ("resources/read", {"uri": "file:///etc/passwd"}, -32602),
    ]:
        assert (
            rpc(
                server, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            )[0]["error"]["code"]
            == code
        )
    first = server.call_tool("start_progress", start_arguments())["structuredContent"]
    update = {
        "run_id": first["run_id"],
        "expected_revision": 1,
        "status": "waiting",
        "steps": first["steps"],
        "summary": "等待输入",
    }
    server.call_tool("update_progress", update)
    conflict = server.call_tool("update_progress", {**update, "summary": "不同的更新"})
    assert conflict["structuredContent"]["error"] == "revision_conflict"
    assert conflict["structuredContent"]["current"]["run_id"] == first["run_id"]


def test_environment_data_selection_is_separate_from_logs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    for name in ["RELAYFORGE_PROGRESS_DATA_DIR", "PLUGIN_DATA", "CLAUDE_PLUGIN_DATA"]:
        monkeypatch.delenv(name, raising=False)
    assert data_directory().name == "progress-panel"
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "claude"))
    assert data_directory() == tmp_path / "claude/progress-panel"
    monkeypatch.setenv("PLUGIN_DATA", str(tmp_path / "codex"))
    assert data_directory() == tmp_path / "codex/progress-panel"
    monkeypatch.setenv("RELAYFORGE_PROGRESS_DATA_DIR", str(tmp_path / "isolated"))
    assert data_directory() == tmp_path / "isolated"


def test_storage_failure_is_nonblocking_and_does_not_echo_a_path(
    tmp_path: Path,
) -> None:
    path = tmp_path / "sensitive-path"
    path.write_text("not a directory")
    result = ProgressServer(path).call_tool("start_progress", start_arguments())
    assert result["isError"]
    assert str(path) not in json.dumps(result)
    assert result["content"][0]["text"] == "storage_unavailable"
