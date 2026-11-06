"""Loopback-only authenticated HTTP shell for the offline observation prototype."""

from __future__ import annotations

import hmac
import json
import secrets
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit


class SnapshotEngine(Protocol):
    """Minimal data-engine contract; the server never opens source files."""

    def snapshot(self) -> dict[str, Any]: ...


ASSETS = {"/": ("index.html", "text/html; charset=utf-8"),
          "/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/styles.css": ("styles.css", "text/css; charset=utf-8")}
MAX_RESPONSE = 8 * 1024 * 1024


class ProgressServer(ThreadingHTTPServer):
    """Bounded local HTTP server with a per-process bearer capability."""

    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, engine: SnapshotEngine, port: int = 0) -> None:
        self.engine = engine
        self.token = secrets.token_urlsafe(32)
        self.slots = threading.BoundedSemaphore(12)
        self.assets = Path(__file__).parent / "static"
        super().__init__(("127.0.0.1", port), ProgressHandler)
        self.origin = f"http://127.0.0.1:{self.server_port}"
        self.host = f"127.0.0.1:{self.server_port}"

    def process_request(self, request: Any, client_address: Any) -> None:
        """Bound concurrent requests before allocating a worker thread."""
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()

    def handle_error(self, request: Any, client_address: Any) -> None:
        """Do not print arbitrary request or filesystem data in tracebacks."""


class ProgressHandler(BaseHTTPRequestHandler):
    """Serve exact allowlisted resources and a strictly read-only API."""

    server: ProgressServer
    server_version = "RelayForgeProgress/0.1"
    sys_version = ""

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress access logs, including accidental tokens and user strings."""

    def _send(self, status: int, body: bytes, kind: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; "
                         "style-src 'self'; connect-src 'self'; img-src 'none'; "
                         "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, TimeoutError):
                pass

    def _json(self, status: int, value: dict[str, Any]) -> None:
        body = json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()
        if len(body) > MAX_RESPONSE:
            self._send(HTTPStatus.SERVICE_UNAVAILABLE, b'{"error":"snapshot_limit"}')
        else:
            self._send(status, body)

    def _safe_request(self) -> bool:
        if self.headers.get_all("Host", []) != [self.server.host]:
            self._json(HTTPStatus.FORBIDDEN, {"error": "host_rejected"})
            return False
        origins = self.headers.get_all("Origin", [])
        if origins and origins != [self.server.origin]:
            self._json(HTTPStatus.FORBIDDEN, {"error": "origin_rejected"})
            return False
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            self._json(HTTPStatus.FORBIDDEN, {"error": "cross_site_rejected"})
            return False
        return True

    def do_GET(self) -> None:
        """Return only safe static assets and authenticated metadata snapshots."""
        if not self._safe_request():
            return
        parsed = urlsplit(self.path)
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_target"})
            return
        path = parsed.path
        if path == "/api/v1/health":
            self._json(200, {"status": "ok", "mode": "offline_prototype"})
            return
        if path in ASSETS:
            name, kind = ASSETS[path]
            try:
                content = (self.server.assets / name).read_bytes()
            except OSError:
                self._json(503, {"error": "asset_unavailable"})
                return
            self._send(200, content, kind)
            return
        if path.startswith("/api/"):
            auth = self.headers.get_all("Authorization", [])
            expected = "Bearer " + self.server.token
            if len(auth) != 1 or not hmac.compare_digest(auth[0].encode(), expected.encode()):
                self._json(401, {"error": "authorization_required"})
                return
            try:
                snapshot = self.server.engine.snapshot()
                if path == "/api/v1/snapshot":
                    self._json(200, snapshot)
                elif path == "/api/v1/capabilities":
                    self._json(200, {"mode": "offline_prototype", "collection_verified": False,
                                     **snapshot.get("capabilities", {}), "transport": "polling",
                                     "preferences": False, "bindings": False, "stream": False})
                else:
                    self._json(404, {"error": "not_found"})
            except (OSError, ValueError, RuntimeError):
                self._json(503, {"error": "snapshot_unavailable"})
            return
        self._json(404, {"error": "not_found"})

    def do_HEAD(self) -> None:
        self.do_GET()

    def _readonly(self) -> None:
        if self._safe_request():
            self._json(405, {"error": "read_only"})

    do_POST = _readonly
    do_PUT = _readonly
    do_PATCH = _readonly
    do_DELETE = _readonly
    do_OPTIONS = _readonly
