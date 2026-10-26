from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    specification = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


LOGGER = load_module("workflow_logger", "scripts/workflow_logger.py")
ANALYZER = load_module("analyze_workflow_logs", "scripts/analyze_workflow_logs.py")


class WorkflowLoggingTests(unittest.TestCase):
    def test_tool_events_exclude_payload_and_calculate_duration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            now = datetime(2026, 10, 26, 2, 0, tzinfo=timezone.utc)
            base = {
                "session_id": "session-secret",
                "turn_id": "turn-secret",
                "tool_use_id": "tool-secret",
                "tool_name": "Bash",
                "tool_input": {"command": "do-not-log-this"},
            }
            LOGGER.handle_event({**base, "hook_event_name": "PreToolUse"}, root, now, 1_000_000)
            LOGGER.handle_event(
                {**base, "hook_event_name": "PostToolUse", "tool_response": {"exit_code": 0, "output": "do-not-log-this"}},
                root,
                now,
                3_500_000,
            )

            path = root / "logs" / "events-2026-10-26.jsonl"
            content = path.read_text(encoding="utf-8")
            events = [json.loads(line) for line in content.splitlines()]

            self.assertEqual([event["event"] for event in events], ["tool_started", "tool_completed"])
            self.assertEqual(events[1]["duration_ms"], 2)
            self.assertEqual(events[1]["outcome"], "succeeded")
            self.assertNotIn("do-not-log-this", content)
            self.assertNotIn("session-secret", content)
            self.assertNotIn("tool-secret", content)

    def test_analyzer_summarizes_tool_and_turn_durations(self):
        records = [
            {"event": "turn_started", "timestamp": "2026-10-26T02:00:00.000Z", "session_id": "s", "turn_id": "t"},
            {"event": "tool_completed", "timestamp": "2026-10-26T02:00:01.000Z", "session_id": "s", "turn_id": "t", "tool_use_id": "u", "tool_name": "Bash", "duration_ms": 250, "outcome": "succeeded"},
            {"event": "turn_stopped", "timestamp": "2026-10-26T02:00:02.000Z", "session_id": "s", "turn_id": "t"},
        ]
        report = ANALYZER.analyze(records, 0)

        self.assertEqual(report["tool_timing"]["Bash"]["calls"], 1)
        self.assertEqual(report["tool_timing"]["Bash"]["total_ms"], 250)
        self.assertEqual(report["turn_timing"]["total_ms"], 2000)
        self.assertEqual(report["unfinished_turns"], 0)

    def test_stop_event_extracts_only_declared_routing_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            LOGGER.handle_event(
                {
                    "hook_event_name": "Stop",
                    "session_id": "session-secret",
                    "turn_id": "turn-secret",
                    "last_assistant_message": (
                        "Changed the endpoint.\n"
                        "Workflow route: Large | Work surfaces: frontend, backend | "
                        "Planned skills: backend-patterns, frontend-patterns  "
                    ),
                },
                root,
                datetime(2026, 10, 26, tzinfo=timezone.utc),
            )

            path = root / "logs" / "events-2026-10-26.jsonl"
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[1]["event"], "routing_decision")
            self.assertEqual(events[1]["route"], "large")
            self.assertEqual(events[1]["work_surfaces"], ["frontend", "backend"])
            self.assertEqual(events[1]["planned_skills"], ["backend-patterns", "frontend-patterns"])
            self.assertNotIn("Changed the endpoint", path.read_text(encoding="utf-8"))

            report = ANALYZER.analyze(events, 0)
            self.assertEqual(report["routing"]["route_counts"], {"large": 1})
            self.assertEqual(report["routing"]["work_surface_counts"], {"backend": 1, "frontend": 1})
            self.assertEqual(report["routing"]["planned_skill_counts"]["backend-patterns"], 1)

    def test_stop_event_extracts_finishing_status_without_reply_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            LOGGER.handle_event(
                {
                    "hook_event_name": "Stop",
                    "session_id": "session-secret",
                    "turn_id": "turn-secret",
                    "last_assistant_message": (
                        "Implementation finished.\n"
                        "Workflow status: Implementation=complete | Minimal checks=passed | "
                        "Test verification=partial | Code review=findings-open | "
                        "Commit=blocked | Push=skipped  "
                    ),
                },
                root,
                datetime(2026, 10, 26, tzinfo=timezone.utc),
            )

            path = root / "logs" / "events-2026-10-26.jsonl"
            content = path.read_text(encoding="utf-8")
            events = [json.loads(line) for line in content.splitlines()]
            self.assertEqual(events[1]["event"], "workflow_status")
            self.assertEqual(events[1]["implementation"], "complete")
            self.assertEqual(events[1]["test_verification"], "partial")
            self.assertEqual(events[1]["code_review"], "findings-open")
            self.assertEqual(events[1]["commit"], "blocked")
            self.assertNotIn("Implementation finished", content)

            report = ANALYZER.analyze(events, 0)
            self.assertEqual(report["workflow_status"]["implementation"], {"complete": 1})
            self.assertEqual(report["workflow_status"]["commit"], {"blocked": 1})

    def test_retention_removes_only_expired_daily_logs(self):
        with tempfile.TemporaryDirectory() as temporary:
            log_directory = Path(temporary)
            today = datetime(2026, 10, 26, tzinfo=timezone.utc)
            expired = log_directory / "events-2026-09-25.jsonl"
            retained = log_directory / "events-2026-09-27.jsonl"
            expired.write_text("{}\n", encoding="utf-8")
            retained.write_text("{}\n", encoding="utf-8")

            LOGGER.clean_old_data(log_directory, today)

            self.assertFalse(expired.exists())
            self.assertTrue(retained.exists())

    def test_concurrent_hook_events_keep_jsonl_intact(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            now = datetime(2026, 10, 26, tzinfo=timezone.utc)

            def write(index: int) -> None:
                LOGGER.handle_event(
                    {
                        "hook_event_name": "UserPromptSubmit",
                        "session_id": "session-" + str(index),
                        "turn_id": "turn-" + str(index),
                    },
                    root,
                    now + timedelta(milliseconds=index),
                )

            workers = [threading.Thread(target=write, args=(index,)) for index in range(12)]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join()

            path = root / "logs" / "events-2026-10-26.jsonl"
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(events), 12)
            self.assertTrue(all(event["event"] == "turn_started" for event in events))

    def test_hook_command_and_analyzer_work_end_to_end(self):
        with tempfile.TemporaryDirectory() as temporary:
            environment = os.environ.copy()
            environment["PLUGIN_DATA"] = temporary
            hook_event = json.dumps(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "session-secret",
                    "turn_id": "turn-secret",
                    "prompt": "do-not-record",
                }
            )
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "workflow_logger.py")],
                input=hook_event,
                text=True,
                capture_output=True,
                check=True,
                env=environment,
            )
            report = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "analyze_workflow_logs.py"),
                    "--log-dir",
                    str(Path(temporary) / "logs"),
                ],
                text=True,
                capture_output=True,
                check=True,
                env=environment,
            )
            self.assertEqual(json.loads(report.stdout)["records"], 1)
            logged = next((Path(temporary) / "logs").glob("events-*.jsonl")).read_text(encoding="utf-8")
            self.assertNotIn("do-not-record", logged)
            self.assertNotIn("session-secret", logged)

    def test_forward_test_log_override_wins_over_managed_plugin_data(self):
        with tempfile.TemporaryDirectory() as managed, tempfile.TemporaryDirectory() as isolated:
            environment = os.environ.copy()
            environment["PLUGIN_DATA"] = managed
            environment["RELAYFORGE_WORKFLOW_LOG_DIR"] = isolated
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "workflow_logger.py")],
                input=json.dumps({"hook_event_name": "UserPromptSubmit"}),
                text=True,
                capture_output=True,
                check=True,
                env=environment,
            )
            self.assertTrue(list((Path(isolated) / "logs").glob("events-*.jsonl")))
            self.assertFalse((Path(managed) / "logs").exists())

    def test_stop_hook_command_returns_required_json_acknowledgement(self):
        with tempfile.TemporaryDirectory() as temporary:
            environment = os.environ.copy()
            environment["PLUGIN_DATA"] = temporary
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "workflow_logger.py")],
                input=json.dumps({"hook_event_name": "Stop", "session_id": "s", "turn_id": "t"}),
                text=True,
                capture_output=True,
                check=True,
                env=environment,
            )
            self.assertEqual(json.loads(result.stdout), {"continue": True})


if __name__ == "__main__":
    unittest.main()
