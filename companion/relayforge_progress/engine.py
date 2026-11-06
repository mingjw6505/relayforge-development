"""Offline-first JSONL ingestion with isolated SQLite state and bounded reads."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sqlite3
import stat
import threading
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, BinaryIO

from .projection import project
from .validation import InvalidRecord, decode, sanitize, valid_uuid

MAX_BYTES = 100 * 1024 * 1024
MAX_LINES = 100_000
MAX_LINE_BYTES = 64 * 1024
MAX_CACHE_EVENTS = 100_000
MAX_CACHE_BYTES = 100 * 1024 * 1024
RETENTION_DAYS = 7
FILE_PATTERN = re.compile(r"events-(\d{4}-\d{2}-\d{2})\.jsonl\Z")


def now_iso() -> str:
    """Return the current UTC time in the metadata timestamp format."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def has_symlink(path: Path) -> bool:
    """Reject symlinks in every existing path component."""
    absolute = path.absolute()
    return any(part.is_symlink() for part in (absolute, *absolute.parents))


class Engine:
    """Observe sanitized metadata without modifying or locking its source.

    Args:
        log_dir: Explicit directory containing existing daily JSONL files.
        state_dir: Independent writable directory for this engine's SQLite state.

    Raises:
        ValueError: If configuration is unsafe; messages never contain paths.
        RuntimeError: If the isolated state cannot be opened.
    """

    def __init__(self, log_dir: Path, state_dir: Path) -> None:
        self._lock = threading.RLock()
        self._closed = False
        self._log_dir = Path(log_dir).absolute()
        state = Path(state_dir).absolute()
        try:
            source_resolved = self._log_dir.resolve()
            state_resolved = state.resolve()
        except (OSError, RuntimeError):
            raise ValueError("invalid_directory_configuration") from None
        if state_resolved == source_resolved or source_resolved in state_resolved.parents:
            raise ValueError("state_directory_overlaps_source")
        if has_symlink(state):
            raise ValueError("state_directory_symlink")
        self._source_symlink = has_symlink(self._log_dir)
        try:
            state.mkdir(parents=True, exist_ok=True, mode=0o700)
            if os.name == "posix" and stat.S_IMODE(state.stat().st_mode) & 0o077:
                raise ValueError("state_directory_permissions")
            db_path = state / "progress.sqlite3"
            if db_path.is_symlink():
                raise ValueError("state_database_symlink")
            self._db = sqlite3.connect(db_path, check_same_thread=False)
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA busy_timeout=3000")
            self._db.executescript("""
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS cursors (
                    name TEXT PRIMARY KEY, generation TEXT NOT NULL, offset INTEGER NOT NULL,
                    prefix TEXT NOT NULL, skipping INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, record TEXT NOT NULL,
                    retained_at TEXT NOT NULL, run_id TEXT
                );
                CREATE TABLE IF NOT EXISTS limited_runs (id TEXT PRIMARY KEY);
            """)
            self._db.commit()
            source_identity = hashlib.sha256(os.fsencode(source_resolved)).hexdigest()
            existing_identity = self._get("source_identity", None)
            if existing_identity is not None and existing_identity != source_identity:
                self._db.close()
                raise ValueError("state_source_mismatch")
            with self._db:
                self._set("source_identity", source_identity)
        except ValueError:
            raise
        except (OSError, sqlite3.Error):
            raise RuntimeError("state_unavailable") from None
        self._snapshot: dict[str, Any] = {}
        self._rebuild()

    def _get(self, key: str, default: Any) -> Any:
        row = self._db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def _set(self, key: str, value: Any) -> None:
        self._db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, json.dumps(value, separators=(",", ":"))))

    def _rebuild(self) -> None:
        records = []
        for identity, data in self._db.execute("SELECT id,record FROM events ORDER BY id"):
            records.append({**json.loads(data), "id": identity})
        limited = {row[0] for row in self._db.execute("SELECT id FROM limited_runs")}
        views = project(records, limited)
        diagnostics = Counter(self._get("diagnostics", {}))
        diagnostics.update(views.pop("diagnostics"))
        evidence = views.pop("evidence")
        source = self._get("source", {"status": "missing", "last_read_at": None, "last_event_at": None})
        coverage = self._get("coverage", {})
        coverage.update({"retained_events": len(records), "from": next((r["timestamp"] for r in records if r.get("timestamp")), None), "to": next((r["timestamp"] for r in reversed(records) if r.get("timestamp")), None)})
        self._snapshot = {"revision": self._get("revision", 0), "mode": "offline_prototype", "source": {"id": "local", **source, "collection_verified": False, "diagnostics": dict(diagnostics), "coverage": coverage}, **views, "capabilities": {"native_plan": False, "mcp_ui": False, "business_stages": False, "evidence": evidence}}

    def _selected_files(self, diagnostics: Counter[str]) -> tuple[list[Path], bool]:
        today = datetime.now(timezone.utc).date()
        selected: list[Path] = []
        limited = False
        with os.scandir(self._log_dir) as entries:
            for entry in entries:
                match = FILE_PATTERN.fullmatch(entry.name)
                if not match:
                    continue
                if entry.is_symlink():
                    diagnostics["symlinks_rejected"] += 1
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                try:
                    day = datetime.strptime(match.group(1), "%Y-%m-%d").date()
                except ValueError:
                    diagnostics["invalid_filenames"] += 1
                    continue
                if not today - timedelta(days=RETENTION_DAYS - 1) <= day <= today:
                    diagnostics["files_outside_window"] += 1
                    limited = True
                    continue
                selected.append(Path(entry.path))
        return sorted(selected), limited

    def _open(self, path: Path) -> BinaryIO:
        if self._source_symlink or has_symlink(self._log_dir) or path.is_symlink():
            raise ValueError("source_symlink")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise ValueError("source_not_regular")
        return os.fdopen(descriptor, "rb")

    def refresh(self) -> bool:
        """Ingest one bounded batch atomically, returning observable changes.

        Refresh is intentionally synchronous; callers may run it in their own
        worker. Source and state failures are reduced to sanitized diagnostics.
        """
        with self._lock:
            if self._closed:
                raise RuntimeError("engine_closed")
            before = copy.deepcopy(self._snapshot)
            diagnostics = Counter(self._get("diagnostics", {}))
            source = self._get("source", {"status": "missing", "last_read_at": None, "last_event_at": None})
            coverage = self._get("coverage", {"selection_days": RETENTION_DAYS, "selection_limited": False, "byte_limit": MAX_BYTES, "line_limit": MAX_LINES})
            current = now_iso()
            try:
                with self._db:
                    if self._source_symlink or has_symlink(self._log_dir):
                        source["status"] = "degraded"
                        diagnostics["source_symlink"] += 1
                    elif not self._log_dir.exists():
                        source["status"] = "missing"
                    elif not self._log_dir.is_dir():
                        source["status"] = "degraded"
                        diagnostics["source_not_directory"] += 1
                    else:
                        files, selection_limited = self._selected_files(diagnostics)
                        coverage["selection_limited"] = selection_limited
                        source["status"] = "readable"
                        source["last_read_at"] = current
                        bytes_left, lines_left = MAX_BYTES, MAX_LINES
                        # Preserve cross-day chronology; bounded batches resume
                        # from persistent cursors rather than reversing history.
                        for path in files:
                            if bytes_left <= 0 or lines_left <= 0:
                                diagnostics["read_budget_exhausted"] += 1
                                coverage["selection_limited"] = True
                                break
                            try:
                                used_bytes, used_lines, last = self._ingest_file(path, bytes_left, lines_left, current, diagnostics)
                                bytes_left -= used_bytes
                                lines_left -= used_lines
                                if last:
                                    source["last_event_at"] = max(last, source.get("last_event_at") or last)
                            except PermissionError:
                                source["status"] = "denied"
                                diagnostics["read_denied"] += 1
                            except (OSError, ValueError):
                                source["status"] = "degraded"
                                diagnostics["read_errors"] += 1
                        if any(diagnostics[k] for k in ("invalid_lines", "invalid_records", "oversized_lines", "symlinks_rejected")) and source["status"] == "readable":
                            source["status"] = "degraded"
                    self._prune(current, diagnostics)
                    self._set("diagnostics", dict(diagnostics))
                    self._set("source", source)
                    self._set("coverage", coverage)
                    self._rebuild()
                    if self._content(self._snapshot) != self._content(before):
                        self._set("revision", self._get("revision", 0) + 1)
            except PermissionError:
                self._failure("denied", "read_denied")
            except (OSError, sqlite3.Error):
                self._failure("degraded", "state_or_read_error")
            self._rebuild()
            # Read timestamp changes are meaningful freshness observations.
            return self._snapshot != before

    @staticmethod
    def _content(snapshot: dict[str, Any]) -> dict[str, Any]:
        """Exclude read freshness and revision from semantic comparisons."""
        result = dict(snapshot)
        result.pop("revision", None)
        result["source"] = dict(snapshot.get("source", {}))
        result["source"].pop("last_read_at", None)
        return result

    def _failure(self, status: str, code: str) -> None:
        source = self._get("source", {"last_read_at": None, "last_event_at": None})
        source["status"] = status
        diagnostics = Counter(self._get("diagnostics", {}))
        diagnostics[code] += 1
        try:
            with self._db:
                self._set("source", source)
                self._set("diagnostics", dict(diagnostics))
                self._set("revision", self._get("revision", 0) + 1)
        except sqlite3.Error:
            raise RuntimeError("state_unavailable") from None

    def _ingest_file(self, path: Path, byte_limit: int, line_limit: int, current: str, diagnostics: Counter[str]) -> tuple[int, int, str | None]:
        consumed = 0
        lines = 0
        last: str | None = None
        with self._open(path) as stream:
            info = os.fstat(stream.fileno())
            generation = f"{info.st_dev}:{info.st_ino}"
            row = self._db.execute("SELECT generation,offset,prefix,skipping FROM cursors WHERE name=?", (path.name,)).fetchone()
            offset, skipping = 0, False
            if row:
                old_generation, old_offset, old_prefix, old_skipping = row
                if old_generation != generation:
                    diagnostics["rotations"] += 1
                elif info.st_size < old_offset:
                    diagnostics["truncations"] += 1
                else:
                    stream.seek(0)
                    prefix = hashlib.sha256(stream.read(min(old_offset, 4096))).hexdigest()
                    if prefix == old_prefix:
                        offset, skipping = old_offset, bool(old_skipping)
                    else:
                        diagnostics["replacements"] += 1
            stream.seek(offset)
            while consumed < byte_limit and lines < line_limit:
                start = stream.tell()
                raw = stream.readline(min(MAX_LINE_BYTES + 2, byte_limit - consumed))
                consumed += len(raw)
                if not raw:
                    break
                if skipping:
                    offset = stream.tell()
                    if raw.endswith(b"\n"):
                        skipping = False
                        lines += 1
                    continue
                if not raw.endswith(b"\n"):
                    if len(raw) > MAX_LINE_BYTES:
                        diagnostics["oversized_lines"] += 1
                        offset = stream.tell()
                        skipping = True
                    else:
                        stream.seek(start)
                    break
                offset = stream.tell()
                lines += 1
                if len(raw.rstrip(b"\r\n")) > MAX_LINE_BYTES:
                    diagnostics["oversized_lines"] += 1
                    continue
                try:
                    value = decode(raw)
                except InvalidRecord:
                    diagnostics["invalid_lines"] += 1
                    continue
                try:
                    record = sanitize(value)
                except (InvalidRecord, TypeError, OverflowError):
                    diagnostics["invalid_records"] += 1
                    if valid_uuid(value.get("task_run_id")):
                        record = {"event": "invalid_declaration", "task_run_id": value["task_run_id"], "timestamp": None, "provenance": "agent_declared"}
                    else:
                        continue
                stamp = record.get("timestamp")
                retained_at = min(stamp, current) if stamp else current
                cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                if retained_at < cutoff:
                    diagnostics["expired_records"] += 1
                    if record.get("task_run_id"):
                        self._db.execute("INSERT OR IGNORE INTO limited_runs VALUES (?)", (record["task_run_id"],))
                    continue
                if stamp:
                    last = max(last or stamp, stamp)
                self._db.execute("INSERT INTO events(record,retained_at,run_id) VALUES (?,?,?)", (json.dumps(record, separators=(",", ":")), retained_at, record.get("task_run_id")))
            stream.seek(0)
            prefix = hashlib.sha256(stream.read(min(offset, 4096))).hexdigest()
            self._db.execute("INSERT OR REPLACE INTO cursors VALUES (?,?,?,?,?)", (path.name, generation, offset, prefix, int(skipping)))
        return consumed, lines, last

    def _prune(self, current: str, diagnostics: Counter[str]) -> None:
        cutoff = (datetime.fromisoformat(current.replace("Z", "+00:00")) - timedelta(days=RETENTION_DAYS)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        expired = [row[0] for row in self._db.execute("SELECT id FROM events WHERE retained_at < ?", (cutoff,))]
        excess = self._db.execute("SELECT max(0,count(*)-?) FROM events", (MAX_CACHE_EVENTS,)).fetchone()[0]
        extra = [row[0] for row in self._db.execute("SELECT id FROM events ORDER BY id LIMIT ?", (excess,))]
        byte_total = self._db.execute("SELECT coalesce(sum(length(CAST(record AS BLOB))),0) FROM events").fetchone()[0]
        byte_extra: list[int] = []
        if byte_total > MAX_CACHE_BYTES:
            for identity, size in self._db.execute("SELECT id,length(CAST(record AS BLOB)) FROM events ORDER BY id"):
                if byte_total <= MAX_CACHE_BYTES:
                    break
                byte_extra.append(identity)
                byte_total -= size
        identities = sorted(set(expired + extra + byte_extra))
        for identity in identities:
            self._db.execute("INSERT OR IGNORE INTO limited_runs SELECT run_id FROM events WHERE id=? AND run_id IS NOT NULL", (identity,))
            self._db.execute("DELETE FROM events WHERE id=?", (identity,))
        diagnostics["retention_pruned"] += len(expired)
        diagnostics["cache_truncated"] += len(extra)
        diagnostics["cache_bytes_truncated"] += len(byte_extra)
        # Avoid unbounded identity-only tombstones after all events disappear.
        self._db.execute("DELETE FROM limited_runs WHERE id NOT IN (SELECT run_id FROM events WHERE run_id IS NOT NULL)")

    def snapshot(self) -> dict[str, Any]:
        """Return an independent JSON-safe snapshot without source paths."""
        with self._lock:
            if self._closed:
                raise RuntimeError("engine_closed")
            return copy.deepcopy(self._snapshot)

    def close(self) -> None:
        """Release isolated state; repeated close calls are harmless."""
        with self._lock:
            if not self._closed:
                self._db.close()
                self._closed = True
