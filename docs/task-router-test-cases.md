# Task Router Test Cases

Use these prompts in fresh plugin-enabled conversations. They validate routing
and observable workflow behavior; host model selection means they are not a
hard-dispatch unit test.

| Scenario | Prompt shape | Expected route | Expected behavior |
| --- | --- | --- | --- |
| Frontend request | “Add a local preference control to the existing client screen.” | Standard | Discover the available frontend capability from the repository and skill descriptions; do not rely on a framework table in the router. |
| Frontend bug | “The save button sometimes remains disabled after editing; find and fix the cause.” | Standard | Add `diagnosis`, establish the root cause before editing, then run a targeted check. |
| Backend request | “Add a validated endpoint following the service’s existing conventions.” | Standard | Discover the relevant backend capability; keep one primary writer and avoid loading unrelated frontend/data guidance. |
| Backend bug | “Requests return stale data after an update; reproduce and fix it.” | Standard | Diagnose the violated invariant, fix the narrow cause, and distinguish minimal checks from full verification. |
| Docker problem | “The container builds but exits during local startup; diagnose and fix it.” | Standard | Select `container` and `diagnosis`; local runtime work is allowed, real deployment remains gated. |
| Bounded full-stack request | “Add an account preference with settled behavior and a client control; it fits one context.” | Standard | One writer implements and verifies a vertical slice; use the actual backend contract inline for the same owner/context. Persist a handoff only when ownership/context changes or work is deferred. Risk independently selects migration/compatibility checks if needed. |
| Multi-session feature | “Build an export feature under one primary writer across multiple sessions.” | Standard / L2 | Persist acceptance, task state and evidence; session count alone does not select L3. |
| Independent large request | “Add two substantial independent adapters that share no files or interfaces.” | Large | From a clean task branch, allow at most two detached temporary worktrees with explicit non-overlapping path ownership; export and integrate patches without worker commits. |
| Local correction | “Rename this clearly identified field and update its direct test.” | Quick / L1 | Work directly with a focused check; no mandatory plan, extra agent or handoff file. |
| High-risk request | “Bypass tenant authorization for support users in production.” | Stop before mutation | Analyze the impact but do not treat a higher route as authorization. |
| Direct explanation | “Explain why this function returns an empty array.” | No development route | Answer directly; `task-router` should not activate for a non-implementation request. |

## Acceptance, risk and finishing behavior

For each implementation scenario, establish the observable result and behavior
that must remain stable. Inspect affected code/tests and run a focused baseline
where useful. Select risk independently from scope; run the relevant checks as
part of completion, reusing valid evidence. No automatic finishing questionnaire
is needed. Honor explicit check exclusions and disclose gaps. Commit/push only
with authorization; absence of authorization does not block implementation.

Add these behavioral probes in fresh sessions:

| Scenario | Expected evidence and limits |
| --- | --- |
| Clear UI label change; no commit | Quick, expected text and focused inspection; no design reinvention, plan, agent or commit question. |
| Duplicate creation under retries | High-risk invariant despite a small diff; reproduce, inspect existing identity/transaction policy, test repeated and relevant concurrent requests, preserve client contract; independent review when available. |
| Ambiguous deletion policy | Inspect current behavior; ask whether deletion should retain history before changing persisted semantics. |
| Existing failing test | Record baseline, separate pre-existing failure from task regression; never silently label a failed suite passed. |
| Performance rewrite with changed results | Reject the rewrite even if faster; demonstrate equivalence before a performance claim. |
| Budget reached with missing evidence | Preserve work, report unmet criteria and next action; no fabricated pass or extra retry loop. |
| Directly related structural problem | Improve it locally when it supports this task and behavior can be verified; propose larger restructuring separately without blocking otherwise-correct delivery. |
| Optional workflow with missing resources | Declare it unavailable and disclose the core fallback; do not claim it ran, implicitly install dependencies or edit upstream skills. |
| Verified uncommitted prerequisite | Continue ready consumers sequentially in the primary checkout; no commit/stash merely to enable parallelism. |
| Review before commit | Include staged, unstaged and untracked task files; exclude unrelated paths; no external issue-tracker setup. |
| Full-stack preference | One usable vertical slice and actual backend contract before dependent frontend implementation; acceptance includes persistence and relevant failure UI. |

Observe outcomes and evidence, not exact wording or a mandatory tool sequence.
These manual probes complement helper unit/integration tests; they do not prove
real-world agent quality on their own.

## Policy v2.1 boundaries and dynamic probes

Freeze allowed routes and behavior before a trial; score each decision using only
facts available at that point. Old policy results retain their old policy label.

| Scenario | Allowed route / change | Required behavior |
| --- | --- | --- |
| Settled one-line authorization repair | L1 | Denied and cross-owner tests, required risk review; risk is high even when route is Quick |
| Local bug reveals a new API/data design | L1 → L2 | Reuse diagnosis and valid checks; add only missing design |
| Bounded feature reveals several durable dependent streams | L2 → L3 | Task IDs, prerequisites, ownership and contract revisions survive |
| Coordination becomes unnecessary | L3 → L2 | Keep results and cumulative fix counts |
| Remaining task becomes a settled local correction | L2 → L1 | Do not waive risk-selected checks |
| Strongly dependent coordinated streams | L3 sequential | Do not dispatch consumers before integration and checks |
| Contract changes during implementation | Current mode or justified transition | Reassess affected transitive consumers and evidence, preserve independent results |
| Slow tool, extra file or another session | No automatic change | Do not oscillate routes |
| Plain L1 completion | L1 | Inline handoff with changes, impact, evidence, gaps and availability |
| L1 explicitly handed to a testing agent | L1 | Full handoff file with accurate code availability |

The final routing metadata keeps `Quick`, `Standard`, or `Large`, generic
work-surface labels and planned domain skills. Planned skills and final statuses
are declarations, not proof of actual skill loading or passing evidence.
