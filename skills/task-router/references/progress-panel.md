# Inline development progress

Use the bundled `relayforge-progress` tools when available. Create one inline
card per development task with `start_progress`, retain its `run_id` and revision,
and update at real milestones. Do not create a card for unrelated questions or
repeat its checklist in chat. Missing tools/UI must not block the requested work.
For failures or requested checks, apply [environment recovery](progress-environment.md)
to notify, inspect and assist authorized repair; an absent card does not prove
Python is missing.

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

### Mode, method progress and concrete action

After routing is actually selected, declare top-level `execution_mode` as `L1`,
`L2` or `L3`. The card displays Quick/L1, Standard/L2 or Large/L3. Preserve it
across workflow loads and finishing; it is not a Skill name. Mode changes are
adjacent and retain completed work/history. Keep the reason in task context.
Omit the field only while no mode has been selected or the tool lacks support.

Declare `method_progress` only for methods actually selected: `sdd`, `tdd` or
`coordination` (dependency coordination, not proof of subagents). Up to three
unique tracks are accepted, each with `method`, `status` and `phases`. Track
status uses the run-status enums; phases use `{label, status}` step entries,
at most eight unique single-line labels of at most 40 characters. Every running
or waiting track has one active phase. Completed tracks have only done/skipped
phases. Do not send a `source` field; the server marks declarations.

Keep three levels separate: execution mode, method phase, concrete action in
`details.current`. For example, Standard/L2 + SDD/specification phase +
"正在生成规格文档". An implementation phase can additionally show a real TDD
red/green/refactor cycle. `steps` remains the concrete task checklist, not an
implicit replacement for method progress. Stage names follow actual scope;
selecting SDD does not require a separate specification file or plan where the
existing workflow permits conversation-based requirements. Say "规格文档" only
when a document is actually being produced. Do not add review, tickets, handoff,
commit or push phases merely to fill the track.

```json
{
  "execution_mode": "L2",
  "method_progress": [{
    "method": "sdd",
    "status": "running",
    "phases": [
      {"label": "规格文档", "status": "active"},
      {"label": "实施计划", "status": "pending"},
      {"label": "实现与验证", "status": "pending"}
    ]
  }],
  "details": {"current": "正在生成规格文档"}
}
```

Both start/update accept these optional fields. Omission preserves existing
mode/tracks; `method_progress` replaces the whole selected list, and `[]` removes
it after a real scope change. Advance phases at actual milestones, never because
a Skill was loaded. Before ending the task, explicitly end remaining tracks:
completed only for finished scope, blocked for a blocked attempt, cancelled for
a discontinued method. Task completion rejects blocked or still-running tracks;
it never auto-completes them or implies tests passed. Unknown legacy mode stays
"未申报" and absent tracks stay absent. If these arguments are unavailable,
continue with the concise text fallback; do not send unsupported fields or
modify the installed host to populate the card.

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
