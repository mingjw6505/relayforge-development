---
name: delivery-handoff
description: Generate or update a testing handoff when selected during finishing, explicitly requested or required by repository rules, using actual changes and development evidence. Skip ordinary completion summaries, product requirements writing and final independent test conclusions.
---

# Delivery Handoff

Reuse finishing's integrated changes, acceptance, evidence and gaps. When invoked
directly, inspect those facts without restarting implementation, tests or review.
The testing agent independently chooses tests and reaches its own conclusions.

Read and apply [progress in the conversation](../task-router/references/progress-display.md),
including for direct handoff requests. Reuse any existing progress view; show
evidence reconciliation, handoff preparation and its actual readiness or blocker.

## Select the form

A selected/requested full handoff, explicit transfer to a testing agent or
repository requirement needs a full Markdown file, including a blocked handoff.
Honor the finishing selection regardless of L1/L2/L3; route size and high risk
alone do not require a file. Other completions report inline without loading the
full template: outcome, actual changes, possible impact, executed checks, gaps
and code availability. Preserve any existing handoff; update it when the current
scope includes maintaining that handoff, not merely because a route changed.

For a full file read [the template](references/test-handoff-template.md). Use the
project's delivery convention, otherwise docs/test-handoffs/Test-Handoff-<task-id>.md.
Normalize the filename ID safely and preserve the original upstream ID inside.
Confirm the path is visible and does not overwrite another task. Update the same
task's handoff instead of creating one per reply. Upload to a document center only
when separately requested; this skill does not send messages or publish.

## Establish facts

- Reuse upstream ID/source and acceptance criteria. Label locally assigned AC IDs.
  Missing consequential product decisions return upstream; do not invent intent.
- Derive added/modified/deleted/renamed files from the actual task baseline and Git
  changes, including staged, unstaged and task-owned untracked content. Exclude
  unrelated user work; disclose uncertain attribution.
- Separate changes from direct and indirect impact. Cite callers/contracts or
  configuration for inferred impact; None means no change, Unknown means unverified.
- Map acceptance to implementation locations and evidence/gaps, not product approval.
- Suggest normal, error, boundary, regression and high-risk scenarios as applicable.
- Record only actual development checks. Use passed/failed/not_run/skipped/unavailable,
  with commands/methods, scopes and actual code/dependency/configuration references.
- Record startup steps as verified or unverified, required services/data and safe
  configuration sources. Do not include credentials or real sensitive test data.

## Code identity and retrieval

A committed result needs precise base and target commits; uncommitted results need
base/HEAD and a scoped snapshot/package or content manifest covering actual task
files, including binary changes where relevant. Reuse existing frozen review
packages; do not commit merely to populate Final Commit. Use not_created when
there is no task commit. A clean tree is not proof of publication or accessibility.

Set Code Availability to available only when the target tester can retrieve the
exact result and verify its identifier. A verified shared checkout may suffice.
local_only means only the development machine has it; unavailable means retrieval
is known to fail; unknown means not checked. Branch/remote names and hashes alone
do not prove availability. Keep credentials out of repository URLs.

Exclude generated handoff/log files from the tested code snapshot to avoid a
self-hash cycle; version them separately if they are delivered artifacts.

## Choose status and check consistency

| Development Status | Required facts |
| --- | --- |
| ready_for_testing | In-scope implementation complete, required development gates passed, no blocking issue, correct code and necessary test entrypoints accessible |
| ready_with_issues | In-scope implementation complete and testable; only disclosed non-blocking issues or permissible verification gaps remain |
| blocked | Necessary implementation, critical gate, environment or code transfer blocks the agreed testing |

Never classify a critical gate failure as non-blocking merely to finish. Explicit
acceptance of a permissible gap preserves the actual failed/missing evidence and
does not count as passing the original benchmark rubric. Unfinished required scope
stays blocked unless the upstream explicitly changes scope.

Implementation can be complete while handoff is blocked by code availability.
Writing a handoff does not make implementation complete or tests passed.
For each issue state impact, whether blocking, next action and owner.

Before delivery check all nine sections, actual file attribution, current code
references, evidence truth, acceptance mapping, retrieval and status consistency.
Remove unexplained template placeholders. Unknown is honest disclosure, not proof
that a field is verified. Link the resulting file; label synthetic examples as
demonstrations, never as executed test evidence.
