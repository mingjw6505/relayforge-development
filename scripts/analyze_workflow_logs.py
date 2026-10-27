#!/usr/bin/env python3
"""Summarize RelayForge Development workflow telemetry JSONL files."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def read_records(log_directory: Path) -> Tuple[List[Dict[str, Any]], int]:
    records: List[Dict[str, Any]] = []
    malformed = 0
    for path in sorted(log_directory.glob("events-*.jsonl")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            malformed += 1
            continue
        for line in lines:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if isinstance(record, dict):
                records.append(record)
            else:
                malformed += 1
    return records, malformed


def percentile(values: List[int], probability: float) -> Optional[int]:
    if not values:
        return None
    position = max(0, math.ceil(len(values) * probability) - 1)
    return sorted(values)[position]


def summary(values: Iterable[int]) -> Dict[str, Optional[float]]:
    samples = list(values)
    if not samples:
        return {"calls": 0, "total_ms": 0, "average_ms": None, "p50_ms": None, "p95_ms": None, "max_ms": None}
    return {
        "calls": len(samples),
        "total_ms": sum(samples),
        "average_ms": round(sum(samples) / len(samples), 2),
        "p50_ms": percentile(samples, 0.50),
        "p95_ms": percentile(samples, 0.95),
        "max_ms": max(samples),
    }


def turn_key(record: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    session = record.get("session_id")
    turn = record.get("turn_id")
    if isinstance(session, str) and isinstance(turn, str):
        return session, turn
    return None


def analyze(records: List[Dict[str, Any]], malformed: int) -> Dict[str, Any]:
    durations: Dict[str, List[int]] = defaultdict(list)
    outcomes: Counter[str] = Counter()
    started_tools = set()
    completed_tools = set()
    turn_started: Dict[Tuple[str, str], datetime] = {}
    turn_finished: Dict[Tuple[str, str], datetime] = {}
    routes: Counter[str] = Counter()
    work_surfaces: Counter[str] = Counter()
    planned_skills: Counter[str] = Counter()
    workflow_status: Dict[str, Counter[str]] = defaultdict(Counter)
    interrupted = 0

    for record in records:
        event = record.get("event")
        key = turn_key(record)
        timestamp = parse_timestamp(record.get("timestamp"))

        if event == "turn_started" and key and timestamp:
            turn_started.setdefault(key, timestamp)
        elif event in {"turn_stopped", "turn_interrupted"} and key and timestamp:
            turn_finished[key] = timestamp
            if event == "turn_interrupted":
                interrupted += 1

        if event == "routing_decision":
            route = record.get("route")
            if isinstance(route, str):
                routes[route] += 1
            skills = record.get("planned_skills")
            if isinstance(skills, list):
                planned_skills.update(skill for skill in skills if isinstance(skill, str))
            surfaces = record.get("work_surfaces")
            if isinstance(surfaces, list):
                work_surfaces.update(surface for surface in surfaces if isinstance(surface, str))

        if event == "workflow_status":
            for field in (
                "implementation",
                "minimal_checks",
                "test_verification",
                "code_review",
                "commit",
                "push",
            ):
                value = record.get(field)
                if isinstance(value, str):
                    workflow_status[field][value] += 1

        tool_id = record.get("tool_use_id")
        tool_key_value = (record.get("session_id"), record.get("turn_id"), tool_id)
        if event == "tool_started" and all(isinstance(item, str) for item in tool_key_value):
            started_tools.add(tool_key_value)
        elif event == "tool_completed":
            if all(isinstance(item, str) for item in tool_key_value):
                completed_tools.add(tool_key_value)
            duration = record.get("duration_ms")
            tool_name = record.get("tool_name", "unknown")
            if isinstance(tool_name, str) and isinstance(duration, int) and duration >= 0:
                durations[tool_name].append(duration)
            outcome = record.get("outcome")
            if isinstance(outcome, str):
                outcomes[outcome] += 1

    turn_durations = [
        max(0, round((turn_finished[key] - started).total_seconds() * 1000))
        for key, started in turn_started.items()
        if key in turn_finished
    ]
    tool_summary = {tool: summary(samples) for tool, samples in sorted(durations.items())}
    incomplete_turns = len(set(turn_started) - set(turn_finished))

    return {
        "records": len(records),
        "malformed_records": malformed,
        "tool_timing": tool_summary,
        "turn_timing": summary(turn_durations),
        "routing": {
            "route_counts": dict(sorted(routes.items())),
            "work_surface_counts": dict(sorted(work_surfaces.items())),
            "planned_skill_counts": dict(sorted(planned_skills.items())),
        },
        "workflow_status": {
            field: dict(sorted(counts.items()))
            for field, counts in sorted(workflow_status.items())
        },
        "tool_outcomes": dict(sorted(outcomes.items())),
        "interrupted_turns": interrupted,
        "unmatched_tool_starts": len(started_tools - completed_tools),
        "unfinished_turns": incomplete_turns,
        "limitations": [
            "Only local Hook-observable tools are included; hosted tools can be absent.",
            "Routing entries are router-declared planned skills, not platform-confirmed skill usage.",
            "Codex does not emit a stable event when a skill is loaded, so this report does not claim actual skill usage.",
            "Token usage is not included because Hooks do not provide a reliable token metric.",
            "Human decision counts require an external benchmark record; Hook turn counts do not prove a decision was required.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", required=True, type=Path, help="Directory containing events-YYYY-MM-DD.jsonl files.")
    arguments = parser.parse_args()
    records, malformed = read_records(arguments.log_dir)
    print(json.dumps(analyze(records, malformed), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
