"""Unittest fixtures for the independent offline metadata engine."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from relayforge_progress.engine import Engine
from relayforge_progress.validation import InvalidRecord, decode, sanitize

SESSION = "sha256:" + "a" * 20
TURN = "sha256:" + "b" * 20
TOOL = "sha256:" + "c" * 20


def stamp(days: int = 0) -> str:
    """Return an aware test timestamp near the actual retention window."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def host(event: str, **fields: object) -> dict[str, object]:
    """Construct a host-shaped metadata fixture."""
    return {"schema_version": 1, "timestamp": stamp(), "event": event, "session_id": SESSION, "turn_id": TURN, **fields}


def declared(kind: str, run: str, sequence: int, **fields: object) -> dict[str, object]:
    """Construct a declaration fixture with strict business metadata."""
    defaults: dict[str, object] = {}
    if kind == "route_selected":
        defaults = {"execution_mode": "L1", "route": "quick", "risk": "normal", "reason_code": "local_scope", "planned_skills": ["task-router"]}
    if kind == "workflow_completed":
        defaults = {"implementation": "blocked", "development_status": "blocked"}
    return {"schema_version": 1, "timestamp": stamp(), "source": "agent_declared", "workflow_event_schema_version": 1, "route_policy_version": "v2.1", "event_id": str(uuid4()), "task_run_id": run, "sequence": sequence, "event": kind, **defaults, **fields}


