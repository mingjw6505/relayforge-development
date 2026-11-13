"""Launch the shipped entrypoint without setup, including after a fresh update."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
REQUEST = '{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n'


@pytest.fixture
def plugin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv("RELAYFORGE_PYTHON", raising=False)
    target = tmp_path / "relocated plugin 空格"
    target.mkdir()
    for name in ("mcp.json", ".mcp.json", "plugin.json"):
        shutil.copyfile(ROOT / name, target / name)
    shutil.copytree(ROOT / "scripts", target / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "progress_panel", target / "progress_panel",
                    ignore=shutil.ignore_patterns("__pycache__", "web", "tests"))
    return target


def command(plugin: Path) -> list[str]:
    server = json.loads((plugin / "mcp.json").read_text())["mcpServers"]["relayforge-progress"]
    entry = plugin / server["command"]
    # Python's CreateProcess wrapper differs from Rust's .exe resolution; select
    # the native artifact explicitly for this protocol test, not a shell wrapper.
    if os.name == "nt":
        entry = entry.with_suffix(".exe")
    return [str(entry), *server["args"]]


def launch(plugin: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command(plugin), input=REQUEST, cwd=plugin.parent,
                          env=env, capture_output=True, text=True, encoding="utf-8", timeout=15)


def assert_discovered(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stderr
    response = json.loads(result.stdout)
    assert "start_progress" in {tool["name"] for tool in response["result"]["tools"]}


def test_fresh_package_and_update_need_no_config_changes(plugin: Path, tmp_path: Path) -> None:
    before = {name: (plugin / name).read_bytes() for name in ("mcp.json", ".mcp.json")}
    env = dict(os.environ, RELAYFORGE_PROGRESS_DATA_DIR=str(tmp_path / "state"))
    assert_discovered(launch(plugin, env))
    # Simulate update replacement with the distributed registrations, not setup output.
    for name in before:
        shutil.copyfile(ROOT / name, plugin / name)
    assert_discovered(launch(plugin, env))
    assert before == {name: (plugin / name).read_bytes() for name in before}
    assert not (tmp_path / "state").exists(), "Discovery must not create task state"


@pytest.mark.skipif(os.name == "nt", reason="POSIX shell entrypoint")
@pytest.mark.parametrize("available", ["python3", "python", "python3.12", "none"])
def test_posix_candidate_fallback(plugin: Path, tmp_path: Path, available: str) -> None:
    commands = tmp_path / "commands"
    commands.mkdir()
    for name in ("python3", "python", "python3.12"):
        path = commands / name
        if name == available:
            path.symlink_to(sys.executable)
        else:
            path.write_text("#!/bin/sh\nexit 1\n")
            path.chmod(0o755)
    result = launch(plugin, dict(os.environ, PATH=str(commands),
                                RELAYFORGE_PROGRESS_DATA_DIR=str(tmp_path / "state")))
    if available == "none":
        assert result.returncode != 0
        assert result.stdout == ""
        assert "Python 3.11+" in result.stderr
    else:
        assert_discovered(result)


@pytest.mark.skipif(os.name == "nt", reason="POSIX shell entrypoint")
def test_posix_service_failure_is_returned_without_retry(plugin: Path, tmp_path: Path) -> None:
    commands = tmp_path / "commands"
    commands.mkdir()
    path = commands / "python3"
    path.write_text('#!/bin/sh\nif [ "$1" = "-c" ]; then echo "RELAYFORGE_PYTHON=$0"; exit 0; fi\nexit 37\n')
    path.chmod(0o755)
    other = commands / "python"
    other.write_text('#!/bin/sh\necho "unexpected fallback"\nexit 0\n')
    other.chmod(0o755)
    result = launch(plugin, dict(os.environ, PATH=str(commands)))
    assert result.returncode == 37
    assert result.stdout == ""


def test_windows_artifact_is_bundled_and_matches_source_record() -> None:
    record = json.loads((ROOT / "scripts/progress_launcher/build.json").read_text())
    source = (ROOT / "scripts/progress_launcher/main.go").read_bytes()
    binary = (ROOT / "scripts/start_progress.exe").read_bytes()
    assert record["source_sha256"] == hashlib.sha256(source).hexdigest()
    assert record["binary_sha256"] == hashlib.sha256(binary).hexdigest()
    assert str(ROOT).encode() not in binary
    assert binary[:2] == b"MZ"
    offset = struct.unpack_from("<I", binary, 0x3C)[0]
    assert binary[offset:offset + 4] == b"PE\0\0"
    assert struct.unpack_from("<H", binary, offset + 4)[0] == 0x14C
    assert (ROOT / "scripts/progress_launcher/GO_LICENSE").is_file()


def test_registered_doctor_keeps_host_and_real_state_unverified(plugin: Path, tmp_path: Path) -> None:
    result = subprocess.run([*command(plugin), "--doctor"], cwd=plugin.parent,
                            env=dict(os.environ, RELAYFORGE_PYTHON=sys.executable,
                                     RELAYFORGE_PROGRESS_DATA_DIR=str(tmp_path / "real-state")),
                            capture_output=True, encoding="utf-8", timeout=15)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "runtime_ready"
    assert report["host_tools"] == report["host_ui"] == report["state_directory"] == "unverified"
    assert not (tmp_path / "real-state").exists()


def test_bad_override_never_uses_a_healthy_fallback(plugin: Path, tmp_path: Path) -> None:
    env = dict(os.environ, RELAYFORGE_PYTHON=str(tmp_path / "missing executable"))
    result = launch(plugin, env)
    assert result.returncode == 78
    assert result.stdout == ""
    report = subprocess.run([*command(plugin), "--doctor"], cwd=plugin.parent, env=env,
                            capture_output=True, encoding="utf-8", timeout=15)
    assert report.returncode == 78
    assert json.loads(report.stdout)["status"] == "python_unavailable"
