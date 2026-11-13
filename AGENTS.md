# RelayForge Development Plugin

## Project map

This repository packages reusable agent skills, a local MCP progress server and
optional Codex Hook telemetry. It is not a RelayForge application service.

- `skills/`: 19 skill entrypoints plus supporting scripts, references and assets.
  The core workflows are `task-router`, `development-workflow`, `writing-plans`,
  `finishing-development` and `delivery-handoff`.
  `to-tickets` is an optional delivery-breakdown step before technical planning.
- `plugin.json`, `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`:
  portable, Codex and Claude Code metadata.
- `mcp.json` and `.mcp.json`: portable and compatibility progress registrations.
- `progress_panel/`: standard-library Python MCP stdio server and SQLite state.
- `progress_panel/web/`: UI source, locked build dependencies and Node tests.
  `progress_panel/static/panel.html` and `THIRD_PARTY_NOTICES.txt` are shipped outputs.
- `hooks/` and `scripts/`: optional local telemetry, workflow analysis helpers and
  the bundled cross-platform progress launcher.
- `tests/`: workflow, helper, telemetry and skill dependency tests;
  `progress_panel/tests/`: server, state, execution and packaging tests.
- `third-party/`: pinned upstream resources and licenses; `docs/`: detailed contracts.

## Repository expectations

- Keep the root `plugin.json` portable and valid against the Agent Plugins schema.
- Keep Codex compatibility metadata in `.codex-plugin/plugin.json` and Claude Code metadata in `.claude-plugin/plugin.json` aligned with the root manifest.
- Put reusable workflows in `skills/<skill-name>/SKILL.md` with YAML front matter containing `name` and `description`.
- Keep skill descriptions specific enough to define activation boundaries; do not put unrelated workflows in one skill.
- Before every commit whose target branch is `main`, increment the patch component of the plugin version by 1 (for example, `0.1.0` → `0.1.1`). Treat the root `plugin.json` as the source of truth, then update the `version` field in `.codex-plugin/plugin.json` and `.claude-plugin/plugin.json` to the same value.
- Do not commit to `main` when the three plugin manifests have different versions, or when the version has not been incremented for that commit. A commit intended for another branch may follow the normal versioning decision for that branch.
- Validate JSON and Markdown structure before handing off changes.
- Do not add MCP servers, hooks, credentials, or external dependencies unless the feature explicitly requires them.

## Workflow and documentation

- Read the affected skill and its needed references before changing its contract.
  Keep routing, implementation, planning, finishing and handoff guidance consistent.
  Route size and risk are separate; small edits do not need a formal plan or agents.
- Keep `to-tickets` independent of product-plugin files, tools and state schemas.
  Accept agreed conversation requirements or existing specifications/issues.
  Select it only for requested/useful delivery breakdowns; existing tickets,
  small changes and Large/L3 alone must not trigger mandatory ticket generation.
- Tickets own delivery IDs, scope, acceptance, dependencies and agreement.
  `writing-plans` references these and owns technical tasks, paths, contracts,
  checks and execution state. Preserve IDs, avoid duplicate breakdowns/status
  ledgers, and resolve affected scope changes without repeating prior approvals.
  Ticket agreement does not imply implementation or publication authorization.
- Preserve the single-primary-writer default. Optional workflows do not add default
  phases or authorize delegation, commit, push or deployment beyond host/user policy.
- Keep README setup, layout and validation commands aligned with actual files.
  Detailed progress and telemetry behavior belongs in `docs/progress-panel.md` and
  `docs/workflow-logging.md`; do not turn historical examples into current test evidence.
- Preserve pinned upstream bytes and licenses. Intentional vendor updates must
  update `third-party/upstream-dependencies.json` and pass its integrity checks.
- Keep internal plans and local artifacts in the established ignored locations
  (`.relayforge/`, `.codex-log/`, `docs/relayforge/`); verify visibility for requested
  public deliverables. Never include user logs, credentials or machine-specific paths.
