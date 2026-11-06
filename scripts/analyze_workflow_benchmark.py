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
MODES = ("L1", "L2", "L3")


def measurement(value, phase=False):
    fields = {"unit", "value", "source"} | ({"phase"} if phase else {"evidence_ref"})
    if not isinstance(value, dict) or set(value) != fields:
        return False
    number = value["value"]
    return (type(number) in (int, float) and math.isfinite(number) and number >= 0
            and value["unit"] in ("ms", "tokens")
            and value["source"] in ("host_observed", "agent_declared")
            and (value["phase"] in ("dispatch", "context", "wait", "integration", "rework")
                 if phase else isinstance(value["evidence_ref"], str) and bool(value["evidence_ref"].strip())))


def valid_workflow_metrics(record):
    for field in ("plugin_version", "route_policy_version", "rubric_id"):
        if field in record and (not isinstance(record[field], str) or not record[field].strip()):
            return False
    if "route_decisions" in record:
        decisions = record["route_decisions"]
        if not isinstance(decisions, list):
            return False
        for item in decisions:
            if (not isinstance(item, dict)
                    or set(item) != {"rubric_id", "allowed_routes", "actual_route"}
                    or not isinstance(item["rubric_id"], str) or not item["rubric_id"].strip()
                    or not isinstance(item["allowed_routes"], list) or not item["allowed_routes"]
                    or any(mode not in MODES for mode in item["allowed_routes"])
                    or item["actual_route"] not in (*MODES, None)):
                return False
    if "route_changes" in record:
        item = record["route_changes"]
        if (not isinstance(item, dict) or set(item) != {"upgrades", "downgrades", "complete", "source"}
                or not count(item["upgrades"]) or not count(item["downgrades"])
                or type(item["complete"]) is not bool
                or item["source"] not in ("host_observed", "agent_declared")):
            return False
    if "handoff" in record:
        item = record["handoff"]
        if (not isinstance(item, dict)
                or set(item) != {"applicable", "verified", "disclosed", "critical_fields_passed", "readiness_passed"}
                or any(not count(item[f]) for f in ("applicable", "verified", "disclosed"))
                or not item["verified"] <= item["disclosed"] <= item["applicable"]
                or any(item[f] is not None and type(item[f]) is not bool
                       for f in ("critical_fields_passed", "readiness_passed"))):
            return False
    if "coordination" in record:
        if (not isinstance(record["coordination"], list)
                or any(not measurement(item, phase=True) for item in record["coordination"])):
            return False
    return all(measurement(record[field]) for field in ("overrouting_cost", "underrouting_cost")
               if field in record)


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
    return valid_workflow_metrics(record)


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
    handoff = record.get("handoff")
    if handoff and any(handoff.get(f) is False for f in ("critical_fields_passed", "readiness_passed")):
        return "failed"
    if any(record.get(f) is False for f in ("acceptance_passed", "required_checks_passed")):
        return "failed"
    if any((record.get(f) or 0) > 0 for f in ("regressions", "unresolved_critical_important")):
        return "failed"
    if any(record.get(f) is not True for f in ("acceptance_passed", "required_checks_passed")):
        return "unknown"
    if handoff and any(handoff.get(f) is not True for f in ("critical_fields_passed", "readiness_passed")):
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


def workflow_metrics(records):
    routing = {}
    for policy in sorted({r.get("route_policy_version", "unknown") for r in records}):
        runs = [r for r in records if r.get("route_policy_version", "unknown") == policy]
        decisions = [d for r in runs for d in r.get("route_decisions", [])]
        scored = [d for d in decisions if d["actual_route"] is not None and policy != "unknown"]
        total = len(scored)
        ratio = lambda number: number / total if total else None
        routing[policy] = {
            "runs": len(runs), "runs_with_decisions": sum("route_decisions" in r for r in runs),
            "decisions": len(decisions), "scored": total,
            "coverage": total / len(decisions) if decisions else None,
            "accuracy": ratio(sum(d["actual_route"] in d["allowed_routes"] for d in scored)),
            "overrouting_rate": ratio(sum(d["actual_route"] > max(d["allowed_routes"]) for d in scored)),
            "underrouting_rate": ratio(sum(d["actual_route"] < min(d["allowed_routes"]) for d in scored)),
            "other_mismatches": sum(d["actual_route"] not in d["allowed_routes"]
                                    and min(d["allowed_routes"]) <= d["actual_route"] <= max(d["allowed_routes"])
                                    for d in scored),
        }
    handoffs = [r["handoff"] for r in records if "handoff" in r]
    changes = [r["route_changes"] for r in records if "route_changes" in r]
    phases = defaultdict(list)
    for record in records:
        for item in record.get("coordination", []):
            phases[(item["phase"], item["unit"], item["source"])].append(item["value"])
    costs = {}
    for field in ("overrouting_cost", "underrouting_cost"):
        values = defaultdict(list)
        for record in records:
            if field in record:
                item = record[field]
                values[(item["unit"], item["source"])].append(item["value"])
        costs[field.removesuffix("_cost")] = [
            {"unit": unit, "source": source, "samples": len(samples), "median": median(samples)}
            for (unit, source), samples in sorted(values.items())
        ] or None
    rework = [r["human_rework"] for r in records if r.get("human_rework") is not None]
    fractions = lambda field: [h[field] / h["applicable"] for h in handoffs if h["applicable"]]
    return {
        "routing": routing, "attributed_costs": costs,
        "handoff": {"runs": len(handoffs),
                    "mean_verified_fraction": statistics.mean(fractions("verified")) if fractions("verified") else None,
                    "mean_disclosed_fraction": statistics.mean(fractions("disclosed")) if fractions("disclosed") else None,
                    "critical_passed": sum(h["critical_fields_passed"] is True for h in handoffs),
                    "readiness_passed": sum(h["readiness_passed"] is True for h in handoffs)},
        "route_changes": {"runs": len(changes), "complete_runs": sum(c["complete"] for c in changes),
                          "observed_upgrades": sum(c["upgrades"] for c in changes) if changes else None,
                          "observed_downgrades": sum(c["downgrades"] for c in changes) if changes else None,
                          "sources": sorted({c["source"] for c in changes})},
        "coordination": [{"phase": phase, "unit": unit, "source": source,
                          "samples": len(samples), "median": median(samples)}
                         for (phase, unit, source), samples in sorted(phases.items())],
        "rework": {"coverage": len(rework), "runs_with_rework_rate":
                   sum(v > 0 for v in rework) / len(rework) if rework else None},
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
        if any(b[f] != c[f] for f in PAIR_CONTEXT) or b.get("rubric_id") != c.get("rubric_id"):
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
        "workflow_metrics": {v: workflow_metrics([r for r in valid if r["variant"] == v])
                             for v in ("baseline", "candidate")},
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
