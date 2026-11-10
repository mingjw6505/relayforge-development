"""Bounded task snapshots; no filesystem, log or command interfaces in tool inputs."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

Snapshot = dict[str, Any]
STEP_STATUSES = {"pending", "active", "done", "blocked", "skipped"}
RUN_STATUSES = {"running", "waiting", "completed", "blocked", "cancelled"}
TERMINAL = {"completed", "blocked", "cancelled"}
MAX_RUNS = 200
MAX_HISTORY = 20
VERIFICATION_STATUSES = {
    "not_run",
    "running",
    "passed",
    "failed",
    "partial",
    "skipped",
    "unavailable",
}
EXECUTION_MODES = {"L1", "L2", "L3"}
METHODS = {"sdd", "tdd", "coordination"}


@dataclass
class ProgressError(ValueError):
    """A public, payload-free error code and optional scoped conflict snapshot."""

    code: str
    current: Snapshot | None = None

    def __str__(self) -> str:
        return self.code


def text(value: object, maximum: int, *, empty: bool = False) -> str:
    """Validate a short, plain single-line declaration without echoing its value."""
    if not isinstance(value, str):
        raise ProgressError("invalid_text")
    result = value.strip()
    if len(result) > maximum or (not result and not empty):
        raise ProgressError("invalid_text")
    if any(ord(character) < 32 or ord(character) == 127 for character in result):
        raise ProgressError("invalid_text")
    return result


def run_id(value: object) -> str:
    """Require a canonical UUID so a task reference can never become a path."""
    if not isinstance(value, str):
        raise ProgressError("invalid_run_id")
    try:
        parsed = uuid.UUID(value)
    except ValueError as error:
        raise ProgressError("invalid_run_id") from error
    if str(parsed) != value:
        raise ProgressError("invalid_run_id")
    return value


def steps(value: object, status: str) -> list[dict[str, str]]:
    """Enforce one current step and keep unfinished work visible at completion."""
    if not isinstance(value, list) or not 1 <= len(value) <= 12:
        raise ProgressError("invalid_steps")
    result = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"label", "status"}:
            raise ProgressError("invalid_steps")
        label = text(item["label"], 80)
        state = item["status"]
        if not isinstance(state, str) or state not in STEP_STATUSES:
            raise ProgressError("invalid_steps")
        result.append({"label": label, "status": state})
    if len({item["label"] for item in result}) != len(result):
        raise ProgressError("duplicate_steps")
    active = sum(item["status"] == "active" for item in result)
    blocked = sum(item["status"] == "blocked" for item in result)
    if active + blocked > 1:
        raise ProgressError("multiple_current_steps")
    if status in {"running", "waiting"} and (active != 1 or blocked):
        raise ProgressError("missing_current_step")
    if status == "completed" and any(
        item["status"] not in {"done", "skipped"} for item in result
    ):
        raise ProgressError("incomplete_steps")
    if status == "blocked" and (active or blocked != 1):
        raise ProgressError("missing_blocked_step")
    if status == "cancelled" and active:
        raise ProgressError("ended_current_step")
    return result


def timestamp() -> str:
    """Return server reception time, never an inferred execution timestamp."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def validate_execution_mode(value: object) -> str | None:
    """Mode is a routing declaration, never inferred from a loaded skill."""
    if value is None:
        return None
    if not isinstance(value, str) or value not in EXECUTION_MODES:
        raise ProgressError("invalid_execution_mode")
    return value


