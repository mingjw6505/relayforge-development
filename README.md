# RelayForge Development Plugin

Reusable software development workflows for RelayForge projects across Codex,
Claude Code, ChatGPT, and compatible agent hosts.

## Layout

- `plugin.json` — portable Agent Plugins manifest.
- `.codex-plugin/plugin.json` — Codex compatibility manifest.
- `.claude-plugin/plugin.json` — Claude Code manifest.
- `.agents/plugins/marketplace.json` — repo marketplace manifest for Codex/ChatGPT.
- `.claude-plugin/marketplace.json` — Claude Code marketplace manifest.
- `mcp.json` / `.mcp.json` — portable and compatibility registrations for the
  bundled `relayforge-progress` stdio server.
- `skills/` — reusable workflows, one directory per skill.
- `skills/task-router/` — stack-neutral L1/Quick, L2/Standard and L3/Large routing.
- `skills/to-tickets/` — optional delivery breakdown from agreed requirements.
- `skills/development-workflow/` — proportional Standard/Large implementation.
- `skills/development-workflow/scripts/parallel_worktree.py` — guarded task
  branches and exceptional parallel-worker worktrees.
- `skills/finishing-development/` — minimal checks and user-selected finishing actions.
- `skills/delivery-handoff/` — testing handoff from actual changes and evidence.
- `hooks/hooks.json` — optional Codex lifecycle telemetry hook.
- `scripts/workflow_logger.py` — metadata-only Hook event logger.
- `scripts/analyze_workflow_logs.py` — local timing report generator.
- `scripts/analyze_workflow_benchmark.py` — baseline/candidate benchmark analyzer.
- `scripts/start_progress` / `scripts/start_progress.exe` — automatic platform
  entrypoints; Python detection runs at startup without configuration edits.
- `scripts/progress_launcher/` — native launcher source, build record and license;
  `scripts/build_progress_launcher.py` rebuilds or verifies the Windows artifact.
- `scripts/check_progress.py` — optional MCP startup and discovery probe.
- `progress_panel/` — Python MCP server, SQLite task state and bundled inline UI.
- `progress_panel/web/` — UI source, build tooling and Node tests.
- `progress_panel/tests/` — progress state, protocol, execution and packaging tests.
- `tests/` — workflow helpers, telemetry, benchmarks and skill dependency checks.
- `third-party/` — pinned upstream inventory and retained licenses.
- `docs/` — workflow specifications, setup, probes and handoff examples.
- `AGENTS.md` — repository guidance for Codex contributors.

## Skill index

The package contains 19 skill entrypoints. Select capabilities for the actual
task; the core route does not automatically invoke every bundled skill.

| Area | Skills and purpose |
| --- | --- |
| Core workflow | [task-router](skills/task-router/SKILL.md) selects the route; [development-workflow](skills/development-workflow/SKILL.md) implements Standard/Large work; [writing-plans](skills/writing-plans/SKILL.md) persists needed decisions; [finishing-development](skills/finishing-development/SKILL.md) closes work; [delivery-handoff](skills/delivery-handoff/SKILL.md) prepares selected testing transfers. |
| Optional delivery breakdown | [to-tickets](skills/to-tickets/SKILL.md) turns agreed requirements into local delivery tickets before technical planning when requested or needed for staged delivery, scheduling or handoff. |
| Frontend | [frontend-design](skills/frontend-design/SKILL.md) guides visual direction; [frontend-patterns](skills/frontend-patterns/SKILL.md) handles nontrivial React/Next.js architecture; [vercel-react-best-practices](skills/vercel-react-best-practices/SKILL.md) provides performance guidance. |
| Backend and packaging | [java-springboot](skills/java-springboot/SKILL.md), [sql-optimization](skills/sql-optimization/SKILL.md) and [multi-stage-dockerfile](skills/multi-stage-dockerfile/SKILL.md). |
| Diagnosis and review | [systematic-debugging](skills/systematic-debugging/SKILL.md) handles problems beyond a focused reproduce-and-fix loop; [code-review](skills/code-review/SKILL.md) reviews changes from a fixed Git point with parallel reviewers when compatible with host policy. |
| Architecture and terminology | [codebase-design](skills/codebase-design/SKILL.md), [domain-modeling](skills/domain-modeling/SKILL.md), [grilling](skills/grilling/SKILL.md) and [improve-codebase-architecture](skills/improve-codebase-architecture/SKILL.md). |
| Optional execution method | [subagent-driven-development](skills/subagent-driven-development/SKILL.md) provides the explicitly selected upstream per-task agent workflow. |