class EngineTests(unittest.TestCase):
    """Exercise cursor persistence, data honesty and source isolation."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.logs = self.root / "logs"
        self.logs.mkdir()
        self.state = self.root / "state"
        self.path = self.logs / ("events-" + datetime.now(timezone.utc).strftime("%Y-%m-%d") + ".jsonl")
        self.engine = Engine(self.logs, self.state)
        self.addCleanup(self.engine.close)

    def append(self, *records: dict[str, object]) -> None:
        with self.path.open("ab") as stream:
            for record in records:
                stream.write(json.dumps(record).encode() + b"\n")

    def test_contract_pairing_and_offline_evidence(self) -> None:
        self.append(host("session_started"), host("turn_started"), host("tool_started", tool_use_id=TOOL, tool_name="shell"), host("tool_completed", tool_use_id=TOOL, tool_name="shell", outcome="failed", duration_ms=12, matched_start=True), host("turn_stopped"))
        before = self.path.read_bytes()
        self.assertTrue(self.engine.refresh())
        result = self.engine.snapshot()
        self.assertEqual(result["mode"], "offline_prototype")
        self.assertFalse(result["source"]["collection_verified"])
        self.assertEqual(result["capabilities"]["evidence"]["paired_tools"], 1)
        session = result["sessions"][0]
        self.assertEqual(session["lifecycle"], "open_observed")
        self.assertEqual(session["turns"][0]["state"], "stop_observed")
        self.assertEqual(session["tools"][0]["state"], "completion_failed")
        self.assertEqual(session["tools"][0]["duration_ms"], 12)
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(list(self.logs.iterdir()), [self.path])
        self.assertNotIn(str(self.root), json.dumps(result))
        result["sessions"].clear()
        self.assertEqual(len(self.engine.snapshot()["sessions"]), 1)

    def test_partial_line_persistence_and_reopen(self) -> None:
        raw = json.dumps(host("tool_started", tool_use_id=TOOL, tool_name="读文件")).encode()
        self.path.write_bytes(raw[:30])
        self.engine.refresh()
        self.assertEqual(self.engine.snapshot()["events"], [])
        self.engine.close()
        with self.path.open("ab") as stream:
            stream.write(raw[30:] + b"\n")
        self.engine = Engine(self.logs, self.state)
        self.addCleanup(self.engine.close)
        self.engine.refresh()
        self.engine.refresh()
        self.assertEqual(len(self.engine.snapshot()["events"]), 1)
        self.assertEqual(self.engine.snapshot()["sessions"][0]["tools"][0]["name"], "读文件")

    def test_truncation_and_inode_replacement(self) -> None:
        self.append(host("tool_started", tool_use_id=TOOL, tool_name="shell"))
        self.engine.refresh()
        self.path.write_bytes(b"\n")
        self.engine.refresh()
        replacement = self.logs / "replacement.tmp"
        replacement.write_text(json.dumps(host("session_ended")) + "\n")
        os.replace(replacement, self.path)
        self.engine.refresh()
        result = self.engine.snapshot()
        self.assertGreaterEqual(result["source"]["diagnostics"]["truncations"], 1)
        self.assertGreaterEqual(result["source"]["diagnostics"]["rotations"], 1)
        self.assertEqual(result["sessions"][0]["lifecycle"], "end_observed")

    def test_prefix_rewrite_same_inode(self) -> None:
        self.append(host("session_started"))
        self.engine.refresh()
        self.path.write_text(json.dumps(host("session_ended")) + "\n" + " " * 200)
        self.engine.refresh()
        self.assertEqual(self.engine.snapshot()["source"]["diagnostics"]["replacements"], 1)

    def test_invalid_and_oversized_lines_and_privacy(self) -> None:
        payload = host("tool_completed", tool_use_id=TOOL, tool_name="shell", outcome="succeeded", prompt="SECRET", command="SECRET", output="SECRET", raw_payload={"secret": "SECRET"})
        self.path.write_bytes(b'{"event":1,"event":2}\n' + b"x" * (70 * 1024) + b"\n" + json.dumps(payload).encode() + b"\r\n")
        for _ in range(3):
            self.engine.refresh()
        result = self.engine.snapshot()
        self.assertGreater(result["source"]["diagnostics"]["invalid_lines"], 0)
        self.assertGreater(result["source"]["diagnostics"]["oversized_lines"], 0)
        self.assertEqual(result["sessions"][0]["tools"][0]["state"], "completion_succeeded")
        self.assertIsNone(result["sessions"][0]["tools"][0]["duration_ms"])
        self.assertNotIn("SECRET", json.dumps(result))
        connection = sqlite3.connect(self.state / "progress.sqlite3")
        self.addCleanup(connection.close)
        self.assertNotIn("SECRET", " ".join(row[0] for row in connection.execute("SELECT record FROM events")))

    def test_missing_ids_are_not_guessed_and_conflicting_tools(self) -> None:
        self.append({"schema_version": 1, "event": "tool_started", "timestamp": stamp(), "tool_name": "shell"}, host("tool_started", tool_name="shell"), host("tool_started", tool_use_id=TOOL), host("tool_started", tool_use_id=TOOL), host("tool_completed", tool_use_id=TOOL, outcome="succeeded"))
        self.engine.refresh()
        result = self.engine.snapshot()
        self.assertEqual(len(result["sessions"]), 1)
        self.assertEqual(len(result["sessions"][0]["tools"]), 1)
        self.assertEqual(result["sessions"][0]["tools"][0]["state"], "conflicted")
        self.assertEqual(result["source"]["diagnostics"]["missing_session_ids"], 1)
        self.assertEqual(result["source"]["diagnostics"]["unpaired_tool_events"], 1)

    def test_incomplete_and_unspecified_tools(self) -> None:
        self.append(host("tool_started", tool_use_id=TOOL), host("turn_interrupted"), host("tool_completed", tool_use_id="sha256:" + "d" * 20, outcome="completed"))
        self.engine.refresh()
        states = [t["state"] for t in self.engine.snapshot()["sessions"][0]["tools"]]
        self.assertEqual(states, ["incomplete", "completion_unspecified"])

    def test_declarations_intact_replay_and_blocked_end(self) -> None:
        run = str(uuid4())
        first = declared("route_selected", run, 1)
        replay = {**first, "timestamp": stamp(-1)}
        self.append(first, replay, declared("workflow_completed", run, 2))
        self.engine.refresh()
        result = self.engine.snapshot()
        item = result["runs"][0]
        self.assertEqual(item["quality"], "intact_ended")
        self.assertEqual(item["route"], "L1")
        self.assertTrue(item["ended"])
        self.assertEqual(item["summary"]["implementation"], "blocked")
        self.assertEqual(item["events"][0]["risk"], "medium")
        self.assertEqual(result["sessions"], [])
        self.assertEqual(result["source"]["diagnostics"]["declaration_replays"], 1)

    def test_declaration_conflict_gap_after_end_discontinuity(self) -> None:
        run = str(uuid4())
        first = declared("route_selected", run, 1)
        conflicting = {**first, "risk": "high"}
        second_run = str(uuid4())
        self.append(first, conflicting, declared("route_selected", second_run, 1), declared("workflow_completed", second_run, 3), declared("route_changed", second_run, 4, **{"from": "L2", "to": "L3", "reason_code": "coordination_required"}))
        self.engine.refresh()
        runs = {r["id"]: r for r in self.engine.snapshot()["runs"]}
        self.assertEqual(runs[run]["quality"], "conflicted")
        self.assertIsNone(runs[run]["route"])
        self.assertEqual(runs[second_run]["quality"], "partial")
        self.assertIn("event_after_completion", runs[second_run]["issues"])
        self.assertIn("route_discontinuity", runs[second_run]["issues"])
        self.assertIn("missing_or_conflicting_sequence", runs[second_run]["issues"])

    def test_invalid_declaration_marks_existing_run_partial(self) -> None:
        run = str(uuid4())
        self.append(declared("route_selected", run, 1), declared("workflow_completed", run, 2, unexpected="SECRET"))
        self.engine.refresh()
        result = self.engine.snapshot()
        self.assertEqual(result["runs"][0]["quality"], "partial")
        self.assertNotIn("SECRET", json.dumps(result))

    def test_retention_and_cache_bound_do_not_fake_completeness(self) -> None:
        run = str(uuid4())
        self.append(declared("route_selected", run, 1), declared("workflow_completed", run, 2), host("session_started", timestamp=stamp(8)))
        with patch("relayforge_progress.engine.MAX_CACHE_EVENTS", 1):
            self.engine.refresh()
        result = self.engine.snapshot()
        self.assertEqual(result["source"]["coverage"]["retained_events"], 1)
        self.assertEqual(result["runs"][0]["quality"], "partial")
        self.assertIn("retention_limited", result["runs"][0]["issues"])
        self.assertEqual(result["source"]["diagnostics"]["expired_records"], 1)

    def test_file_selection_symlinks_and_state_isolation(self) -> None:
        outside = self.root / "outside"
        outside.write_text(json.dumps(host("session_started")) + "\n")
        self.path.symlink_to(outside)
        (self.logs / "events-1999-01-01.jsonl").write_text("{}\n")
        (self.logs / "random.jsonl").write_text(json.dumps(host("session_started")) + "\n")
        self.engine.refresh()
        result = self.engine.snapshot()
        self.assertEqual(result["events"], [])
        self.assertEqual(result["source"]["diagnostics"]["symlinks_rejected"], 1)
        self.assertTrue(result["source"]["coverage"]["selection_limited"])
        with self.assertRaisesRegex(ValueError, "overlaps_source"):
            Engine(self.logs, self.logs / "state")
        with self.assertRaisesRegex(ValueError, "overlaps_source"):
            Engine(self.logs, self.logs)

    def test_missing_denied_and_symlink_directory(self) -> None:
        missing = Engine(self.root / "missing", self.root / "missing-state")
        self.addCleanup(missing.close)
        missing.refresh()
        self.assertEqual(missing.snapshot()["source"]["status"], "missing")
        with patch("relayforge_progress.engine.os.scandir", side_effect=PermissionError("SECRET")):
            self.engine.refresh()
        self.assertEqual(self.engine.snapshot()["source"]["status"], "denied")
        self.assertNotIn("SECRET", json.dumps(self.engine.snapshot()))
        linked = self.root / "linked"
        linked.symlink_to(self.logs, target_is_directory=True)
        engine = Engine(linked, self.root / "linked-state")
        self.addCleanup(engine.close)
        engine.refresh()
        self.assertEqual(engine.snapshot()["source"]["status"], "degraded")

    def test_transaction_rollback_cursor_and_events(self) -> None:
        self.append(host("session_started"))
        original = self.engine._prune
        with patch.object(self.engine, "_prune", side_effect=sqlite3.OperationalError("SECRET")):
            self.engine.refresh()
        self.assertEqual(self.engine.snapshot()["events"], [])
        self.engine._prune = original
        self.engine.refresh()
        self.assertEqual(len(self.engine.snapshot()["events"]), 1)

    def test_limits_are_explicit(self) -> None:
        self.append(*(host("tool_started", tool_use_id="sha256:" + f"{n:020x}") for n in range(205)))
        with patch("relayforge_progress.projection.MAX_EVENTS", 5):
            self.engine.refresh()
        result = self.engine.snapshot()
        self.assertEqual(len(result["events"]), 5)
        self.assertEqual(len(result["sessions"][0]["tools"]), 200)
        self.assertEqual(result["source"]["diagnostics"]["tools_truncated"], 5)
        self.assertEqual(result["source"]["diagnostics"]["events_truncated"], 200)

    def test_state_source_identity_and_hostile_types(self) -> None:
        other = self.root / "other-logs"
        other.mkdir()
        with self.assertRaisesRegex(ValueError, "state_source_mismatch"):
            Engine(other, self.state)
        run = str(uuid4())
        self.append(
            host("tool_completed", tool_use_id=[], outcome={}, duration_ms=[]),
            {"schema_version": 1, "event": [], "session_id": {}},
            declared("route_selected", run, 1, risk=[]),
            declared("route_selected", run, 2, planned_skills={}),
            host("session_started"),
        )
        self.engine.refresh()
        self.assertEqual(self.engine.snapshot()["sessions"][0]["lifecycle"], "open_observed")
        self.assertGreaterEqual(self.engine.snapshot()["source"]["diagnostics"]["invalid_records"], 3)

    def test_byte_cache_budget_and_incremental_batch_budget(self) -> None:
        self.append(*(host("session_started") for _ in range(5)))
        with patch("relayforge_progress.engine.MAX_LINES", 2):
            self.engine.refresh()
            self.assertEqual(len(self.engine.snapshot()["events"]), 2)
            self.engine.refresh()
            self.assertEqual(len(self.engine.snapshot()["events"]), 4)
            self.engine.refresh()
        self.assertEqual(len(self.engine.snapshot()["events"]), 5)
        with patch("relayforge_progress.engine.MAX_CACHE_BYTES", 250):
            self.engine.refresh()
        self.assertLess(len(self.engine.snapshot()["events"]), 5)
        self.assertGreater(self.engine.snapshot()["source"]["diagnostics"]["cache_bytes_truncated"], 0)

    def test_cross_day_ingestion_preserves_lifecycle_order(self) -> None:
        yesterday = self.logs / ("events-" + (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d") + ".jsonl")
        yesterday.write_text(json.dumps(host("session_started", timestamp=stamp(1))) + "\n" + json.dumps(host("tool_started", tool_use_id=TOOL, tool_name="shell", timestamp=stamp(1))) + "\n")
        self.append(host("tool_completed", tool_use_id=TOOL, tool_name="shell", outcome="succeeded", matched_start=True, duration_ms=123), host("session_ended"))
        self.engine.refresh()
        result = self.engine.snapshot()
        self.assertEqual(result["sessions"][0]["lifecycle"], "end_observed")
        self.assertEqual(result["sessions"][0]["tools"][0]["state"], "completion_succeeded")
        self.assertEqual(result["sessions"][0]["tools"][0]["duration_ms"], 123)
        self.assertEqual([item["event"] for item in result["events"]], ["session_started", "tool_started", "tool_completed", "session_ended"])

    def test_quiet_refresh_preserves_content_revision(self) -> None:
        self.append(host("session_started"))
        self.engine.refresh()
        first = self.engine.snapshot()
        with patch("relayforge_progress.engine.now_iso", return_value=stamp(-1)):
            self.engine.refresh()
        second = self.engine.snapshot()
        self.assertEqual(second["revision"], first["revision"])
        self.assertNotEqual(second["source"]["last_read_at"], first["source"]["last_read_at"])
        self.append(host("session_ended"))
        self.engine.refresh()
        self.assertGreater(self.engine.snapshot()["revision"], first["revision"])

    @unittest.skipUnless(os.name == "posix", "POSIX directory permissions")
    def test_rejects_permissive_existing_state_without_chmod(self) -> None:
        permissive = self.root / "permissive"
        permissive.mkdir(mode=0o755)
        permissive.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "state_directory_permissions"):
            Engine(self.logs, permissive)
        self.assertEqual(permissive.stat().st_mode & 0o777, 0o755)
        self.assertEqual(list(permissive.iterdir()), [])

    def test_close_and_no_public_mutation(self) -> None:
        self.engine.close()
        self.engine.close()
        with self.assertRaisesRegex(RuntimeError, "engine_closed"):
            self.engine.refresh()
        with self.assertRaisesRegex(RuntimeError, "engine_closed"):
            self.engine.snapshot()


class ValidationTests(unittest.TestCase):
    """Reject unknown schemas and unsafe metadata without preserving input."""

    def test_bad_json_and_untrusted_values(self) -> None:
        for raw in (b"[]", b'{"x":NaN}', b'\xff', b'{"x":1,"x":2}'):
            with self.subTest(raw=raw), self.assertRaises(InvalidRecord):
                decode(raw)
        for record in ({"schema_version": 2, "event": "session_started"}, {"schema_version": True, "event": "session_started"}, {"schema_version": 1, "event": "anything"}):
            with self.subTest(record=record), self.assertRaises(InvalidRecord):
                sanitize(record)
        safe = sanitize(host("tool_completed", session_id="/secret/path", tool_name="/secret/path", duration_ms=True, timestamp="bad", model="SECRET"))
        self.assertNotIn("session_id", safe)
        self.assertNotIn("tool_name", safe)
        self.assertNotIn("duration_ms", safe)
        self.assertIsNone(safe["timestamp"])
        self.assertNotIn("SECRET", json.dumps(safe))


if __name__ == "__main__":
    unittest.main()
