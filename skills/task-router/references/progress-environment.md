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
./scripts/start_progress --doctor
```

On Windows use `.\scripts\start_progress.exe --doctor` explicitly. The MCP host
uses the shared extensionless command and Windows resolves its `.exe` sibling;
manual shell invocation should use the platform's actual file. No Node or Go
installation is needed. This check selects Python 3.11+ with sqlite3 and verifies
imports, tools, shipped HTML and SQLite in temporary storage. It never reads user
task history, installs software or changes PATH. JSON marks host tools, UI and
real state-directory permissions `unverified`. Normal startup diagnostics use
stderr; doctor JSON uses stdout. Exit 78 means runtime unavailable, 70 package
failure; other service failures preserve their exit code. Report the category
and next action without arbitrary child output or secrets. A failed probe does
not establish that Python is absent from the machine.

## Prefer existing runtimes

1. Inspect the fixed registration and packaged entrypoint before proposing a
   runtime installation. The App process may have a different PATH from the Agent
   shell; shell success alone does not establish host availability. A missing
   native executable or POSIX executable permission is a package problem.
2. Windows tries `py -3`, `python`, `python3`, then `py -3.15` through `py -3.11`;
   POSIX tries `python3`, `python`, then versioned names 3.15 through 3.11.
   Windows probes have 1.5-second individual and 6.5-second total budgets, plus
   bounded pipe cleanup. POSIX shell probes have no external timeout guarantee;
   stop a hung diagnostic rather than inferring absence or looping retries.
3. Inspect existing Python: Windows `Get-Command py,python,python3 -All` and
   `py -0p`; POSIX `command -v python3` and `command -v python`. Verify version and
   sqlite3. Distinguish Store aliases, old Python, permissions and missing sqlite3.
   Do not reinstall healthy Python just to fix an alias.
4. Prefer a supported user-local MCP environment/command override or user
   environment over editing plugin caches. Set `RELAYFORGE_PYTHON` to one verified
   executable path, never a command string such as `py -3`. It is strict: an
   invalid override fails instead of selecting another interpreter. Validate a
   temporary override before persisting an authorized change.

PowerShell session-only example (substitute the verified local path):

```powershell
$env:RELAYFORGE_PYTHON = 'C:\path\to\python.exe'
.\scripts\start_progress.exe --doctor
```

POSIX session-only example:

```sh
RELAYFORGE_PYTHON='/path/to/python3' ./scripts/start_progress --doctor
```

`package_check_failed` with healthy Python calls for package inspection, not a
Python reinstall. For storage errors inspect only the selected directory's
permissions/error, not task contents; reproduce in isolated storage. Never remove
existing user data to repair the panel.

## Assist installation when necessary

If no usable existing runtime is found, prepare a concrete repair specifying
runtime/version, official source, user/system scope, download and PATH effects,
and any administrator requirement. Use [Python downloads](https://www.python.org/downloads/)
or a verified trusted system package manager. The registered bootstrap does not
need Node or Go; do not install either just to repair its Python discovery. Verify current package IDs/commands before execution.
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