def method_progress(value: object) -> list[Snapshot]:
    """Validate selected methods and their independently declared phase states."""
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > 3:
        raise ProgressError("invalid_method_progress")
    result: list[Snapshot] = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"method", "status", "phases"}:
            raise ProgressError("invalid_method_progress")
        name, status = item["method"], item["status"]
        if not isinstance(name, str) or name not in METHODS:
            raise ProgressError("invalid_method_progress")
        if not isinstance(status, str) or status not in RUN_STATUSES:
            raise ProgressError("invalid_method_progress")
        phases = steps(item["phases"], status)
        if len(phases) > 8:
            raise ProgressError("invalid_method_progress")
        for phase in phases:
            text(phase["label"], 40)
        result.append({"method": name, "status": status, "phases": phases,
                       "source": "agent_declared"})
    if len({item["method"] for item in result}) != len(result):
        raise ProgressError("duplicate_methods")
    return result


def validate_method_end(progress: list[Snapshot], status: str) -> None:
    """Ending a task never fabricates completion of its selected methods."""
    if status in TERMINAL and any(
        item["status"] not in TERMINAL
        or (status == "completed" and item["status"] == "blocked")
        for item in progress
    ):
        raise ProgressError("unfinished_methods")


def details(value: object) -> Snapshot:
    """Accept bounded declarations, never client-supplied load receipts or provenance."""
    if not isinstance(value, dict) or set(value) - {
        "current",
        "change",
        "remaining",
        "waiting_for",
        "reason",
        "verification",
    }:
        raise ProgressError("invalid_details")
    result: Snapshot = {
        key: text(item, 120, empty=True)
        for key, item in value.items()
        if key != "verification"
    }
    if "waiting_for" in result and result["waiting_for"] not in {"user", "external"}:
        raise ProgressError("invalid_waiting_for")
    if "verification" not in value:
        return result
    verification = value["verification"]
    if not isinstance(verification, dict) or set(verification) - {
        "status",
        "passed",
        "failed",
        "pending",
        "evidence",
    }:
        raise ProgressError("invalid_verification")
    status = verification.get("status")
    if not isinstance(status, str) or status not in VERIFICATION_STATUSES:
        raise ProgressError("invalid_verification")
    counts = {
        key: verification[key]
        for key in ("passed", "failed", "pending")
        if key in verification
    }
    if any(
        type(count) is not int or not 0 <= count <= 1000000 for count in counts.values()
    ):
        raise ProgressError("invalid_verification")
    evidence = text(verification.get("evidence", ""), 120, empty=True)
    if counts and not evidence:
        raise ProgressError("verification_evidence_required")
    if status == "passed" and (
        counts.get("failed", 0) or counts.get("pending", 0) or counts.get("passed") == 0
    ):
        raise ProgressError("invalid_verification")
    if status in {"not_run", "skipped", "unavailable"} and counts:
        raise ProgressError("invalid_verification")
    if status == "failed" and counts.get("failed") == 0:
        raise ProgressError("invalid_verification")
    result["verification"] = {
        "status": status,
        **counts,
        "evidence": evidence,
        "source": "agent_declared",
    }
    return result


def stage_details(value: Snapshot, status: str) -> Snapshot:
    """Keep declarations valid for this state without inferring check results."""
    result = dict(value)
    if status != "waiting":
        result.pop("waiting_for", None)
    if status not in {"waiting", "blocked"}:
        result.pop("reason", None)
    if status in {"completed", "cancelled"}:
        result.pop("current", None)
        result.pop("remaining", None)
    return result


def stage_event(
    revision: int, at: str, status: str, summary: str,
    execution: Snapshot, declared_steps: list[dict[str, str]],
    mode: str | None, methods: list[Snapshot],
) -> Snapshot:
    """Store the bounded declarations needed to read a past milestone."""
    event: Snapshot = {
        "revision": revision, "at": at, "status": status,
        "summary": summary, "details": execution,
        "execution_mode": mode, "method_progress": methods,
    }
    current = next(
        (step["label"] for step in declared_steps if step["status"] in {"active", "blocked"}),
        None,
    )
    if current:
        event["current_step"] = current
    return event


