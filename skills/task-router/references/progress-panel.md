# Codex task progress panel

Use the bundled `relayforge-progress` MCP tools for software development tasks
in Codex desktop. This is an Agent-declared view, not a host-verified trace.
Use brief plain-language updates when tools or UI are unavailable. Explanations
and unrelated requests do not create a task panel. No Hook or raw log is needed.

## Start once, keep the task identity

Before substantive work, call `start_progress` once with a short title, a small
list of actual workflow steps, and an optional summary. Exactly one step is
`active`; other steps are `pending`, `done` or `skipped`. Steps have unique labels.
Choose steps appropriate to the task; do not add review, commit or deployment
unless selected or required. Quick work can use only implementation and checks.
The tool returns a full snapshot including a random `run_id` and `revision`.
Keep these in task context or an existing checkpoint, never in source code.

Example arguments (adapt the work, not just the text):

```json
{
  "title": "实现请求的功能",
  "steps": [
    {"label": "检查相关接口", "status": "active"},
    {"label": "实现变更", "status": "pending"},
    {"label": "执行必要验证", "status": "pending"}
  ],
  "summary": "正在确认现有行为和变更范围"
}
```

The panel declares fullscreen-only presentation, which opened the right panel
in the tested Codex desktop version. Do not repeatedly call the render tool to
refresh it. The panel reads its own task every two seconds without model calls.
The host may reuse the panel for an explicit new render result; this switches
its task and discards old reads. Poll responses can never switch the bound task.
If the user closes it, reopen only when requested with `open_progress(run_id)`.
An empty UI automation tab list alone does not prove a render failure.

## Update real milestones

Call `update_progress` at meaningful phase changes, blockers, resumption or the
final outcome. Send `run_id`, `expected_revision` from the last successful reply,
`status`, the full current `steps`, and an optional concise `summary`.
The reply is a compact acknowledgement with the new revision. Keep it for the
next update. Do not add a call for every tool, elapsed-time tick or file edit.
The primary agent owns updates; delegated workers report to that coordinator.

| Run status | Steps and meaning |
| --- | --- |
| `running` | Exactly one active step; work is underway |
| `waiting` | Keep one active step; a real user/external dependency is pending |
| `completed` | All steps done or explicitly skipped; only the agreed scope ended |
| `blocked` | Mark one step blocked, keep unfinished steps pending; this attempt ended |
| `cancelled` | No active step; the user actually cancelled the attempt |

`done` means supported by evidence; `skipped` is never counted as done. Do not
turn a test or tool failure into successful verification. Before the final reply,
record the actual result: completed when the scope and required checks finished,
blocked when the attempt cannot deliver, or waiting when a live decision remains.
Do not complete a run because a turn stopped. Terminal runs are immutable; a new
attempt after a blocked/completed/cancelled run gets a new run ID. Mid-task
clarifications and ordinary resumes keep the same still-live run.

A revision conflict returns the current scoped snapshot. Reconcile it with real
work and retry once with its revision; do not blindly overwrite newer state.
An identical retry is safe. A missing/pruned task or storage failure means panel
state is unavailable; retain the work state in the conversation. Report the gap
once and continue, without repeated setup/retry loops. A new panel after a lost
run must be identified as a new attempt; do not fabricate the lost history.

## Data boundary

Only send short, plain milestone declarations. Never pass the raw prompt,
commands, source, patches, tool output, credentials or raw log records. Do not
attach a target project's files or read conversation stores to populate the UI.
The run ID scopes the view; never substitute another task or a latest-task query.
The panel shows step counts and received updates, not inferred percentages,
token usage, tool activity, approvals or ETA. Presentation success does not prove
the declared work is true. Existing verification and authorization rules remain.
