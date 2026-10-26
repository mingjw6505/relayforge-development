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
- `skills/task-router/` — light Quick/Standard workflow selection for Codex.
- `hooks/hooks.json` — optional Codex lifecycle telemetry hook.
- `scripts/workflow_logger.py` — metadata-only Hook event logger.
- `scripts/analyze_workflow_logs.py` — local timing report generator.
- `AGENTS.md` — repository guidance for Codex contributors.

## Workflow Routing

`task-router` classifies development work as Quick or Standard before selecting
the existing skills needed for the task. Quick work stays direct and uses only
minimal verification. Standard work can combine relevant backend, frontend,
SQL, Docker, and debugging skills in dependency order.

Planning, subagent development, independent review, and commit workflows are
used only when explicitly requested. Requests involving permissions,
credentials, sensitive or production data, destructive operations, deployment,
or irreversible external effects remain subject to the host's approval rules.

Skill selection is model-based. Existing skills may be selected directly by the
host, so the router improves routing but does not provide a hard dispatcher.

## Local Telemetry

Codex users can review and trust the bundled Hook to record local,
metadata-only telemetry for plugin-enabled sessions. It records Hook events,
tool names, timing, and hashed technical identifiers; when the router is used,
it also records its declared route and planned Skills. It does not record
prompts, commands, source, patches, tool input/output, credentials, or
environment variables. Codex does not expose a reliable Skill-load event, so
planned Skills are not reported as confirmed Skill usage.

Logs are written under Codex's plugin data directory and retained for 30 days.
See [workflow logging](docs/workflow-logging.md) for the event model, limits,
and analysis command. This Hook is for local Codex App/CLI use and is not a
portable Claude Code telemetry feature.

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
