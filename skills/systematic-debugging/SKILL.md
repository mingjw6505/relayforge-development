---
name: systematic-debugging
description: Diagnose complex, intermittent, cross-component, or repeatedly failing technical problems when ordinary reproduce-and-fix evidence is insufficient. Do not use for a simple local bug already covered by development-workflow.
---

# Systematic Debugging

Find the cause before changing behavior. Use this specialist only when the
normal development workflow cannot localize the failure cheaply.

## Activation boundary

Use this skill for one or more of these conditions:

- the symptom is intermittent or cannot yet be reproduced reliably;
- evidence must cross process, service, network, data, build, or deployment
  boundaries;
- two attempted fixes have failed or the same failure keeps returning;
- several plausible causes remain after the first focused inspection; or
- the failure is high risk and guessing would expand its blast radius.

Do not load it for a small local bug with a direct failing test and an obvious
single-code-path cause. `development-workflow` already covers reproduce,
root-cause evidence, minimal repair, and a targeted check for that case.

## Evidence loop

1. **Reproduce** — record the smallest reliable trigger, actual result, expected
   result, and relevant environment. If it is intermittent, gather timestamps
   and distinguishing conditions instead of guessing.
2. **Locate the boundary** — trace the bad value or state backward. In a
   multi-component path, observe inputs and outputs at each boundary until the
   first divergence is known. Do not log secrets or production payloads.
3. **Form one hypothesis** — state the proposed cause and the evidence that
   would confirm or reject it.
4. **Probe minimally** — change or instrument one variable. Prefer an existing
   test, focused command, safe read-only inspection, or temporary diagnostic.
5. **Repair the cause** — make the smallest coherent production change only
   after the hypothesis is supported.
6. **Prove the repair** — rerun the original reproduction and the cheapest
   adjacent regression check. Remove temporary diagnostics unless they are a
   deliberate, safe part of the solution.

Use [root-cause tracing](root-cause-tracing.md) only when the failing value is
deep in a call chain. Use [defense in depth](defense-in-depth.md) only after the
source fix when multiple validation layers are justified. Use [condition-based
waiting](condition-based-waiting.md) for timing or polling failures.

## Failed attempts and stop conditions

- Do not repeat the same failed action without new evidence.
- Count production fix attempts, not diagnostic probes.
- After two failed fixes, reassess the boundary and assumptions before trying a
  third.
- After three failed fixes, stop changing code and raise an architecture or
  missing-context decision to the user.
- Stop earlier when the next probe needs credentials, production mutation,
  destructive access, or a product-contract decision.

## Handoff

Report the reproduction, root cause or strongest remaining hypothesis, evidence
collected, changed paths, exact focused checks, and unresolved risks. Separate
environmental or pre-existing failures from regressions caused by the task.
