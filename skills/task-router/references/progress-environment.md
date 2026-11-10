# Progress environment diagnosis and assisted repair

Apply when progress tools are missing, a call reports startup/storage failure,
the user reports a missing card, or requests an environment check. This recovery
path is conditional, not a prerequisite for every task. Keep useful development
work moving with text progress. Notify once with the observed symptom; do not
infer missing Python from an absent card or create repeated cards as a test.
Reuse diagnostics until the environment changes. If commands are unavailable,
state that limitation and provide manual commands without claiming repair.

## Inspect the installed plugin

Resolve its root from the actual skill location/host inventory, not the user's
application repository. Inspect its MCP registration. From that root run:

```sh
node scripts/progress-launcher.cjs --doctor
```

Use a discovered Node executable and absolute script path when needed. This
bounded check selects Python 3.11+ with sqlite3 and verifies imports, tools,
shipped HTML and SQLite in temporary storage. It never reads user task history,
installs software or changes PATH. JSON explicitly marks host tools, UI and real
state-directory permissions `unverified`. Normal startup diagnostics use stderr;
doctor JSON uses stdout. Exit 78 means runtime unavailable, 70 package/server
failure, 64 invalid arguments. Report the category and next action; never paste
arbitrary output or secrets into chat. An exhausted probe budget does not prove
Python is not installed.

## Prefer existing runtimes

1. If `node` is missing, discover an existing trusted host-provided/installed
   Node.js 18+ before proposing installation. Windows: `Get-Command node -All`;
   POSIX: `command -v node`. The App process may have a different PATH from the
   Agent shell; check the host environment instead of assuming shell success.
2. The launcher tries Windows `py -3`, `python3`, `python`, then `py -3.15` through
   `py -3.11`; POSIX tries `python3`, `python`, then versioned names 3.15 through
   3.11. Probes have 1.2-second individual / 6.5-second total budgets.
3. If selection fails, inspect existing Python: Windows
   `Get-Command py,python,python3 -All` and `py -0p`; POSIX `command -v python3`
   and `command -v python`. Verify version and sqlite3. Distinguish Store aliases,
   old Python, permission failures and missing sqlite3. Do not reinstall healthy
   Python just to fix an alias.
4. Prefer a supported user-local MCP environment/command override or user
   environment over editing plugin caches. Set `RELAYFORGE_PYTHON` to one verified
   executable path, never a command string such as `py -3`. It is strict: an
   invalid override fails rather than silently selecting another interpreter.
   Validate a temporary override before persisting an authorized change.

PowerShell session-only example (substitute the verified local path):

```powershell
$env:RELAYFORGE_PYTHON = 'C:\path\to\python.exe'
node scripts/progress-launcher.cjs --doctor
```

POSIX session-only example:

```sh
RELAYFORGE_PYTHON='/path/to/python3' node scripts/progress-launcher.cjs --doctor
```

`package_check_failed` with healthy Python calls for package inspection, not a
Python reinstall. For storage errors inspect only the selected directory's
permissions/error, not task contents; reproduce in isolated storage. Never remove
existing user data to repair the panel.

## Assist installation when necessary

If no usable existing runtime is found, prepare a concrete repair specifying
runtime/version, official source, user/system scope, download and PATH effects,
and any administrator requirement. Use [Python downloads](https://www.python.org/downloads/)
or [Node.js downloads](https://nodejs.org/en/download), or a verified trusted
system package manager. Verify current package IDs/commands before execution.
Do not use unverified download-and-execute snippets, bypass policy, auto-elevate
or install runtime npm packages for this panel.

Reuse explicit repair/installation authorization from the conversation; do not
ask again for the same authorized action. A normal development request alone
does not authorize runtime installation: otherwise ask for the concrete change,
continuing independent work. If network/admin/host restrictions block repair,
explain the specific limitation and provide manual steps. The launcher itself
never installs software.

## Verify each layer separately

After a change rerun the doctor, then inspect host tool discovery. One new chat
or reload may be needed after plugin/environment changes; do not restart in a
loop when inventory is unchanged. Reuse a live task ID and show another display
only when requested. If no task exists, create one card for the actual task once
tools are available.

Report runtime readiness, host MCP loading, tool-call success and visible inline
rendering separately. Only host render evidence or user confirmation establishes
visibility. Successful doctor/tool calls do not. If the host lacks MCP Apps UI,
explain and use text progress; installing runtimes cannot add UI support.
A Skill can notify only after it is loaded and the host lets the Agent run and
communicate; it cannot guarantee OS alerts if the entire plugin is unavailable.
