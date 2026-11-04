#!/usr/bin/env python3
"""Freeze a scoped Git diff, including uncommitted files, without changing the index."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile


def git(root: Path, *args: str, env=None) -> bytes:
    result = subprocess.run(
        ["git", "--literal-pathspecs", *args], cwd=root, env=env,
        capture_output=True, check=False,
    )
    if result.returncode:
        raise ValueError(result.stderr.decode("utf-8", errors="replace").strip())
    return result.stdout


def owned_paths(path: Path | None) -> list[str]:
    if path is None:
        return ["."]
    result = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip().replace("\\", "/")
        if not value:
            continue
        parts = PurePosixPath(value)
        if parts.is_absolute() or ".." in parts.parts or ":" in value or ".git" in parts.parts:
            raise ValueError(f"unsafe review path: {value}")
        result.append(value)
    if not result:
        raise ValueError("empty paths file")
    return sorted(set(result))


def snapshot(root: Path, base: str, target: str, paths: list[str]) -> tuple[str, str, bytes]:
    head = git(root, "rev-parse", "HEAD").decode("ascii").strip()
    base_sha = git(root, "rev-parse", "--verify", f"{base}^{{commit}}").decode("ascii").strip()
    git(root, "merge-base", "--is-ancestor", base_sha, head)
    options = ["--binary", "--full-index", "--no-ext-diff", "--no-textconv", "--no-renames", "-U10"]
    if target == "HEAD":
        diff = git(root, "diff", *options, base_sha, head, "--", *paths)
    else:
        with tempfile.TemporaryDirectory(prefix="relayforge-review-") as temporary:
            env = os.environ.copy()
            env["GIT_INDEX_FILE"] = str(Path(temporary) / "index")
            git(root, "read-tree", head, env=env)
            # HEAD does not know new ignored files explicitly staged by the user.
            # Only force-add that existing staged inventory, never all ignored files.
            staged_additions = git(
                root, "diff", "--cached", "--name-only", "--no-renames",
                "--diff-filter=A", "-z", head, "--", *paths,
            ).decode("utf-8").split("\0")
            for path in staged_additions:
                if path and os.path.lexists(root / path):
                    git(root, "add", "-f", "--", path, env=env)
            update_paths = []
            for path in paths:
                if os.path.lexists(root / path) or git(root, "ls-files", "--cached", "-z", "--", path, env=env):
                    update_paths.append(path)
                elif not (git(root, "ls-tree", "-r", "--name-only", "-z", base_sha, "--", path)
                          or git(root, "ls-files", "--cached", "-z", "--", path)):
                    raise ValueError(f"unknown review path: {path}")
                # A base-only committed deletion/rename must stay in the diff scope,
                # but cannot be passed to add when absent from both HEAD and disk.
                # A staged addition deleted from disk likewise has no final content.
            if update_paths:
                git(root, "add", "-A", "--", *update_paths, env=env)
            diff = git(root, "diff", "--cached", *options, base_sha, "--", *paths, env=env)
    if git(root, "rev-parse", "HEAD").decode("ascii").strip() != head:
        raise ValueError("HEAD moved while building the review package; retry from a stable checkout")
    return base_sha, head, diff


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="HEAD", help="Ancestor commit; pass merge-base for a branch review.")
    parser.add_argument("--target", choices=("WORKTREE", "HEAD"), default="WORKTREE")
    parser.add_argument("--paths-file", type=Path, help="One task-owned repository-relative path per line.")
    parser.add_argument("--output", type=Path, required=True, help="New package outside the checkout or in an ignored directory.")
    args = parser.parse_args()
    try:
        root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").decode("utf-8").strip()).resolve()
        output = args.output.resolve()
        manifest = output.with_name(output.name + ".json")
        for destination in (output, manifest):
            if destination.exists():
                raise ValueError(f"refusing to overwrite frozen evidence: {destination}")
            if destination.is_relative_to(root):
                git(root, "check-ignore", "--quiet", "--", destination.relative_to(root).as_posix())
        paths = owned_paths(args.paths_file)
        base, head, diff = snapshot(root, args.base, args.target, paths)
        if not diff:
            raise ValueError("empty review surface")
        metadata = {
            "base": base, "head": head, "target": args.target, "paths": paths,
            "sha256": hashlib.sha256(diff).hexdigest(), "bytes": len(diff),
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as handle:
            handle.write(diff)
        with manifest.open("x", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2, ensure_ascii=True)
            handle.write("\n")
        print(json.dumps({"package": str(output), "manifest": str(manifest), **metadata}, ensure_ascii=True))
        return 0
    except (ValueError, OSError) as error:
        print(f"review-package: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
