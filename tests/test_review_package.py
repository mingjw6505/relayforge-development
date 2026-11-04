from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/finishing-development/scripts/review_package.py"


class ReviewPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SCRIPT.is_file():
            raise AssertionError(f"Required review helper is missing: {SCRIPT}")
        probe = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True)
        if probe.returncode != 0:
            raise AssertionError(f"Review helper cannot start: {probe.stderr!r}")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.repo = self.base / "审查 with spaces"
        self.repo.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        for name in ("committed.txt", "staged.txt", "working.txt", "deleted.txt", "unrelated.txt"):
            (self.repo / name).write_text("original\n", encoding="utf-8")
        (self.repo / ".gitignore").write_text(".relayforge/\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "base")
        self.start = self.git("rev-parse", "HEAD").decode().strip()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.repo, capture_output=True, check=True).stdout

    def package(self, paths=None, target="WORKTREE", name="review.diff", base=None):
        output = self.base / name
        args = [sys.executable, str(SCRIPT), "--base", base or self.start,
                "--target", target, "--output", str(output)]
        if paths is not None:
            pathfile = self.base / "paths.txt"
            pathfile.write_text("\n".join(paths), encoding="utf-8")
            args += ["--paths-file", str(pathfile)]
        result = subprocess.run(args, cwd=self.repo, capture_output=True, text=True, encoding="utf-8")
        return result, output

    def test_all_change_states_are_reviewed_and_index_is_preserved(self):
        (self.repo / "committed.txt").write_text("committed change\n", encoding="utf-8")
        self.git("add", "committed.txt")
        self.git("commit", "-m", "task part")
        (self.repo / "staged.txt").write_text("staged change\n", encoding="utf-8")
        self.git("add", "staged.txt")
        (self.repo / "working.txt").write_text("working change\n", encoding="utf-8")
        (self.repo / "deleted.txt").unlink()
        (self.repo / "新增.txt").write_text("new change\n", encoding="utf-8")
        (self.repo / "blob.bin").write_bytes(bytes([0, 255, 1]))
        (self.repo / "unrelated.txt").write_text("private unrelated change\n", encoding="utf-8")
        before = (self.repo / ".git/index").read_bytes()
        status = self.git("status", "--porcelain", "-z")
        head = self.git("rev-parse", "HEAD")
        result, output = self.package(["committed.txt", "staged.txt", "working.txt", "deleted.txt", "新增.txt", "blob.bin"])
        self.assertEqual(result.returncode, 0, result.stderr)
        diff = output.read_bytes()
        for content in (b"committed change", b"staged change", b"working change", b"deleted file mode", b"new change", b"GIT binary patch"):
            self.assertIn(content, diff)
        self.assertNotIn(b"private unrelated change", diff)
        self.assertEqual(before, (self.repo / ".git/index").read_bytes())
        self.assertEqual(status, self.git("status", "--porcelain", "-z"))
        self.assertEqual(head, self.git("rev-parse", "HEAD"))
        meta = json.loads(output.with_name(output.name + ".json").read_text())
        self.assertEqual(meta["sha256"], hashlib.sha256(diff).hexdigest())

    def test_committed_only_does_not_include_working_changes(self):
        (self.repo / "committed.txt").write_text("saved\n")
        self.git("add", "committed.txt")
        self.git("commit", "-m", "task")
        (self.repo / "working.txt").write_text("unsaved\n")
        result, output = self.package(target="HEAD")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("saved", output.read_text())
        self.assertNotIn("unsaved", output.read_text())

    def test_force_staged_ignored_addition_is_included_without_other_ignored_files(self):
        (self.repo / ".gitignore").write_text(".relayforge/\n*.generated\n", encoding="utf-8")
        (self.repo / "chosen.generated").write_text("intentionally staged\n", encoding="utf-8")
        (self.repo / "private.generated").write_text("must stay private\n", encoding="utf-8")
        self.git("add", "-f", "chosen.generated")
        before = (self.repo / ".git/index").read_bytes()
        result, output = self.package()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("intentionally staged", output.read_text())
        self.assertNotIn("must stay private", output.read_text())
        self.assertEqual(before, (self.repo / ".git/index").read_bytes())
        result, output = self.package(["chosen.generated"], name="selected.diff")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("intentionally staged", output.read_text())
        self.assertNotIn("must stay private", output.read_text())
        self.assertEqual(before, (self.repo / ".git/index").read_bytes())

    def test_staged_addition_deleted_from_worktree_is_not_reported_as_present(self):
        (self.repo / "new.txt").write_text("then removed\n")
        self.git("add", "new.txt")
        (self.repo / "new.txt").unlink()
        (self.repo / "working.txt").write_text("still changed\n")
        result, output = self.package()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("then removed", output.read_text())
        selected, scoped = self.package(["new.txt", "working.txt"], name="scoped-deleted-addition.diff")
        self.assertEqual(selected.returncode, 0, selected.stderr)
        self.assertNotIn("then removed", scoped.read_text())

    def test_committed_deletion_is_kept_in_explicit_working_review_scope(self):
        (self.repo / "deleted.txt").unlink()
        self.git("add", "deleted.txt")
        self.git("commit", "-m", "remove obsolete file")
        (self.repo / "working.txt").write_text("later working change\n")
        index = (self.repo / ".git/index").read_bytes()
        head = self.git("rev-parse", "HEAD")
        result, output = self.package(["deleted.txt", "working.txt"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("deleted file mode", output.read_text())
        self.assertIn("later working change", output.read_text())
        only, removed = self.package(["deleted.txt"], name="only-committed-deletion.diff")
        self.assertEqual(only.returncode, 0, only.stderr)
        self.assertIn("deleted file mode", removed.read_text())
        self.assertEqual(index, (self.repo / ".git/index").read_bytes())
        self.assertEqual(head, self.git("rev-parse", "HEAD"))

    def test_committed_rename_old_path_can_share_scope_with_working_changes(self):
        self.git("mv", "committed.txt", "renamed.txt")
        self.git("commit", "-m", "rename task file")
        (self.repo / "working.txt").write_text("later working change\n")
        result, output = self.package(["committed.txt", "renamed.txt", "working.txt"])
        self.assertEqual(result.returncode, 0, result.stderr)
        text = output.read_text()
        self.assertIn("deleted file mode", text)
        self.assertIn("new file mode", text)
        self.assertIn("later working change", text)

    def test_literal_paths_do_not_expand_wildcards(self):
        (self.repo / "[one].txt").write_text("literal\n")
        (self.repo / "o.txt").write_text("unrelated\n")
        result, output = self.package(["[one].txt"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("literal", output.read_text())
        self.assertNotIn("unrelated", output.read_text())

    def test_empty_bad_base_and_escaping_paths_fail(self):
        for paths, base in ((None, None), (["../secret"], None), (["C:/secret"], None), ([".git/config"], None), ([], None), (None, "missing-ref")):
            result, output = self.package(paths, base=base)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(result.stderr.startswith("review-package:"), result.stderr)
            self.assertFalse(output.exists())

    def test_frozen_packages_are_not_overwritten_and_drift_changes_digest(self):
        (self.repo / "working.txt").write_text("one\n")
        first, output = self.package(["working.txt"])
        self.assertEqual(first.returncode, 0, first.stderr)
        initial = output.read_bytes()
        (self.repo / "working.txt").write_text("two\n")
        refused, _ = self.package(["working.txt"])
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("review-package: refusing to overwrite frozen evidence", refused.stderr)
        self.assertEqual(output.read_bytes(), initial)
        changed, second = self.package(["working.txt"], name="second.diff")
        self.assertEqual(changed.returncode, 0, changed.stderr)
        self.assertNotEqual(hashlib.sha256(initial).digest(), hashlib.sha256(second.read_bytes()).digest())

    def test_output_cannot_overwrite_or_pollute_source(self):
        (self.repo / "working.txt").write_text("modified\n")
        result, output = self.package(name="审查 with spaces/new-source.diff")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.stderr.startswith("review-package:"), result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
