---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks in the current session
---

# Subagent-Driven Development

Run a fresh implementer for each independent task, a separate task reviewer,
scoped re-reviews after fixes, and one final whole-change review. This skill
does not alter Quick / Standard / Large routing. Read the plugin's
`agents/PROTOCOL.md`, role and responsibility metadata, and the current host
adapter before dispatch. The main session is the Controller.

## Setup

Use `relayforge:using-git-worktrees` to create or verify an isolated workspace.
Do not start implementation on main/master without explicit user consent.
Run `bash scripts/sdd-workspace PLAN_FILE` from this skill directory; it prints
this plan's ignored artifact directory. Keep a `progress.md` ledger there with
`# SDD ledger — plan: <plan path>` as its first line. On resume, trust the
ledger and verify its recorded Git checkpoints; never redispatch a completed
task. Preserve a pending, uncommitted checkpoint rather than assuming it is
in Git. Never touch another plan's workspace.

Read the plan and reachable spec. Preflight task dependencies and conflicts:
write one ledger row per task for internal consistency and one per pair of
tasks sharing a file or interface. The spec is binding when it and the plan
conflict. Record decisions as `Ruling: <decision> — <why> — <cost if wrong>`.
Do not silently dismiss defects mandated by plan text.

## Capability selection

The Controller chooses one role and relevant domain responsibility packs from
the brief, changed surface, risk labels, and explicit user skill requests.
Do not infer packs from Quick / Standard / Large. Before each dispatch write
`task-N-implementer-capability-map.yaml` in the plan workspace with the fields in
`agents/PROTOCOL.md`: required skill paths and reasons, excluded paths and
reasons, read/write scope, risks, and model tier.
Explicit user-requested skills take priority. Hidden domain skills are read
by exact path, not advertised as top-level skills. The child must read every
required SKILL.md completely and list actually loaded paths in its report.
If a required skill is missing, resolve that before accepting the handoff.

Use abstract model tiers: `fast` for truly mechanical 1-2-file work with a
complete spec, `standard` for integration and most reviews, `strongest` for
architecture and final review. Reviewer judgment scales with risk; use at
least `standard` for prose-based tasks. Map tiers through the active adapter
and current host allowlist, specifying model and reasoning effort when the
host supports both. Rounds 4-5 escalate one tier above the stuck implementer
where possible. Never use a stale hard-coded model name.

## Local trace

The plan workspace includes `trace.jsonl`, a git-ignored, low-volume journal.
Its scripts automatically record task and verification events. The Controller
also records each selected/loaded skill and each child dispatch/completion with
the protocol's `trace-event` helper. Keep it metadata-only: never put prompts,
commands, test output, or code in the trace. Run `trace-summary PLAN_FILE` for
event counts when investigating workflow cost or routing.

## Task loop

Batch independent, same-shape edits when one brief and one review surface
are clearer. Otherwise use one implementer per task. Never run two writers
in the same worktree. Read-only advisors may run concurrently. Separate
worktrees and non-overlapping ownership are prerequisites for parallel writers.
Children are leaves; no child may spawn another child. The implementer cannot
be its own independent reviewer.

1. Record `BASE=$(git rev-parse HEAD)` and the initial worktree status. If
   task-owned paths already contain unrelated user edits, isolate them or ask
   before proceeding; do not package or stage them as task work. Run
   `bash scripts/task-brief PLAN_FILE N` to create the authoritative brief.
   Copy the binding Global Constraints from the plan/spec into the brief;
   `task-brief` alone extracts only the task section. If the extracted task
   includes legacy `git add`/`git commit` steps, mark them as Controller
   checkpoint steps in the brief. The implementer must neither perform nor
   silently omit them. Write the `implementer` capability map and give the
   implementer paths to both, plus
   `task-N-worker-report.md`, narrow interface context, and the role prompt
   in [implementer-prompt.md](implementer-prompt.md). Do not paste the whole
   plan or accumulated task history. Record the implementer identity for
   fix-round resumption.
2. Accept `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`. For
   concerns, decide if they affect correctness before review. For missing
   context, supply it. For a blocker, change context, tier, or task split;
   do not simply repeat an unchanged dispatch. The worker report must show
   changed files, loaded skills, tests/outputs, and self-review. The worker
   must not stage, commit, amend, branch, merge, or push.
