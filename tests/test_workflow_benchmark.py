from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("benchmark", ROOT / "scripts/analyze_workflow_benchmark.py")
BENCHMARK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCHMARK)


def pair(identity="one", **candidate_changes):
    common = dict(pair_id=identity, task_id="preference-v1", scenario="full-stack",
                  snapshot="abc123", model="model+effort", environment="host+tools+permissions",
                  human_decisions=0, acceptance_passed=True, required_checks_passed=True,
                  review_required=False, regressions=0)
    return [dict(common, variant="baseline", duration_ms=1000, tokens=1000),
            dict(dict(common, variant="candidate", duration_ms=700, tokens=650), **candidate_changes)]


class WorkflowBenchmarkTests(unittest.TestCase):
    def test_policy_scoped_route_metrics_and_unknown_coverage(self):
        records = pair()
        records[1].update(plugin_version="0.1.9", route_policy_version="v2.1",
                         route_decisions=[
                             dict(rubric_id="local", allowed_routes=["L1"], actual_route="L1"),
                             dict(rubric_id="bounded", allowed_routes=["L1", "L2"], actual_route="L3"),
                             dict(rubric_id="coordinated", allowed_routes=["L3"], actual_route="L1"),
                             dict(rubric_id="missing", allowed_routes=["L2"], actual_route=None),
                         ])
        metrics = BENCHMARK.analyze(records)["workflow_metrics"]["candidate"]
        self.assertEqual(metrics["routing"]["v2.1"]["scored"], 3)
        self.assertEqual(metrics["routing"]["v2.1"]["accuracy"], 1 / 3)
        self.assertEqual(metrics["routing"]["v2.1"]["coverage"], 0.75)
        self.assertEqual(metrics["routing"]["v2.1"]["overrouting_rate"], 1 / 3)
        self.assertIsNone(metrics["attributed_costs"].get("overrouting"))

    def test_handoff_requires_facts_and_critical_readiness(self):
        record = pair()[1]
        record["handoff"] = dict(applicable=5, verified=5, disclosed=5,
                                 critical_fields_passed=False, readiness_passed=False)
        result = BENCHMARK.analyze([pair()[0], record])
        self.assertEqual(result["workflow_metrics"]["candidate"]["handoff"]["mean_verified_fraction"], 1)
        self.assertFalse(result["comparison"]["cost_comparison_eligible"])
        self.assertFalse(result["comparison"]["quality_preserved"])

    def test_new_counts_are_strict_and_rubrics_match(self):
        for changes in (
            dict(route_decisions=[dict(rubric_id="x", allowed_routes=["L9"], actual_route="L1")]),
            dict(route_changes=dict(upgrades=True, downgrades=0, complete=True, source="agent_declared")),
            dict(handoff=dict(applicable=2, verified=3, disclosed=2,
                              critical_fields_passed=True, readiness_passed=True)),
            dict(coordination=[dict(phase="wait", unit="ms", value=float("inf"), source="host_observed")]),
        ):
            self.assertFalse(BENCHMARK.valid_record(dict(pair()[1], **changes)))
        records = pair()
        records[0]["rubric_id"] = "fixed-v1"
        records[1]["rubric_id"] = "changed-after-run"
        self.assertFalse(BENCHMARK.analyze(records)["pairing"]["complete"])

    def test_paired_outcomes_allow_explicit_cost_targets(self):
        report = BENCHMARK.analyze(pair(), duration_target=25, token_target=30)
        self.assertEqual(report["comparison"]["duration_reduction_pct"], 30)
        self.assertEqual(report["comparison"]["token_reduction_pct"], 35)
        self.assertTrue(report["comparison"]["quality_preserved"])
        self.assertTrue(report["targets"]["duration_target_met"])
        self.assertTrue(report["targets"]["token_target_met"])

    def test_no_default_performance_target(self):
        report = BENCHMARK.analyze(pair())
        self.assertIsNone(report["targets"]["duration_target_met"])
        self.assertIsNone(report["targets"]["token_target_met"])

    def test_fast_wrong_result_cannot_meet_cost_target(self):
        for changes in (dict(acceptance_passed=False), dict(regressions=1),
                        dict(required_checks_passed=False), dict(unresolved_critical_important=1)):
            with self.subTest(changes=changes):
                report = BENCHMARK.analyze(pair(duration_ms=1, **changes), duration_target=20)
                self.assertFalse(report["comparison"]["quality_preserved"])
                self.assertFalse(report["comparison"]["cost_comparison_eligible"])
                self.assertIsNone(report["targets"]["duration_target_met"])

    def test_skipped_quality_is_unknown_not_success(self):
        records = pair()
        for record in records:
            for field in ("acceptance_passed", "required_checks_passed", "regressions", "review_required"):
                record.pop(field)
            record.update(verification_selected=False, review_selected=False)
        report = BENCHMARK.analyze(records, duration_target=20)
        self.assertIsNone(report["comparison"]["quality_preserved"])
        self.assertIsNone(report["targets"]["duration_target_met"])

    def test_required_review_needs_evidence_and_finding_count(self):
        report = BENCHMARK.analyze(pair(review_required=True, review_selected=False))
        self.assertIsNone(report["comparison"]["quality_preserved"])
        report = BENCHMARK.analyze(pair(review_required=True, review_evidence=True, unresolved_critical_important=0))
        self.assertTrue(report["comparison"]["quality_preserved"])

    def test_selected_verification_without_evidence_is_unknown(self):
        report = BENCHMARK.analyze(pair(verification_selected=True))
        self.assertIsNone(report["comparison"]["quality_preserved"])

    def test_each_pair_context_must_match(self):
        for field in BENCHMARK.PAIR_CONTEXT:
            with self.subTest(field=field):
                report = BENCHMARK.analyze(pair(**{field: "other"}), duration_target=20)
                self.assertFalse(report["pairing"]["complete"])
                self.assertIsNone(report["comparison"]["duration_reduction_pct"])
                self.assertIsNone(report["targets"]["duration_target_met"])

    def test_duplicates_and_unmatched_trials_block_overall_claim(self):
        for records in (pair() + [pair()[1]], pair() + [pair("two")[0]]):
            report = BENCHMARK.analyze(records)
            self.assertFalse(report["pairing"]["complete"])
            self.assertIsNone(report["comparison"]["duration_reduction_pct"])

    def test_legacy_records_remain_descriptive_only(self):
        records = pair()
        for record in records:
            record.pop("pair_id")
        report = BENCHMARK.analyze(records)
        self.assertEqual(report["variants"]["candidate"]["runs"], 1)
        self.assertFalse(report["comparison"]["cost_comparison_eligible"])

    def test_paired_percentages_do_not_pool_task_sizes(self):
        first = pair("one", duration_ms=500)
        second = pair("two", duration_ms=90000)
        second[0]["duration_ms"] = 100000
        report = BENCHMARK.analyze(first + second)
        self.assertEqual(report["comparison"]["duration_reduction_pct"], 30)

    def test_missing_tokens_and_zero_baselines_are_not_fabricated(self):
        records = pair(tokens=None)
        report = BENCHMARK.analyze(records)
        self.assertFalse(report["comparison"]["token_metric_complete"])
        self.assertIsNone(report["comparison"]["token_reduction_pct"])
        records[0]["duration_ms"] = 0
        self.assertIsNone(BENCHMARK.analyze(records)["comparison"]["duration_reduction_pct"])

    def test_empty_or_malformed_input_never_passes(self):
        for records, malformed in (([], 0), (pair(), 1)):
            report = BENCHMARK.analyze(records, malformed)
            self.assertFalse(report["comparison"]["cost_comparison_eligible"])
            self.assertIsNone(report["comparison"]["quality_preserved"])

    def test_strict_types_and_nonfinite_numbers(self):
        for changes in (dict(duration_ms=float("nan")), dict(duration_ms=float("inf")),
                        dict(tokens=True), dict(regressions=False), dict(human_decisions=-1),
                        dict(acceptance_passed="true"), dict(review_required=None)):
            self.assertFalse(BENCHMARK.valid_record(pair(**changes)[1]))
        with self.assertRaises(ValueError):
            BENCHMARK.analyze(pair(), duration_target=float("nan"))

    def test_jsonl_reader_keeps_invalid_data_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runs.jsonl"
            path.write_text(json.dumps(pair()[0]) + "\nnot-json\n[]\n", encoding="utf-8")
            records, malformed = BENCHMARK.read_records(path)
            self.assertEqual(len(records), 1)
            self.assertEqual(malformed, 2)


if __name__ == "__main__":
    unittest.main()
