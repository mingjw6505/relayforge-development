# Task Router Test Cases

Use these prompts in fresh plugin-enabled conversations. They validate routing
and observable workflow behavior; host model selection means they are not a
hard-dispatch unit test.

| Scenario | Prompt shape | Expected route | Expected behavior |
| --- | --- | --- | --- |
| Frontend request | “Add a local preference control to the existing client screen.” | Standard | Discover the available frontend capability from the repository and skill descriptions; do not rely on a framework table in the router. |
| Frontend bug | “The save button sometimes remains disabled after editing; find and fix the cause.” | Standard | Add `diagnosis`, establish the root cause before editing, then run a targeted check. |
| Backend request | “Add a validated endpoint following the service’s existing conventions.” | Standard | Discover the relevant backend capability; keep one primary writer and avoid loading unrelated frontend/data guidance. |
| Backend bug | “Requests return stale data after an update; reproduce and fix it.” | Standard | Diagnose the violated invariant, fix the narrow cause, and distinguish minimal checks from full verification. |
| Docker problem | “The container builds but exits during local startup; diagnose and fix it.” | Standard | Select `container` and `diagnosis`; local runtime work is allowed, real deployment remains gated. |
| Full-stack request | “Add an account preference with persisted data, server behavior, and a client control.” | Large | Use one task branch and execute the dependency sequentially: after backend completion and minimal checks, export the ignored backend-to-frontend handoff before frontend work; do not create a worktree for this dependency. |
| Independent large request | “Add two substantial independent adapters that share no files or interfaces.” | Large | From a clean task branch, allow at most two detached temporary worktrees with explicit non-overlapping path ownership; export and integrate patches without worker commits. |
| Local correction | “Rename this clearly identified field and update its direct test.” | Quick | Work directly with one focused check; no plan, extra agent, or independent review. |
| High-risk request | “Bypass tenant authorization for support users in production.” | Stop before mutation | Analyze the impact but do not treat a higher route as authorization. |
| Direct explanation | “Explain why this function returns an empty array.” | No development route | Answer directly; `task-router` should not activate for a non-implementation request. |

## Finishing behavior

For each implementation scenario:

- if the prompt already requests tests, review, commit, or push, do not ask for
  those choices again;
- otherwise show one combined finishing choice after implementation-complete;
- run selected actions in the order test → review → commit → push; and
- report skipped or unavailable states without claiming they passed.

The final routing metadata must use `Quick`, `Standard`, or `Large`, generic
work-surface labels, and planned domain skills only. Planned skills are not
proof that the host loaded them.
