# RelayForge Development Plugin

Reusable software development workflows for RelayForge projects across Codex,
Claude Code, ChatGPT, and compatible agent hosts.

## Layout

- `plugin.json` — portable Agent Plugins manifest.
- `.codex-plugin/plugin.json` — Codex compatibility manifest.
- `.claude-plugin/plugin.json` — Claude Code manifest.
- `.agents/plugins/marketplace.json` — repo marketplace manifest for Codex/ChatGPT.
- `.claude-plugin/marketplace.json` — Claude Code marketplace manifest.
- `skills/` — reusable workflows, one directory per skill.
- `skills/task-router/` — stack-neutral L1/Quick, L2/Standard and L3/Large routing.
- `skills/development-workflow/` — proportional Standard/Large implementation.
- `skills/development-workflow/scripts/parallel_worktree.py` — guarded task
  branches and exceptional parallel-worker worktrees.
- `skills/finishing-development/` — minimal checks and user-selected finishing actions.
- `skills/delivery-handoff/` — testing handoff from actual changes and evidence.
- `hooks/hooks.json` — optional Codex lifecycle telemetry hook.
- `scripts/workflow_logger.py` — metadata-only Hook event logger.
- `scripts/analyze_workflow_logs.py` — local timing report generator.
- `scripts/analyze_workflow_benchmark.py` — baseline/candidate benchmark analyzer.
- `AGENTS.md` — repository guidance for Codex contributors.

## Workflow Routing

`task-router` selects Quick, Standard or Large from requirement clarity, scope and
dependency coordination. Risk independently determines verification. Descriptions
identify candidate skills; the selected skill's actual instructions and resources
are checked before use. The router contains no framework/language table.

Quick work stays in the current context. Standard work uses one primary writer
and minimal Spec/Plan/Tasks, merged or inline when appropriate. A settled high-risk
local fix can be Quick with all required risk checks. A single-writer multi-session
task can remain Standard with a persisted plan. Large means durable dependency
coordination, including sequential work; it does not require multiple agents.
Load only needed specialist capabilities. Every mutating route creates or reuses
one task branch; sequential work uses the primary checkout. Large work may
create at most two
detached temporary worktrees only for substantial parallel writers with the
same clean base, non-overlapping paths, and no interface dependency; otherwise
it stays sequential. Verified but uncommitted prerequisites can support sequential
work in the primary checkout; the workflow does not create commits to unlock
parallelism. Small full-stack changes can be Standard. Their verified backend
contract stays inline for the same owner/context; a change of owner/context or
deferred execution requires a persisted ignored handoff.

Each task establishes a lightweight acceptance agreement: observable outcome,
behavior to preserve, relevant failure cases and evidence. Risk is independent of
route size and selects required checks. Existing-project work inspects affected
callers and tests and captures a focused baseline where useful. Large full-stack
work proceeds in small vertical slices, with a verified backend contract handed
to the dependent frontend within each slice.

Verification is part of implementation: reuse passing evidence and run missing
required checks. Finishing reuses the user's existing choices; otherwise it offers
one compact selection, recommending minimal checks and an inline result. Users
can add extra tests, code review, a handoff document, commit and/or push. Required
repository/acceptance gates remain in force; skipped checks stay visible. Full
finishing includes tests, review and handoff, while commit and push each need
explicit authorization. Core execution can
continue sequentially from verified uncommitted work. The separate upstream
per-task workflow has different checkpoint requirements and is not selected just
because a plan or subagent is used.

The optional `skills/finishing-development/scripts/review_package.py` freezes selected
committed and working changes, including staged, untracked and binary files,
without modifying the real index. Use a discovered Python interpreter (`python`,
`python3`, or `py -3`) and Git; this helper and the default workflow need no Bash.
Use it for mixed Git states or a portable independent review, not every local edit.
Older SDD shell helpers remain preserved with their upstream workflow.

## Optional workflow availability

The core workflow loads optional capabilities only when selected for the task.
`skills/task-router/references/optional-workflows.json` declares their required
resources and fallback behavior. The previously missing resources are now bundled:

