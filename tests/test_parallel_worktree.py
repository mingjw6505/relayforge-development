from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "development-workflow" / "scripts" / "parallel_worktree.py"
REVIEW_SCRIPT = ROOT / "skills" / "subagent-driven-development" / "scripts" / "review-package"


class ParallelWorktreeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repository = self.base / "project"
        self.repository.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "RelayForge Test")
        self.git("config", "user.email", "relayforge@example.invalid")
        (self.repository / ".gitignore").write_text(".relayforge/\n", encoding="utf-8")
        for name in ("alpha.txt", "beta.txt", "gamma.txt"):
            (self.repository / name).write_text(f"base {name}\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "initial")
        self.environment = os.environ.copy()
        self.environment["RELAYFORGE_WORKTREE_ROOT"] = str(self.base / "workers")

    def git(self, *arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *arguments],
            cwd=cwd or self.repository,
            check=True,
            capture_output=True,
            text=True,
        )

    def helper(self, *arguments: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", str(SCRIPT), *arguments],
            cwd=self.repository,
            env=self.environment,
            check=check,
            capture_output=True,
            text=True,
        )

    def paths_file(self, name: str, *paths: str) -> Path:
        target = self.base / f"{name}-paths.txt"
        target.write_text("".join(f"{path}\n" for path in paths), encoding="utf-8")
        return target

    def prepare_task_branch(self) -> None:
        completed = self.helper("prepare", "--task", "sample", "--kind", "feat")
        self.assertEqual(completed.stdout.strip(), "relayforge/feat/sample")

    def test_prepare_creates_one_task_branch_and_refuses_dirty_transition(self):
        self.prepare_task_branch()
        self.assertEqual(self.git("branch", "--show-current").stdout.strip(), "relayforge/feat/sample")
        repeated = self.helper("prepare", "--task", "sample", "--kind", "feat")
        self.assertEqual(repeated.stdout.strip(), "relayforge/feat/sample")

        (self.repository / "alpha.txt").write_text("dirty\n", encoding="utf-8")
        refused = self.helper("prepare", "--task", "second", "--kind", "fix", check=False)
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("dirty checkout", refused.stderr)
        self.assertEqual(self.git("branch", "--show-current").stdout.strip(), "relayforge/feat/sample")

    def test_parallel_worker_exports_integrates_and_cleans_up_without_commits(self):
        self.prepare_task_branch()
        base = self.git("rev-parse", "HEAD").stdout.strip()
        created = self.helper(
            "create",
            "--task",
            "sample",
            "--unit",
            "alpha",
            "--base",
            base,
            "--paths-file",
            str(self.paths_file("alpha", "alpha.txt", "beta.txt", "new.txt", "blob.bin")),
        )
        worker = Path(created.stdout.strip())
        (worker / "alpha.txt").write_text("worker result\n", encoding="utf-8")
        (worker / "beta.txt").unlink()
        (worker / "new.txt").write_text("new file\n", encoding="utf-8")
        (worker / "blob.bin").write_bytes(b"\x00relayforge\xff")

        exported = self.helper("export", "--task", "sample", "--unit", "alpha")
        patch = Path(exported.stdout.strip())
        self.assertTrue(patch.is_file())
        self.assertEqual(self.git("diff", "--cached", cwd=worker).stdout, "")
        self.helper("integrate", "--task", "sample", "--unit", "alpha")
        self.assertEqual((self.repository / "alpha.txt").read_text(encoding="utf-8"), "worker result\n")
        self.assertFalse((self.repository / "beta.txt").exists())
        self.assertEqual((self.repository / "new.txt").read_text(encoding="utf-8"), "new file\n")
        self.assertEqual((self.repository / "blob.bin").read_bytes(), b"\x00relayforge\xff")
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), base)

        self.helper("cleanup", "--task", "sample", "--unit", "alpha")
        self.assertFalse(worker.exists())
        manifest = json.loads(
            (self.repository / ".relayforge" / "worktrees" / "sample" / "alpha" / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(manifest["status"], "cleaned")

    def test_export_rejects_worker_changes_outside_owned_paths(self):
        self.prepare_task_branch()
        created = self.helper(
            "create",
            "--task",
            "sample",
            "--unit",
            "alpha",
            "--paths-file",
            str(self.paths_file("alpha", "alpha.txt")),
        )
        worker = Path(created.stdout.strip())
        (worker / "beta.txt").write_text("out of scope\n", encoding="utf-8")
        exported = self.helper("export", "--task", "sample", "--unit", "alpha", check=False)
        self.assertNotEqual(exported.returncode, 0)
        self.assertIn("outside its ownership", exported.stderr)

    def test_create_rejects_overlapping_ownership_and_more_than_two_workers(self):
        self.prepare_task_branch()
        self.helper(
            "create",
            "--task",
            "sample",
            "--unit",
            "alpha",
            "--paths-file",
            str(self.paths_file("alpha", "alpha.txt")),
        )
        overlap = self.helper(
            "create",
            "--task",
            "sample",
            "--unit",
            "overlap",
            "--paths-file",
            str(self.paths_file("overlap", "alpha.txt")),
            check=False,
        )
        self.assertNotEqual(overlap.returncode, 0)
        self.assertIn("ownership overlaps", overlap.stderr)

        self.helper(
            "create",
            "--task",
            "sample",
            "--unit",
            "beta",
            "--paths-file",
            str(self.paths_file("beta", "beta.txt")),
        )
        third = self.helper(
            "create",
            "--task",
            "sample",
            "--unit",
            "gamma",
            "--paths-file",
            str(self.paths_file("gamma", "gamma.txt")),
            check=False,
        )
        self.assertNotEqual(third.returncode, 0)
        self.assertIn("more than two", third.stderr)

    def test_integrate_rejects_worker_changes_after_export(self):
        self.prepare_task_branch()
        created = self.helper(
            "create",
            "--task",
            "sample",
            "--unit",
            "alpha",
            "--paths-file",
            str(self.paths_file("alpha", "alpha.txt")),
        )
        worker = Path(created.stdout.strip())
        (worker / "alpha.txt").write_text("first result\n", encoding="utf-8")
        self.helper("export", "--task", "sample", "--unit", "alpha")
        (worker / "alpha.txt").write_text("changed after export\n", encoding="utf-8")

        integrated = self.helper("integrate", "--task", "sample", "--unit", "alpha", check=False)
        self.assertNotEqual(integrated.returncode, 0)
        self.assertIn("changed after", integrated.stderr)
        self.assertEqual((self.repository / "alpha.txt").read_text(encoding="utf-8"), "base alpha.txt\n")

    def test_integrate_rejects_primary_changes_to_worker_owned_paths(self):
        self.prepare_task_branch()
        created = self.helper(
            "create",
            "--task",
            "sample",
            "--unit",
            "alpha",
            "--paths-file",
            str(self.paths_file("alpha", "alpha.txt")),
        )
        worker = Path(created.stdout.strip())
        (worker / "alpha.txt").write_text("worker result\n", encoding="utf-8")
        self.helper("export", "--task", "sample", "--unit", "alpha")
        (self.repository / "alpha.txt").write_text("controller result\n", encoding="utf-8")

        integrated = self.helper("integrate", "--task", "sample", "--unit", "alpha", check=False)
        self.assertNotEqual(integrated.returncode, 0)
        self.assertIn("already changed worker-owned paths", integrated.stderr)
        self.assertEqual((self.repository / "alpha.txt").read_text(encoding="utf-8"), "controller result\n")

    def test_review_package_uses_uncommitted_mode_name(self):
        self.prepare_task_branch()
        base = self.git("rev-parse", "HEAD").stdout.strip()
        (self.repository / "alpha.txt").write_text("review me\n", encoding="utf-8")
        plan = self.repository / ".relayforge" / "plan.md"
        plan.parent.mkdir(parents=True, exist_ok=True)
        plan.write_text("# Plan\n", encoding="utf-8")
        output = self.base / "review.diff"
        completed = subprocess.run(
            [
                "bash",
                str(REVIEW_SCRIPT),
                str(plan),
                base,
                "UNCOMMITTED",
                str(output),
                str(self.paths_file("review", "alpha.txt")),
            ],
            cwd=self.repository,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("review me", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
