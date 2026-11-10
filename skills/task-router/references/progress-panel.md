# Inline development progress

Use the bundled `relayforge-progress` tools when available. Create one inline
card per development task with `start_progress`, retain its `run_id` and revision,
and update at real milestones. Do not create a card for unrelated questions or
repeat its checklist in chat. Missing tools/UI must not block the requested work.

## Start and load selected instructions

Start before substantive work with a user-recognizable title and actual steps.
Exactly one step is active; other steps are pending, done or skipped. Do not add
unselected review, publication or deployment. Optional `details` carries concise
`current`, `change`, `remaining` and `verification` declarations.

```json
{
  "title": "修复请求重试",
  "steps": [
    {"label": "定位原因", "status": "active"},
    {"label": "修复与验证", "status": "pending"}
  ],
  "details": {"current": "检查重复请求", "remaining": "修复与验证"}
}
```

When entering a selected bundled workflow or specialist Skill, use
`load_progress_skill(run_id, expected_revision, skill)` if available. The skill
argument is its folder slug, such as `development-workflow` or `frontend-design`.
The tool actually reads this plugin's SKILL.md, returns its instructions, and
records a timestamp and content hash. Apply those instructions within the user's
scope. Core workflow loads also select the current workflow. The card labels
these records **loaded**, never executed or successfully completed.

Load only skills actually selected for the task, once per unchanged skill and
task. Do not pre-load a planned list to fill the UI. Track the returned
`loaded_skill` so returned instructions do not recursively load themselves.
Both this tool and `update_progress` write revisions: retain the revision from
every successful write. Re-entering a different core workflow may require a load
to select it again; repeated identical loads are safe and do not duplicate rows.

This loader covers bundled skills only. External or host-loaded skills without
a receipt remain unrecorded; do not infer they were not used. Do not fabricate a
load record from a plan, file name, elapsed time or absent host lifecycle event.
If the loader is missing, use normal skill delivery and continue; never install
or reconfigure the host just to populate the card.

## Meaningful updates

`update_progress` requires the existing run ID, last revision, actual run status
and full step list. Optional `details` replaces the details object; omission keeps
the applicable previous declaration. Include short concrete changes and remaining work.
When scope or checks change, replace stale verification instead of retaining an
old pass. Do not emit updates for every tool call or timer tick.

For a real wait, declare `details.waiting_for` as `user` or `external` and put its
short reason in `details.reason`; `details.remaining` states the next action.
Omit the waiting target when it is unknown; the card will not assume the user
must respond. A blocked attempt should also declare its reason and next action.
These are metadata declarations, not raw error output.

Leaving waiting clears its target; leaving waiting/blocked clears the reason.
Completion/cancellation clears old current and remaining declarations while
preserving verification. Supply a final summary. The completed view shows no
remaining work in the agreed scope; it never turns partial verification into a pass.
New milestone history stores bounded details for later inspection. Missing legacy
details are not reconstructed, and retained history is capped at 20 entries.

```json
{
  "current": "验证并发与重试",
  "change": "已补齐幂等校验",
  "remaining": "超时恢复",
  "verification": {
    "status": "partial",
    "passed": 18,
    "pending": 2,
    "evidence": "相关回归用例结果"
  }
}
```

Use actual results, never copy example counts. Verification status is one of
not_run/running/passed/failed/partial/skipped/unavailable. Counts are optional;
if supplied they need a short evidence description. Do not send raw commands,
paths, test output, patches, prompts or credentials. Counts and conclusions are
explicitly Agent-declared; a completed task does not imply tests passed.

| Run status | Meaning |
| --- | --- |
| running | One active step, work underway |
| waiting | One active step, a real user/external dependency pending |
| completed | Agreed scope ended; all steps done or explicitly skipped |
| blocked | One blocked step, this attempt ended without delivery |
| cancelled | User cancelled the attempt; no active step |

Record the actual outcome before the final reply. Keep a waiting run live across
clarifications; do not complete it because a turn ends. Terminal runs are immutable
and a new attempt gets a new ID. A revision conflict returns the scoped snapshot;
reconcile and retry once. Identical retries are safe. Missing/pruned state or
storage failure means unavailable progress: report the gap once and continue.

## Display and boundaries

The resource and MCP Apps initialization are inline-only; there is no automatic
thread side-panel entrypoint. The visible card reads its task every two seconds without
model calls; hidden pages suspend reads and unchanged revisions do not redraw.
Permanent missing-state errors stop polling, while temporary failures retry.
Keep details and records inside the card. Do not call the render tool
again to refresh; use `open_progress(run_id)` only when the user requests another
display. A missing MCP Apps automation tab alone says nothing about inline cards.

After plugin updates, a new chat may be necessary to acquire new tools. Do not
loop through restarts or repeated mentions when the tool inventory has not changed.
Keep IDs and revisions in task context or an existing checkpoint, never source.
Do not read user logs or conversation stores to populate the card. Existing work,
authorization and verification rules remain unchanged.
