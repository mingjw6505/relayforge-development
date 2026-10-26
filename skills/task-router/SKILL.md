---
name: task-router
description: Classify software development work as Quick or Standard and select the minimal relevant RelayForge development skills. Use at the start of development work that needs workflow selection, including full-stack tasks; do not use for direct answers that need no implementation workflow.
---

# Task Router

Choose the lightest reliable workflow before loading other plugin skills. This
skill orchestrates existing skills; it does not replace their instructions.

## Boundaries

- Keep existing repository rules and explicit user instructions first.
- Do not load skills just because they are available. Load each selected skill
  only when its work surface is present.
- Do not automatically create a plan, delegate to subagents, request an
  independent review, or make a Git commit.
- Lifecycle hooks record local tool timing automatically. They do not expose a
  reliable event for actual skill loading, so never describe planned skills as
  platform-confirmed usage data.

## Risk Check

Before classifying, look for permissions, credentials, sensitive or production
data, destructive operations, deployments, or irreversible external effects.
These do not become ordinary Standard work. Follow the host's approval rules
and obtain explicit authorization when it is required.

## Quick

Use Quick when the target is clear, the change is local and low risk, and a
small relevant check can validate it. Work directly:

1. Inspect only the files needed for the request.
2. Make the focused change or answer.
3. Run the smallest relevant verification.
4. Report what changed and what was verified.

Do not load another skill by default. A clear single-line fix, a local text
change, or a direct code explanation are typical Quick work.

## Standard

Use Standard for all other non-high-risk development work, including full-stack
features, cross-module changes, and complex tasks. Larger scope alone does not
require a heavier workflow in this plugin version.

1. Identify the real work surfaces and dependencies.
2. Select the relevant skills below. Multiple skills are allowed when each
   owns a distinct part of the task.
3. Load skills in dependency order. Avoid reading every candidate skill at
   once.
4. Implement as one coordinated task, following repository conventions.
5. Run validation that covers the changed surfaces and state any gaps.

When this router is used, finish the response with one exact metadata line:

```text
Workflow route: Standard | Planned skills: backend-patterns, frontend-patterns
```

For Quick work, use `Workflow route: Quick | Planned skills: none`. List only
skills selected by this router. The local Hook extracts only this line for
telemetry and discards the surrounding response; planned skills are not proof
that the host loaded them.

Use these existing skills when applicable:

| Work surface | Skill |
| --- | --- |
| Unexpected behavior, failing tests, or a bug with an unclear cause | `systematic-debugging` |
| Node.js, Express, or Next.js server work | `backend-patterns` |
| Backend architecture, API, data model, integration, or scalability review | `backend-design-review` |
| SQL execution plans, indexes, slow queries, pagination, or batch processing | `sql-optimization` |
| React or Next.js UI state, rendering, or performance work | `frontend-patterns` |
| New UI visual direction or a substantial UI redesign | `frontend-design` |
| Docker image construction, cache, size, or image hardening work | `multi-stage-dockerfile` |

The following are explicit-only workflows. Use them only when the user asks
for that outcome, or when another applicable repository rule explicitly
requires it:

| Requested outcome | Skill |
| --- | --- |
| An implementation plan | `writing-plans` |
| Subagent-based implementation | `subagent-driven-development` |
| Independent code review | `requesting-code-review` |
| A commit message or commit workflow | `caveman-commit` |

When skill guidance conflicts, prefer explicit user instructions, repository
rules, and the established architecture. Do not infer Git, deployment, or
other external-operation authorization from the selected workflow.
