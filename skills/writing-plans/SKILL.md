---
name: writing-plans
description: Persist technical implementation decisions, tasks and checks for multi-session work, deferred execution, handoff or an explicit implementation-plan request. Consume existing tickets; skip delivery-ticket breakdowns and formal plans for small tasks that fit the conversation.
---

# Writing Plans

Write the decisions needed to implement and verify the outcome without replaying
the conversation. Reuse an existing spec/plan. Small authorized tasks stay inline;
multi-session work needs a durable plan even if implementation starts now. Announce
use of this skill briefly in the conversation's language.

Read and apply [progress display](../task-router/references/progress-display.md),
including for a direct planning-only request. Reuse the task's inline card when
available; finish the planning scope without implying implementation occurred.

When the task already selected SDD, use the
[mode/method contract](../task-router/references/progress-panel.md#mode-method-progress-and-concrete-action)
to mark its actual planning phase active and describe the concrete planning action.
Preserve the routed L1/L2/L3 mode and other phases; a Skill load alone never marks
the specification or plan complete. Do not create additional documents for the card.

## Scope and storage

Read affected code, tests and existing decisions. Separate agreed requirements
from assumptions; ask only for consequential unresolved choices. A technical
unknown needs a bounded investigation, not invented implementation details.
Planning alone does not authorize implementation.

Store internal plans under ignored `.relayforge/plans/<task>.md`; verify the
directory is ignored first. For a requested public deliverable use the project's
documentation convention, otherwise `docs/relayforge/plans/YYYY-MM-DD-<task>.md`
and make sure it is actually visible rather than ignored. Never expose internal
briefs/ledgers merely because a public plan was requested.

Use the conversation's language for prose; preserve literal paths, code, identifiers
and specified values. A second spec document is unnecessary when this plan already
contains the agreement. Do not copy an entire spec into every task.

## Decompose for execution

- When delivery tickets exist, retain their IDs, scope, acceptance and delivery
  dependencies by reference. Add only needed code paths, interface contracts,
  technical prerequisites and checks; do not regenerate or renumber the backlog.
  Map technical task IDs to their source ticket IDs. The plan owns technical task
  execution state; tickets own delivery scope and agreement, not a duplicate ledger.
- A ticket is optional input. Without tickets, plan directly from the agreed
  requirements. If the request is to create a delivery backlog rather than an
  implementation plan, use [to-tickets](../to-tickets/SKILL.md) instead. Do not
  create tickets solely because this plan contains tasks.
- If technical findings require changing agreed ticket scope or acceptance, surface
  that specific decision and hold affected work. Preserve independent work and
  prior authorization; do not silently rewrite agreement or repeat unchanged approvals.
- Prefer user-visible vertical slices with independently checkable outcomes.
  Include required setup/configuration in the slice that needs it; do not split
  into frontend/backend/data plans by default.
- Each task should fit one focused context. Record prerequisite IDs, ownership,
  consumed/produced contracts and checks. Ordering alone is not a dependency graph.
  Shared contract work must be an explicit prerequisite.
- Specify paths and interfaces that constrain another task. Leave ordinary local
  implementation choices to repository conventions; include code only to resolve
  real ambiguity. File length alone is not a reason to restructure.
- Allow directly related, verifiable local structural fixes that support the
  requested change. Larger cross-module or infrastructure refactors are separate
  proposals; do not expand the plan unless required for correctness or authorized.
- Default to one writer. Mark parallel candidates only when prerequisites can be
  verified in one clean base, ownership is disjoint, no mutual contract/runtime
  dependency remains, and the benefit exceeds coordination cost. Execution owns
  worktrees; uncommitted prerequisites can support sequential work in the primary
  checkout. Do not add checkpoint commits just to permit parallelism.

## Compact plan shape

Adapt this outline to the task. Omit irrelevant sections, retain requirements and
dependencies. Fixed labels used by an explicitly selected legacy executor must
follow that executor's parser; ordinary execution needs no rigid document schema.

```markdown
# [Feature] Implementation Plan

**Goal / acceptance:** [observable outcomes, preserved behavior, exclusions]
**Spec:** [existing source or agreed requirements here; distinguish assumptions]
**Tickets (if any):** [source index/revision, selected ticket IDs and acceptance references]
**Approach:** [module ownership, contracts, relevant decisions and source pointers]
**Execution:** [base/working snapshot, task branch, method and reason, authorization,
stated budget if any, execution_mode, route history, selected risks and verification]

### Task 1: [Observable outcome]
**Depends on:** [IDs or none]
**Files / interfaces:** [owned paths, consumed and produced contracts]
**Checks:** [criterion, public boundary, command and expected result]
**State:** [pending / active / blocked / integrated; contract revision, evidence and fix count]
- [ ] [Failing behavior test when appropriate, then minimal implementation]
- [ ] [Run affected checks, integrate and record evidence]

### Remaining risks
[Only material gaps, owning task, required evidence or unresolved decision]
```

For business rules/regressions, plan one behavior test then implementation at a
time. Expectations come from requirements/worked examples, not the implementation.
For mechanical changes plan the edit and focused check. An unrelated environment
failure is not an expected red test. No separate agent, review or commit packet is
required per task; finishing owns the integrated review at the chosen risk level.

Keep mode separate from task status. When logging is enabled retain task_run_id,
event IDs and sequence in this same plan, not a separate state engine. Before
context handoff name the next ready task, unresolved decisions and source/snapshot
pointers. On resume compare actual files and contracts before trusting old evidence.

## Check once and hand off

Self-check acceptance coverage, preserved behavior, compatible interfaces, valid
acyclic prerequisites and evidence for selected risks. Fix concrete gaps and recheck
affected sections. Do not generate a reviewer or another plan review for editorial
changes. A plan should record decisions, not transcribe the implementation.

Link the saved plan. If only planning was requested, stop. If execution is already
authorized, continue through [development-workflow](../development-workflow/SKILL.md)
without a method-selection or per-task approval question. A larger required product
decision remains a real blocker. Use `subagent-driven-development` only when explicitly
selected and preflighted through task-router's optional workflow requirements;
ordinary bounded children are managed by development-workflow.