@dataclass(frozen=True)
class ProgressStore:
    """Persist independent tasks with atomic optimistic updates and bounded history."""

    directory: Path

    def __post_init__(self) -> None:
        if self.directory.is_symlink():
            raise ProgressError("unsafe_data_directory")
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name == "posix" and self.directory.stat().st_mode & 0o077:
            raise ProgressError("unsafe_data_directory")
        database = self.directory / "progress.sqlite3"
        if database.is_symlink():
            raise ProgressError("unsafe_data_directory")
        database.touch(mode=0o600, exist_ok=True)
        if os.name == "posix" and database.stat().st_mode & 0o077:
            raise ProgressError("unsafe_data_directory")
        with self.connection() as connection:
            connection.execute("PRAGMA max_page_count = 8192")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, "
                "updated TEXT NOT NULL, payload TEXT NOT NULL)"
            )

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Close each short connection; do not retain locks between MCP requests."""
        connection = sqlite3.connect(self.directory / "progress.sqlite3", timeout=2)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _read(connection: sqlite3.Connection, identifier: str) -> Snapshot:
        row = connection.execute(
            "SELECT payload FROM runs WHERE id = ?", (identifier,)
        ).fetchone()
        if row is None:
            raise ProgressError("unknown_run")
        return cast(Snapshot, json.loads(row[0]))

    @staticmethod
    def _prune(connection: sqlite3.Connection, keep_id: str) -> None:
        cutoff = (
            (datetime.now(UTC) - timedelta(days=7)).isoformat().replace("+00:00", "Z")
        )
        connection.execute(
            "DELETE FROM runs WHERE updated < ? AND id != ?", (cutoff, keep_id)
        )
        connection.execute(
            "DELETE FROM runs WHERE id IN "
            "(SELECT id FROM runs WHERE id != ? ORDER BY updated DESC, id DESC LIMIT -1 OFFSET ?)",
            (keep_id, MAX_RUNS - 1),
        )

    def start(
        self,
        title: object,
        declared_steps: object,
        summary: object = "",
        execution: object = None,
        *, execution_mode: object = None, declared_methods: object = None,
    ) -> Snapshot:
        """Start a new task; the returned random run ID scopes all later operations."""
        title = text(title, 80)
        summary = text(summary, 240, empty=True)
        declared_steps = steps(declared_steps, "running")
        execution = stage_details(details(execution) if execution is not None else {}, "running")
        mode = validate_execution_mode(execution_mode)
        methods = method_progress(declared_methods)
        now = timestamp()
        identifier = str(uuid.uuid4())
        snapshot: Snapshot = {
            "schema_version": 1,
            "source": "agent_declared",
            "run_id": identifier,
            "revision": 1,
            "title": title,
            "status": "running",
            "steps": declared_steps,
            "summary": summary,
            "details": execution,
            "workflow": None,
            "execution_mode": mode,
            "method_progress": methods,
            "skill_loads": [],
            "created_at": now,
            "updated_at": now,
            "history": [
                stage_event(1, now, "running", summary, execution, declared_steps, mode, methods)
            ],
        }
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO runs VALUES (?, ?, ?)",
                (identifier, now, json.dumps(snapshot, ensure_ascii=False)),
            )
            self._prune(connection, identifier)
        return snapshot

    def read(self, identifier: object) -> Snapshot:
        """Read exactly one task; never select a latest task or scan other sources."""
        identifier = run_id(identifier)
        with self.connection() as connection:
            return self._read(connection, identifier)

    def update(
        self,
        identifier: object,
        expected_revision: object,
        status: object,
        declared_steps: object,
        summary: object = "",
        execution: object = None,
        *, execution_mode: object = None, declared_methods: object = None,
    ) -> Snapshot:
        """Apply a declaration atomically; identical lost-response retries are safe."""
        identifier = run_id(identifier)
        if type(expected_revision) is not int or expected_revision < 1:
            raise ProgressError("invalid_revision")
        if not isinstance(status, str) or status not in RUN_STATUSES:
            raise ProgressError("invalid_status")
        declared_steps = steps(declared_steps, status)
        summary = text(summary, 240, empty=True)
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = self._read(connection, identifier)
            execution = stage_details(
                details(execution)
                if execution is not None
                else current.get("details", {}),
                status,
            )
            mode = (validate_execution_mode(execution_mode) if execution_mode is not None
                    else current.get("execution_mode"))
            methods = (method_progress(declared_methods) if declared_methods is not None
                       else current.get("method_progress", []))
            if current["revision"] != expected_revision:
                identical_retry = (
                    current["revision"] == expected_revision + 1
                    and current["status"] == status
                    and current["steps"] == declared_steps
                    and current["summary"] == summary
                    and current.get("details", {}) == execution
                    and current.get("execution_mode") == mode
                    and current.get("method_progress", []) == methods
                )
                if identical_retry:
                    return current
                raise ProgressError("revision_conflict", current)
            if current["status"] in TERMINAL:
                raise ProgressError("run_ended")
            previous_mode = current.get("execution_mode")
            if previous_mode and mode and abs(int(mode[-1]) - int(previous_mode[-1])) > 1:
                raise ProgressError("invalid_mode_transition")
            validate_method_end(methods, status)
            now = timestamp()
            revision = expected_revision + 1
            history = current["history"] + [
                stage_event(revision, now, status, summary, execution, declared_steps, mode, methods)
            ]
            updated = dict(
                current,
                revision=revision,
                status=status,
                steps=declared_steps,
                summary=summary,
                details=execution,
                execution_mode=mode,
                method_progress=methods,
                updated_at=now,
                history=history[-MAX_HISTORY:],
            )
            connection.execute(
                "UPDATE runs SET updated = ?, payload = ? WHERE id = ?",
                (now, json.dumps(updated, ensure_ascii=False), identifier),
            )
            self._prune(connection, identifier)
            return updated

    def record_skill_load(
        self,
        identifier: object,
        expected_revision: object,
        name: str,
        digest: str,
        is_workflow: bool,
    ) -> Snapshot:
        """Record a completed bundled file read, not a planned or inferred invocation."""
        identifier = run_id(identifier)
        if type(expected_revision) is not int or expected_revision < 1:
            raise ProgressError("invalid_revision")
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = self._read(connection, identifier)
            if current["status"] in TERMINAL:
                raise ProgressError("run_ended")
            loads = current.get("skill_loads", [])
            existing = next((item for item in loads if item["name"] == name), None)
            unchanged = (
                existing is not None
                and existing["sha256"] == digest
                and (not is_workflow or current.get("workflow") == name)
            )
            if unchanged and expected_revision <= current["revision"]:
                return current
            if current["revision"] != expected_revision:
                raise ProgressError("revision_conflict", current)
            if existing is None and len(loads) >= 32:
                raise ProgressError("skill_load_limit")
            now = timestamp()
            receipt = {
                "name": name,
                "sha256": digest,
                "loaded_at": now,
                "kind": "workflow" if is_workflow else "skill",
                "source": "mcp_skill_load",
            }
            revision = current["revision"] + 1
            event = {
                "revision": revision,
                "at": now,
                "status": current["status"],
                "kind": "skill_loaded",
                "skill": name,
                "source": "mcp_skill_load",
                "summary": "",
                "execution_mode": current.get("execution_mode"),
                "method_progress": current.get("method_progress", []),
            }
            updated = dict(
                current,
                revision=revision,
                updated_at=now,
                skill_loads=[item for item in loads if item["name"] != name]
                + [receipt],
                workflow=name if is_workflow else current.get("workflow"),
                history=(current["history"] + [event])[-MAX_HISTORY:],
            )
            connection.execute(
                "UPDATE runs SET updated = ?, payload = ? WHERE id = ?",
                (now, json.dumps(updated, ensure_ascii=False), identifier),
            )
            self._prune(connection, identifier)
            return updated
