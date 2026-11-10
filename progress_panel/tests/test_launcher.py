"""Exercise the actual registered entrypoint with isolated state and UTF-8 pipes."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
NODE = shutil.which("node")


@unittest.skipUnless(NODE, "Node runtime unavailable")
class LauncherTests(unittest.TestCase):
    def test_doctor_uses_existing_executable_and_leaves_real_state_unverified(self):
        result = subprocess.run(
            [NODE, str(ROOT / "scripts/progress-launcher.cjs"), "--doctor"],
            env={**os.environ, "RELAYFORGE_PYTHON": sys.executable},
            capture_output=True, encoding="utf-8", timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "runtime_ready")
        self.assertEqual(report["host_ui"], "unverified")
        self.assertEqual(report["state_directory"], "unverified")

    def test_registered_launcher_handles_spaces_foreign_cwd_and_protocol(self):
        with tempfile.TemporaryDirectory(prefix="relayforge launcher ") as folder:
            root = Path(folder)
            shutil.copytree(ROOT / "scripts", root / "scripts")
            shutil.copytree(ROOT / "progress_panel", root / "progress_panel",
                            ignore=shutil.ignore_patterns("__pycache__", "node_modules"))
            shutil.copyfile(ROOT / "plugin.json", root / "plugin.json")
            request = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                       "params": {"protocolVersion": "2025-11-25"}}
            result = subprocess.run(
                [NODE, str(root / "scripts/progress-launcher.cjs")],
                cwd=root.parent,
                env={**os.environ, "RELAYFORGE_PYTHON": sys.executable,
                     "RELAYFORGE_PROGRESS_DATA_DIR": str(root / "isolated-state")},
                input=json.dumps(request) + "\n", capture_output=True,
                encoding="utf-8", timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["result"]["serverInfo"]["name"],
                             "relayforge-progress")
            self.assertEqual(result.stderr, "")
            self.assertFalse((root / "isolated-state").exists())


if __name__ == "__main__":
    unittest.main()
