---
name: requesting-code-review
description: Run an implementation-independent review of a completed change when the user requests code review or selects it as a finishing action. Do not activate merely because a feature is large or implementation has ended.
---

# Requesting Code Review

Review the work product against the requested behavior and concrete diff. This
skill reports and classifies findings; authorization for commit, push, or other
side effects remains separate.

## Review inputs

Give the reviewer only what changes its judgment:

- user-visible outcome and acceptance criteria;
- repository constraints and relevant risks;
- exact changed paths or a non-mutating diff package;
- verification commands and results; and
- known gaps or deferred Minor findings.

Do not give it the implementer's conclusion or the whole chat history. Use a
different agent from the implementer when the host supports independent review.
Otherwise review inline and label the result non-independent.

For committed changes, a range such as the merge base through `HEAD` can define
the surface. For uncommitted work, capture tracked, staged, and task-owned
untracked changes without staging or mutating Git. Exclude unrelated user work.

Use [code-reviewer.md](code-reviewer.md) as the reviewer contract.

## Finding levels

- `Critical`: security, data loss, broken core behavior, or an unsafe release
  condition. It blocks completion.
- `Important`: requirement gap, likely regression, material reliability issue,
  or missing proof for a core path. It blocks selected commit and push.
- `Minor`: bounded maintainability or polish issue that can be disclosed and
  deferred.

Every finding cites concrete evidence and explains impact. Push back on an
incorrect finding with code or test evidence rather than accepting it
ceremonially.

## Repair and re-review

When this skill is called from `finishing-development`, return findings to the
implementation owner. Automatically fix and re-review Critical and Important
findings for no more than three rounds. Stop sooner when the fix needs new
product scope, permission, or a material user decision. Re-review the fix delta
and affected behavior, not an unrelated broad surface.

The review passes when no Critical or Important finding remains. Disclose open
Minor findings and whether the review was independent. A passed review does not
imply tests, commit, push, CI, merge, or deployment occurred.
