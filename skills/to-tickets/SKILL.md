---
name: to-tickets
description: "Split agreed requirements or a confirmed specification into local delivery tickets when requested or when staged delivery, scheduling or handoff needs a breakdown. Skip existing usable tickets, small local changes and technical implementation planning."
---

# To Tickets

Turn agreed requirements into local Markdown delivery tickets: observable
outcomes, acceptance, scope and delivery dependencies. This is an optional step
before implementation planning, not a prerequisite for every development task.
It needs no product plugin, PRD, requirement-state file or external tracker.

Read and apply [progress display](../task-router/references/progress-display.md).
Reuse the current task when present; ticket-only completion means the breakdown
is finished, not that implementation or verification occurred.

## Select and establish the source

- Use when the user requests tickets, or an authorized development request needs
  separately deliverable slices for scheduling or handoff. Large/L3 alone does
  not require tickets; a small change or one manageable implementation can skip this.
- Reuse suitable existing tickets and their IDs. Do not regenerate a backlog or
  run this skill merely because writing-plans needs technical tasks.
- Read the confirmed specification, existing issue or agreement in the current
  conversation. Record its path, URL/version or a short summary of the agreed
  source when no document exists. Link a PRD, prototype or decision record only
  if available and relevant; do not create missing product artifacts.
- Separate agreed behavior from assumptions. Ask only about unresolved decisions
  that affect scope or acceptance; hold affected tickets while independent slices
  may proceed. Do not invent product behavior or require another plugin to resolve it.

## Decompose delivery outcomes

Prefer independently demonstrable vertical slices with user-visible outcomes.
Include the setup and layers needed for each outcome; do not create frontend,
backend and database tickets by default. Pure technical enablers belong in the
implementation plan unless separately requested as delivery work.

Each ticket records:

- stable ID and title;
- user-visible outcome and acceptance criteria;
- in scope, out of scope and behavior to preserve;
- blocked-by ticket IDs (or none), including external blockers when known;
- source reference and any relevant existing decisions;
- agreement status and unresolved questions.

Number prerequisites before dependents. Verify acceptance coverage, no duplicated
scope, and no missing or cyclic blocking edges. Distinguish delivery dependencies
between tickets from technical prerequisites within a ticket's implementation.

## Store and agree proportionally

Follow the project's ticket convention. Otherwise keep internal tickets under
ignored `.relayforge/tickets/<requirement-slug>/`, verifying it is ignored first.
For a requested shared/versioned deliverable, use the public documentation
convention or `docs/tickets/YYYY-MM-DD-<requirement-slug>/` and verify it is visible
to Git. Do not silently put a shared deliverable under an ignored directory.

Write an `index.md` with the source, ticket-set revision, IDs/links, dependency
order and agreement status, plus one file per ticket. Preserve existing IDs and
update the same set. No artifact register, hash protocol, approval ledger or
product-state schema is required; reference existing records without duplicating them.

Use `ready-for-review` for a draft and `approved` only when user agreement covers
that breakdown. Reuse explicit approval or an existing agreement that already
covers the slices, scope and dependencies. Do not ask again for a formatting-only
decomposition of agreed work. For consequential new scope, priorities or dependency
choices, present the affected proposal and ask for that decision. Silence does
not establish approval. Record the applicable agreement source in the index;
material changes invalidate agreement only for affected tickets/consumers.

Ticket agreement, implementation authorization and delivery completion are
different facts. Creating or approving tickets does not authorize coding,
publication, external tracker updates, commit or push.

## Hand off without a second breakdown

Link the saved index and note its visibility, agreement and remaining blockers.
For a ticket-only request, stop. When implementation is already authorized,
continue through [task-router](../task-router/SKILL.md) for the selected ticket(s),
reusing existing routing context instead of starting a ticket-generation loop.
Route size is determined by the selected implementation, not total backlog size.

[Writing-plans](../writing-plans/SKILL.md) owns code paths, interface contracts,
technical prerequisites, tests and execution task state. It consumes ticket IDs,
scope and acceptance by reference and adds only missing implementation detail.
Tickets own delivery scope and agreement; avoid mirroring technical task state
in the ticket index. Execution and finishing provide actual delivery evidence.
