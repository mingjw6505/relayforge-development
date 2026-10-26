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
- selected specialist capabilities;
- repository rules and known risks; and
- test, review, commit, or push actions the user already requested.

Resolve context from the repository before asking the user to repeat it. Ask
only when a missing choice would change product behavior, public contracts,
persisted data, permissions, security, cost, or blast radius.

## Shared implementation rules

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
do not create implementation agents, formal plans, or review packages by
default.

## Large / full-stack

The main session is the Controller. Before editing, maintain a compact map of:

- each work surface and user-visible outcome;
- dependency and integration order;
- file or component ownership; and
- the check that will prove each surface before integration.

Use additional writers only when their deliverables and write scopes are truly
independent. Never run more than two writers concurrently. Do not run two
writers in the same worktree or on overlapping paths. Children receive only
their scoped outcome, constraints, interfaces, owned paths, and expected
checks; they do not receive the full conversation and may not spawn children.

When safe parallel writers are unavailable, execute surfaces sequentially.
Update dependent workers when a shared contract changes. The Controller owns
integration and reconciles all surface results before declaring implementation
complete.

## Implementation completion

Reach `implementation-complete` only when:

- the requested implementation exists or a precise blocker is known;
- all changed paths have an in-scope reason;
- available minimal checks have a recorded result; and
- unresolved risks and unavailable capabilities are explicit.

Then load [finishing-development](../finishing-development/SKILL.md). Pass its
status inputs and the user's preselected finishing actions. Do not claim full
verification or independent review at this boundary.

An action the user did not mention is unresolved, not skipped. When any of test
verification, code review, commit, or push remains unresolved, stop after
implementation-complete and let `finishing-development` ask its single combined
question. Do not choose an answer on the user's behalf.
