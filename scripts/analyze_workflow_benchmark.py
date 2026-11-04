#!/usr/bin/env python3
"""Compare paired workflow runs with explicit outcome evidence and optional targets."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics


PAIR_CONTEXT = ("task_id", "scenario", "snapshot", "model", "environment")
BOOLEAN_FIELDS = ("acceptance_passed", "required_checks_passed", "review_required",
                  "verification_selected", "verification_evidence", "review_selected", "review_evidence")
COUNT_FIELDS = ("tokens", "regressions", "human_rework", "unresolved_critical_important")


def count(value):
    return type(value) is int and value >= 0


def valid_record(record):
    if not isinstance(record, dict) or record.get("variant") not in {"baseline", "candidate"}:
        return False
    duration = record.get("duration_ms")
    if type(duration) not in (int, float) or not math.isfinite(duration) or duration < 0:
        return False
    if not count(record.get("human_decisions")):
        return False
    if not isinstance(record.get("scenario"), str) or not record["scenario"].strip():
        return False
    for field in ("pair_id", *PAIR_CONTEXT):
        if field in record and (not isinstance(record[field], str) or not record[field].strip()):
            return False
    for field in BOOLEAN_FIELDS:
        if field in record and type(record[field]) is not bool:
            return False
    for field in COUNT_FIELDS:
        if field in record and record[field] is not None and not count(record[field]):
            return False
    return True


def read_records(path):
    records, malformed = [], 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return records, 1
    for line in lines:
        try:
            record = json.loads(line)
        except (ValueError, TypeError):
            malformed += 1
            continue
        if valid_record(record):
            records.append(record)
        else:
            malformed += 1
    return records, malformed


def median(values):
    values = list(values)
    return round(float(statistics.median(values)), 2) if values else None


def reduction(baseline, candidate):
    if baseline is None or candidate is None or baseline <= 0:
        return None
    return (baseline - candidate) / baseline * 100


def outcome(record):
    # A demonstrated failure dominates missing evidence. Absence is never a pass.
    if any(record.get(f) is False for f in ("acceptance_passed", "required_checks_passed")):
        return "failed"
    if any((record.get(f) or 0) > 0 for f in ("regressions", "unresolved_critical_important")):
        return "failed"
    if any(record.get(f) is not True for f in ("acceptance_passed", "required_checks_passed")):
        return "unknown"
    if record.get("regressions") != 0 or "review_required" not in record:
        return "unknown"
    if record.get("verification_selected") and record.get("verification_evidence") is not True:
        return "unknown"
    if record["review_required"] or record.get("review_selected"):
        if (record.get("review_evidence") is not True
                or record.get("unresolved_critical_important") != 0):
            return "unknown"
    return "passed"


def summarize(records):
    states = [outcome(r) for r in records]
    return {
        "runs": len(records),
        "outcomes": {state: states.count(state) for state in ("passed", "failed", "unknown")},
        "median_duration_ms": median(r["duration_ms"] for r in records),
        "median_tokens": median(r["tokens"] for r in records if r.get("tokens") is not None),
        "token_coverage": sum(r.get("tokens") is not None for r in records),
        "median_human_decisions": median(r["human_decisions"] for r in records),
        "median_human_rework": median(r["human_rework"] for r in records if r.get("human_rework") is not None),
    }


def analyze(records, malformed=0, *, duration_target=None, token_target=None):
    for target in (duration_target, token_target):
        if target is not None and (type(target) not in (int, float) or not math.isfinite(target) or not 0 <= target <= 100):
            raise ValueError("reduction targets must be finite percentages from 0 to 100")
    valid = [r for r in records if valid_record(r)]
    malformed += len(records) - len(valid)
    groups = defaultdict(list)
    excluded = []
    for index, record in enumerate(valid):
        if not all(record.get(field) for field in ("pair_id", *PAIR_CONTEXT)):
            excluded.append({"record": index, "reason": "missing pair identity or comparable context"})
        else:
            groups[record["pair_id"]].append(record)
    pairs = []
    for pair_id, runs in sorted(groups.items()):
        baseline = [r for r in runs if r["variant"] == "baseline"]
        candidate = [r for r in runs if r["variant"] == "candidate"]
        if len(baseline) != 1 or len(candidate) != 1:
            excluded.append({"pair_id": pair_id, "reason": "requires exactly one run per variant"})
            continue
        b, c = baseline[0], candidate[0]
        if any(b[f] != c[f] for f in PAIR_CONTEXT):
            excluded.append({"pair_id": pair_id, "reason": "task, scenario, snapshot, model or environment mismatch"})
            continue
        pairs.append({"pair_id": pair_id, "scenario": b["scenario"],
                      "baseline_outcome": outcome(b), "candidate_outcome": outcome(c),
                      "duration_reduction_pct": reduction(b["duration_ms"], c["duration_ms"]),
                      "token_reduction_pct": reduction(b.get("tokens"), c.get("tokens"))})
    complete = bool(pairs) and not excluded and not malformed
    states = [p[f] for p in pairs for f in ("baseline_outcome", "candidate_outcome")]
    quality = False if "failed" in states else (True if complete and all(s == "passed" for s in states) else None)
    duration_complete = complete and all(p["duration_reduction_pct"] is not None for p in pairs)
    tokens_complete = complete and all(p["token_reduction_pct"] is not None for p in pairs)
    duration = median(p["duration_reduction_pct"] for p in pairs) if duration_complete else None
    tokens = median(p["token_reduction_pct"] for p in pairs) if tokens_complete else None
    eligible = complete and quality is True
    def meets(value, target):
        return value >= target if eligible and value is not None and target is not None else None
    return {
        "schema_version": 2, "records": len(valid), "malformed_records": malformed,
        "variants": {v: summarize([r for r in valid if r["variant"] == v]) for v in ("baseline", "candidate")},
        "pairing": {"complete": complete, "matched_pairs": len(pairs), "excluded": excluded},
        "pairs": pairs,
        "comparison": {"duration_reduction_pct": duration, "token_reduction_pct": tokens,
                       "token_metric_complete": tokens_complete,
                       "quality_preserved": quality, "cost_comparison_eligible": eligible},
        "targets": {"duration_reduction_pct": duration_target, "token_reduction_pct": token_target,
                    "duration_target_met": meets(duration, duration_target),
                    "token_target_met": meets(tokens, token_target)},
        "limitations": [
            "Outcome fields require independently checked acceptance, regression and required-check evidence; declarations alone are not proof.",
            "Pairs must share task/rubric, repository snapshot, exact model settings and environment; repeat with new pair IDs in isolated workspaces.",
            "Reductions are medians of within-pair percentages, not pooled medians. All recorded pairs must be comparable before an overall claim.",
            "Unknown evidence is not success. Include failed/interrupted attempts and rework in the task run; do not select only successful runs.",
            "No default time/token target or autonomy target is imposed. Missing reliable tokens remain unavailable.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--duration-target", type=float)
    parser.add_argument("--token-target", type=float)
    args = parser.parse_args()
    records, malformed = read_records(args.input)
    try:
        report = analyze(records, malformed, duration_target=args.duration_target, token_target=args.token_target)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
