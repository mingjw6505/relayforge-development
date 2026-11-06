# Route adjustments and recovery

Maintain decisions in the existing context or plan: task_run_id, current
execution_mode, route_policy_version=v2.1, risk, reason, and affected task IDs.
Use a fresh opaque UUID for a new run; reuse it when resuming that run.
Persist before context handoff, deferred execution or multi-session work.

| Transition | Reason code | Meaning |
| --- | --- | --- |
| Initial L1 | local_scope | Settled local change |
| Initial L2 | bounded_sdd | Minimal design under one primary writer |
| Initial L3 | coordination_required | Durable dependency coordination |
| L1 → L2 | design_required or contract_changed | New design or contract work |
| L2 → L3 | coordination_required | Substantial coordinated tasks discovered |
| L3 → L2 | coordination_unnecessary | One owner can manage the remaining work |
| L2 → L1 | scope_simplified | Only a settled local change remains |

Apply adjacent transitions; if two are needed, record both without repeating
analysis. Reassess at a concrete new boundary, before dispatch or after a bounded
failed attempt, not at every tool call.

Before dispatch, preserve completed work and checks, update the plan, and mark
affected direct/transitive consumers for reassessment when their contract changes.
No transition resets fix counts, task status or authorization. A downgrade never
waives high-risk checks. Existing durable artifacts may remain after a downgrade.

When telemetry is already enabled, emit route_selected once, then route_changed
through the existing logger's --record-workflow-event stdin interface. Resolve
scripts/workflow_logger.py from the plugin root, not the target project. The
[logging contract](../../../docs/workflow-logging.md) specifies allowed fields.
Keep event_id and the increasing sequence in the same existing plan/checkpoint;
retry uncertain writes with the original event_id. The logger receives metadata
only; explanations belong in the plan, not a free-text log reason.

If collection is unavailable, keep the decisions in context/plan and report
telemetry partial or unavailable. Do not enable hooks, fabricate missing events
or treat planned skills/agents as observed execution.
