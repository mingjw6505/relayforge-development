---
name: task-router
description: Route implementation by requirement clarity, task size, dependencies, risk and cost. Combine specification, test-first work and delegation as needed; skip explanations and planning-only requests.
---

# Task Router

Choose the lightest reliable route. User instructions, repository rules and host
permissions take precedence. A route does not authorize commit, push, deployment
or other external/destructive actions.

The primary agent is the single coordinator. This is a recommended entrypoint,
not a hard dispatcher: hosts may select a skill directly. That skill fills missing
context without restarting routing or creating a second coordinator.

For implementation tasks, read and apply the shared
[progress display](references/progress-display.md). Prefer the inline card;
keep chat focused on useful findings, blockers and the final result.
When tools are missing or a card failure is reported, follow the conditional
[environment recovery](references/progress-environment.md): diagnose once, prefer
an existing runtime, then assist authorized repair without blocking development.

## Inspect once, decide

Resolve from the request and affected code:

- observable outcome, behavior to preserve and unresolved product decisions;
- work surfaces, prerequisite contracts and shared ownership;
- whether implementation fits one context or needs durable coordination;
- risk, the cheapest meaningful evidence, exclusions and any stated budget.

Read local facts before asking. Ask only for consequential choices that remain
unknown; continue independent work while dependent behavior waits. Diagnose
technical uncertainty with a bounded reproduction/experiment. A prototype can
settle a design question but is not production acceptance evidence. Once settled,
continue authorized work without a routine plan/method/phase confirmation.

Risk is separate from size: low for mechanical local edits, medium for business
behavior, high for permissions, concurrency, transactions, migrations or costly
irreversible failure. Read legacy normal as medium. A small sensitive diff is not
low risk, but can still be Quick when its contract and fix are settled. Read
[acceptance and risk](../development-workflow/references/acceptance-and-risk.md)
only for ambiguity, material boundaries or an effort-limit decision.

## Optional delivery breakdown

Ticket-only requests go to [to-tickets](../to-tickets/SKILL.md) and stop after
the breakdown. Technical planning-only requests go to writing-plans. Neither
request authorizes implementation.

For implementation, reuse existing tickets and agreements. When agreed requirements
need distinct delivery slices for scheduling or handoff, select to-tickets before
technical planning; it also accepts agreement from the current conversation without
a product plugin or formal specification file. Skip it for a small local change,
usable existing tickets or work manageable directly in one plan. L3 alone does not
require tickets. Reuse prior approval; ask only about consequential unresolved
choices, not the internal route. After breakdown, route the selected ticket(s)
using this same task context, without generating tickets again.

Tickets define delivery outcomes, scope, acceptance and delivery dependencies.
Writing-plans adds implementation paths, contracts, technical tasks and checks
without duplicating the ticket backlog. Preserve IDs and acceptance by reference.

## Route and compose

| Route | When | Execution |
| --- | --- | --- |
| Quick / L1 | Clear local change, known cause and settled behavior; no additional design or durable dependency coordination needed | Work inline, then finish with risk-selected checks. No mandatory plan, agent, worktree or handoff file. |
| Standard / L2 | Needs minimal specification/design; one primary writer can manage it, including across sessions | Use development-workflow; persist only necessary decisions and tasks. |
| Large / L3 | Substantial tasks or contexts need persistent contract, ownership and dependency coordination | Use development-workflow with a durable plan; delegation and parallelism remain optional. |

