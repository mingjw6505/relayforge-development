"""Explicit-source launcher and diagnostics; no plugin or Codex configuration writes."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import hashlib
import shutil
import signal
import sqlite3
import sys
import tempfile
import threading
import webbrowser
from pathlib import Path
from typing import Any

from .engine import Engine
from .server import ProgressServer


class ObservationState:
    """Expose refresh failures without presenting cached data as fresh."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.lock = threading.RLock()
        self.errors = 0
        self.last_error = False

    def refresh(self) -> None:
        try:
            self.engine.refresh()
            with self.lock:
                self.last_error = False
        except (OSError, ValueError, RuntimeError, sqlite3.Error):
            with self.lock:
                self.errors += 1
                self.last_error = True

    def snapshot(self) -> dict[str, Any]:
        value = self.engine.snapshot()
        with self.lock:
            value["source"]["diagnostics"]["refresh_errors"] = self.errors
            if self.last_error:
                value["source"]["status"] = "degraded"
        return value


def default_state_directory() -> Path:
    """Return a dedicated local cache path, never a plugin data directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return base / "relayforge-progress"


def parser() -> argparse.ArgumentParser:
    """Define only source-explicit and foreground commands for the prototype."""
    root = argparse.ArgumentParser(description="RelayForge Progress · offline observation prototype")
    commands = root.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="inspect sanitized existing metadata, not Codex trust")
    doctor.add_argument("--log-dir", type=Path, required=True)
    serve = commands.add_parser("serve", help="run foreground loopback browser prototype")
    serve.add_argument("--log-dir", type=Path, required=True)
    serve.add_argument("--state-dir", type=Path, default=None)
    serve.add_argument("--port", type=int, default=0)
    serve.add_argument("--open", action="store_true")
    commands.add_parser("version", help="show independent companion version")
    return root


def diagnose(log_dir: Path) -> dict[str, Any]:
    """Inspect sanitized field evidence without persisting a source cache."""
    with tempfile.TemporaryDirectory(prefix="relayforge-doctor-") as temporary:
        engine = Engine(log_dir.expanduser(), Path(temporary).resolve())
        try:
            engine.refresh()
            snapshot = engine.snapshot()
            return {
                "mode": "offline_prototype",
                "c1": "unverified",
                "reason": "Live Codex trust and a user-confirmed ordinary task must be verified separately.",
                "source": snapshot["source"],
                "sessions_observed": len(snapshot["sessions"]),
                "runs_observed": len(snapshot["runs"]),
                "capabilities": snapshot["capabilities"],
                "codex_cli_on_path": shutil.which("codex") is not None,
            }
        finally:
            engine.close()


async def run_server(arguments: argparse.Namespace) -> int:
    """Run the foreground server and source refresh loop with bounded cleanup."""
    source_key = hashlib.sha256(str(arguments.log_dir.expanduser().absolute()).encode()).hexdigest()[:20]
    state_dir = arguments.state_dir or default_state_directory() / source_key
    engine = Engine(arguments.log_dir.expanduser(), state_dir.expanduser())
    server: ProgressServer | None = None
    worker: threading.Thread | None = None
    loop = asyncio.get_running_loop()
    installed: list[signal.Signals] = []
    stop = asyncio.Event()
    try:
        state = ObservationState(engine)
        await asyncio.to_thread(state.refresh)
        server = ProgressServer(state, arguments.port)
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
                installed.append(sig)
            except (NotImplementedError, RuntimeError):
                pass
        # A directly started thread avoids executor-start cancellation races.
        worker = threading.Thread(target=server.serve_forever, args=(0.2,), daemon=True)
        worker.start()
        url = f"{server.origin}/#token={server.token}"
        print("离线原型 · Codex 实时采集未验证", flush=True)
        print("只读本地元数据；Ctrl+C 停止。链接含临时本地访问令牌，请勿分享。", flush=True)
        print(url, flush=True)
        if arguments.open:
            await asyncio.to_thread(webbrowser.open, url)
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=2)
            except TimeoutError:
                await asyncio.to_thread(state.refresh)
    finally:
        if server is not None:
            if worker is not None and worker.is_alive():
                await asyncio.to_thread(server.shutdown)
                await asyncio.to_thread(worker.join, 2)
            server.server_close()
        engine.close()
        for sig in installed:
            loop.remove_signal_handler(sig)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Launch the prototype, returning sanitized actionable failures only."""
    arguments = parser().parse_args(argv)
    try:
        if arguments.command == "version":
            print("relayforge-progress 0.1.0 (offline prototype)")
            return 0
        if arguments.command == "doctor":
            print(json.dumps(diagnose(arguments.log_dir), ensure_ascii=False, indent=2))
            return 0
        if not 0 <= arguments.port <= 65535:
            raise ValueError("invalid port")
        return asyncio.run(run_server(arguments))
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, RuntimeError, sqlite3.Error):
        print("Companion 无法启动：请检查显式日志目录、独立缓存目录及端口；未修改插件。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
