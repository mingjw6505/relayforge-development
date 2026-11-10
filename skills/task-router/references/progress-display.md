# Progress display

For software development tasks in Codex desktop, prefer the bundled progress
inline card when its tools are available. Follow the [panel contract](progress-panel.md):
start once before substantive work, retain the task ID across workflow transitions,
update meaningful milestones and record the actual final outcome. Use steps for
the agreed scope; planning-only or handoff-only work does not imply implementation.

Do not repeat the card's checklist, current-step labels or status table in chat.
Use conversation updates for useful findings, changed scope, blockers and required
user action. Keep the final reply concise: the result, relevant checks and any
remaining gap. Do not require fixed routing or finishing metadata footers.

If tools or UI are unavailable, briefly report the current work or blocker in
plain language at meaningful changes. Keep working without an installation,
permission change or retry loop. Honor requests to reduce updates. Normal host
communication requirements still apply; a panel does not replace necessary
questions, explanations or the final result.

Workflow names and tool-load evidence come from actual instruction-load receipts.
For every other Skill actually read and applied to this task (including external,
direct-file reads and host-provided instructions), include its qualified name and
read channel in `skill_uses` on the next start/update milestone. Flush any pending
use declarations before ending the task. Never report metadata discovery, planned
use or a Skill merely mentioned in chat. Use declarations stay Agent-declared,
separate from tool-load receipts and host audit evidence. Follow the linked
progress contract for namespacing, incremental updates and older-tool fallback.
Other progress fields are also Agent declarations. Preserve valid
evidence across resumes, identify invalidated checks, distinguish failed/skipped
work from completed work, and never invent completion, percentages or Skill loads.
Closing a card is not a request to keep creating replacements; show it again only when asked.