- `improve-codebase-architecture`: `codebase-design`, `grilling` and
  `domain-modeling`, including their supporting references and original metadata,
  from [Matt Pocock's skills](https://github.com/mattpocock/skills).
- `subagent-driven-development`: the final reviewer template at
  `skills/requesting-code-review/code-reviewer.md`, from
  [obra's superpowers](https://github.com/obra/superpowers). Only this resource is
  bundled; no additional requesting-code-review entrypoint is installed.

These additions resolve the packaged file dependencies. The selected workflow
still needs compatible host tools and authorization for its actions. They add no
default interview, glossary, design-comparison or review phase: routine work keeps
the core route, and referenced resources are read only when needed. Existing and
imported upstream skill files are preserved; no runtime installation occurs.

[Pinned source inventory](third-party/upstream-dependencies.json) records the exact
commits, original paths and Git blob hashes. The upstream MIT licenses are retained
in [Matt Pocock's notice](third-party/mattpocock-LICENSE) and
[superpowers' notice](third-party/obra-LICENSE). Tests verify the imported bytes,
both workflows' file availability, and unresolved or stale dependency declarations.

## Effort and scope defaults

Small tasks use the current context. Multi-session work persists only the needed
agreement, dependency plan and evidence. When review is selected or required,
ordinary changes use a Controller review and high-risk work adds independent
review when available and authorized. Directly related, verifiable structural
improvements are allowed; larger refactors are separate proposals and do not stop
correct in-scope delivery unless they are prerequisites.

Keep one primary implementation context by default. Load only needed references,
reuse valid checks, and reassess after two unsuccessful fixes. The shared review
loop allows at most three rounds per unresolved issue. Honor user time/token
budgets when supplied; do not invent them or remove required checks to meet a
cost target. These skill rules guide behavior; they are not a runtime budget
limiter. Requests involving credentials, production access, destructive actions
or deployment remain subject to host and repository authorization.

Skill selection is model-based. Existing skills may be selected directly by the
host, so the router improves routing but does not provide a hard dispatcher.
The primary agent holds the single Orchestrator role; directly selected workflow
skills infer missing context. Routes adjust when new design or coordination facts
appear, preserving tasks, valid evidence, authorization and cumulative fix counts.
Risk is low/medium/high; legacy normal is read as medium.

## Conversation progress

The five core workflows (`task-router`, `writing-plans`, `development-workflow`,
`finishing-development` and `delivery-handoff`) share a compact progress view in
the conversation, including direct planning or handoff requests: the current
workflow, completed work, the current step, remaining steps and any blocker.
The same view continues across workflow transitions. Failed and skipped steps
remain distinct from completed work; planning-only requests end at the plan.
Updates follow meaningful changes rather than every tool call. The
agent reports its own task state, not a host-verified history of Skill loads;
planned or skipped work is never presented as completed. When intermediate
messages are unavailable, the final response carries the status instead.
This requires no telemetry hook or separate service, but depends on the host
selecting the relevant workflow and displaying intermediate messages.
Standalone specialist Skills do not automatically load these core instructions.
See [conversation progress probes](docs/task-router-test-cases.md#conversation-progress-probes)
for behavioral acceptance; structural tests alone do not establish host behavior.

## Testing handoff

All routes use an inline completion summary by default. A selected handoff
document, explicit testing transfer or repository requirement produces a
Test-Handoff-<task-id>.md; Standard/L2 and Large/L3 alone do not trigger a file.
Changed files, direct/indirect impact, upstream acceptance, test suggestions,
actual development checks, environment, code references and gaps remain separate.

Uncommitted results use scoped content fingerprints or the existing frozen review
package. Same HEAD is insufficient to reuse evidence. Code Availability records
whether the target tester can retrieve that exact result; branch names or hashes
alone do not establish access. Critical missing/failed gates or inaccessible code
block the agreed handoff. ready_with_issues is for testable non-blocking gaps.
Development evidence never substitutes for the testing agent's independent result.

See the [complete specification](docs/relayforge-v2.1-revised-implementation-spec.md)
and [implementation progress](docs/relayforge-v2.1-implementation-progress.md).

## Local Telemetry

Codex desktop users can review and trust the bundled Hook to record local,
metadata-only telemetry for plugin-enabled sessions. It records Hook events,
tool names, timing, and hashed technical identifiers; when the router is used,
it also records its declared route, generic work surfaces, planned Skills, and
declared finishing states. It does not record
prompts, commands, source, patches, tool input/output, credentials, or
environment variables. Codex does not expose a reliable Skill-load event, so
planned Skills are not reported as confirmed Skill usage.

The optional --record-workflow-event stdin mode records bounded, agent-declared
route selections/changes and finishing/handoff summaries without replacing the
Hook protocol. The analyzer keeps these separate from legacy final-line metadata
and host events, detects replays/gaps/conflicts, and never infers missing history.

Logs are written under Codex's plugin data directory and retained for 30 days.
Isolated forward tests can redirect this logger with
`RELAYFORGE_WORKFLOW_LOG_DIR` without changing Codex's managed plugin data.
See [workflow logging](docs/workflow-logging.md) for the event model, limits,
and analysis command. CLI builds do not all expose plugin-bundled Hooks; verify
the source appears in `/hooks` before relying on telemetry. This is not a
portable Claude Code telemetry feature.

Use [the workflow benchmark](docs/workflow-benchmark.md) to compare equivalent
baseline and candidate tasks for paired task outcomes, regressions, duration, reliable token counts and human
rework. Cost targets are optional; unknown or failed quality cannot qualify a
cost-improvement claim.

## Add a skill

Create `skills/<skill-name>/SKILL.md` with front matter like:

```md
---
name: example-workflow
description: A concise description of when this workflow should activate.
---

Describe the workflow, inputs, outputs, boundaries, and verification steps.
```

Keep skills focused on one recognizable user goal. Add `scripts/`, `references/`,
or `assets/` inside the skill directory only when the workflow needs them.

## Validate

```bash
python3 -m json.tool plugin.json >/dev/null
python3 -m json.tool .codex-plugin/plugin.json >/dev/null
python3 -m json.tool .claude-plugin/plugin.json >/dev/null
python3 -m unittest discover -s tests -v
```

No MCP server, credentials, third-party runtime dependencies, or network calls
are configured. The optional Codex Hook uses only the Python standard library.

## Install from this repository

When adding this GitHub repository as a marketplace, use:

```text
https://github.com/mingjw6505/relayforge-development
```

The repository includes marketplace manifests that point to the root plugin
package. If the desktop app cached the previous invalid marketplace, remove or
refresh that marketplace and add the repository again.
