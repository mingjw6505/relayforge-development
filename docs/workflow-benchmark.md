# Workflow Benchmark

Compare baseline and candidate on the same real task and acceptance rubric,
repository snapshot, exact model/reasoning settings, host/tools/permissions and
runtime environment. Begin with representative existing-project tasks; the
[router scenarios](task-router-test-cases.md) are seeds, not an executable eval.
Use isolated checkouts and fresh sessions. Repeat noisy tasks with new pair IDs;
retain failures, interruptions, rework and necessary human decisions. Do not
select only successful runs or expose prior trial solutions to later trials.

## Records and evidence

Store one JSON object per **whole task run** in an ignored local JSONL file.
`pair_id` identifies exactly one baseline and one candidate repetition. Context
fields must match within a pair; `task_id` identifies the fixed task and rubric,
not a vague task category. `model` includes reasoning settings; `environment`
identifies the host build, tools, permissions and relevant runtime configuration.
Store identifiers/hashes, not prompts, code, credentials or payloads.

```json
{"variant":"baseline","pair_id":"preference-01","task_id":"preference-v1","scenario":"full-stack","snapshot":"abc123","model":"same-model-and-effort","environment":"same-host-tools-permissions","duration_ms":1000,"tokens":1000,"human_decisions":0,"human_rework":0,"acceptance_passed":true,"required_checks_passed":true,"regressions":0,"review_required":false}
{"variant":"candidate","pair_id":"preference-01","task_id":"preference-v1","scenario":"full-stack","snapshot":"abc123","model":"same-model-and-effort","environment":"same-host-tools-permissions","duration_ms":700,"tokens":650,"human_decisions":0,"human_rework":0,"acceptance_passed":true,"required_checks_passed":true,"regressions":0,"review_required":false}
```

Required for parsing: `variant`, `scenario`, finite non-negative `duration_ms`,
and non-negative integer `human_decisions`. Pairing additionally requires all
identity/context fields above. Legacy records remain descriptive but cannot
qualify a comparison. Duplicate, missing or mismatched pairs and malformed data
are reported; overall cost claims remain unavailable until resolved.

Outcome evidence:

- `acceptance_passed`: fixed user-facing rubric checked against the resulting
  artifact by tests/independent assessment, not the implementer's self-declaration.
- `required_checks_passed`: all risk-selected gates in that same rubric passed.
  A gate waived to save cost does not satisfy the original benchmark rubric.
- `regressions`: independently observed regression count, including existing
  behavior checks; missing is unknown, not zero.
- `review_required`: determined by the fixed risk rubric. If true, or if
  `review_selected` is true, require `review_evidence: true` and an explicit
  `unresolved_critical_important` count. A non-independent review does not satisfy
  a rubric requiring an independent reviewer.
- Optional legacy `verification_selected: true` requires
  `verification_evidence: true`. Skipping selected actions never substitutes for
  acceptance or required checks.

Keep raw evidence in the local task workspace and audit sampled records. The
analyzer validates records and comparisons; it does not run agents, verify a
reviewer's independence, or establish the truth of submitted booleans. A true
field without supporting evidence is an invalid measurement.

`tokens` is optional and must come from a reliable host metric covering the task,
including children and retries; missing/null stays unknown. Duration includes
rework and necessary waiting; use one measurement definition for both variants.
`human_rework` counts corrective interventions after a delivered attempt.
Necessary product clarifications are recorded, not treated as an autonomy failure.

## Analysis

```text
python scripts/analyze_workflow_benchmark.py --input results.jsonl
```

There are no default time/token reduction targets. Establish a baseline first.
To evaluate an explicitly chosen target, add `--duration-target 25` or
`--token-target 30`; these values are examples, not plugin promises.

The report includes per-variant outcome counts and descriptive medians, matching
problems, every comparable pair and median **within-pair** percentage reductions.
All recorded trials must pair cleanly before overall reductions are reported.
Both variants must have passing quality evidence for cost-target eligibility.
Failed outcomes disqualify the claim; missing evidence is unknown. Missing token
coverage or a zero baseline makes that metric unavailable. `null` never means
passed. Per-pair metrics remain diagnostics when overall eligibility is false.

Use repeated trials and inspect variation and failures; these descriptive numbers
are not confidence intervals or proof of general performance. Confirm improvements
on held-out real tasks before adopting a new default. Schema v2 replaces v1's fixed
30%/25%/80% target keys; consumers must use `comparison.cost_comparison_eligible`
and the optional `targets` fields.

## Small executable probes

Begin with three isolated working repositories: a mechanical UI label change,
a bounded API/client filter, and an ownership-check regression. Give baseline
and candidate the same request, initial files, existing tests and host restrictions.
Use fresh agent contexts. Freeze the acceptance grader before either result is
inspected; do not provide its code or the other variant's solution to implementers.

Actually execute the changed code and existing regression tests. For the API/client
probe, exercise HTTP behavior and the client request/state functions; report browser
or target-framework coverage separately if those environments are unavailable.
Inspect the high-risk result independently and verify that an unavailable delegated
review was reported honestly. Keep requests, grading code, outputs and scoped diffs
in the isolated evidence workspace for reproducibility.

Record needed user decisions, extra plans/agents/reviews and repeated unchanged
checks along with artifact correctness. Agent-reported operation counts must be
labelled as such unless independently observed. A single probe per variant is a
smoke comparison, not a timing/token benchmark. Entry-point text size can be measured
exactly, but it is not actual token usage or proof of runtime savings. Keep missing
metrics unknown and do not infer target-host compatibility from fixture success.
