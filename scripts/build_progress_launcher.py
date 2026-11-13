#!/usr/bin/env python3
"""Rebuild or verify the shipped Windows bootstrap (Go is development-only)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/progress_launcher/main.go"
OUTPUT = ROOT / "scripts/start_progress.exe"
RECORD = ROOT / "scripts/progress_launcher/build.json"
FLAGS = ["-trimpath", "-buildvcs=false", "-ldflags=-s -w -buildid="]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Rebuild in a temporary directory and compare bytes")
    args = parser.parse_args()
    env = dict(os.environ, GOOS="windows", GOARCH="386", GO386="sse2", CGO_ENABLED="0",
               GO111MODULE="off", GOTOOLCHAIN="local", GOWORK="off", GOENV="off", GOFLAGS="")
    version = subprocess.check_output(["go", "version"], text=True, env=env).split()[2]
    with tempfile.TemporaryDirectory(prefix="relayforge-build-") as directory:
        target = Path(directory) / "start_progress.exe"
        subprocess.run(["go", "build", *FLAGS, "-o", str(target), str(SOURCE.relative_to(ROOT))],
                       cwd=ROOT, env=env, check=True)
        binary = target.read_bytes()
    record = {
        "go_version": version, "goos": "windows", "goarch": "386", "go386": "sse2", "cgo_enabled": "0",
        "flags": FLAGS,
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "binary_sha256": hashlib.sha256(binary).hexdigest(),
    }
    if args.check:
        if record != json.loads(RECORD.read_text()) or binary != OUTPUT.read_bytes():
            raise SystemExit("Windows launcher differs; rebuild with the recorded Go version")
        print("Windows launcher rebuild matches shipped bytes and source record.")
    else:
        OUTPUT.write_bytes(binary)
        RECORD.write_text(json.dumps(record, indent=2) + "\n")
        print(f"Built Windows launcher with {version} ({len(binary)} bytes).")


if __name__ == "__main__":
    main()
