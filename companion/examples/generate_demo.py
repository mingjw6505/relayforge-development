"""Create conspicuously synthetic metadata in a new directory for offline demos.

Never point this generator at plugin data. It refuses an existing destination.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID


def records() -> list[dict[str, object]]:
    """Return synthetic independent session and declaration streams."""
    now = datetime.now(timezone.utc)
    session = "sha256:" + "a" * 20
    turn = "sha256:" + "b" * 20
    events: list[dict[str, object]] = []

    def event(kind: str, seconds: int, **fields: object) -> dict[str, object]:
        return {"schema_version": 1, "timestamp": (now - timedelta(seconds=seconds)).isoformat(),
                "event": kind, **fields}

    events.append(event("session_started", 100, session_id=session))
    events.append(event("turn_started", 95, session_id=session, turn_id=turn))
    for key, name, outcome, seconds in (("c", "shell", "failed", 80),
                                         ("d", "read_file", "succeeded", 50)):
        ids = {"session_id": session, "turn_id": turn, "tool_use_id": "sha256:" + key * 20,
               "tool_name": name}
        events.append(event("tool_started", seconds, **ids))
        events.append(event("tool_completed", seconds - 4, **ids, matched_start=True,
                            duration_ms=4000, outcome=outcome))
    events.append(event("tool_started", 12, session_id=session, turn_id=turn,
                        tool_use_id="sha256:" + "e" * 20, tool_name="shell"))
    run = "10000000-0000-4000-8000-000000000001"
    common = {"source": "agent_declared", "workflow_event_schema_version": 1,
              "task_run_id": run, "route_policy_version": "v2.1"}
    events.append(event("route_selected", 70, **common,
                        event_id=str(UUID(int=2)), sequence=1, execution_mode="L2", route="standard",
                        risk="medium", reason_code="bounded_sdd", planned_skills=["development-workflow"]))
    events.append(event("verification_summary", 30, **common,
                        event_id=str(UUID(int=3)), sequence=2, implementation="blocked",
                        minimal_checks="failed", test_verification="partial", code_review="skipped",
                        commit="skipped", push="skipped"))
    events.append(event("workflow_completed", 20, **common,
                        event_id=str(UUID(int=4)), sequence=3, implementation="blocked",
                        development_status="blocked"))
    return events


def main() -> None:
    parser = argparse.ArgumentParser(description="SYNTHETIC demo generator — never use real plugin data directories")
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    destination = arguments.destination.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=False)
    path = destination / f"events-{datetime.now(timezone.utc).date().isoformat()}.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in records()), encoding="utf-8")
    (destination / "SYNTHETIC-DEMO.txt").write_text(
        "SYNTHETIC DEMO ONLY. Not captured from Codex. Do not use as C1 evidence.\n", encoding="utf-8")
    print("Synthetic demo created. This does NOT verify Codex collection.")


if __name__ == "__main__":
    main()