Once selected, declare the route as `execution_mode` on the task's progress card
when supported. Declare selected SDD/TDD/coordination phase tracks separately
and use `details.current` for the actual action. Follow the
[progress contract](references/progress-panel.md#mode-method-progress-and-concrete-action);
loading a workflow neither selects a mode nor advances a method phase.

Do not size work from framework names, layer/file counts or missing product intent.
Resolve the intent first. Choose methods independently:

A high-risk local fix can be L1 with its required tests and review. A single-writer
multi-session feature can be L2. Multiple stacks do not imply multiple agents.
Unsettled product intent is a decision gap, not a reason to increase route size.

- **SDD (specification-driven):** use agreed conversation/acceptance for small work;
  persist decisions and dependencies for multi-session, deferred or handed-off work.
  Technical planning-only requests go directly to writing-plans and stop with the
  plan; delivery-breakdown requests use the optional ticket step above.
- **TDD:** prefer a failing behavior test then one implementation slice for business
  rules, bug regressions and high-risk invariants. Mechanical edits need a focused
  result check, not an invented unit test. Development-workflow owns the loop.
- **Subagents:** stay inline unless bounded investigation, implementation or review
  offers a clear benefit over dispatch/context/integration cost. Parallel writers
  additionally need ready independent tasks and safe isolation.

Using SDD or a child does not select `subagent-driven-development`. Its heavier
per-task workflow is only for an explicit user choice after availability checks.

## Adjust when facts change

Escalate L1 to L2 for newly needed design/contracts or linked scope; L2 to L3 for
durable coordination. De-escalate L3 to L2 when coordination is no longer useful,
or L2 to L1 when only a settled local edit remains. Strong dependencies may require
sequential L3, not a downgrade. Slow tools, file counts and session boundaries
alone do not change the route.

Before affected dispatch, record the reason, new mode and invalidated consumers.
Reuse analysis, work, valid evidence, task IDs, authorization and cumulative fix
counts. Stop affected consumers after contract changes; preserve independent work.
Read [route adjustments](references/route-adjustments.md) for durable recovery or
event emission. Do not load the full development engine just to execute L1.

## Select capabilities lazily

Find candidates from available descriptions. Read the selected skill's actual
instructions and required resources before invoking it; do not load every skill
or its references at routing time. Reuse that inspection until its source changes.
Respect negative activation boundaries and invocation policies. Select only
specialists needed by the current task; new stacks must work without a router edit.

Bundling optional dependencies adds no default phase. Routine clarification, local
structural fixes and ordinary review stay in the core route; load a bundled
dependency only for a selected workflow or its specifically requested capability.

[Optional workflow requirements](references/optional-workflows.json) declares
required resources for the architecture and per-task agent workflows.
Check those resources when considering either workflow. Missing dependencies or
incompatible mandatory side effects make it unavailable for this task. Disclose
the limitation and use compatible core guidance where authorized; never claim an
unavailable skill ran, install it implicitly, or modify upstream skills. If the
user's required method cannot be honored, resolve that specific choice.

Ordinary reproduce-and-fix work is already built in. Add systematic debugging
only when the problem needs more than that focused evidence loop.

## Continue

For Quick, reuse a branch dedicated to this task; otherwise follow
[task-branch](../development-workflow/references/task-branch.md) before editing.
Never auto-stash unrelated changes or create a Quick worktree. Batch nearby reads,
make the change and run the focused check once. Existing tests unrelated to a
mechanical edit need not run unless repository rules require them. Once this
evidence establishes the result, do not add equivalent assertions/status reads.

For Standard/Large, pass route, acceptance, unresolved decisions, surfaces,
dependencies, selected skills, risk/checks, spec/test/delegation choice and existing
authorization to [development-workflow](../development-workflow/SKILL.md). Keep it
in context, not a new form. Mark `full-stack` only for an actual frontend/backend
implementation dependency. Parallel candidates are not permission to dispatch.
After implementation or a blocker, use
[finishing-development](../finishing-development/SKILL.md).

Keep communication proportional; do not make the user approve internal routing.
Keep route decisions, work surfaces and selected skills in task context or an
existing plan/checkpoint. Structured declarations use execution_mode L1/L2/L3
and route_policy_version v2.1. Do not require a routing footer in the final reply.

Before replying after an implementation route, including Quick, read and apply
finishing-development using the evidence already collected. This closes the same
task; it does not automatically start another test/review cycle. Finishing reuses
existing choices, or offers one selection of optional work, distinct from
approving implementation or internal routing. All routes default to minimal
finishing; extra tests, review and a handoff file run only when selected or required.
