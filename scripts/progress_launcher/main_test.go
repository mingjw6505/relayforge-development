package main

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestMain(m *testing.M) {
	if os.Getenv("RELAYFORGE_LAUNCHER_TEST_HELPER") == "1" {
		name := strings.TrimSuffix(filepath.Base(os.Args[0]), ".exe")
		if len(os.Args) > 1 && os.Args[1] == "-c" {
			input, err := io.ReadAll(os.Stdin)
			if err != nil || len(input) != 0 {
				os.Exit(88)
			}
			switch name {
			case "old":
				os.Exit(1)
			case "alias":
				os.Exit(9009)
			case "hung":
				time.Sleep(10 * time.Second)
				os.Exit(1)
			case "junk":
				fmt.Println("not Python")
				os.Exit(0)
			case "relative":
				fmt.Println("RELAYFORGE_PYTHON=python")
				os.Exit(0)
			case "directory":
				fmt.Println("RELAYFORGE_PYTHON=" + filepath.Dir(os.Args[0]))
				os.Exit(0)
			case "not_executable":
				path := os.Args[0] + ".invalid"
				if err := os.WriteFile(path, []byte("not executable"), 0600); err != nil {
					os.Exit(1)
				}
				fmt.Println("RELAYFORGE_PYTHON=" + path)
				os.Exit(0)
			}
			path, err := os.Executable()
			if err != nil {
				os.Exit(1)
			}
			fmt.Println("RELAYFORGE_PYTHON=" + path)
			os.Exit(0)
		}
		if name == "service_failure" {
			os.Exit(37)
		}
		fmt.Println("ARGS=" + strings.Join(os.Args[1:], "|"))
		if _, err := io.Copy(os.Stdout, os.Stdin); err != nil {
			os.Exit(1)
		}
		os.Exit(0)
	}
	os.Exit(m.Run())
}

func TestRun(t *testing.T) {
	executable, err := os.Executable()
	if err != nil {
		t.Fatal(err)
	}
	image, err := os.ReadFile(executable)
	if err != nil {
		t.Fatal(err)
	}
	t.Setenv("RELAYFORGE_LAUNCHER_TEST_HELPER", "1")
	t.Setenv("RELAYFORGE_PYTHON", "")
	for _, test := range []struct {
		name       string
		candidates []string
		code       int
		output     bool
	}{
		{"first usable", []string{"working"}, 0, true},
		{"old and Store alias", []string{"old", "alias", "working"}, 0, true},
		{"missing and invalid success", []string{"missing", "junk", "working"}, 0, true},
		{"invalid interpreter paths", []string{"relative", "directory", "working"}, 0, true},
		{"hung probe", []string{"hung", "working"}, 0, true},
		{"no Python", []string{"missing", "old", "alias"}, 78, false},
		{"server failure does not retry", []string{"service_failure", "working"}, 37, false},
		{"selected executable fails to start", []string{"not_executable", "working"}, 1, false},
	} {
		t.Run(test.name, func(t *testing.T) {
			root := t.TempDir()
			var candidates [][]string
			for _, name := range test.candidates {
				path := filepath.Join(root, name+".exe")
				if name != "missing" {
					if err := os.WriteFile(path, image, 0700); err != nil {
						t.Fatal(err)
					}
				}
				candidates = append(candidates, []string{path})
			}
			var stdout, stderr bytes.Buffer
			code := run(context.Background(), root, candidates, []string{"--data-dir", "路径 with spaces"}, strings.NewReader("MCP input\n"), &stdout, &stderr)
			if code != test.code {
				t.Fatalf("exit=%d, want %d; stderr=%s", code, test.code, stderr.String())
			}
			want := ""
			if test.output {
				want = "ARGS=-m|progress_panel.server|--data-dir|路径 with spaces\nMCP input\n"
			}
			if stdout.String() != want {
				t.Fatalf("stdout=%q, want %q", stdout.String(), want)
			}
			if (test.code == 1 || test.code == 78) && !strings.Contains(stderr.String(), "Python") {
				t.Fatalf("missing actionable diagnostic: %s", stderr.String())
			}
		})
	}
}

func TestStrictOverrideAndDoctor(t *testing.T) {
	t.Setenv("RELAYFORGE_PYTHON", filepath.Join(t.TempDir(), "missing executable"))
	var stdout, stderr bytes.Buffer
	code := run(context.Background(), t.TempDir(), [][]string{{"python3"}}, []string{"--doctor"}, strings.NewReader(""), &stdout, &stderr)
	if code != 78 || !strings.Contains(stdout.String(), `"status":"python_unavailable"`) || stderr.Len() != 0 {
		t.Fatalf("strict override must fail without fallback: exit=%d stdout=%s stderr=%s", code, stdout.String(), stderr.String())
	}
}
