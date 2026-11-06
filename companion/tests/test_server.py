"""HTTP safety and readonly shell tests; no external packages or source logs needed."""

from __future__ import annotations

import http.client
import json
import sys
import threading
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from relayforge_progress.server import ProgressServer


class StubEngine:
    def snapshot(self) -> dict[str, Any]:
        return {"mode": "offline_prototype", "revision": 1, "source": {},
                "sessions": [], "runs": [], "events": [],
                "capabilities": {"native_plan": False, "business_stages": False}}


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ProgressServer(StubEngine())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path: str, headers: dict[str, str] | None = None,
                method: str = "GET") -> tuple[int, dict[str, str], bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            connection.request(method, path, headers=headers or {})
            result = connection.getresponse()
            return result.status, dict(result.getheaders()), result.read()
        finally:
            connection.close()

    def auth(self) -> dict[str, str]:
        return {"Authorization": "Bearer " + self.server.token}

    def test_health_has_no_metadata_and_security_headers(self) -> None:
        status, headers, body = self.request("/api/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), {"status": "ok", "mode": "offline_prototype"})
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        self.assertNotIn(self.server.token.encode(), body)

    def test_snapshot_needs_token(self) -> None:
        self.assertEqual(self.request("/api/v1/snapshot")[0], 401)
        self.assertEqual(self.request("/api/v1/snapshot", {"Authorization": "Bearer wrong"})[0], 401)
        status, _, body = self.request("/api/v1/snapshot", self.auth())
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["mode"], "offline_prototype")

    def test_bad_host_origin_cross_site_rejected(self) -> None:
        for headers in ({"Host": "attacker.example"}, {"Origin": "http://evil.example"},
                        {"Origin": "null"}, {"Sec-Fetch-Site": "cross-site"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.request("/api/v1/health", headers)[0], 403)
        self.assertEqual(self.request("/api/v1/snapshot", {**self.auth(), "Origin": self.server.origin})[0], 200)

    def test_no_writes_no_path_access_no_query_token(self) -> None:
        for method in ("POST", "PATCH", "PUT", "DELETE", "OPTIONS"):
            self.assertEqual(self.request("/api/v1/snapshot", self.auth(), method)[0], 405)
        for path in ("/../cli.py", "/%2e%2e/cli.py", "/api/v1/execute", "/api/v1/files"):
            self.assertEqual(self.request(path, self.auth())[0], 404)
        self.assertEqual(self.request("/api/v1/snapshot?token=secret", self.auth())[0], 400)

    def test_duplicate_host_and_auth_rejected(self) -> None:
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            connection.putrequest("GET", "/api/v1/snapshot")
            connection.putheader("Host", self.server.host)
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 403)
            response.read()
        finally:
            connection.close()
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        try:
            connection.putrequest("GET", "/api/v1/snapshot")
            for _ in range(2):
                connection.putheader("Authorization", "Bearer " + self.server.token)
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 401)
            response.read()
        finally:
            connection.close()

    def test_capabilities_honest(self) -> None:
        status, _, body = self.request("/api/v1/capabilities", self.auth())
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertFalse(data["collection_verified"])
        self.assertFalse(data["bindings"])
        self.assertFalse(data["stream"])
        self.assertEqual(data["transport"], "polling")

    def test_static_allowlist_and_head(self) -> None:
        status, _, body = self.request("/", method="HEAD")
        self.assertIn(status, (200, 503))
        self.assertEqual(body, b"")
        self.assertEqual(self.request("/server.py")[0], 404)


if __name__ == "__main__":
    unittest.main()
