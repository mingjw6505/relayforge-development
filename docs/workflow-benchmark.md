# Workflow Benchmark

Compare the current released workflow (`baseline`) with the candidate workflow
using the six implementation scenarios in
[task-router test cases](task-router-test-cases.md). Use the same model tier,
repository snapshot, permissions, and equivalent prompt for each pair.

## Record format

Write one JSON object per run to a local JSONL file under the ignored
`.relayforge/benchmarks/` workspace. Do not include prompts, source code,
credentials, or tool payloads.

```json
{"variant":"candidate","scenario":"frontend-request","duration_ms":8400,"tokens":3200,"human_decisions":0,"verification_selected":true,"verification_evidence":true,"review_selected":false}
```

Required fields:

- `variant`: `baseline` or `candidate`;
- `scenario`: stable scenario name;
- `duration_ms`: non-negative wall-clock duration; and
- `human_decisions`: number of mid-course questions that required a user choice.

Optional fields:

- `tokens`: reliable host-reported total only;
- `verification_selected` and `verification_evidence`;
- `review_selected`; and
- `unresolved_critical_important`.

Do not estimate unavailable token usage. The analyzer reports the token target
as unavailable unless every baseline and candidate run has a reliable value.

## Analyze

```bash
python3 scripts/analyze_workflow_benchmark.py --input .relayforge/benchmarks/results.jsonl
```

The report compares median duration and tokens, the percentage of candidate
runs needing no mid-course decision, and selected quality-gate evidence. The v1
targets are:

- median token reduction of at least 30%;
- median duration reduction of at least 25%;
- at least 80% of clear tasks need no mid-course user decision;
- every selected verification has evidence; and
- selected reviews have no unresolved Critical or Important finding.

Run multiple repetitions when model or tool latency is noisy. Keep raw records
outside the repository unless the user explicitly requests a checked-in result.
