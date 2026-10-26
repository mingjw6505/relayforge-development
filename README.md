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
- `skills/task-router/` — stack-neutral Quick/Standard/Large routing.
- `skills/development-workflow/` — proportional Standard/Large implementation.
- `skills/finishing-development/` — one finishing choice for tests, review, commit, and push.
- `hooks/hooks.json` — optional Codex lifecycle telemetry hook.
- `scripts/workflow_logger.py` — metadata-only Hook event logger.
- `scripts/analyze_workflow_logs.py` — local timing report generator.
- `scripts/analyze_workflow_benchmark.py` — baseline/candidate benchmark analyzer.
- `AGENTS.md` — repository guidance for Codex contributors.

## Workflow Routing

`task-router` classifies development work as Quick, Standard, or Large from
generic work surfaces and dependencies. It discovers the smallest useful
capability set from the repository and currently available Skill descriptions;
the core router does not contain a framework or language table.

Quick work stays in the current context. Standard work uses one primary writer
and only needed specialist capabilities. Large/full-stack work coordinates
surface ownership and dependencies, allowing at most two non-overlapping
writers when parallelism is safe.

After implementation, the plugin asks once which remaining actions to run:
full test verification, code review, commit, and push. Actions already selected
in the initial request are not asked again. Skipped gates remain visible as
unverified or unreviewed. Requests involving permissions, credentials,
sensitive or production data, destructive operations, deployment, or
irreversible external effects remain subject to host and repository rules.

Skill selection is model-based. Existing skills may be selected directly by the
host, so the router improves routing but does not provide a hard dispatcher.

## Local Telemetry

Codex desktop users can review and trust the bundled Hook to record local,
metadata-only telemetry for plugin-enabled sessions. It records Hook events,
tool names, timing, and hashed technical identifiers; when the router is used,
it also records its declared route, generic work surfaces, planned Skills, and
declared finishing states. It does not record
prompts, commands, source, patches, tool input/output, credentials, or
environment variables. Codex does not expose a reliable Skill-load event, so
planned Skills are not reported as confirmed Skill usage.

Logs are written under Codex's plugin data directory and retained for 30 days.
Isolated forward tests can redirect this logger with
`RELAYFORGE_WORKFLOW_LOG_DIR` without changing Codex's managed plugin data.
See [workflow logging](docs/workflow-logging.md) for the event model, limits,
and analysis command. CLI builds do not all expose plugin-bundled Hooks; verify
the source appears in `/hooks` before relying on telemetry. This is not a
portable Claude Code telemetry feature.

Use [the workflow benchmark](docs/workflow-benchmark.md) to compare equivalent
baseline and candidate tasks for duration, token availability, human decisions,
and selected quality-gate evidence.

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
