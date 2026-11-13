# Progress bootstrap

Both MCP registrations use `./scripts/start_progress`. POSIX runs the executable
shell script at that path. Windows Rust process resolution appends `.exe` before
falling back to the extensionless file, selecting the bundled native executable.
Both files remain within the plugin root. No configuration rewrite is involved.

The Windows executable uses only Go standard-library packages, built with CGO
disabled. Users need Python 3.11+ with SQLite in PATH, but no Go, Node, Bash on
Windows, or additional runtime installation. The Go runtime's BSD license ships
in [GO_LICENSE](GO_LICENSE). The shipped x86 Windows artifact still needs native
Windows and Codex host acceptance; cross-compilation does not establish either.

`main.go` probes `py -3`, `python`, and `python3`, then versioned `py -3.15`
through `py -3.11`, with NUL stdin and isolated stdout/stderr. Each probe has a
1.5-second timeout within a 6.5-second total budget, plus bounded pipe cleanup,
and must report a real absolute interpreter path. A `RELAYFORGE_PYTHON` override
is strict: its failure never selects another environment. The chosen interpreter
inherits MCP stdio and receives the
server arguments directly, without shell quoting. Server failures retain their
exit code and never trigger fallback to another interpreter. POSIX uses `exec`
after its version/SQLite probe so signals and exit codes reach the server.

Both registered entrypoints support `--doctor`, running the preserved isolated
Python package check. It explicitly leaves host loading, rendering and real
state-directory permissions unverified. The prior Node launcher remains an
optional compatibility entrypoint, not a dependency of current MCP registration.

Run from the repository root with the exact Go version in [build.json](build.json):

```bash
go test -race -cover scripts/progress_launcher/main.go scripts/progress_launcher/main_test.go
go vet scripts/progress_launcher/main.go
python3 scripts/build_progress_launcher.py
python3 scripts/build_progress_launcher.py --check
python3 -m pytest progress_panel/tests
```

Use `py -3` or `python` for the Python development commands on Windows. Go is
needed only when changing/rebuilding the native bootstrap, not for Python server,
UI or prose-only changes. The builder forces `GOOS=windows`, `GOARCH=386`,
`CGO_ENABLED=0`, local toolchain selection and no module resolution. It records
compiler version, flags and source/binary SHA-256. `--check` builds in a temporary
directory and requires byte-for-byte equality; it does not overwrite the artifact.
Packaging tests fail if the source changes without rebuilding or either artifact
is missing. Preserve the POSIX script's executable bit when distributing it.

Normal startup never writes manifests, downloads dependencies or uses build tools.
The optional `python3 scripts/check_progress.py` probe checks MCP discovery using
a temporary data directory and leaves configuration/task state untouched.
