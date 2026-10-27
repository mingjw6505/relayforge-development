# Task branch

Use one task branch as the normal isolation boundary for mutating work. Record
the current branch, `HEAD`, and status. Reuse the branch only when it is already
dedicated to this task; otherwise create `relayforge/<kind>/<task-slug>` from a
clean current `HEAD` before editing.

The repository must ignore `.relayforge/` before local workflow state is
written. Resolve `scripts/parallel_worktree.py` relative to the
`development-workflow` skill directory and run it from the target repository
root. The bundled helper performs the guarded transition:

```bash
python3 "$PARALLEL_WORKTREE_SCRIPT" prepare \
  --task <task-slug> --kind feat
```

Use `fix`, `chore`, or another short kind when appropriate. If unrelated
uncommitted changes prevent a safe transition, do not stash, commit, reset, or
carry them automatically; preserve them and request a user decision. Never
create a nested task branch merely because another work surface becomes active.

Sequential implementation uses this branch and the primary checkout. Commit,
push, merge, rebase, branch deletion, and switching back remain separate
actions governed by repository rules and user authorization.
