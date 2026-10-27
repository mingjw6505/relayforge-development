#!/usr/bin/env python3
"""Guard task-branch setup and rare parallel Git worktrees without commits."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from typing import Iterable


SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ACTIVE = {"active", "exported", "integrated"}


class WorkflowError(RuntimeError):
    pass


def run(
    arguments: list[str],
    *,
    cwd: Path,
    check: bool = True,
    text: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    completed = subprocess.run(
        arguments,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=text,
        env=env,
    )
    if check and completed.returncode != 0:
        stderr = completed.stderr.strip() if text else completed.stderr.decode(errors="replace").strip()
        raise WorkflowError(f"command failed ({' '.join(arguments)}): {stderr}")
    return completed


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def repository_root() -> Path:
    completed = run(["git", "rev-parse", "--show-toplevel"], cwd=Path.cwd())
    return Path(completed.stdout.strip()).resolve()


def git_text(root: Path, *arguments: str) -> str:
    return run(["git", *arguments], cwd=root).stdout.strip()


def git_path(root: Path, argument: str) -> Path:
    value = Path(git_text(root, "rev-parse", argument))
    return (value if value.is_absolute() else root / value).resolve()


def validate_slug(value: str, label: str) -> str:
    if not SLUG.fullmatch(value):
        raise WorkflowError(f"{label} must match {SLUG.pattern}: {value!r}")
    return value


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def clean_status(root: Path) -> bool:
    return not git_text(root, "status", "--porcelain", "--untracked-files=all")


def normalize_owned_path(raw: str) -> str:
    value = raw.strip().replace("\\", "/")
    path = PurePosixPath(value)
    if not value or value == "." or path.is_absolute() or ".." in path.parts:
        raise WorkflowError(f"unsafe owned path: {raw!r}")
    return path.as_posix().rstrip("/")


def read_owned_paths(path: Path) -> list[str]:
    if not path.is_file():
        raise WorkflowError(f"missing paths file: {path}")
    values = [normalize_owned_path(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not values:
        raise WorkflowError(f"empty paths file: {path}")
    return sorted(set(values))


def path_is_owned(path: str, owned: Iterable[str]) -> bool:
    return any(path == root or path.startswith(root + "/") for root in owned)


def owned_paths_overlap(left: Iterable[str], right: Iterable[str]) -> bool:
    return any(path_is_owned(a, [b]) or path_is_owned(b, [a]) for a in left for b in right)


def changed_paths(checkout: Path) -> tuple[list[str], list[str]]:
    tracked = run(
        ["git", "diff", "--name-only", "--no-renames", "-z", "HEAD"],
        cwd=checkout,
    ).stdout.split("\0")
    untracked = run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=checkout,
    ).stdout.split("\0")
    tracked_paths = sorted({value for value in tracked if value})
    untracked_paths = sorted({value for value in untracked if value})
    return tracked_paths, untracked_paths


def patch_bytes(checkout: Path) -> tuple[bytes, list[str]]:
    tracked, untracked = changed_paths(checkout)
    with tempfile.TemporaryDirectory(prefix="relayforge-index-") as temporary:
        environment = os.environ.copy()
        environment["GIT_INDEX_FILE"] = str(Path(temporary) / "index")
        run(["git", "read-tree", "HEAD"], cwd=checkout, env=environment)
        run(["git", "add", "-A", "--", "."], cwd=checkout, env=environment)
        content = run(
            ["git", "diff", "--cached", "--binary", "--full-index", "--no-renames", "HEAD"],
            cwd=checkout,
            text=False,
            env=environment,
        ).stdout
    return content, sorted(set(tracked + untracked))


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def state_root(root: Path) -> Path:
    return root / ".relayforge" / "worktrees"


def require_ignored_runtime(root: Path) -> None:
    probe = root / ".relayforge" / ".relayforge-ignore-probe"
    completed = run(
        ["git", "check-ignore", "--quiet", str(probe)],
        cwd=root,
        check=False,
    )
    if completed.returncode != 0:
        raise WorkflowError(".relayforge/ must be ignored before workflow state is written")


def unit_state(root: Path, task: str, unit: str) -> Path:
    return state_root(root) / task / unit


def manifest_path(root: Path, task: str, unit: str) -> Path:
    return unit_state(root, task, unit) / "manifest.json"


def load_manifest(root: Path, task: str, unit: str) -> tuple[Path, dict]:
    path = manifest_path(root, task, unit)
    if not path.is_file():
        raise WorkflowError(f"missing worker manifest: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if Path(manifest["repository"]).resolve() != root:
        raise WorkflowError("worker manifest belongs to another repository")
    return path, manifest


def save_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_worker(manifest: dict) -> Path:
    checkout = Path(manifest["worktree"]).resolve()
    if not checkout.is_dir():
        raise WorkflowError(f"worker worktree is missing: {checkout}")
    actual_root = Path(git_text(checkout, "rev-parse", "--show-toplevel")).resolve()
    if actual_root != checkout:
        raise WorkflowError(f"worker path identity mismatch: {actual_root} != {checkout}")
    if git_path(checkout, "--git-common-dir") != Path(manifest["git_common_dir"]).resolve():
        raise WorkflowError("worker belongs to another Git repository")
    if git_text(checkout, "rev-parse", "HEAD") != manifest["base"]:
        raise WorkflowError("worker HEAD moved from its recorded base")
    return checkout


def command_prepare(args: argparse.Namespace) -> None:
    root = repository_root()
    require_ignored_runtime(root)
    task = validate_slug(args.task, "task")
    kind = validate_slug(args.kind, "kind")
    target = f"relayforge/{kind}/{task}"
    current = git_text(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if current == target:
        print(target)
        return
    if not clean_status(root):
        raise WorkflowError("refusing task-branch creation from a dirty checkout")
    exists = run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{target}"], cwd=root, check=False)
    if exists.returncode == 0:
        raise WorkflowError(f"task branch already exists but is not checked out: {target}")
    if exists.returncode not in {0, 1}:
        raise WorkflowError(f"cannot inspect task branch: {target}")
    base = git_text(root, "rev-parse", "HEAD")
    run(["git", "switch", "-c", target], cwd=root)
    record = root / ".relayforge" / "tasks" / task / "branch.json"
    save_manifest(
        record,
        {
            "base_branch": current,
            "base_sha": base,
            "created_at": now(),
            "repository": str(root),
            "task_branch": target,
        },
    )
    print(target)


def command_create(args: argparse.Namespace) -> None:
    root = repository_root()
    require_ignored_runtime(root)
    task = validate_slug(args.task, "task")
    unit = validate_slug(args.unit, "unit")
    branch = git_text(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch in {"main", "master"}:
        raise WorkflowError("parallel workers require a dedicated task branch")
    if not clean_status(root):
        raise WorkflowError("parallel workers require a clean primary checkout")
    base = git_text(root, "rev-parse", args.base)
    if base != git_text(root, "rev-parse", "HEAD"):
        raise WorkflowError("parallel worker base must equal primary HEAD")
    owned = read_owned_paths(Path(args.paths_file).resolve())

    manifests = state_root(root) / task
    active = 0
    if manifests.is_dir():
        for candidate in manifests.glob("*/manifest.json"):
            try:
                existing = json.loads(candidate.read_text(encoding="utf-8"))
                if existing.get("status") in ACTIVE:
                    active += 1
                    if owned_paths_overlap(owned, existing.get("owned_paths", [])):
                        raise WorkflowError(
                            "parallel worker ownership overlaps an active unit: "
                            + candidate.parent.name
                        )
            except (OSError, json.JSONDecodeError):
                raise WorkflowError(f"invalid existing worker manifest: {candidate}")
    if active >= 2:
        raise WorkflowError("refusing more than two active parallel worktrees")

    state = unit_state(root, task, unit)
    if state.exists():
        raise WorkflowError(f"worker state already exists: {state}")
    external = os.environ.get("RELAYFORGE_WORKTREE_ROOT")
    external_root = (
        Path(external).expanduser().resolve()
        if external
        else (root.parent / ".relayforge-worktrees" / root.name).resolve()
    )
    if external_root == Path(external_root.anchor) or external_root == Path.home().resolve():
        raise WorkflowError(f"unsafe parallel worktree root: {external_root}")
    checkout = (external_root / task / unit).resolve()
    if is_within(checkout, root):
        raise WorkflowError("parallel worktree must be outside the primary repository")
    if checkout.exists():
        raise WorkflowError(f"parallel worktree path already exists: {checkout}")
    checkout.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "worktree", "add", "--detach", str(checkout), base], cwd=root)

    manifest = {
        "base": base,
        "created_at": now(),
        "git_common_dir": str(git_path(root, "--git-common-dir")),
        "owned_paths": owned,
        "primary_branch": branch,
        "repository": str(root),
        "status": "active",
        "task": task,
        "unit": unit,
        "worktree": str(checkout),
    }
    save_manifest(manifest_path(root, task, unit), manifest)
    print(checkout)


def command_export(args: argparse.Namespace) -> None:
    root = repository_root()
    task = validate_slug(args.task, "task")
    unit = validate_slug(args.unit, "unit")
    path, manifest = load_manifest(root, task, unit)
    checkout = verify_worker(manifest)
    content, changed = patch_bytes(checkout)
    if not changed or not content:
        raise WorkflowError("worker has no exportable changes")
    outside = [value for value in changed if not path_is_owned(value, manifest["owned_paths"])]
    if outside:
        raise WorkflowError("worker changed paths outside its ownership: " + ", ".join(outside))
    output = Path(args.output).resolve() if args.output else path.parent / "changes.patch"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(content)
    manifest.update(
        {
            "changed_paths": changed,
            "exported_at": now(),
            "patch": str(output),
            "patch_sha256": digest(content),
            "status": "exported",
        }
    )
    save_manifest(path, manifest)
    print(output)


def current_patch(manifest: dict) -> bytes:
    checkout = verify_worker(manifest)
    content, changed = patch_bytes(checkout)
    if changed != manifest.get("changed_paths"):
        raise WorkflowError("worker changed after its patch was exported")
    if digest(content) != manifest.get("patch_sha256"):
        raise WorkflowError("worker patch content changed after export")
    return content


def command_integrate(args: argparse.Namespace) -> None:
    root = repository_root()
    task = validate_slug(args.task, "task")
    unit = validate_slug(args.unit, "unit")
    path, manifest = load_manifest(root, task, unit)
    if manifest.get("status") != "exported":
        raise WorkflowError("worker must have one exported patch before integration")
    content = current_patch(manifest)
    patch = Path(manifest["patch"])
    if not patch.is_file() or digest(patch.read_bytes()) != digest(content):
        raise WorkflowError("frozen patch is missing or does not match the worker")
    if git_text(root, "rev-parse", "HEAD") != manifest["base"]:
        raise WorkflowError("primary HEAD moved from the workers' recorded base")
    primary_tracked, primary_untracked = changed_paths(root)
    primary_changed = set(primary_tracked + primary_untracked)
    overlaps = sorted(primary_changed.intersection(manifest["changed_paths"]))
    if overlaps:
        raise WorkflowError("primary checkout already changed worker-owned paths: " + ", ".join(overlaps))
    run(["git", "apply", "--check", "--binary", str(patch)], cwd=root)
    run(["git", "apply", "--binary", str(patch)], cwd=root)
    manifest.update(
        {
            "integrated_at": now(),
            "integrated_patch_sha256": manifest["patch_sha256"],
            "status": "integrated",
        }
    )
    save_manifest(path, manifest)
    print(patch)


def command_cleanup(args: argparse.Namespace) -> None:
    root = repository_root()
    task = validate_slug(args.task, "task")
    unit = validate_slug(args.unit, "unit")
    path, manifest = load_manifest(root, task, unit)
    if manifest.get("status") != "integrated":
        raise WorkflowError("refusing cleanup before successful integration")
    current_patch(manifest)
    if manifest.get("integrated_patch_sha256") != manifest.get("patch_sha256"):
        raise WorkflowError("integrated patch identity is missing")
    patch = Path(manifest["patch"])
    reverse = run(
        ["git", "apply", "--check", "--reverse", "--binary", str(patch)],
        cwd=root,
        check=False,
    )
    if reverse.returncode != 0:
        raise WorkflowError("cannot prove the worker patch is present in the primary checkout")
    checkout = Path(manifest["worktree"]).resolve()
    run(["git", "worktree", "remove", "--force", str(checkout)], cwd=root)
    manifest.update({"cleaned_at": now(), "status": "cleaned"})
    save_manifest(path, manifest)
    print(checkout)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare", help="create one guarded primary task branch")
    prepare.add_argument("--task", required=True)
    prepare.add_argument("--kind", default="feat")
    prepare.set_defaults(handler=command_prepare)

    create = commands.add_parser("create", help="create one detached parallel worker worktree")
    create.add_argument("--task", required=True)
    create.add_argument("--unit", required=True)
    create.add_argument("--base", default="HEAD")
    create.add_argument("--paths-file", required=True)
    create.set_defaults(handler=command_create)

    export = commands.add_parser("export", help="freeze and validate one worker patch")
    export.add_argument("--task", required=True)
    export.add_argument("--unit", required=True)
    export.add_argument("--output")
    export.set_defaults(handler=command_export)

    integrate = commands.add_parser("integrate", help="apply one frozen worker patch to the primary checkout")
    integrate.add_argument("--task", required=True)
    integrate.add_argument("--unit", required=True)
    integrate.set_defaults(handler=command_integrate)

    cleanup = commands.add_parser("cleanup", help="remove one proven-integrated worker worktree")
    cleanup.add_argument("--task", required=True)
    cleanup.add_argument("--unit", required=True)
    cleanup.set_defaults(handler=command_cleanup)
    return root


def main() -> int:
    try:
        arguments = parser().parse_args()
        arguments.handler(arguments)
        return 0
    except (WorkflowError, OSError, json.JSONDecodeError) as error:
        print(f"parallel-worktree: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
