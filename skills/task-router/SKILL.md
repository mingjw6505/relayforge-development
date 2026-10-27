---
name: task-router
description: Classify implementation work as Quick, Standard, or Large and select the smallest useful set of available capabilities. Use at the start of code, configuration, debugging, container, or cross-surface implementation; skip direct explanations and other requests that need no development workflow.
---

# Task Router

Choose the lightest reliable route before loading implementation guidance. The
router coordinates capabilities; it does not contain framework-specific
development rules.

## Preserve authority

- User instructions and repository rules override plugin defaults.
- Routing never grants permission for credentials, production data, permission
  changes, destructive actions, real deployment, or irreversible external
  effects. Analyze safely, then obtain any authorization the host requires.
- Do not infer permission to commit, push, publish, or deploy from a route.

## Discover the work

Identify only what changes routing decisions:

1. the requested outcome and whether the cause is known;
2. affected work surfaces, using generic labels such as `frontend`, `backend`,
   `data`, `container`, `diagnosis`, `integration`, or `general`;
3. contracts or ordering between those surfaces;
4. risk, reversibility, and the cheapest check that could catch the main
   regression; and
5. test, review, commit, or push actions already requested by the user.

Do not classify from framework names. Inspect the repository and the
descriptions of currently available skills, then select the minimum relevant
capability set. Load a capability only when entering the surface it owns. A new
language or framework skill must be discoverable without editing this router.
If no specialist exists, continue with general repository conventions unless
the missing expertise makes a correct result unsafe; disclose the fallback.
Treat every negative activation boundary in a skill description as a hard
constraint. Do not load a skill for a task it explicitly excludes.
The core development workflow already includes reproduce-before-fix root-cause
work. Do not add a generic debugging skill merely because a bug's cause starts
unknown; select one only when the failure needs techniques beyond that core
flow.

## Choose a route

### Quick

Use Quick only when all are true:

- the target and expected result are clear;
- one local work surface is involved;
- no unknown root cause must be diagnosed;
- no cross-component contract, data compatibility, security boundary, or
  deployment behavior changes; and
- one cheap, focused check can catch the main regression.

Work directly in the current context. Do not create a plan, dispatch an agent,
or load a domain skill by default. Use a specialist only when the small change
genuinely depends on non-obvious domain rules.

Batch the initial file inspection when practical. After editing, run one
focused evidence check; do not repeat equivalent `diff`, status, or file-read
commands once the requested result is already established.

### Standard

Use Standard when any are true and Large does not apply:

- the root cause is unknown;
- several files or modules in one primary surface must change;
- a specialist capability or several ordered steps are needed; or
- integration risk is material but one writer can keep clear ownership.

Load [development-workflow](../development-workflow/SKILL.md), then only the
specialist skills selected from current availability.

### Large

Use Large when any are true:

- two or more work surfaces have interface, data, or release dependencies;
- multiple independently useful outputs need coordinated ownership and order;
  or
- integration risk is too broad for one context to hold the constraints
  reliably.

Load [development-workflow](../development-workflow/SKILL.md). Large means
coordinated full-stack work, not automatically maximum agents or maximum
process.

## Route handoff

Pass the selected route, work surfaces, dependency notes, planned specialist
skills, known risks, and any preselected post-development actions to the next
workflow. Mark the handoff as `full-stack` only when `frontend` and `backend`
are both active surfaces with an implementation dependency between them. For
Standard and Large, `development-workflow` owns implementation.
After any route reaches implementation-complete, use
[finishing-development](../finishing-development/SKILL.md).

Keep the planned specialist list stable through the turn. If the response
announces or loads a specialist as part of this route, include it in `Planned
skills`; use `none` only when no specialist was selected. Do not silently drop
a selected skill from the final metadata.

When this router is used, include exactly one route metadata line in the final
response:

```text
Workflow route: Standard | Work surfaces: diagnosis | Planned skills: none
```

Use `none` when no specialist skill is planned. `Planned skills` lists domain
capabilities selected by this router, not the three core workflow skills. The
line declares a plan; it is not proof that the host loaded those skills.
Emit it as plain text with no trailing spaces or Markdown hard break.
The example values are illustrative, not defaults. Include `data` only for a
real persistence, schema, or query surface; use `integration` for a shared
contract with no data-layer change.
