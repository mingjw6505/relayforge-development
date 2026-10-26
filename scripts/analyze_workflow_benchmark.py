#!/usr/bin/env python3
"""Compare baseline and candidate workflow benchmark JSONL records."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


TARGET_TOKEN_REDUCTION = 30.0
TARGET_DURATION_REDUCTION = 25.0
TARGET_AUTONOMY_RATE = 80.0


def read_records(path: Path) -> Tuple[List[Dict[str, Any]], int]:
    records: List[Dict[str, Any]] = []
    malformed = 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return records, 1
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(value, dict) and valid_record(value):
            records.append(value)
        else:
            malformed += 1
    return records, malformed


def non_negative_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


def valid_record(record: Dict[str, Any]) -> bool:
    if record.get("variant") not in {"baseline", "candidate"}:
        return False
    if not isinstance(record.get("scenario"), str) or not record["scenario"]:
        return False
    if not non_negative_number(record.get("duration_ms")):
        return False
    decisions = record.get("human_decisions")
    if not isinstance(decisions, int) or isinstance(decisions, bool) or decisions < 0:
        return False
    tokens = record.get("tokens")
    return tokens is None or (isinstance(tokens, int) and not isinstance(tokens, bool) and tokens >= 0)


def median(values: Iterable[float]) -> Optional[float]:
    samples = list(values)
    return round(float(statistics.median(samples)), 2) if samples else None


def percent_reduction(baseline: Optional[float], candidate: Optional[float]) -> Optional[float]:
    if baseline is None or candidate is None or baseline == 0:
        return None
    return round((baseline - candidate) / baseline * 100, 2)


def percent(value: int, total: int) -> Optional[float]:
    return round(value / total * 100, 2) if total else None


def quality_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    verification = [record for record in records if record.get("verification_selected") is True]
    review = [record for record in records if record.get("review_selected") is True]
    return {
        "verification_selected": len(verification),
        "verification_with_evidence": sum(
            record.get("verification_evidence") is True for record in verification
        ),
        "review_selected": len(review),
        "review_without_open_critical_or_important": sum(
            isinstance(record.get("unresolved_critical_important"), int)
            and record["unresolved_critical_important"] == 0
            for record in review
        ),
        "review_with_open_critical_or_important": sum(
            isinstance(record.get("unresolved_critical_important"), int)
            and record["unresolved_critical_important"] > 0
            for record in review
        ),
    }


def variant_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    token_samples = [record["tokens"] for record in records if isinstance(record.get("tokens"), int)]
    by_scenario: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_scenario[record["scenario"]].append(record)
    return {
        "runs": len(records),
        "median_duration_ms": median(record["duration_ms"] for record in records),
        "median_tokens": median(token_samples),
        "token_coverage": {"reported": len(token_samples), "runs": len(records)},
        "no_midcourse_decision_rate_pct": percent(
            sum(record["human_decisions"] == 0 for record in records), len(records)
        ),
        "quality": quality_summary(records),
        "scenarios": {
            scenario: {
                "runs": len(samples),
                "median_duration_ms": median(sample["duration_ms"] for sample in samples),
                "median_tokens": median(
                    sample["tokens"] for sample in samples if isinstance(sample.get("tokens"), int)
                ),
            }
            for scenario, samples in sorted(by_scenario.items())
        },
    }


def analyze(records: List[Dict[str, Any]], malformed: int = 0) -> Dict[str, Any]:
    grouped = {
        variant: [record for record in records if record["variant"] == variant]
        for variant in ("baseline", "candidate")
    }
    summaries = {variant: variant_summary(samples) for variant, samples in grouped.items()}
    baseline = summaries["baseline"]
    candidate = summaries["candidate"]
    tokens_complete = all(
        summary["runs"] > 0 and summary["token_coverage"]["reported"] == summary["runs"]
        for summary in summaries.values()
    )
    token_reduction = (
        percent_reduction(baseline["median_tokens"], candidate["median_tokens"])
        if tokens_complete
        else None
    )
    duration_reduction = percent_reduction(
        baseline["median_duration_ms"], candidate["median_duration_ms"]
    )
    quality = candidate["quality"]
    verification_ok = (
        candidate["runs"] > 0
        and quality["verification_selected"] == quality["verification_with_evidence"]
    )
    review_ok = (
        candidate["runs"] > 0
        and quality["review_selected"]
        == quality["review_without_open_critical_or_important"]
    )
    autonomy = candidate["no_midcourse_decision_rate_pct"]
    return {
        "records": len(records),
        "malformed_records": malformed,
        "variants": summaries,
        "comparison": {
            "duration_reduction_pct": duration_reduction,
            "token_reduction_pct": token_reduction,
            "token_metric_complete": tokens_complete,
        },
        "targets": {
            "duration_reduction_at_least_25_pct": (
                duration_reduction is not None and duration_reduction >= TARGET_DURATION_REDUCTION
            ),
            "token_reduction_at_least_30_pct": (
                None if token_reduction is None else token_reduction >= TARGET_TOKEN_REDUCTION
            ),
            "no_midcourse_decision_rate_at_least_80_pct": (
                autonomy is not None and autonomy >= TARGET_AUTONOMY_RATE
            ),
            "selected_verification_has_evidence": verification_ok,
            "selected_review_has_no_open_critical_or_important": review_ok,
        },
        "limitations": [
            "A null token target means one or more runs did not expose a reliable token metric.",
            "Compare equivalent prompts with the same model tier and a similar execution environment.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Benchmark JSONL input.")
    arguments = parser.parse_args()
    records, malformed = read_records(arguments.input)
    print(json.dumps(analyze(records, malformed), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
