from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPECIFICATION = importlib.util.spec_from_file_location(
    "analyze_workflow_benchmark", ROOT / "scripts" / "analyze_workflow_benchmark.py"
)
assert SPECIFICATION and SPECIFICATION.loader
BENCHMARK = importlib.util.module_from_spec(SPECIFICATION)
SPECIFICATION.loader.exec_module(BENCHMARK)


class WorkflowBenchmarkTests(unittest.TestCase):
    def test_analyze_reports_improvements_and_quality_targets(self):
        records = [
            {"variant": "baseline", "scenario": "frontend-request", "duration_ms": 1000, "tokens": 1000, "human_decisions": 2},
            {"variant": "baseline", "scenario": "backend-bug", "duration_ms": 1200, "tokens": 1200, "human_decisions": 1},
            {"variant": "candidate", "scenario": "frontend-request", "duration_ms": 700, "tokens": 650, "human_decisions": 0, "verification_selected": True, "verification_evidence": True},
            {"variant": "candidate", "scenario": "backend-bug", "duration_ms": 800, "tokens": 750, "human_decisions": 0, "review_selected": True, "unresolved_critical_important": 0},
        ]

        report = BENCHMARK.analyze(records)

        self.assertEqual(report["comparison"]["duration_reduction_pct"], 31.82)
        self.assertEqual(report["comparison"]["token_reduction_pct"], 36.36)
        self.assertTrue(report["targets"]["duration_reduction_at_least_25_pct"])
        self.assertTrue(report["targets"]["token_reduction_at_least_30_pct"])
        self.assertTrue(report["targets"]["no_midcourse_decision_rate_at_least_80_pct"])
        self.assertTrue(report["targets"]["selected_verification_has_evidence"])
        self.assertTrue(report["targets"]["selected_review_has_no_open_critical_or_important"])

    def test_missing_tokens_marks_token_target_unavailable(self):
        records = [
            {"variant": "baseline", "scenario": "docker-problem", "duration_ms": 1000, "human_decisions": 1},
            {"variant": "candidate", "scenario": "docker-problem", "duration_ms": 700, "human_decisions": 0},
        ]

        report = BENCHMARK.analyze(records)

        self.assertFalse(report["comparison"]["token_metric_complete"])
        self.assertIsNone(report["comparison"]["token_reduction_pct"])
        self.assertIsNone(report["targets"]["token_reduction_at_least_30_pct"])

    def test_selected_review_requires_an_explicit_material_finding_count(self):
        records = [
            {"variant": "baseline", "scenario": "backend-bug", "duration_ms": 1000, "human_decisions": 1},
            {"variant": "candidate", "scenario": "backend-bug", "duration_ms": 700, "human_decisions": 0, "review_selected": True},
        ]

        report = BENCHMARK.analyze(records)

        self.assertFalse(report["targets"]["selected_review_has_no_open_critical_or_important"])

    def test_empty_input_does_not_pass_quality_targets(self):
        report = BENCHMARK.analyze([])

        self.assertFalse(report["targets"]["selected_verification_has_evidence"])
        self.assertFalse(report["targets"]["selected_review_has_no_open_critical_or_important"])

    def test_invalid_records_are_rejected(self):
        self.assertFalse(BENCHMARK.valid_record({"variant": "candidate"}))
        self.assertFalse(
            BENCHMARK.valid_record(
                {"variant": "candidate", "scenario": "x", "duration_ms": -1, "human_decisions": 0}
            )
        )


if __name__ == "__main__":
    unittest.main()
