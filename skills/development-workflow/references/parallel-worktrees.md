# Parallel worktrees

A Git worktree is an exception for genuinely parallel writers, not a default
workspace for every agent or task. Read this protocol only after the execution
map identifies a real parallel candidate.

Resolve `scripts/parallel_worktree.py` relative to the
`development-workflow` skill directory, assign its absolute path to
`PARALLEL_WORKTREE_SCRIPT`, and run every command below from the target
repository root. Examples below use Bash syntax; in PowerShell use the discovered
Python interpreter (`py -3` or `python`) and native variable/line-continuation
syntax. The helper itself needs only Python and Git.

## Eligibility

Create temporary worktrees only when every condition holds:

- at least two substantial write tasks can run at the same recorded `HEAD`;
- every prerequisite of both tasks is integrated and verified in that base;
- their owned paths do not overlap;
- neither consumes the other's contract, schema, migration, generated output,
  or runtime result;
- the primary checkout is clean before dispatch;
- setup, patch integration, and cleanup cost less than the expected time saved;
  and
- the host permits a workflow-owned directory outside the repository.

Otherwise run one writer at a time in the primary checkout. Read-only advisors
and reviewers do not justify a worktree. A backend/frontend dependency that
uses the backend-to-frontend handoff is sequential and therefore ineligible.
An earlier dependency does not forbid parallelism forever: independent consumers
can become eligible after its contract and implementation are verified in a clean
checkpoint. If that prerequisite is only in the working tree, continue sequentially
there. Never manufacture a checkpoint commit or stash to unlock this optimization.

Never use more than two concurrent writers. During their work the Controller
coordinates only; it does not edit source. Workers are leaves and may not run
Git state-changing commands.

## Detached worker protocol

Put each worker's owned repository-relative paths in a file under the ignored
`.relayforge/` directory, one path per line. From the clean primary task branch:

```bash
BASE=$(git rev-parse HEAD)
python3 "$PARALLEL_WORKTREE_SCRIPT" create \
  --task <task-slug> --unit <unit-slug> --base "$BASE" \
  --paths-file .relayforge/worktrees/<task-slug>/<unit-slug>-paths.txt
```

The helper creates a detached worktree outside the repository, records exact
ownership and identity under `.relayforge/worktrees/`, and refuses more than
two active worktrees for one task. It defaults to a hidden sibling directory;
set `RELAYFORGE_WORKTREE_ROOT` only when the host requires another approved
external root. Give the printed path to that worker.

After the worker reports, freeze and validate its complete tracked, staged,
deleted, binary, and untracked change as a patch:

```bash
python3 "$PARALLEL_WORKTREE_SCRIPT" export \
  --task <task-slug> --unit <unit-slug>
```

The command rejects empty or out-of-scope changes. Review or inspect the frozen
patch, then integrate it into the unchanged primary task branch:

```bash
python3 "$PARALLEL_WORKTREE_SCRIPT" integrate \
  --task <task-slug> --unit <unit-slug>
```

Integrate one patch at a time. The helper refuses a moved `HEAD`, a changed
worker patch, overlapping primary changes, or a patch that does not apply
cleanly. Run the cross-surface checks after every patch is present.
Mark a task integrated and unblock its consumers only after the patch and required
checks are accepted. A failed integration keeps those consumers blocked. Recompute
ready tasks after the batch; the next parallel batch needs another clean, verified
base with no retained workers. Without one, continue sequentially.

## Cleanup and recovery

Clean up only after integration:

```bash
python3 "$PARALLEL_WORKTREE_SCRIPT" cleanup \
  --task <task-slug> --unit <unit-slug>
```

Cleanup verifies that the worker patch is unchanged and that the same patch is
present in the primary checkout. It removes only the exact recorded worktree;
it never runs a broad prune. If any proof fails, keep the worktree and report
its path. Never reset, clean, force-switch, or delete an unrecorded directory
to recover automatically.

Only the primary task branch may later be committed or pushed. Temporary
worker worktrees never create or publish branches or commits.
