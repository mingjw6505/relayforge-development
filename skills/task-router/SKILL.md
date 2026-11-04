---
name: task-router
description: Route implementation by requirement clarity, task size, dependencies, risk and cost. Combine specification, test-first work and delegation as needed; skip explanations and planning-only requests.
---

# Task Router

Choose the lightest reliable route. User instructions, repository rules and host
permissions take precedence. A route does not authorize commit, push, deployment
or other external/destructive actions.

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

Risk is separate from size: low for mechanical local edits, normal for business
behavior, high for permissions, concurrency, transactions, migrations or costly
irreversible failure. A small sensitive diff is not low risk. Read
[acceptance and risk](../development-workflow/references/acceptance-and-risk.md)
only for ambiguity, material boundaries or an effort-limit decision.

## Route and compose

| Route | When | Execution |
| --- | --- | --- |
| Quick | Clear local low-risk change; known cause; no shared contract, data compatibility, security or deployment change; one focused check suffices | Work inline, then finish. No plan, agent or domain skill by default. |
| Standard | Bounded work fits one implementation context; Quick does not apply | Use development-workflow with one writer. A small full-stack feature or high-risk one-line fix can be Standard. |
| Large | Multiple contexts/sessions or several substantial outcomes require persistent dependency coordination | Use development-workflow with a durable plan; delegate only if worthwhile. |

Do not size work from framework names, layer/file counts or missing product intent.
Resolve the intent first. Choose methods independently:

- **SDD (specification-driven):** use agreed conversation/acceptance for small work;
  persist decisions and dependencies for multi-session, deferred or handed-off work.
  Planning-only requests go directly to writing-plans and stop with the plan.
- **TDD:** prefer a failing behavior test then one implementation slice for business
  rules, bug regressions and high-risk invariants. Mechanical edits need a focused
  result check, not an invented unit test. Development-workflow owns the loop.
- **Subagents:** stay inline unless bounded investigation, implementation or review
  offers a clear benefit over dispatch/context/integration cost. Parallel writers
  additionally need ready independent tasks and safe isolation.

Using SDD or a child does not select `subagent-driven-development`. Its heavier
per-task workflow is only for an explicit user choice after availability checks.

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
When this router ran, include exactly one plain final metadata line:

```text
Workflow route: Standard | Work surfaces: diagnosis | Planned skills: none
```

Values are illustrative. Surfaces are `frontend`, `backend`, `data`, `container`,
`diagnosis`, `integration` or `general`; `full-stack` is a dependency marker,
and tests are evidence, not separate work-surface labels. List selected domain skills,
excluding core workflow skills; `none` means none selected. Preserve announced
selections and explain later changes instead of silently dropping them. This line
is a declared plan, not proof of skill loading. No trailing spaces/hard break.

Before replying after an implementation route, including Quick, read and apply
finishing-development using the evidence already collected. This closes the same
task; it does not start another test/review cycle or approval question.
