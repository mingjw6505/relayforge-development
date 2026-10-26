# Workflow Logging

RelayForge Development includes a Codex lifecycle Hook that writes local,
metadata-only telemetry. The hook is enabled only after the user reviews and
trusts it in Codex. It is intended primarily for manually installed Codex
desktop plugins. A CLI build may not load bundled plugin Hooks even when it
loads the plugin's Skills; use `/hooks` to verify this source is present before
expecting files.

## Stored Data

The hook stores daily JSONL files in:

```text
PLUGIN_DATA/logs/events-YYYY-MM-DD.jsonl
```

Records include the Hook event name, timestamp, hashed session/turn/tool IDs,
model name, permission mode, tool name, tool completion outcome, and timing.
When `task-router` supplies its required final metadata line, the Hook also
records its Quick/Standard/Large decision, generic work surfaces, and planned
Skill names. When `finishing-development` supplies its status line, the Hook
records the declared implementation, checks, verification, review, commit, and
push states.
The logger retains 30 calendar days, prunes unfinished tool-pair state after
24 hours, and serializes concurrent writers with a short lock file.

`PreToolUse` and `PostToolUse` run synchronously so calls can be paired even
when a tool returns immediately. Reported duration is therefore a close local
wall-clock measurement, including a small amount of Hook scheduling and log
write overhead.

For an isolated forward test, set `RELAYFORGE_WORKFLOW_LOG_DIR` before starting
Codex. The logger writes there instead of the host-managed `PLUGIN_DATA`
directory; ordinary plugin sessions should leave this override unset.

It never persists the user prompt, shell command, tool input, tool output,
source code, patch contents, environment variables, or credentials. The
temporary pending-call state contains only hashed IDs, timestamps, and tool
names so `PreToolUse` and `PostToolUse` can be paired.

## Observable Events

- `SessionStart` and `SessionEnd`
- `UserPromptSubmit`
- `PreToolUse` and `PostToolUse`
- `SubagentStart` and `SubagentStop`
- `Stop` and `Interrupt`

The data represents the plugin-enabled session's observable activity, not an
audit log of every plugin or Skill invocation. Router data is a declared plan,
not confirmation that Codex loaded a Skill. Codex does not offer a stable Hook
event for a Skill load. The telemetry can show tool-call patterns and time
spent in local tools, but it cannot claim which Skills Codex actually loaded.
Hosted tools can also bypass local tool Hooks, so they may be absent from the
log.

## Analyze Logs

Run the analyzer against the `logs` directory:

```bash
python3 scripts/analyze_workflow_logs.py --log-dir "$PLUGIN_DATA/logs"
```

On Windows, use:

```powershell
py -3 scripts/analyze_workflow_logs.py --log-dir "$env:PLUGIN_DATA\logs"
```

The JSON report includes route, work-surface, planned-Skill, and workflow-state
counts; per-tool call counts and timing totals; average, P50, P95, maximum,
completed-tool outcomes, interrupted and unfinished turns, and unmatched tool
starts. It also states the collection limits, including the absence of reliable
token, required-human-decision, and actual Skill-load metrics.

Use [workflow benchmark](workflow-benchmark.md) when comparing baseline and
candidate token, duration, human-decision, and quality targets. Benchmark
records are separate from Hook logs because a Hook-observed turn does not prove
that human input was materially required.

## Support Boundaries

The Hook uses `commandWindows` with `py -3` for Windows and `python3` for
macOS/Linux. The logger and analyzer entry points are verified in this release.
An installed plugin still needs a host that exposes bundled Hooks, user trust,
and a real lifecycle event. If the plugin source is absent from `/hooks`, use
CLI JSONL output plus the separate workflow benchmark instead of treating an
empty log directory as a zero-event run.

Plugin-bundled Hooks are not guaranteed in cloud-orchestrated environments and
are not appropriate for public-plugin distribution. They add no network calls,
MCP servers, credentials, or third-party Python packages.
