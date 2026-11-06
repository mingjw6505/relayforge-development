# Progress in the conversation

When the host supports intermediate messages, show a compact progress view in
the user's language for core workflow work, including standalone planning,
finishing and testing handoffs. Use the task's actual work and selected workflows;
this is an agent-maintained declaration, not a host-observed trace of Skill loads.
Do not invent stages, completed work, verification or a percentage. A planned
Skill is not evidence it was invoked.

Read and apply this reference when entering a core workflow. Once the requested
outcome is understood, show the meaningful steps already known and the current
step; do not wait for routing to finish. Direct invocation does not require
running the router. Reuse one progress view across core workflows rather than
starting a new checklist at each entrypoint. Keep step names stable while their
scope is unchanged so the user can follow transitions.

Use a short list or compact status line. Name the current workflow in ordinary
language; include its Skill identifier when it helps identify which workflow is
running. For example, during implementation:

```text
工作流：开发（development-workflow）
进度：✓ 明确需求 | ▶ 实现进度展示 | ○ 验证与交付
当前：正在实现对话中的进度更新。
```

| Display | Meaning |
| --- | --- |
| ✓ Completed | Supported by completed work or evidence |
| ▶ In progress | Work actually underway |
| ○ Pending | Known remaining work within the agreed scope |
| ⏸ Blocked / waiting | Cannot proceed until the stated dependency or decision is resolved |
| ✗ Failed | A check or attempted action failed; its result remains visible |
| — Skipped / not applicable | Omitted with a reason; never counted as completed |

Use descriptive names rather than assuming every task needs design, tests,
review, commit or push. Only list a workflow as completed after it actually ran;
omit unselected workflows. Planning-only work ends with a checked plan, not
pending implementation. A handoff-only request ends with the actual handoff
status, without claiming the underlying implementation or tests were performed
in this run. Statuses of checks, review, commit and push must agree with finishing
evidence and authorization. Unrequested publication is not outstanding work.

Update when a meaningful step completes, the current step changes, the plan
changes, or work becomes blocked; combine nearby changes into one concise
message. Keep progress current during long operations according to host guidance;
do not emit a message for every tool call or delay work solely to display one.
For a blocked step, state what is needed and the next action; show independent
work as current if it can proceed. After a failed check, keep its failure visible
until an applicable recheck passes; completing a fix alone does not pass the check.
When new facts change the plan, revise the remaining steps without erasing valid
completed work; identify invalidated work or evidence. On resume, check the
available plan and actual evidence before reporting earlier work as complete.
Persist only necessary state in an existing plan/checkpoint for deferred or
multi-session work; this display does not require a separate progress file.

The final response closes the progress view with the outcome, verification and
remaining gaps or blockers; use one compact line if useful rather than repeating
the whole checklist. Claim no remaining work only within the agreed scope. If
intermediate messaging is unavailable, include the same truthful status in the
final response instead.
Honor user preferences to reduce or omit updates. This display needs no Hook,
logger, network service or extra model call, and cannot guarantee that the host
will select a plugin Skill or render an intermediate message.
