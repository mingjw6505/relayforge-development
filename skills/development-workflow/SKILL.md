---
name: development-workflow
description: Execute Standard or Large work with acceptance evidence, focused tests and bounded coordination. Use after routing; skip Quick tasks, planning-only requests and standalone reviews.
---

# Development Workflow

Default to one writer, the existing conversation and repository conventions.
Reuse the router's acceptance, dependencies, risk, selected skills, budget and
authorization. If invoked directly, infer these from the request and affected
code instead of starting another routing conversation.

Standard=L2 uses minimal specification-driven development (SDD); Large=L3
adds durable dependency coordination. A primary agent can coordinate sequentially.
Multiple sessions alone do not select L3. Quick/L1 stays inline with the same
evidence principles and finishing, without loading this whole workflow.

## Minimal SDD and adjustments

Maintain three logical areas: Spec (outcome, scope, behavior, boundaries and
acceptance); Plan (approach, affected contracts/data, risks and checks); Tasks
(work, dependencies, ownership and completion). Reuse upstream requirements and
existing plans. One combined file or the current context is enough; persist for
multi-session, deferred work or handoff through writing-plans.

Do not conduct product discovery or invent unresolved behavior. Return consequential
product decisions to the user/upstream, continuing independent authorized work.
Keep execution_mode separate from pending/active/blocked/integrated task states.
Read [task contracts and recovery](references/task-contracts.md) for coordinated
tasks, contract changes or context recovery. Route changes preserve valid results,
authorization and fix counts; update the existing plan rather than restart it.

## Establish only missing context

Inspect the affected path, direct callers and adjacent tests. Record the observable
outcome, behavior to preserve and cheapest useful checks. Capture a baseline when
it separates pre-existing failures from regressions. Ask only for unresolved
product, contract, data, security or significant-cost decisions; do independent
work while those answers are pending. Reuse answers and valid evidence across phases.

For multi-session/deferred work or handoff, use
[writing-plans](../writing-plans/SKILL.md), even when implementation starts now.
Reuse existing plans; small tasks remain inline. Continue already-authorized
execution without a new plan approval. Read
[acceptance and risk](references/acceptance-and-risk.md) for material boundaries,
ambiguous acceptance or an effort-limit decision, not for every mechanical edit.

Use a branch already dedicated to the task or follow
[task-branch](references/task-branch.md) before editing. Preserve unrelated changes;
never automatically stash, commit, reset or carry them to another branch.

## Implement and check

- For unknown failures, obtain reproduction/root-cause evidence before a production
  fix. Use a bounded experiment when a reliable trigger is not yet available.
- For business rules, regressions and high-risk invariants, prefer one behavior
  test at a public boundary, observe the expected failure, then implement enough
  to pass. Repeat by vertical slice. Use expectations from requirements or known
  examples, not the implementation's formula; avoid private-structure tests and
  writing all tests before any implementation.
- Characterize legacy behavior that must survive without preserving a known bug.
  An unrelated import/environment failure is not a regression proof. If a red test
  cannot be obtained, record the alternative evidence and gap. Mechanical prose,
  styling and equivalent edits need a focused result check instead of a new unit test.
- Use a compatible installed TDD skill if available; otherwise perform this loop
  directly. Choose boundaries from existing contracts; no routine confirmation
  is needed when the product behavior is settled.
- Run relevant compilation/type checks and focused tests as they inform the work.
  Record command, result and relevant inputs. A new phase or reviewer is not a
  reason to rerun unchanged checks; finishing runs only missing/invalidated checks.
- After two fixes without progress, reassess. Share a three-round review/fix limit
  per unresolved issue across children and phases; respect a user budget earlier.
  At a limit preserve evidence and report the next useful action. Do not reduce
  required checks, invent passes or reset the count by spawning another child.

## Local improvement boundary

Fix directly related structural problems when they simplify this change and can
be verified: remove duplicated logic being touched, clarify state ownership, or
isolate a concrete dependency needed by the task. Keep established public behavior
and contracts unless their change is part of the requirement. Inspect the final
diff for scope growth. Do not turn style preferences into automatic rewrite loops.

Cross-module reorganization, infrastructure replacement or a larger architectural
change is a separate proposal with its reason and likely scope. Continue the
requested work if it can be delivered correctly without that refactor; ask for a
decision only if the larger change actually blocks a correct result. File size
alone does not justify a split. New shared state/side effects warrant a brief check
of ownership, failure/retry behavior and affected callers before implementation.

## Delegate only for a concrete benefit

A bounded advisor or fresh implementation child can reduce uncertainty/context
pressure. Give it outcome, acceptance, owned paths, source pointers, constraints
and checks. The Controller stops writing when a child owns the primary checkout.
Children are leaves, cannot mutate Git state, and return changes, evidence and
blockers. Validate their results. If tools/policy forbid delegation, work inline
and expose any required independent-review gap. Using a child does not require
the separate `subagent-driven-development` workflow.

For coordinated work, maintain task IDs, prerequisites, ownership, checks and
states (`pending`, `active`, `blocked`, `integrated`) in the plan or existing
context. Detect missing/cyclic prerequisites before dispatch. A task is ready
only when its prerequisites are integrated and required checks passed, not when
a child merely says DONE. Recompute readiness after integration; continue
independent ready work if another branch is blocked and scope/budget allow.

Read [parallel-worktrees](references/parallel-worktrees.md) only if two substantial
ready tasks have no mutual path/contract/runtime dependency and dispatch plus
integration costs plausibly less than the expected benefit. Maximum two writers;
Controller coordinates without editing. The protocol owns isolation, frozen
patches, integration and cleanup. Its clean base must contain verified prerequisites.
If a prerequisite is only uncommitted, continue sequentially in that checkout;
do not manufacture a commit/stash to enable parallelism. Stop affected consumers
when shared contracts change, refresh inputs, then reschedule. Reassess their
transitive consumers and affected checks; keep old code/evidence for diagnosis
instead of automatically deleting or reverting it.

For dependent frontend/backend work, implement vertical slices and follow
[backend-to-frontend handoff](references/backend-frontend-handoff.md): verify the
backend contract before dependent frontend work, then check the integrated slice.
Small same-owner/context slices keep evidence inline; persist it when ownership
or context changes or execution is deferred. Independent groundwork may proceed.

## Continue through completion

Before compaction/handoff, save only decisions, task state, source/revision or
working-snapshot pointers, evidence and open findings. On resume check the actual
checkout before redispatching completed work. Do not automatically clear context
or pass the whole conversation to every child.

Implementation is complete when the requested changes exist in the primary
checkout, paths are in scope, acceptance maps to evidence or explicit gaps,
dependent frontend work consumed the current contract, and worker integration/
recovery state is known. An unmet implementation requirement remains blocked.
Pass results and gaps to [finishing-development](../finishing-development/SKILL.md)
automatically; do not ask which routine finishing steps to perform.
