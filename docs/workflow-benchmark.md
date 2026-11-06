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

## Workflow metrics extension

Schema v2 retains its existing keys, pairing and quality gates. Optional
plugin_version and route_policy_version are variant attributes and may differ
between baseline and candidate. Missing versions remain unknown. Optional top-level
rubric_id must match within a pair if either record supplies it; task_id continues
to identify a fixed task and rubric for legacy records.

| Optional field | Structure and interpretation |
| --- | --- |
| route_decisions | List of rubric_id, allowed_routes (non-empty L1/L2/L3 list), actual_route (L1/L2/L3 or null) |
| route_changes | upgrades, downgrades (non-negative integers), complete (boolean), source (host_observed or agent_declared) |
| coordination | List of phase (dispatch/context/wait/integration/rework), unit (ms/tokens), value (finite non-negative number), source |
| overrouting_cost / underrouting_cost | unit, value, source and non-empty evidence_ref for attributed extra cost; omit when unknown |
| handoff | applicable, verified, disclosed counts with verified ≤ disclosed ≤ applicable; critical_fields_passed and readiness_passed (boolean or null) |

Example candidate fields, illustrative rather than measured:

~~~json
{
  "plugin_version": "0.1.9",
  "route_policy_version": "v2.1",
  "rubric_id": "fixed-task-v1",
  "route_decisions": [
    {"rubric_id": "initial-local", "allowed_routes": ["L1"], "actual_route": "L1"},
    {"rubric_id": "revealed-design", "allowed_routes": ["L2"], "actual_route": null}
  ],
  "route_changes": {"upgrades": 1, "downgrades": 0, "complete": false, "source": "agent_declared"},
  "handoff": {"applicable": 5, "verified": 4, "disclosed": 5, "critical_fields_passed": true, "readiness_passed": null}
}
~~~

Freeze allowed routes, risks, critical handoff fields and required behavior before
execution. Multiple reasonable routes may be allowed. Reveal dynamic facts in
stages and grade using only information available at each decision. Do not change
the rubric after seeing a solution. A requirement change creates a new task/rubric
version, not a corrected answer for a completed trial.

workflow_metrics groups routing by variant and policy. Accuracy, over- and
under-routing rates use scored decisions; missing actual routes reduce coverage.
Routes above the highest allowed level are over-routing; below the lowest are
under-routing; other disallowed routes are separate mismatches. No policy version
means decisions are not scored. Report both decision coverage and run coverage;
an omitted list is not a run with perfect routing.

Keep coordination samples separated by phase, unit and source. Do not add
overlapping worker time to controller waiting as task elapsed time. Route-choice
counts do not establish extra cost: attributed route costs require evidence;
missing costs are null. Incomplete route-change histories report observed counts,
not proven full-task totals. human_rework remains corrective intervention count;
the report additionally shows runs-with-rework over measured runs.

Handoff verified means facts checked, not merely headings or filled placeholders.
Unknown can be disclosed but is not verified. Use applicable fields for the
required form: ordinary L1 inline handoffs do not need nine full sections.
critical_fields_passed verifies identity, attribution, evidence, code reference,
availability and blocking disclosures. readiness_passed separately checks that
the required testing transfer is usable; a complete blocked report may pass
disclosure while failing readiness. False fails quality, null leaves it unknown,
even if acceptance booleans elsewhere are true. Field counts alone cannot prove
truth; retain supporting assessment.

## Functional and effectiveness acceptance

F covers implementation, input validation, compatibility, missing data, deduplication,
statistics and actual workflow behavior. Q requires real paired agent runs with
the fixed acceptance/risk rubric and reliable cost measurement. F passing does not
establish Q. Without such runs, report Q not evaluated; if trials failed, preserve
that failure. Unknown or failed quality never qualifies an overall cost claim.
One smoke probe or shorter entrypoint text is not a token/performance benchmark.

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
