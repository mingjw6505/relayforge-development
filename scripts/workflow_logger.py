#!/usr/bin/env python3
"""Write metadata-only Codex hook events as daily JSONL files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


RETENTION_DAYS = 30
SCHEMA_VERSION = 1
LOCK_TIMEOUT_SECONDS = 2.0
STALE_LOCK_SECONDS = 15.0
LOG_PREFIX = "events-"
STATE_FILE = "workflow-log-state.json"
ROUTE_LINE_PATTERN = re.compile(
    r"^Workflow route: (Quick|Standard|Large) \| Work surfaces: "
    r"([a-z0-9-]+(?:, [a-z0-9-]+)*|none) \| Planned skills: "
    r"([a-z0-9-]+(?:, [a-z0-9-]+)*|none)[ \\t]*$",
    re.MULTILINE,
)
STATUS_LINE_PATTERN = re.compile(
    r"^Workflow status: Implementation=(complete|blocked) \| "
    r"Minimal checks=(passed|failed|partial|unavailable) \| "
    r"Test verification=(passed|failed|partial|skipped|unavailable) \| "
    r"Code review=(passed|findings-open|skipped|unavailable) \| "
    r"Commit=(completed|skipped|blocked|unavailable) \| "
    r"Push=(completed|skipped|blocked|unavailable)[ \\t]*$",
    re.MULTILINE,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_timestamp(value: Optional[datetime] = None) -> str:
    timestamp = value or utc_now()
    return timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def opaque_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:20]
    return "sha256:" + digest


def data_directory(value: Optional[str] = None) -> Path:
    configured = (
        value
        or os.environ.get("RELAYFORGE_WORKFLOW_LOG_DIR")
        or os.environ.get("PLUGIN_DATA")
        or os.environ.get("CLAUDE_PLUGIN_DATA")
    )
    if not configured:
        raise ValueError("a plugin data directory or --data-dir is required")
    return Path(configured).expanduser().resolve()


@contextmanager
def directory_lock(root: Path) -> Iterator[None]:
    """Serialize short state and JSONL writes across concurrent hook processes."""
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / ".workflow-log.lock"
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    descriptor: Optional[int] = None

    while descriptor is None:
        try:
            descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
                if age > STALE_LOCK_SECONDS:
                    lock_path.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError("workflow log lock timed out")
            time.sleep(0.02)

    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        yield
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def state_path(root: Path) -> Path:
    return root / STATE_FILE


def read_state(root: Path) -> Dict[str, Any]:
    path = state_path(root)
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {"pending_tools": {}}
    if not isinstance(content, dict) or not isinstance(content.get("pending_tools"), dict):
        return {"pending_tools": {}}
    return content


def write_state(root: Path, state: Dict[str, Any]) -> None:
    destination = state_path(root)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=str(root), prefix=".workflow-log-", delete=False
    ) as handle:
        json.dump(state, handle, separators=(",", ":"), sort_keys=True)
        temporary = Path(handle.name)
    temporary.replace(destination)


def clean_old_data(root: Path, today: datetime) -> None:
    cutoff = today.date() - timedelta(days=RETENTION_DAYS - 1)
    for candidate in root.glob(LOG_PREFIX + "*.jsonl"):
        date_part = candidate.stem[len(LOG_PREFIX):]
        try:
            log_date = datetime.strptime(date_part, "%Y-%m-%d").date()
        except ValueError:
            continue
        if log_date < cutoff:
            candidate.unlink(missing_ok=True)


def discard_stale_pending(state: Dict[str, Any], current_monotonic: int) -> bool:
    """Bound recovery state when a process ends before PostToolUse arrives."""
    pending = state["pending_tools"]
    cutoff = current_monotonic - 86_400 * 1_000_000_000
    stale = [
        key
        for key, value in pending.items()
        if not isinstance(value, dict)
        or not isinstance(value.get("started_monotonic_ns"), int)
        or value["started_monotonic_ns"] < cutoff
    ]
    for key in stale:
        pending.pop(key, None)
    return bool(stale)


def append_record(root: Path, record: Dict[str, Any], now: datetime) -> None:
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    clean_old_data(logs, now)
    path = logs / (LOG_PREFIX + now.strftime("%Y-%m-%d") + ".jsonl")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n")


def base_record(event: Dict[str, Any], name: str, now: datetime) -> Dict[str, Any]:
    record: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": iso_timestamp(now),
        "event": name,
    }
    for field in ("session_id", "turn_id", "tool_use_id", "agent_id"):
        opaque = opaque_id(event.get(field))
        if opaque:
            record[field] = opaque
    for field in ("model", "permission_mode", "tool_name", "agent_type"):
        value = event.get(field)
        if isinstance(value, str) and value:
            record[field] = value
    return record


def tool_key(event: Dict[str, Any]) -> Optional[str]:
    session = opaque_id(event.get("session_id"))
    turn = opaque_id(event.get("turn_id"))
    tool = opaque_id(event.get("tool_use_id"))
    if not (session and turn and tool):
        return None
    return "|".join((session, turn, tool))


def tool_outcome(event: Dict[str, Any]) -> str:
    response = event.get("tool_response")
    if isinstance(response, dict):
        exit_code = response.get("exit_code")
        if isinstance(exit_code, int):
            return "succeeded" if exit_code == 0 else "failed"
    return "completed"


def route_record(event: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    """Extract explicitly declared routing metadata without persisting the reply."""
    message = event.get("last_assistant_message")
    if not isinstance(message, str):
        return None
    match = ROUTE_LINE_PATTERN.search(message)
    if not match:
        return None
    record = base_record(event, "routing_decision", now)
    record["route"] = match.group(1).lower()
    surfaces = match.group(2)
    record["work_surfaces"] = [] if surfaces == "none" else surfaces.split(", ")
    selected = match.group(3)
    record["planned_skills"] = [] if selected == "none" else selected.split(", ")
    return record


def status_record(event: Dict[str, Any], now: datetime) -> Optional[Dict[str, Any]]:
    """Extract the declared finishing state without persisting the reply."""
    message = event.get("last_assistant_message")
    if not isinstance(message, str):
        return None
    match = STATUS_LINE_PATTERN.search(message)
    if not match:
        return None
    record = base_record(event, "workflow_status", now)
    keys = (
        "implementation",
        "minimal_checks",
        "test_verification",
        "code_review",
        "commit",
        "push",
    )
    record.update(zip(keys, match.groups()))
    return record


def handle_event(event: Dict[str, Any], root: Path, now: Optional[datetime] = None, monotonic_ns: Optional[int] = None) -> bool:
    """Persist one supported hook event without retaining its prompt or payload."""
    event_name = event.get("hook_event_name")
    if not isinstance(event_name, str):
        return False

    current_time = now or utc_now()
    current_monotonic = monotonic_ns if monotonic_ns is not None else time.monotonic_ns()

    with directory_lock(root):
        if event_name == "SessionStart":
            append_record(root, base_record(event, "session_started", current_time), current_time)
            return False

        if event_name == "SessionEnd":
            append_record(root, base_record(event, "session_ended", current_time), current_time)
            return False

        if event_name == "UserPromptSubmit":
            append_record(root, base_record(event, "turn_started", current_time), current_time)
            return False

        if event_name == "PreToolUse":
            record = base_record(event, "tool_started", current_time)
            state = read_state(root)
            state_changed = discard_stale_pending(state, current_monotonic)
            key = tool_key(event)
            if key:
                state["pending_tools"][key] = {
                    "started_at": record["timestamp"],
                    "started_monotonic_ns": current_monotonic,
                    "tool_name": record.get("tool_name"),
                }
                state_changed = True
            if state_changed:
                write_state(root, state)
            append_record(root, record, current_time)
            return False

        if event_name == "PostToolUse":
            record = base_record(event, "tool_completed", current_time)
            record["outcome"] = tool_outcome(event)
            state = read_state(root)
            state_changed = discard_stale_pending(state, current_monotonic)
            key = tool_key(event)
            start = state["pending_tools"].pop(key, None) if key else None
            if start:
                record["duration_ms"] = max(0, round((current_monotonic - start["started_monotonic_ns"]) / 1_000_000))
                record["matched_start"] = True
                if not record.get("tool_name") and start.get("tool_name"):
                    record["tool_name"] = start["tool_name"]
                state_changed = True
            else:
                record["matched_start"] = False
            if state_changed:
                write_state(root, state)
            append_record(root, record, current_time)
            return False

        simple_events = {
            "SubagentStart": "subagent_started",
            "SubagentStop": "subagent_stopped",
            "Stop": "turn_stopped",
            "Interrupt": "turn_interrupted",
        }
        output_name = simple_events.get(event_name)
        if output_name:
            append_record(root, base_record(event, output_name, current_time), current_time)
            if event_name == "Stop":
                planned_route = route_record(event, current_time)
                if planned_route:
                    append_record(root, planned_route, current_time)
                finishing_status = status_record(event, current_time)
                if finishing_status:
                    append_record(root, finishing_status, current_time)
            return event_name in {"Stop", "SubagentStop"}

    return event_name in {"Stop", "SubagentStop"}


def read_input() -> Dict[str, Any]:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", help="Override PLUGIN_DATA for local testing.")
    arguments = parser.parse_args()

    try:
        needs_json_acknowledgement = handle_event(read_input(), data_directory(arguments.data_dir))
    except (OSError, TimeoutError, ValueError):
        # Telemetry must not block the task that caused the hook to run.
        return 0
    if needs_json_acknowledgement:
        # Stop and SubagentStop require JSON output from successful command hooks.
        print('{"continue":true}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