3. Freeze the review surface: list exactly the task-owned changed paths in
   `task-N-paths.txt`, one relative path per line. Run
   `bash scripts/review-package PLAN_FILE BASE WORKTREE OUTFILE PATHS_FILE`
   to capture tracked, staged, and untracked changes without mutating Git.
   `HEAD` must still equal `BASE`; if it moved, reconcile before review.
   Write a reviewer capability map with `role_id: task-reviewer`, read-only
   project scope, and only its report artifact writable. Hand the brief,
   reviewer capability map, worker report, global constraints, and
   diff package to a different read-only agent using
   [task-reviewer-prompt.md](task-reviewer-prompt.md). It returns separate
   spec and quality verdicts in `task-N-review-report.md`. Never skip the
   diff or accept a self-review as independent review. If no subagent tool
   exists, work inline but label review non-independent and surface the gap,
   especially for high-risk work.
4. Resolve review findings. Critical/Important findings and confirmed spec
   gaps enter the fix loop. Record Minor findings for final triage. For a
   plan-mandated defect, record a ruling before changing direction. Fix
   rounds 1-3 resume the same implementer (or a fresh one with the report
   path if host resumption is unavailable). Rounds 4-5 use a fresh, stronger
   implementer. Each round appends covering test command and output to the
   worker report. Refresh `task-N-paths.txt` to include any newly created fix
   files and verify it still excludes unrelated user changes. Build a new
   `WORKTREE` package with a distinct output path,
   then write a `re-reviewer` capability map and run a scoped re-review
   using [re-review-prompt.md](re-review-prompt.md). Give the re-reviewer the
   previous package and new package so it can inspect only the fix delta.
   New Critical/Important breakage joins the open findings. At five rounds,
   stop dispatching, adjudicate each open finding, and ledger every ruling.
   Never silently discard a finding or let a load-bearing defect propagate.
   The Controller does not fix code in place of the worker.
5. After a clean task review or explicit breaker rulings, prepare a commit
   packet: exact reviewed file list, tests, review verdict, remaining risks,
   and a Conventional Commits message generated by `caveman-commit` (subject
   at most 72 characters; required body for breaking/security/migration/
   revert). Read `caveman-commit/SKILL.md` before drafting. The commit skill
   only drafts text. Ask the user immediately
   before the actual commit. If approved, the Controller alone stages the
   exact files, verifies the staged diff matches the reviewed package, and
   commits. Record `Task N: complete (checkpoint <sha>, review clean)` or
   the parked findings. If approval is absent, record `Task N: reviewed,
   checkpoint pending` and pause; do not start a later task against a
   fictional Git checkpoint. Do not delete uncommitted artifacts.

Reviewer `Cannot verify from diff` items are resolved by the Controller
against cross-task context before task completion. Never ask a reviewer to
rerun a suite merely to repeat the worker's evidence. A focused diagnostic
test is allowed for a concrete doubt. Keep child chat replies short: status,
report path, test summary, blocker. File artifacts carry details.

## Final review and finish

After all task checkpoints, build a whole-branch package with
`bash scripts/review-package PLAN_FILE MERGE_BASE HEAD` and dispatch the
strongest available independent final reviewer with a `final-reviewer`
capability map using
`../requesting-code-review/code-reviewer.md`. Point it to ledgered deferred
minors and parked findings. If final review finds defects, record
`FIX_BASE=HEAD`, then dispatch one worker for the complete fix wave. Build
`review-package PLAN_FILE FIX_BASE WORKTREE` with an explicit paths file and
unique output path. The scoped re-review receives the final review findings,
the original whole-branch package for context, and this fix-only package;
it judges only the fix. This final-fix invocation uses the fix-only package,
not the task-loop same-BASE snapshot comparison. Adjudicate residuals and
disclose them. Fix-wave workers obey the same no-Git rule and require another
Controller commit packet and explicit pre-commit approval.

Before cleaning the plan workspace, collect every `Ruling:` line into the
final message in ledger order, including the cost if wrong. Delete only this
plan's workspace, only after the final review is clean and all artifacts are
represented by confirmed Git checkpoints. Then use
`relayforge:finishing-a-development-branch`. Never merge, push, publish, or
perform another external side effect without its own authorization.
