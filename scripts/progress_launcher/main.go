// Command progress_launcher bootstraps the Python MCP server on Windows.
// The shipped executable requires no Go installation or third-party modules.
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

const probe = `import sys, sqlite3; sys.exit(1) if sys.version_info < (3, 11) else print("RELAYFORGE_PYTHON=" + sys.executable)`

func usablePython(ctx context.Context, candidate []string, root string) string {
	ctx, cancel := context.WithTimeout(ctx, 1500*time.Millisecond)
	defer cancel()
	args := append(append([]string{}, candidate[1:]...), "-c", probe)
	cmd := exec.CommandContext(ctx, candidate[0], args...)
	// A launcher grandchild may inherit stdout after the probed process exits.
	// Bound pipe cleanup as well as the direct child's lifetime.
	cmd.WaitDelay = 100 * time.Millisecond
	cmd.Dir = root
	cmd.Env = append(os.Environ(), "PYTHONIOENCODING=utf-8")
	var output bytes.Buffer
	cmd.Stdout = &output
	// Nil stdin is NUL: probes must never consume the host's MCP requests.
	if err := cmd.Run(); err != nil {
		return ""
	}
	path, found := strings.CutPrefix(strings.TrimSpace(output.String()), "RELAYFORGE_PYTHON=")
	if !found || !filepath.IsAbs(path) {
		return ""
	}
	info, err := os.Stat(path)
	if err != nil || info.IsDir() {
		return ""
	}
	return path
}

func run(ctx context.Context, root string, candidates [][]string, args []string, stdin io.Reader, stdout, stderr io.Writer) int {
	probeContext, cancel := context.WithTimeout(ctx, 6500*time.Millisecond)
	defer cancel()
	if override := os.Getenv("RELAYFORGE_PYTHON"); override != "" {
		candidates = [][]string{{override}}
	}
	doctor := len(args) == 1 && args[0] == "--doctor"
	for _, candidate := range candidates {
		python := usablePython(probeContext, candidate, root)
		if python == "" {
			continue
		}
		serverArgs := append([]string{"-m", "progress_panel.server"}, args...)
		if doctor {
			serverArgs = []string{"-m", "progress_panel.doctor"}
		}
		cmd := exec.CommandContext(ctx, python, serverArgs...)
		cmd.Dir = root
		cmd.Stdin, cmd.Stdout, cmd.Stderr = stdin, stdout, stderr
		if err := cmd.Run(); err != nil {
			var exited *exec.ExitError
			if errors.As(err, &exited) {
				return exited.ExitCode()
			}
			fmt.Fprintf(stderr, "RelayForge progress: unable to start selected Python: %v\n", err)
			return 1
		}
		return 0
	}
	message := "RelayForge progress requires Python 3.11+ with sqlite3. Check PATH, Windows App execution aliases and any strict RELAYFORGE_PYTHON override. No software was installed."
	if doctor {
		if err := json.NewEncoder(stdout).Encode(map[string]string{
			"status": "python_unavailable", "host_tools": "unverified", "host_ui": "unverified",
			"state_directory": "unverified", "message": message,
		}); err != nil {
			fmt.Fprintln(stderr, "RelayForge progress: unable to write diagnostic:", err)
		}
	} else {
		fmt.Fprintln(stderr, message)
	}
	return 78
}

func main() {
	executable, err := os.Executable()
	if err != nil {
		fmt.Fprintln(os.Stderr, "RelayForge progress: unable to locate the plugin:", err)
		os.Exit(1)
	}
	root := filepath.Dir(filepath.Dir(executable))
	candidates := [][]string{{"py", "-3"}, {"python"}, {"python3"}}
	for _, version := range []string{"3.15", "3.14", "3.13", "3.12", "3.11"} {
		candidates = append(candidates, []string{"py", "-" + version})
	}
	os.Exit(run(context.Background(), root, candidates, os.Args[1:], os.Stdin, os.Stdout, os.Stderr))
}
