from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


LOGGER = module("workflow_logger")
ANALYZER = module("analyze_workflow_logs")


def event(kind="route_selected", sequence=1, run=None, **fields):
    value = dict(event=kind, workflow_event_schema_version=1, event_id=str(uuid4()),
                 task_run_id=run or str(uuid4()), sequence=sequence, route_policy_version="v2.1")
    if kind == "route_selected":
        value.update(execution_mode="L1", route="quick", risk="high",
                     reason_code="local_scope", planned_skills=[])
    elif kind == "route_changed":
        value.update({"from": "L1", "to": "L2", "reason_code": "design_required"})
    value.update(fields)
    return value


class WorkflowDecisionTests(unittest.TestCase):
    def test_multiple_transitions_replay_and_legacy_are_separate(self):
        first = event()
        second = event("route_changed", 2, first["task_run_id"])
        third = event("route_changed", 3, first["task_run_id"],
                      **{"from": "L2", "to": "L3", "reason_code": "coordination_required"})
        last = event("route_changed", 4, first["task_run_id"],
                     **{"from": "L3", "to": "L2", "reason_code": "coordination_unnecessary"})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for item in (first, second, third, last, second):
                LOGGER.record_workflow_event(item, root)
            records, malformed = ANALYZER.read_records(root / "logs")
            records.append(dict(event="routing_decision", route="standard"))
            report = ANALYZER.analyze(records, malformed)
        decisions = report["workflow_decisions"]
        self.assertEqual(decisions["tasks"], 1)
        self.assertEqual(decisions["duplicates"], 1)
        self.assertEqual(decisions["upgrades"], 2)
        self.assertEqual(decisions["downgrades"], 1)
        self.assertEqual(decisions["final_routes"], {"L2": 1})
        self.assertEqual(decisions["partial_tasks"], 0)
        self.assertEqual(report["routing"]["route_counts"], {"standard": 1})

    def test_missing_conflicting_and_discontinuous_events_are_partial(self):
        first = event()
        for other in (
            event("route_changed", 3, first["task_run_id"]),
            event("route_changed", 2, first["task_run_id"],
                  **{"from": "L2", "to": "L3", "reason_code": "coordination_required"}),
            dict(first, execution_mode="L2", route="standard", reason_code="bounded_sdd"),
            event(sequence=1, run=first["task_run_id"]),
        ):
            with self.subTest(other=other):
                report = ANALYZER.analyze([dict(first, source="agent_declared"),
                                          dict(other, source="agent_declared")], 0)
                self.assertEqual(report["workflow_decisions"]["partial_tasks"], 1)
                self.assertTrue(report["workflow_decisions"]["issues"])
        orphan = event("route_changed", 2)
        self.assertEqual(ANALYZER.analyze([dict(orphan, source="agent_declared")], 0)
                         ["workflow_decisions"]["partial_tasks"], 1)

    def test_strict_payloads_do_not_reach_disk(self):
        first = event()
        cases = [
            dict(first, prompt="secret"), dict(first, source="host_observed"),
            dict(first, sequence=True), dict(first, sequence=0),
            dict(first, event_id="user-secret"), dict(first, risk="normal"),
            dict(first, route="large"), dict(first, planned_skills=["source code!"]),
            dict(first, reason_code="a full prompt"),
            event("route_changed", 2, **{"from": "L1", "to": "L3"}),
            event("route_changed", 2, **{"from": "L1", "to": "L1"}),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for item in cases:
                with self.subTest(item=item), self.assertRaises(ValueError):
                    LOGGER.record_workflow_event(item, root)
            self.assertEqual(list(root.iterdir()), [])

    def test_summary_enums_and_blocked_completion(self):
        summary = event("verification_summary", implementation="complete", minimal_checks="passed",
                        test_verification="partial", code_review="unavailable", commit="skipped", push="skipped")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            LOGGER.record_workflow_event(summary, root)
            LOGGER.record_workflow_event(event("handoff_generated", form="file",
                development_status="blocked", code_availability="local_only"), root)
            LOGGER.record_workflow_event(event("workflow_completed",
                implementation="complete", development_status="blocked"), root)
            with self.assertRaises(ValueError):
                LOGGER.record_workflow_event(dict(summary, test_verification="not_run"), root)
            with self.assertRaises(ValueError):
                LOGGER.record_workflow_event(event("handoff_generated", form="file",
                    development_status="ready_for_testing", code_availability="local_only"), root)
            with self.assertRaises(ValueError):
                LOGGER.record_workflow_event(event("workflow_completed",
                    implementation="blocked", development_status="ready_with_issues"), root)

    def test_cli_size_limit_rejection_and_no_payload_echo(self):
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, str(ROOT / "scripts/workflow_logger.py"),
                       "--record-workflow-event", "--data-dir", directory]
            for payload in (json.dumps(event()), '{"prompt":"' + "S" * 17000 + '"}',
                            '{"event":1,"event":2}', '{"prompt":"secret"}', '[1]'):
                result = subprocess.run(command, input=payload, text=True, capture_output=True)
                if '"workflow_event_schema_version"' in payload:
                    self.assertEqual(result.returncode, 0, result.stderr)
                else:
                    self.assertEqual(result.returncode, 2)
                self.assertNotIn("secret", result.stdout + result.stderr)
                self.assertNotIn("SSSS", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
