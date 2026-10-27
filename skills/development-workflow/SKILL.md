---
name: development-workflow
description: Execute Standard or Large implementation work after routing, with scoped context, clear ownership, proportional AI resources, and low-cost development checks. Do not use for Quick tasks or post-development test, review, commit, and push choices.
---

# Development Workflow

Implement the routed task while keeping context and coordination proportional.
This skill ends at `implementation-complete`; it does not silently run the
optional finishing actions.

## Input contract

Start from the router handoff:

- route: `Standard` or `Large`;
- requested outcome and acceptance criteria;
- work surfaces and their dependencies;
- whether the router identified a frontend/backend `full-stack` dependency;
- current branch, `HEAD`, and checkout status;
- selected specialist capabilities;
- repository rules and known risks; and
- test, review, commit, or push actions the user already requested.

Resolve context from the repository before asking the user to repeat it. Ask
only when a missing choice would change product behavior, public contracts,
persisted data, permissions, security, cost, or blast radius.

## Shared implementation rules

- Use one primary task branch as the normal isolation boundary. Reuse the
  current branch only when it is already dedicated to this task; otherwise
  create a task branch from a clean current `HEAD` before editing. Do not
  automatically stash, commit, reset, or carry unrelated changes. Read
  [the task-branch protocol](references/task-branch.md) only when a transition
  is needed.
- Load each selected specialist only when its work surface becomes active.
- Keep one writer per owned file set. Preserve unrelated user changes.
- For an unknown failure, establish a reproducible symptom and root-cause
  evidence before changing code.
- Make the smallest coherent changes that satisfy the current outcome. Avoid
  unrelated cleanup.
- Development may run compilation, type checks, and targeted tests that directly
  guide the implementation. Record them as `Minimal checks`, never as complete
  `Test verification`.
- When a check fails, fix an in-scope regression. Preserve evidence for
  unrelated, pre-existing, environmental, or permission-blocked failures.
- Do not repeat the same failing action without new evidence.

## Standard

Use one primary implementation context. Reconstruct the affected behavior,
select the needed capability, implement, and run the narrowest useful checks.
A read-only advisor is justified only when it materially reduces uncertainty;
do not create implementation agents, worktrees, formal plans, or review
packages by default.

## Large / full-stack

The main session is the Controller. Before editing, maintain a compact map of:

- each work surface and user-visible outcome;
- dependency and integration order;
- file or component ownership; and
- the check that will prove each surface before integration.

Default to one writer in the primary checkout and execute surfaces
sequentially. A second writer is allowed only when two substantial units share
the same stable base but have no path, contract, schema, migration, generated
output, or runtime dependency. Read and follow
[the parallel-worktree protocol](references/parallel-worktrees.md) only when
this strict parallel case exists.

Never run more than two writers concurrently. Parallel writers use separate,
detached temporary worktrees outside the repository; the Controller does not
edit while they run. Each child receives only its outcome, constraints,
interfaces, owned paths, checkout path, and expected checks. Children may not
spawn children or mutate Git state. Integrate validated patches one at a time
into the primary task branch, then run cross-surface checks.

When any parallel condition is absent, do not create a worktree; execute in the
primary checkout. Update dependent workers when a shared contract changes. The
Controller owns integration and reconciles all surface results before declaring
implementation complete.

### Backend-to-frontend handoff

For a `full-stack` task, complete the backend surface and its minimal checks,
then automatically export a frontend handoff before contract-dependent frontend
implementation begins. This local process artifact does not require a separate
user choice.

Read and follow
[the backend-to-frontend handoff contract](references/backend-frontend-handoff.md)
only for these full-stack tasks. Write the artifact under the ignored
`.relayforge/handoffs/<task-slug>/` workspace. The frontend owner must read it
before consuming backend behavior, and the Controller must refresh it whenever
the backend contract changes.

Independent frontend groundwork may run earlier, but do not implement against
an assumed backend contract. If the backend is blocked or its observable
contract is not stable enough to hand off, keep dependent frontend work blocked
and report the precise reason.

## Implementation completion

Reach `implementation-complete` only when:

- the requested implementation exists or a precise blocker is known;
- all changed paths have an in-scope reason;
- available minimal checks have a recorded result; and
- every full-stack backend/frontend dependency has a current handoff artifact
  consumed by the frontend owner; and
- every temporary worker patch is integrated, while any retained worktree and
  its recovery reason are explicit; and
- unresolved risks and unavailable capabilities are explicit.

Then load [finishing-development](../finishing-development/SKILL.md). Pass its
status inputs and the user's preselected finishing actions. Do not claim full
verification or independent review at this boundary.

An action the user did not mention is unresolved, not skipped. When any of test
verification, code review, commit, or push remains unresolved, stop after
implementation-complete and let `finishing-development` ask its single combined
question. Do not choose an answer on the user's behalf.
