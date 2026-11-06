"""CLI diagnostic and error-state tests for the offline prototype."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from relayforge_progress.cli import ObservationState, diagnose, main


class FakeEngine:
    def __init__(self) -> None:
        self.fail = True

    def refresh(self) -> bool:
        if self.fail:
            raise OSError("private-source-must-not-leak")
        return True

    def snapshot(self) -> dict[str, Any]:
        return {"source": {"status": "readable", "diagnostics": {}}}


class CliTests(unittest.TestCase):
    def test_doctor_missing_source_does_not_create_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory).resolve() / "does-not-exist"
            report = diagnose(missing)
            self.assertFalse(missing.exists())
            self.assertEqual(report["c1"], "unverified")
            self.assertFalse(report["source"]["collection_verified"])
            self.assertNotIn(str(missing), json.dumps(report))

    def test_diagnostic_output_and_version(self) -> None:
        for argv in (["version"], ["doctor", "--log-dir", "/definitely-not-a-plugin-log-dir"]):
            with contextlib.redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(main(argv), 0)
            self.assertIn("offline", stream.getvalue())

    def test_invalid_port_error_is_sanitized(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()) as stream:
            self.assertEqual(main(["serve", "--log-dir", "/private/source", "--port", "65536"]), 2)
        self.assertNotIn("/private/source", stream.getvalue())

    def test_refresh_errors_degrade_then_recover(self) -> None:
        engine = FakeEngine()
        state = ObservationState(engine)  # type: ignore[arg-type]
        state.refresh()
        self.assertEqual(state.snapshot()["source"]["status"], "degraded")
        self.assertEqual(state.snapshot()["source"]["diagnostics"]["refresh_errors"], 1)
        engine.fail = False
        state.refresh()
        self.assertEqual(state.snapshot()["source"]["status"], "readable")
        self.assertNotIn("private-source", json.dumps(state.snapshot()))


    def test_browser_launch_failure_closes_engine_and_server(self) -> None:
        import asyncio
        from relayforge_progress.cli import parser, run_server
        from relayforge_progress.server import ProgressServer
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            args = parser().parse_args(["serve", "--log-dir", str(root / "missing"),
                                        "--state-dir", str(root / "state"), "--open"])
            servers = []
            def factory(*values: Any) -> ProgressServer:
                server = ProgressServer(*values)
                servers.append(server)
                return server
            with patch("relayforge_progress.cli.ProgressServer", side_effect=factory), \
                    patch("relayforge_progress.cli.webbrowser.open", side_effect=OSError("private-browser-error")), \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(OSError):
                    asyncio.run(run_server(args))
            self.assertEqual(len(servers), 1)
            self.assertEqual(servers[0].socket.fileno(), -1)
            with self.assertRaises(RuntimeError):
                servers[0].engine.engine.snapshot()


if __name__ == "__main__":
    unittest.main()
