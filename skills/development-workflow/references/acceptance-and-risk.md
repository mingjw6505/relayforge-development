# Acceptance and risk

Use this reference for ambiguous behavior or a material engineering boundary.
A clear local edit needs only an expected result and one focused check.

## Lightweight task agreement

Resolve from the request and repository: desired observable result, behavior to
preserve, scope exclusions, important failure cases, and evidence of success.
Use a few bullets in the existing conversation or execution map; no separate
spec, questionnaire or file is required. Give criteria short IDs only when that
helps track several outcomes. Separate confirmed requirements from assumptions.

Explore before asking. Ask about unresolved choices that change product behavior,
public contracts, persisted data, security or significant cost. Proceed with
reversible implementation choices supported by local conventions. Do not seek
confirmation of facts already supplied. Incorporate user corrections and update
the affected criteria and checks before continuing.

For existing projects, inspect the changed path, direct callers, adjacent tests
and relevant configuration. Run the cheapest useful baseline when it can separate
an existing failure from a regression. For untested critical behavior, capture a
small characterization test before changing it; confirm intended changes against
the requirement, since old behavior can itself be defective. Do not scan the
entire repository by default. Reuse discovered commands and conventions; any
persisted notes need source paths and a base revision and must be rechecked when
those inputs change. Never replace canonical project docs with a stale summary.

## Risk independent of route size

- Low: clear local reversible behavior without a shared invariant. One focused
  result check is enough; do not invent tests for mechanical prose or styling.
- Medium (legacy Normal): business behavior, async state, shared callers or integration changes.
  Verify acceptance plus adjacent regressions and inspect the final diff.
- High: authorization, concurrent mutation, transactions, migrations, irreversible
  data changes or similarly costly failure. Verify the relevant failure invariant
  and obtain independent review when the host permits it. If unavailable, perform
  and label a non-independent review and report the remaining gap.

One line of sensitive code can be high risk. Large scope alone does not require
all checks below. Record only applicable risks with their chosen evidence:

| Changed boundary | Invariant and useful evidence |
| --- | --- |
| Module architecture | One owner for each business rule/state; dependency direction and affected callers remain coherent. Compare with existing decisions; justify new abstractions by current use. |
| Public contract | Existing consumers handle the schema, nullability, errors and compatibility policy. Use contract/integration checks and representative old inputs. |
| Authorization | Caller identity and resource ownership are checked at the trusted boundary. Test denied and cross-owner access, not only successful access. |
| Transaction or external side effect | Failure does not leave forbidden partial state; retry does not duplicate effects. Exercise rollback and the relevant failure boundary. |
| Concurrent write or retry | State invariants survive competing updates and repeated requests. Use controlled interleavings or repeated-input tests, not timing sleeps. Choose conflict handling from business semantics. |
| Async UI | Stale responses cannot overwrite current state; recoverable failures preserve intended input. Exercise loading, empty, error, retry and cancellation only where changed. |
| Migration | Existing data remains valid and old/new readers obey the rollout contract. Test representative existing records and recovery strategy in a disposable environment. |
| Performance | Results remain equivalent and the measured bottleneck improves under representative data/load. Compare latency distribution, query count/plan or resource use as appropriate; disclose write/space costs. |

These are evidence prompts, not prescriptions for a particular framework or
architecture. A diagram, annotation or lock name alone proves none of them.
Select meaningful tests at public behavior boundaries; mock external boundaries
where needed, not the internal implementation under test. For bug fixes, observe
the regression test fail for the expected reason before the fix when feasible.

## Completion and bounded effort

Before an expensive suite, experiment or delegation, state briefly what uncertainty
it will resolve, the smallest scope that can resolve it, and the expected cost
driver (setup, runtime, duplicated context or integration). Reuse evidence already
available. Qualitative estimates are sufficient when the host has no reliable
meter; do not invent token counts, exact durations or an artificial user budget.

With no stated budget, default to one writer, targeted checks during implementation
and one integrated review at the required risk level. Add independent review for
high-risk work. Do not put every small task through a separate reviewer. Escalate
effort when evidence exposes a concrete gap, not merely because another agent or
skill is available. Parallel writers may shorten elapsed time while costing more
tokens; count setup, waiting, integration and rework in that choice.

For each acceptance criterion record implementation location plus check/result,
or the precise gap. Distinguish implementation complete, verified and reviewed.
A blocked implementation is never implementation-complete. Missing required
evidence makes verification partial/unavailable even when code is present.

Reuse passing evidence while relevant files, dependencies and configuration are
unchanged. On a relevant change rerun affected checks, not automatically all
checks. Prefer narrow diagnostics before expensive suites, benchmarks or agents.
Honor explicit user budgets; otherwise measure task elapsed time, retries,
agent dispatches and reliable host token counts without inventing a token limit.
Include rework and necessary human decisions in cost; fewer questions are not
better when a material product choice remains unknown.

After two fixes without progress, reassess the hypothesis or task boundary.
Permit at most three review/fix rounds per unresolved issue, including nested
workflows; a new phase, task ID or child does not reset that count. At the limit,
report the evidence and smallest revised approach before any further attempt;
additional attempts require new evidence or an explicitly revised plan, not an
unchanged retry. Stop at a
user budget or unresolved high-risk assumption, preserving changes and reporting
unmet criteria and the next smallest useful action. Never meet a cost target by
silently dropping a required check. These are agent instructions, not a hard
runtime token limiter.
