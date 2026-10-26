# Task Router Test Cases

Use these fixed prompts in a fresh Codex conversation with the plugin enabled.
They check workflow selection, not whether a host chose to load the router.

| Scenario | Prompt shape | Expected route | Expected skills or behavior |
| --- | --- | --- |
| Local correction | "Rename this clearly identified field and update its direct test." | Quick | Direct work and the smallest relevant test; no plan, subagent, review, or commit workflow. |
| Code explanation | "Explain why this function returns an empty array." | Quick | Direct explanation without a development workflow. |
| Node endpoint | "Add a validated endpoint to the existing Express service." | Standard | `backend-patterns`; inspect adjacent routes and run relevant tests. |
| Full-stack feature | "Add an account preference that has an API, persisted query, and React screen." | Standard | Combine `backend-patterns`, `sql-optimization` when query/index work is real, and `frontend-patterns`; add `frontend-design` only for new visual direction. |
| Failed test | "This test started failing after the cache change; find and fix the cause." | Standard | `systematic-debugging`, then any domain skill required by the root cause. |
| Container optimization | "Reduce the Docker image size without changing runtime behavior." | Standard | `multi-stage-dockerfile`. |
| Explicit plan | "Write an implementation plan for this feature." | Standard | `writing-plans` because the user explicitly requested a plan. |
| Explicit review | "Independently review this change for regressions." | Standard | `requesting-code-review` because the user explicitly requested review. |
| Permission change | "Allow support staff to bypass the tenant authorization check." | Stop normal routing | Explain the security impact and obtain the necessary authorization before implementation. |

The host may directly select an existing skill without loading `task-router`.
That is an inherent best-effort limitation of model-based Skill selection, not a
test failure.
