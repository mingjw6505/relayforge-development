---
name: finishing-development
description: Reconcile acceptance and risk-proportional verification, review the actual changes and perform only authorized commit/push actions. Use after implementation or when these finishing actions are requested.
---

# Finishing Development

Use existing acceptance, risk, baseline and authorization. Finish required checks
without another questionnaire. Honor exclusions and report resulting gaps.

## Evidence and review

Map required outcomes to the integrated result, not the sum of child reports.
Reuse a passed check while its relevant source, dependencies and configuration
are unchanged. Run missing/invalidated checks; full suites only when repository
rules or blast radius require them. Preserve unrelated baseline failures separately.
Unavailable credentials, required external mutation or an exceeded budget leaves
a gap requiring the relevant decision, not a fabricated pass.

| Change | Default review |
| --- | --- |
| Low-risk mechanical edit | Focused result check; code review may be skipped |
| Ordinary behavior change | Controller inspects requirements conformance and engineering quality |
| High-risk invariant or explicit independent-review requirement | One bounded independent reviewer when available; provide existing evidence, do not have it rerun suites without a concrete doubt |

If independence is unavailable, label self-review and the gap. A missing required
independent review blocks selected commit/push until resolved or explicitly accepted.
Material findings block publication; minor preferences do not trigger rewrite loops.
Fix in-scope defects and recheck affected evidence. Review only the fix delta and
newly affected contracts. Share development-workflow's three-round limit per issue;
two attempts without progress require reassessment, and user budgets take precedence.

Cover the actual task result: committed, staged, unstaged and task-owned untracked
files, including deletions/renames. Compare with the starting revision and existing
change baseline, exclude unrelated work and identify mixed ownership before staging.
Record revision and content/hashes; later relevant changes invalidate the affected
review. Missing starting evidence limits attribution and must be disclosed.

Read [review surface](references/review-surface.md) only when a reviewer needs a
portable frozen diff, Git states are mixed, or the upstream `code-review` skill is
being considered. Direct inspection is enough for ordinary local work. The upstream
skill's HEAD-only diff cannot prove coverage of uncommitted work; do not commit or
edit an upstream skill merely to make its review work. Use a disclosed direct
review fallback when its inputs, prerequisites or delegation policy do not fit.

## Authorized publication

Reuse existing authorization. If commit/push were not requested, finish with them
skipped; do not ask a finishing-choice question. For an authorized commit, stage
only task-owned changes and check them against the reviewed snapshot, following
repository version/message rules. Required gates must pass or an allowable gap
must be explicitly accepted. Preserve unrelated changes.

Push needs its own authorization, an existing task commit and a clear destination.
A push-only request does not authorize a new commit. Neither action authorizes a
merge, release, deployment, branch deletion or switching branches. Preserve and
report the local commit if a push fails.

## Report proportionally

State outcome, verification scope, material gaps and review independence. For a
substantial task include the method choice and any measured cost/limit; a Quick
task needs no process essay. `passed` means the agreed risk-proportional scope
passed, not every possible test. Declined required checks stay skipped/partial.

Use the existing declared-status vocabulary:

```text
Workflow status: Implementation=complete | Minimal checks=passed | Test verification=passed | Code review=skipped | Commit=skipped | Push=skipped
```

Allowed values: Implementation `complete|blocked`; Minimal checks
`passed|failed|partial|unavailable`; Test verification
`passed|failed|partial|skipped|unavailable`; Code review
`passed|findings-open|skipped|unavailable`; Commit/Push
`completed|skipped|blocked|unavailable`.

Label a passed non-independent review explicitly in prose. Missing required
independence is `unavailable`. If a required gate is missing, say `实现完成，未验证`
or `实现完成，未审查` as applicable. Never describe blocked implementation as complete.