- Internal tickets default to `.relayforge/tickets/`; requested shared/versioned
  sets follow public project conventions or `docs/tickets/`. Verify ignore status
  before writing; do not silently place shared tickets in ignored `docs/relayforge/`.

## Progress panel and telemetry

- Keep `mcp.json` and `.mcp.json` equivalent apart from portable schema/type fields.
  Preserve plugin-relative `cwd: "./"` and the shared `./scripts/start_progress`
  entrypoint. Ship both the executable POSIX script and matching Windows `.exe`;
  startup must probe Python 3.11+ without per-machine configuration or runtime downloads.
  Launcher source changes require rebuilding the Windows artifact and its build record
  with `scripts/build_progress_launcher.py`, then checking reproducible bytes.
  Go is a launcher development tool only; preserve its bundled runtime license.
- Keep server runtime dependencies in the Python standard library. npm packages
  are for UI development; the shipped UI must work without runtime npm or a CDN.
- Edit UI source under `progress_panel/web/src/`, then rebuild the shipped HTML
  and license notices. Rebuild on version changes too: the UI embeds `plugin.json`
  version. Do not hand-edit generated bundles or omit third-party license notices.
- Preserve task-scoped UUIDs, revision conflict checks, retry behavior and immutable
  terminal states. Never introduce a latest-task fallback or synthesize load receipts.
- A Skill-load receipt proves instruction reading, not execution or success.
  Agent-declared progress, actual verification and Hook events remain distinct.
  Missing MCP tools/UI must allow a concise text fallback.
- Keep state and telemetry local and bounded. Use temporary directories or
  `RELAYFORGE_PROGRESS_DATA_DIR` / `RELAYFORGE_WORKFLOW_LOG_DIR` for isolated checks;
  do not inspect real user logs to populate cards or tests.

## Verification

Choose checks for the changed surface and reuse valid evidence. For documentation
edits, check local links, Markdown fences, command accuracy and `git diff --check`.
Do not install tools or rebuild the UI solely for prose changes.

Run the following checks after changing plugin metadata or skills (commands assume
the repository root and Python 3.11+; Windows may use `py -3` or `python`):

```bash
python3 -m json.tool plugin.json >/dev/null
python3 -m json.tool .codex-plugin/plugin.json >/dev/null
python3 -m json.tool .claude-plugin/plugin.json >/dev/null
python3 -m unittest discover -s tests -v
```

For registration changes, also validate `mcp.json` and `.mcp.json` with
`python3 -m json.tool`. For server, state or registration changes, run:

```bash
python3 -m pytest progress_panel/tests
python3 -m mypy --strict progress_panel/state.py progress_panel/server.py progress_panel/skills.py
```

For bootstrap changes run the Go launcher tests and reproducible build check in
`scripts/progress_launcher/README.md`, plus `python3 scripts/check_progress.py` and
the registered entrypoint with `--doctor` (use `.exe` explicitly on Windows).
Retain the optional legacy Node launcher checks while that compatibility entry
exists: `node --test scripts/progress-launcher.test.cjs` and
`node scripts/progress-launcher.cjs --doctor`. An isolated doctor does not verify
real state-directory permissions or host UI rendering.

For UI source, build tooling or embedded version changes, run:

```bash
npm --prefix progress_panel/web ci --ignore-scripts
npm --prefix progress_panel/web run build
npm --prefix progress_panel/web test
```

`pytest` and `mypy` are development tools. Missing tools or host-level integration
checks must be reported as gaps, not passing evidence. Python/Node checks do not
prove inline rendering works on every host; use the documented host probes when
changing that integration.

Before a `main` commit, also verify that all plugin manifest versions match:

```bash
python3 - <<'PY'
import json
from pathlib import Path

paths = [Path("plugin.json"), Path(".codex-plugin/plugin.json"), Path(".claude-plugin/plugin.json")]
versions = {json.loads(path.read_text())["version"] for path in paths}
assert len(versions) == 1, f"manifest versions differ: {versions}"
print(f"Plugin version: {versions.pop()}")
PY
```
