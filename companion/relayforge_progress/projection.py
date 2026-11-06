"""Deterministic projections of sanitized observation records."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .validation import ENUMS, FIELDS

MAX_SESSIONS = 100
MAX_RUNS = 100
MAX_TOOLS = 200
MAX_EVENTS = 1000
MAX_TURNS = 200
MAX_DECLARATIONS = 200
MAX_RUN_EVENTS = 1000


def business_fields(record: dict[str, Any]) -> dict[str, Any]:
    """Return declaration identity fields, excluding reception metadata."""
    return {k: v for k, v in record.items() if k not in {"timestamp", "provenance", "id"}}


def project(records: list[dict[str, Any]], limited_runs: set[str]) -> dict[str, Any]:
    """Build bounded views without guessing missing identities or semantics."""
    sessions: dict[str, dict[str, Any]] = {}
    runs: dict[str, list[dict[str, Any]]] = {}
    tool_maps: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
    turns: dict[str, dict[str, str]] = {}
    diagnostics: Counter[str] = Counter()
    evidence: Counter[str] = Counter()
    seen: dict[str, dict[str, Any]] = {}
    conflicting: set[str] = set()
    conflict_runs: set[str] = set()
    invalid_runs: set[str] = set()
    for item in records:
        kind = item["event"]
        run = item.get("task_run_id")
        if kind == "invalid_declaration":
            if run:
                invalid_runs.add(run)
            continue
        if kind in FIELDS:
            runs.setdefault(run, [])
            identity = item["event_id"]
            if identity in seen:
                if business_fields(item) == business_fields(seen[identity]):
                    diagnostics["declaration_replays"] += 1
                else:
                    conflicting.add(identity)
                    conflict_runs.update((run, seen[identity]["task_run_id"]))
                    diagnostics["declaration_conflicts"] += 1
                continue
            seen[identity] = item
            runs[run].append(item)
            continue
        session_id = item.get("session_id")
        if not session_id:
            diagnostics["missing_session_ids"] += 1
            continue
        session = sessions.setdefault(session_id, {"id": session_id, "label": session_id[-8:], "lifecycle": "unknown", "last_at": None, "turns": [], "tools": [], "declarations": []})
        tool_map = tool_maps.setdefault(session_id, {})
        turn_map = turns.setdefault(session_id, {})
        session["last_at"] = item.get("timestamp") or session["last_at"]
        if kind == "session_started":
            session["lifecycle"] = "open_observed"
        elif kind == "session_ended":
            session["lifecycle"] = "end_observed"
        turn_id = item.get("turn_id")
        if kind.startswith("turn_") and turn_id:
            turn_map[turn_id] = {"turn_started": "start_observed", "turn_stopped": "stop_observed", "turn_interrupted": "interrupt_observed"}.get(kind, "unknown")
            evidence[kind] += 1
        if kind in {"routing_decision", "workflow_status"}:
            session["declarations"].append(dict(item))
        if kind not in {"tool_started", "tool_completed"}:
            continue
        tool_id = item.get("tool_use_id")
        if not turn_id or not tool_id:
            diagnostics["unpaired_tool_events"] += 1
            continue
        key = (turn_id, tool_id)
        tool = tool_map.setdefault(key, {"id": tool_id, "name": item.get("tool_name"), "state": "incomplete", "started_at": None, "ended_at": None, "duration_ms": None, "turn_id": turn_id, "_start": False, "_end": False})
        tool["name"] = item.get("tool_name") or tool["name"]
        if kind == "tool_started":
            if tool["_start"] or tool["_end"]:
                tool["state"] = "conflicted"
            else:
                tool["state"] = "start_observed"
            tool["_start"] = True
            tool["started_at"] = item.get("timestamp")
        else:
            if tool["_end"]:
                tool["state"] = "conflicted"
            elif tool["state"] != "conflicted":
                tool["state"] = {"succeeded": "completion_succeeded", "failed": "completion_failed"}.get(item.get("outcome"), "completion_unspecified")
            tool["_end"] = True
            tool["ended_at"] = item.get("timestamp")
            # Only durations explicitly paired by the logger qualify as evidence.
            if tool["_start"] and item.get("matched_start") is True and "duration_ms" in item:
                tool["duration_ms"] = item["duration_ms"]
                evidence["paired_tools"] += 1
            elif not tool["_start"]:
                diagnostics["orphan_tool_completions"] += 1
    for session_id, session in sessions.items():
        all_tools = list(tool_maps[session_id].values())
        diagnostics["tools_truncated"] += max(0, len(all_tools) - MAX_TOOLS)
        for tool in all_tools[-MAX_TOOLS:]:
            tool.pop("_start")
            tool.pop("_end")
            if tool["state"] == "start_observed" and turns[session_id].get(tool["turn_id"]) in {"stop_observed", "interrupt_observed"}:
                tool["state"] = "incomplete"
            session["tools"].append(tool)
        all_turns = list(turns[session_id].items())
        diagnostics["turns_truncated"] += max(0, len(all_turns) - MAX_TURNS)
        session["turns"] = [{"id": key, "state": value} for key, value in all_turns[-MAX_TURNS:]]
        diagnostics["legacy_declarations_truncated"] += max(0, len(session["declarations"]) - MAX_DECLARATIONS)
        session["declarations"] = session["declarations"][-MAX_DECLARATIONS:]
    result_runs: list[dict[str, Any]] = []
    for run, items in runs.items():
        ordered = sorted(items, key=lambda e: e["sequence"])
        issues: list[str] = []
        if run in limited_runs:
            issues.append("retention_limited")
        if run in invalid_runs:
            issues.append("invalid_declaration")
        if run in conflict_runs:
            issues.append("event_id_conflict")
        counts = Counter(item["sequence"] for item in ordered)
        if [item["sequence"] for item in ordered] != list(range(1, len(ordered) + 1)):
            issues.append("missing_or_conflicting_sequence")
        current: str | None = None
        selected = 0
        ended = False
        summary: dict[str, str] = {}
        for item in ordered:
            if item["event_id"] in conflicting or counts[item["sequence"]] > 1:
                continue
            kind = item["event"]
            if ended:
                issues.append("event_after_completion")
            if kind == "route_selected":
                selected += 1
                if selected != 1 or item["sequence"] != 1:
                    issues.append("invalid_initial_selection")
                else:
                    current = item["execution_mode"]
            elif kind == "route_changed":
                if current != item["from"]:
                    issues.append("route_discontinuity")
                current = item["to"]
            elif kind == "workflow_completed":
                ended = True
            for field in ENUMS:
                if field in item:
                    summary[field] = item[field]
        if selected != 1:
            issues.append("missing_initial_selection")
        if len(ordered) > MAX_RUN_EVENTS:
            issues.append("display_events_truncated")
            diagnostics["run_events_truncated"] += len(ordered) - MAX_RUN_EVENTS
        quality = "conflicted" if run in conflict_runs or any(n > 1 for n in counts.values()) else "partial" if issues else "intact_ended" if ended else "intact_open"
        result_runs.append({"id": run, "label": run[:8], "quality": quality, "route": current if not issues else None, "ended": ended, "summary": summary, "events": ordered[-MAX_RUN_EVENTS:], "issues": list(dict.fromkeys(issues))})
    diagnostics["sessions_truncated"] = max(0, len(sessions) - MAX_SESSIONS)
    diagnostics["runs_truncated"] = max(0, len(result_runs) - MAX_RUNS)
    diagnostics["events_truncated"] = max(0, len(records) - MAX_EVENTS)
    latest = []
    for item in records[-MAX_EVENTS:]:
        latest.append({key: value for key, value in item.items() if key in {"id", "event", "timestamp", "session_id", "task_run_id", "tool_name", "outcome", "provenance"}})
    return {"sessions": list(sessions.values())[-MAX_SESSIONS:], "runs": result_runs[-MAX_RUNS:], "events": latest, "diagnostics": dict(diagnostics), "evidence": dict(evidence)}
