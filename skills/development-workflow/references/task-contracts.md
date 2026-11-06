# Task contracts and context recovery

Use existing plans/checkpoints, not a new task database. A coordinated task needs
ID, goal, owned paths, owner, prerequisites, consumed/produced contracts with
revision, acceptance, checks, status and evidence pointers. Adapt the format.

~~~yaml
id: API-001
goal: Provide the agreed order details behavior
owner: primary
scope: [backend/orders/]
dependencies: []
contract:
  revision: order-detail-v1
  consumes: []
  produces: [GET /api/orders/{id}]
acceptance: [AC-001, AC-002]
verification: [order behavior tests, adjacent regression checks]
status: pending
evidence: []
~~~

Before dispatch reject missing/cyclic prerequisites, overlapping ownership and
unstable mutually consumed contracts. Readiness requires integrated prerequisites
and passed required checks; a worker's DONE statement is insufficient.
For parallelism also apply the existing parallel-worktrees protocol: same clean
verified base, independent paths/contracts/runtime, at most two writers and a
coordinating Controller that does not edit.

When behavior, API or data semantics change, advance the contract revision and
reassess affected direct and transitive consumers. Pause those consumers, identify
invalidated evidence, then refresh and reschedule. Unrelated ready tasks continue.
Do not erase old results or reset status indiscriminately.

When the user removes a task from scope, retain its record and reason in the
plan's exclusions and remove it from the dispatch set. Reassess dependent tasks;
do not mark excluded work integrated or dispatch an old pending item merely
because its previous prerequisites are satisfied. No new task-state enum is needed.

Implementation errors stay with the implementer; contract errors go to the primary
coordinator; architecture errors need bounded architecture analysis; integration
errors return to relevant tasks. Two unsuccessful fixes trigger reassessment;
the three-round review/fix limit is shared across phases, task IDs and children.

Before context handoff persist the source spec pointer, base and working snapshot,
mode/risk, route history, task states, owners, contract revisions, valid evidence,
failure counts, blockers, authorization and next ready task. Keep task_run_id and
event sequence here if logging is enabled. On resume inspect the actual checkout
and changes against those pointers before dispatching; never redo completed work
solely because a fresh context started.
