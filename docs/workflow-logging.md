# Workflow Logging

RelayForge Development includes a Codex lifecycle Hook that writes local,
metadata-only telemetry. The hook is enabled only after the user reviews and
trusts it in Codex. It is intended primarily for manually installed Codex
desktop plugins. A CLI build may not load bundled plugin Hooks even when it
loads the plugin's Skills; use `/hooks` to verify this source is present before
expecting files.

## First-use check

1. Install or refresh RelayForge and confirm the installed manifest is `0.1.9`.
2. In Codex desktop, open **Settings > Hooks** or **Review hooks** in the
   composer. In the CLI, use `/hooks`. Find the RelayForge source, review its
   commands and trust it. Installation alone does not enable collection; an
   updated bundled script can require a new trust review.
3. Complete one ordinary task that uses a local tool. Confirm that a current
   `events-YYYY-MM-DD.jsonl` exists and contains events from that session before
   relying on the report. Missing logs mean collection is unverified, not zero
   activity. No extra agent or model call is needed for collection.
4. Keep the plugin version, host and model alongside an exported report when
   comparing runs. Hook logs do not currently include the plugin version, and
   cannot judge whether the delivered feature met your intent. When a task goes
   wrong, retain a short note about the expected result, observed failure and
   rework; there is no mandatory per-task feedback form.

The host supplies `PLUGIN_DATA` to hook processes; an ordinary terminal may not
have that environment variable. Use the actual plugin data directory rather
than an empty `$env:PLUGIN_DATA`. On Windows, after the first task, this local
search can help locate logs under the usual Codex home (or `CODEX_HOME` override):

```powershell
$codexDataRoot = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE '.codex' }
Get-ChildItem -LiteralPath $codexDataRoot -Filter 'events-*.jsonl' -File -Recurse -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 10 FullName, LastWriteTime
```

Select the RelayForge directory, not another plugin's files. A host using a
different data root or an explicit logger override needs its actual path. Export
a report from your local checkout, substituting that directory:

```powershell
$logDir = 'C:\path\to\relayforge-plugin-data\logs'
py -3 'E:\my-project\relayforge-development\scripts\analyze_workflow_logs.py' --log-dir $logDir |
    Set-Content -LiteralPath '.\relayforge-usage-report.json' -Encoding utf8
```

Keep the daily JSONL files if a later investigation needs the event sequence;
the summary alone loses ordering. Collection is local and does not upload logs
to GitHub or any analytics service. Archive a useful sample before the 30-day
retention window expires. This adapter targets Codex; Claude Code collection has
not been validated and must not be assumed active.

See the current [official hook trust instructions](https://learn.chatgpt.com/docs/hooks#plugin-bundled-hooks).

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
