"""Bounded metadata validation, independent of the production plugin runtime."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

HASH = re.compile(r"sha256:[0-9a-f]{20}\Z")
SKILL = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
COMMON = {"event", "workflow_event_schema_version", "event_id", "task_run_id", "sequence", "route_policy_version"}
FIELDS = {
    "route_selected": {"execution_mode", "route", "risk", "reason_code", "planned_skills"},
    "route_changed": {"from", "to", "reason_code"},
    "verification_summary": {"implementation", "minimal_checks", "test_verification", "code_review", "commit", "push"},
    "handoff_generated": {"form", "development_status", "code_availability"},
    "workflow_completed": {"implementation", "development_status"},
}
ENUMS = {
    "implementation": {"complete", "blocked"},
    "minimal_checks": {"passed", "failed", "partial", "unavailable"},
    "test_verification": {"passed", "failed", "partial", "skipped", "unavailable"},
    "code_review": {"passed", "findings-open", "skipped", "unavailable"},
    "commit": {"completed", "skipped", "blocked", "unavailable"},
    "push": {"completed", "skipped", "blocked", "unavailable"},
    "form": {"file", "inline"},
    "development_status": {"ready_for_testing", "ready_with_issues", "blocked"},
    "code_availability": {"available", "local_only", "unavailable", "unknown"},
}
TRANSITIONS = {
    ("L1", "L2"): {"design_required", "contract_changed"},
    ("L2", "L3"): {"coordination_required"},
    ("L3", "L2"): {"coordination_unnecessary"},
    ("L2", "L1"): {"scope_simplified"},
}
HOST_EVENTS = {"session_started", "session_ended", "turn_started", "turn_stopped", "turn_interrupted", "tool_started", "tool_completed", "subagent_started", "subagent_stopped", "routing_decision", "workflow_status"}


class InvalidRecord(ValueError):
    """A sanitized validation failure with no source contents."""


def timestamp(value: Any) -> str | None:
    """Return a canonical aware UTC timestamp, rejecting naive values."""
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    except (ValueError, OverflowError):
        return None


def valid_uuid(value: Any) -> bool:
    """Check canonical lowercase UUID format."""
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def decode(raw: bytes) -> dict[str, Any]:
    """Decode an object while rejecting duplicate JSON keys and constants."""
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise InvalidRecord("duplicate_key")
            result[key] = value
        return result

    def constant(_: str) -> None:
        raise InvalidRecord("invalid_constant")

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise InvalidRecord("invalid_json") from None
    if not isinstance(value, dict):
        raise InvalidRecord("invalid_object")
    return value


def declaration(record: dict[str, Any]) -> dict[str, Any]:
    """Validate strict v1 declarations with the documented read alias."""
    payload = {key: value for key, value in record.items() if key not in {"timestamp", "schema_version", "source"}}
    kind = payload.get("event")
    if not isinstance(kind, str) or kind not in FIELDS:
        raise InvalidRecord("invalid_declaration")
    if set(payload) != COMMON | FIELDS[kind] or record.get("source") != "agent_declared":
        raise InvalidRecord("invalid_declaration")
    if payload.get("risk") == "normal":
        payload["risk"] = "medium"
    if type(payload.get("workflow_event_schema_version")) is not int or payload["workflow_event_schema_version"] != 1:
        raise InvalidRecord("invalid_declaration")
    if payload.get("route_policy_version") != "v2.1" or type(payload.get("sequence")) is not int or payload["sequence"] < 1:
        raise InvalidRecord("invalid_declaration")
    if not all(valid_uuid(payload.get(key)) for key in ("event_id", "task_run_id")):
        raise InvalidRecord("invalid_declaration")
    for key, values in ENUMS.items():
        if key in payload and (not isinstance(payload[key], str) or payload[key] not in values):
            raise InvalidRecord("invalid_declaration")
    if kind == "route_selected":
        mode = payload["execution_mode"]
        routes = {"L1": "quick", "L2": "standard", "L3": "large"}
        reasons = {"L1": "local_scope", "L2": "bounded_sdd", "L3": "coordination_required"}
        if not isinstance(mode, str) or mode not in routes or payload["route"] != routes[mode] or payload["reason_code"] != reasons[mode]:
            raise InvalidRecord("invalid_declaration")
        if not isinstance(payload["risk"], str) or payload["risk"] not in {"low", "medium", "high"}:
            raise InvalidRecord("invalid_declaration")
        skills = payload["planned_skills"]
        if not isinstance(skills, list) or len(skills) > 64 or any(not isinstance(s, str) or not SKILL.fullmatch(s) for s in skills):
            raise InvalidRecord("invalid_declaration")
    if kind == "route_changed":
        before, after, reason = payload["from"], payload["to"], payload["reason_code"]
        if not all(isinstance(v, str) for v in (before, after, reason)) or reason not in TRANSITIONS.get((before, after), set()):
            raise InvalidRecord("invalid_declaration")
    if kind == "handoff_generated" and payload["development_status"] != "blocked" and payload["code_availability"] != "available":
        raise InvalidRecord("invalid_declaration")
    if kind == "workflow_completed" and payload["implementation"] == "blocked" and payload["development_status"] != "blocked":
        raise InvalidRecord("invalid_declaration")
    if len(json.dumps(payload, ensure_ascii=False).encode()) > 16 * 1024:
        raise InvalidRecord("invalid_declaration")
    return {**payload, "timestamp": timestamp(record.get("timestamp")), "provenance": "agent_declared"}


def sanitize(record: dict[str, Any]) -> dict[str, Any]:
    """Whitelist metadata, never retaining arbitrary input or raw payloads."""
    if type(record.get("schema_version")) is not int or record["schema_version"] != 1:
        raise InvalidRecord("unsupported_schema")
    kind = record.get("event")
    if (isinstance(kind, str) and kind in FIELDS) or "workflow_event_schema_version" in record:
        return declaration(record)
    if not isinstance(kind, str) or kind not in HOST_EVENTS:
        raise InvalidRecord("unknown_event")
    result: dict[str, Any] = {"event": kind, "timestamp": timestamp(record.get("timestamp")), "provenance": "agent_declared" if kind in {"routing_decision", "workflow_status"} else "host_observed"}
    for key in ("session_id", "turn_id", "tool_use_id", "agent_id"):
        value = record.get(key)
        if isinstance(value, str) and HASH.fullmatch(value):
            result[key] = value
    name = record.get("tool_name")
    if isinstance(name, str) and 0 < len(name) <= 128 and not any(ord(c) < 32 for c in name) and not any(c in name for c in "/\\"):
        result["tool_name"] = name
    if kind == "tool_completed":
        outcome = record.get("outcome")
        result["outcome"] = outcome if isinstance(outcome, str) and outcome in {"succeeded", "failed", "completed"} else "completed"
        duration = record.get("duration_ms")
        if type(duration) is int and 0 <= duration <= 365 * 86400 * 1000:
            result["duration_ms"] = duration
        if type(record.get("matched_start")) is bool:
            result["matched_start"] = record["matched_start"]
    if kind == "routing_decision":
        if record.get("route") in ("quick", "standard", "large"):
            result["route"] = record["route"]
        for key in ("planned_skills", "work_surfaces"):
            value = record.get(key)
            if isinstance(value, list):
                result[key] = [s for s in value[:64] if isinstance(s, str) and SKILL.fullmatch(s)]
    if kind == "workflow_status":
        for key, allowed in ENUMS.items():
            value = record.get(key)
            if isinstance(value, str) and value in allowed:
                result[key] = value
    return result