`skills/requesting-code-review/code-reviewer.md` is a supporting reviewer template,
not another skill entrypoint. Optional methods require their referenced resources,
compatible host tools and authorization; see [availability](#optional-workflow-availability).

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

## Delivery tickets and implementation plans

`to-tickets` is an optional development entry step. It accepts a confirmed
specification, an existing issue or agreed requirements from the conversation;
no RelayForge Product plugin, PRD, requirement state or approval ledger is needed.
It supports conditional automatic selection as well as explicit invocation.

When a breakdown is useful, the flow is:

```text
Agreed requirements → to-tickets (optional delivery breakdown)
                   → task-router (selected tickets or direct requirements)
                   → writing-plans (when technical planning needs persistence)
                   → development-workflow → finishing-development
```

The router can select the optional step, then reuse the same task context to
route the chosen tickets. Ticket-only requests end with the breakdown; technical
planning-only requests end with the plan. Quick work can implement directly.
Existing suitable tickets are reused; route size alone never requires tickets.

| Responsibility | `to-tickets` | `writing-plans` |
| --- | --- | --- |
| Outcome | Independently demonstrable delivery slices | Technical approach for selected scope |
| Content | Stable ticket IDs, scope, acceptance, delivery dependencies and agreement | Code paths, contracts, technical prerequisites, checks and execution state |
| Existing tickets | Reuse and update the same set | Reference their IDs and acceptance; add only missing technical detail |
| Without tickets | Create only when a breakdown is requested or useful | Plan directly from agreed requirements |

Internal tickets default to ignored `.relayforge/tickets/<requirement-slug>/`.
Requested shared/versioned tickets follow project conventions or default to
`docs/tickets/YYYY-MM-DD-<requirement-slug>/`; verify Git visibility before delivery.
Each set has an index and ticket files. Reuse existing agreement; resolve only
consequential new decisions. Ticket agreement does not authorize implementation,
external publication, commit or push. Technical plans do not duplicate ticket
scope or maintain a second delivery-status ledger.

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

## Development progress

Codex desktop can display a compact inline card at the start of development work.
The bundled local MCP server displays current work, changes, verification and blockers;
the card refreshes itself. Selected bundled Skills can be loaded through the MCP
tool to produce actual instruction-read receipts. External Skills, direct file reads
and host-provided instructions actually used for the task are synchronized through
`skill_uses` on progress start/update. The compact list merges names; details distinguish
tool reads from Agent use declarations. Unreported use cannot be captured automatically.
These records remain separate from declared work and verification. Python 3.11+
with sqlite3 is required; Node, Go, runtime npm packages, an API key, Hook trust
and raw logs are not required. See [setup and limits](docs/progress-panel.md).

The registered command is `./scripts/start_progress` on every system. The package
ships a POSIX shell entrypoint for macOS/Linux and a matching Windows executable;
Windows process resolution selects `start_progress.exe`. Each startup probes
Python 3.11+ with SQLite support: `python3`, then `python` on macOS/Linux;
`py -3`, `python`, then `python3` on Windows, followed by versioned 3.15 through
3.11 candidates on each platform. `RELAYFORGE_PYTHON` strictly selects a single
executable path when set. Failed or unsupported candidates are
skipped, including a Store alias returning 9009. At least one working candidate
must be available through the host's PATH.

No setup script, registration rewrite, machine-specific path, Node runtime or
Go installation is required. Updates ship the same registration and both
entrypoints, so there is no per-machine configuration to repeat. The bootstrap
never installs Python or changes PATH. See [automatic startup and diagnostics](docs/progress-panel.md#automatic-startup).

The registered entrypoint also supports `--doctor` for isolated package, tools,
HTML and SQLite checks: use `./scripts/start_progress --doctor` on macOS/Linux
or `.\scripts\start_progress.exe --doctor` in PowerShell. It keeps host loading,
rendering and real state permissions explicitly unverified. The conditional
[environment recovery workflow](skills/task-router/references/progress-environment.md)
notifies once and assists authorized repairs without blocking development.

For optional diagnostics, run `python3 scripts/check_progress.py` on macOS/Linux
or `py -3 scripts/check_progress.py` on Windows (use `python` if needed). This
checks real MCP startup and tool discovery without changing configuration or
creating a task. It does not prove inline rendering. Reload the updated plugin
and check its tools in a new chat. Hosts without MCP Apps can use skills and text
updates. Launcher source and reproducible build instructions are in
[scripts/progress_launcher](scripts/progress_launcher/README.md).

The tools create (`start_progress`), update (`update_progress`) and reopen
(`open_progress`, on request) a task card. `load_progress_skill` reads a selected
bundled skill and records its content hash; `read_progress` serves the bound card.
Usage declarations carry only a qualified Skill name and read channel, never file
paths or contents. They are additive and task-scoped; they do not select a workflow
or manufacture a load receipt. See the [record contract](skills/task-router/references/progress-panel.md).
Writes retain the task's `run_id` and returned revision. State is local under the
plugin data directory or the platform fallback; isolated checks can use
`RELAYFORGE_PROGRESS_DATA_DIR`. The card is separate from Hook telemetry.

The five core workflows share one task's progress across transitions. Chat carries
useful findings, blockers and the final result, without a duplicate checklist or
fixed metadata footer. When the card is unavailable, concise plain-language
updates provide a fallback. Planned work and Skill names are not execution evidence.
See [progress display probes](docs/task-router-test-cases.md#progress-display-probes).

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
tool names, timing, and hashed technical identifiers. It does not parse assistant
replies for routing or finishing metadata. It does not record
prompts, commands, source, patches, tool input/output, credentials, or
environment variables. Codex does not expose a reliable Skill-load event, so
planned Skills are not reported as confirmed Skill usage.

The optional --record-workflow-event stdin mode records bounded, agent-declared
route selections/changes and finishing/handoff summaries without replacing the
Hook protocol. The analyzer still reads historical final-line metadata separately
from structured declarations and host events, detects replays/gaps/conflicts, and
never infers missing history. The progress panel does not automatically write to
this telemetry interface.

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

## Develop and validate

Use Python 3.11+ for the progress server. The Python runtime uses only the standard
library. The progress tests and strict type checks use the development-only
`pytest` and `mypy` tools. UI development needs Node.js and npm; its locked
dependencies are build tools, not runtime installation requirements.

From the repository root, validate metadata and run the workflow/helper suite:

```bash
python3 -m json.tool plugin.json
python3 -m json.tool .codex-plugin/plugin.json
python3 -m json.tool .claude-plugin/plugin.json
python3 -m json.tool mcp.json
python3 -m json.tool .mcp.json
python3 -m unittest discover -s tests -v
node --test scripts/progress-launcher.test.cjs
```

For progress server, state or registration changes, run:

```bash
python3 -m pytest progress_panel/tests
python3 -m mypy --strict progress_panel/state.py progress_panel/server.py progress_panel/skills.py
```

For UI source or build changes, install the locked development dependencies, build
the shipped HTML and license notices, and run the UI tests:

```bash
npm --prefix progress_panel/web ci --ignore-scripts
npm --prefix progress_panel/web run build
npm --prefix progress_panel/web test
```

On Windows, `py -3` or `python` can replace `python3` in development commands after
checking the interpreter version. This does not change the MCP launch requirement.
Check Markdown links/fences and run `git diff --check` before handoff. Changes to
skills should also pass the structure and dependency checks in the root test suite.

Before every commit targeting `main`, increment the root manifest's patch version
once and synchronize both compatibility manifests, even for a documentation-only
commit. If preparing a version change, rebuild the UI because its build embeds
the root plugin version. See [AGENTS.md](AGENTS.md) for contributor gates.

The bundled MCP server and optional Codex Hook use local standard-library Python
code. Neither needs credentials or makes network calls. npm installation is a
development step; the built UI and third-party license notices ship in the package.

## Install from this repository

When adding this GitHub repository as a marketplace, use:

```text
https://github.com/mingjw6505/relayforge-development
```

The repository includes marketplace manifests that point to the root plugin
package. If the desktop app cached the previous invalid marketplace, remove or
refresh that marketplace and add the repository again.
