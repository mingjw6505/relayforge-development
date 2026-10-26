---
name: finishing-development
description: Finish an implementation by offering one combined choice for full test verification, code review, commit, and push, then report each action's status accurately. Use only after implementation-complete or when the user explicitly requests one of these finishing actions.
---

# Finishing Development

Keep implementation, verification, review, commit, and push as separate states.
The user controls the four finishing actions without having to approve ordinary
development edits step by step.

## Inputs

Collect:

- implementation result and changed paths;
- minimal checks and known gaps;
- route, work surfaces, repository rules, and relevant risks; and
- any finishing actions already selected in the user's request.

## One selection point

Silence is not a selection. Treat each action as `selected`, `declined`, or
`unresolved`; never turn “not requested” into `skipped` on the user's behalf.
If the user already selected or declined all four actions, do not ask again.
Otherwise stop and ask once which unresolved actions to run:

- test verification;
- code review;
- commit;
- push; or
- skip all remaining actions.

Explain in the same prompt that push requires an existing task commit or a
simultaneous commit choice. You may recommend tests and review, but never select
them for the user. A repository, host, or organization may still impose a
stricter authorization immediately before an external mutation.

This question is the handoff for the current turn. Do not continue into any
unselected action and do not emit a final workflow-status line until every
action is resolved by the user. A non-interactive host may return the question
as its final answer and resume from the user's next message.

Execute selected actions in this order:

```text
test verification → code review → commit → push
```

## Test verification

Use repository-native commands that cover the changed surfaces. Report exact
commands, results, unrun checks, and coverage gaps. `unavailable` and `partial`
are valid evidence states. A selected verification that fails blocks selected
commit and push unless the user explicitly accepts the reported risk.

## Code review

Use an implementation-independent reviewer when available. Give it the user
outcome, acceptance criteria, final diff, and verification evidence—not the
implementer's conclusion. If independence is unavailable, label the review
non-independent.

Classify findings as `Critical`, `Important`, or `Minor`. Automatically fix and
re-review Critical and Important findings for at most three rounds. Stop early
when a fix needs new product scope, permission, or an unsafe assumption. Open
Critical or Important findings block selected commit and push. Disclose Minor
findings in the handoff.

## Commit and push

Run these only when the user selected them and all selected upstream gates are
clear.

- Commit only task-owned, reviewed paths; preserve unrelated worktree changes.
- Follow repository branch, version, message, and immediate-approval rules.
- Push only when a task commit exists and the remote and branch are clear.
- Never create an implicit commit merely because push was selected.
- A push failure does not roll back the local commit; report the recoverable
  state.

Commit and push do not imply PR creation, remote CI, merge, release, or real
deployment.

## Final status

Only after all four choices are resolved, report a concise human summary and
finish with exactly one workflow-status metadata line:

```text
Workflow status: Implementation=complete | Minimal checks=passed | Test verification=skipped | Code review=skipped | Commit=skipped | Push=skipped
```

Allowed values:

- `Implementation`: `complete`, `blocked`
- `Minimal checks`: `passed`, `failed`, `partial`, `unavailable`
- `Test verification`: `passed`, `failed`, `partial`, `skipped`, `unavailable`
- `Code review`: `passed`, `findings-open`, `skipped`, `unavailable`
- `Commit` and `Push`: `completed`, `skipped`, `blocked`, `unavailable`

If tests or review were skipped, say plainly: `实现完成，未验证` and/or
`实现完成，未审查`. Never turn a skipped or unavailable gate into a completion
claim.
