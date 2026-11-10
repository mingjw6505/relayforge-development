---
name: finishing-development
description: Finish implementation with minimal checks and user-selected extra tests, review, handoff or authorized commit/push. Use after implementation or when these finishing actions are requested.
---

# Finishing Development

Use existing acceptance, risk, baseline, finishing choices and authorization.
Default to minimal finishing; extra work follows the user's selection.

Read and apply [progress display](../task-router/references/progress-display.md)
when entering finishing, including direct selection. Update the task's inline card
with its actual outcome; keep the final reply concise and evidence-based.

Preserve the selected L1/L2/L3 `execution_mode` when entering finishing. Update
only already-selected method tracks to their actual finishing phase where one
exists; do not add optional reviews or publication phases. Follow the
[mode/method contract](../task-router/references/progress-panel.md#mode-method-progress-and-concrete-action):
explicitly end declared method tracks before ending the task, without converting
unfinished phases to done or partial verification to passed.

## Choose finishing scope once

Reuse choices already stated in the request or conversation, including exclusions
and time limits. Do not ask again because a phase, route or session changed.
Otherwise offer one compact choice before starting optional work, in the user's
language, for example: "收尾默认精简（推荐）；可加选：补充测试 / 代码审查 /
交接文档 / commit / push。需要哪些？" Use the host's question tool when available;
if it cannot represent multiple selections, allow a free-text combination.
Complete the minimal checks while awaiting the answer; wait for the selection
before optional work. If interactive choice is unavailable, report the minimal
result and skipped extras. Silence or a preselected option is not authorization.

| Scope | Work |
| --- | --- |
| Minimal (recommended) | Check task scope and result, reuse valid evidence, run missing required checks, and give a short inline outcome with gaps |
| Extra tests | Run selected additional tests within the agreed scope/budget; no automatic full suite |
| Code review | Review the actual changes using the risk guidance below |
| Handoff document | Use delivery-handoff to create/update the full testing handoff |
| Commit / push | Perform only the separately selected or previously authorized action, subject to its gates |

"Full finishing" selects extra tests, review and the handoff document; it does
not itself authorize commit or push. Route size alone adds no optional step.
Keep the selection in the current task context; no new configuration file is needed.

Repository-mandated checks and explicit acceptance/review requirements still apply
in minimal mode. Explain any remaining required cost or gate. If the user declines
a required check, record skipped/partial and its effect on delivery/publication;
do not claim it passed or bypass a non-waivable repository rule. Risk-based
recommendations beyond those requirements are optional, with gaps disclosed.

## Evidence and review

Map required outcomes to the integrated result, not the sum of child reports.
Reuse a passed check while its relevant source, dependencies and configuration
are unchanged. Run missing/invalidated required checks and selected extras; a
full suite needs a repository/acceptance requirement or the selected test scope.
Preserve unrelated baseline failures separately.
Unavailable credentials, required external mutation or an exceeded budget leaves
a gap requiring the relevant decision, not a fabricated pass.

Apply this table when review is selected or required; minimal result inspection
does not automatically start a separate review phase.

| Change | Review scope |
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
For a selected/required review, record revision and scoped content/hashes; later
relevant changes invalidate it. Missing starting evidence limits attribution and
must be disclosed.

Bind each check to command/method, result, scope, evidence pointer and the actual
code inputs: commit for committed results, or base/HEAD plus scoped content hashes
or a frozen package for working changes. Same HEAD does not prove unchanged code.
Include relevant dependency/configuration identifiers. Use existing review_package
or direct file fingerprints, not a new snapshot engine. A hash identifies content;
it does not make that content accessible to a testing agent.

Keep generated handoffs/logs outside the code snapshot unless they are themselves
delivered artifacts; record those separately to avoid self-referential hashes.
Verification statuses are passed/failed/not_run/skipped/unavailable; give a reason
for skipped or unavailable checks and do not convert missing evidence into success.

Read [review surface](references/review-surface.md) only when a reviewer needs a
portable frozen diff, Git states are mixed, or the upstream `code-review` skill is
being considered. Direct inspection is enough for ordinary local work. The upstream
skill's HEAD-only diff cannot prove coverage of uncommitted work; do not commit or
edit an upstream skill merely to make its review work. Use a disclosed direct
review fallback when its inputs, prerequisites or delegation policy do not fit.

## Authorized publication

Reuse existing authorization, including explicit selections above. If commit/push
were not selected or requested, mark them skipped; no separate publication prompt.
For an authorized commit, stage
only task-owned changes and check them against the reviewed snapshot, following
repository version/message rules. Required gates must pass or an allowable gap
must be explicitly accepted. Preserve unrelated changes.

Push needs its own authorization, an existing task commit and a clear destination.
A push-only request does not authorize a new commit. Neither action authorizes a
merge, release, deployment, branch deletion or switching branches. Preserve and
report the local commit if a push fails.

## Report proportionally

Give a concise inline outcome by default. Only when a full handoff is selected,
explicitly requested or required by repository rules, use
[delivery-handoff](../delivery-handoff/SKILL.md). Pass actual changed files,
direct/indirect impact with evidence or Unknown, upstream acceptance mapping,
test suggestions, executed verification, environment, Git/snapshot references and
known gaps. Do not rerun checks merely to fill the handoff.

L1/L2/L3 all use inline changes, impact, verification, gaps and code availability
unless a full handoff is selected or required. Do not generate a handoff file,
portable review package or separate evidence report solely because of route size.
Use scoped content fingerprints for local evidence; freeze a package only for
a selected/required review or transfer that needs it. Missing
required implementation or critical gates cannot be hidden as ready_with_issues.
Implementation completion and downstream code availability are separate facts.

State outcome, verification scope, material gaps and review independence. For a
substantial task include the method choice and any measured cost/limit; a Quick
task needs no process essay. `passed` means the agreed risk-proportional scope
passed, not every possible test. Declined required checks stay skipped/partial.

Use natural language for the final outcome and relevant check results. Do not
require a fixed finishing-status footer or repeat every unselected operation.
When recording structured declarations, retain the existing status enums and
separate implementation, verification, review and publication outcomes.

Label a passed non-independent review explicitly. Missing required independence
is unavailable. If a required gate is missing, say `实现完成，未验证` or
`实现完成，未审查` as applicable. Never describe blocked implementation as complete.
