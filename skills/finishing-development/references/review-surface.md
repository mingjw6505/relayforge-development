# Review surface

Read only for mixed Git states, a portable independent review or compatibility
with the upstream review skill. Do not package every mechanical edit.

Record the task's starting revision, pre-existing changes and exact owned paths.
Review the final aggregate while preserving unrelated work. A committed HEAD diff
omits uncommitted edits; a working diff alone omits task commits and new files.

## Optional frozen package

Resolve [review_package.py](../scripts/review_package.py) relative to this skill,
then run it from the target repository using its available Python interpreter:

```text
python <absolute-review-package-script> --base <task-start-sha> --target WORKTREE --paths-file <owned-paths.txt> --output <new-review.diff>
```

The paths file lists task-owned repository-relative files/directories, one per line.
Use explicit paths when unrelated changes exist. `WORKTREE` captures the net result
from the ancestor base through current files, including committed, staged, unstaged,
new and deleted content; superseded staged content is not the final result.
`HEAD` captures committed changes only. The helper uses a temporary index and does
not change the real index or create a commit. It writes a checksum manifest beside
the diff and refuses empty surfaces, unsafe paths and overwriting frozen evidence.
Output must be outside the checkout or in an ignored workflow directory.

Pause writers during capture. The package is evidence, not an attribution engine:
same-file pre-existing edits still need reconciliation against the initial baseline.
Give reviewers the package, acceptance and existing test evidence. After changes,
create a new package and inspect the delta; never reuse a stale passed verdict.

## Upstream compatibility

Read [code-review](../../code-review/SKILL.md) only when considering its two-axis
workflow. Verify its tracker inputs, fixed point, spec and delegation requirements.
Use it when its committed-diff surface covers the task. Its current HEAD-only
implementation cannot consume this package as a replacement diff automatically.
For uncommitted/mixed work use a direct scoped review with an independent read-only
agent when required/available, and disclose that fallback. Do not modify the
upstream skill, imply it ran, or commit solely to satisfy it.
