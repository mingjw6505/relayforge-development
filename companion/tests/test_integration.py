"""Offline end-to-end engine/API checks using explicitly synthetic local metadata."""

from __future__ import annotations

import hashlib
import http.client
import json
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from generate_demo import records
from relayforge_progress.engine import Engine
from relayforge_progress.server import ProgressServer


class IntegrationTests(unittest.TestCase):
    def test_synthetic_snapshot_assets_and_source_immutability(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            logs = root / "logs"
            logs.mkdir()
            path = logs / f"events-{datetime.now(timezone.utc).date().isoformat()}.jsonl"
            path.write_text("".join(json.dumps(item) + "\n" for item in records()))
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            engine = Engine(logs, root / "state")
            server = None
            thread = None
            try:
                engine.refresh()
                server = ProgressServer(engine)
                thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
                thread.start()
                for target in ("/", "/app.js", "/styles.css", "/api/v1/snapshot"):
                    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
                    try:
                        connection.request("GET", target, headers={"Authorization": "Bearer " + server.token})
                        response = connection.getresponse()
                        body = response.read()
                        self.assertEqual(response.status, 200, target)
                        if target == "/api/v1/snapshot":
                            data = json.loads(body)
                            self.assertEqual(data["mode"], "offline_prototype")
                            self.assertFalse(data["source"]["collection_verified"])
                            self.assertEqual(len(data["sessions"]), 1)
                            self.assertEqual(len(data["runs"]), 1)
                            self.assertEqual(data["runs"][0]["summary"]["development_status"], "blocked")
                            states = {item["state"] for item in data["sessions"][0]["tools"]}
                            self.assertIn("completion_failed", states)
                            self.assertIn("completion_succeeded", states)
                            self.assertIn("start_observed", states)
                            self.assertNotIn(str(root), body.decode())
                    finally:
                        connection.close()
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)
                self.assertEqual({p.name for p in logs.iterdir()}, {path.name})
            finally:
                if server is not None:
                    server.shutdown()
                    server.server_close()
                if thread is not None:
                    thread.join(timeout=2)
                engine.close()


if __name__ == "__main__":
    unittest.main()
