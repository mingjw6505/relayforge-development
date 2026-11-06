"""Check that observation development has not changed plugin runtime assets."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


class PluginImmutabilityTests(unittest.TestCase):
    def test_protected_assets_match_frozen_baseline(self) -> None:
        companion = Path(__file__).resolve().parents[1]
        repository = companion.parent
        baseline = json.loads((companion / "protected-baseline.json").read_text())
        manifests = {"plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/plugin.json"}
        release = json.loads((repository / "plugin.json").read_text())["version"]
        for name, expected in baseline["sha256"].items():
            with self.subTest(asset=name):
                path = repository / name
                self.assertTrue(path.is_file())
                content = path.read_bytes()
                if name in manifests:
                    # Main releases require a version bump. Keep every original
                    # digest and normalize only that explicitly allowed field.
                    version = json.loads(content)["version"]
                    self.assertEqual(version, release)
                    components = version.split(".")
                    self.assertEqual(len(components), 3)
                    self.assertTrue(all(part.isdecimal() for part in components))
                    self.assertGreaterEqual(tuple(map(int, components)), (0, 1, 11))
                    content = content.replace(
                        f'"version": "{version}"'.encode(),
                        b'"version": "0.1.11"',
                        1,
                    )
                self.assertEqual(hashlib.sha256(content).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
