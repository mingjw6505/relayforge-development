---
name: frontend-patterns
description: Use only for nontrivial React or Next.js work involving component architecture, state ownership, effects, data fetching, forms, routing, accessibility, or render performance. Never use for a mechanical copy, prop, markup, or single-expression change that follows existing code.
metadata:
  origin: ECC
---

# Frontend Patterns

Follow the repository's component, styling, state, data-fetching, and test
conventions. Add a pattern only when the task creates a real design decision.

## Scope first

- Identify the user-visible state, data owner, interaction boundary, and
  loading, empty, error, and success states affected by the change.
- Read adjacent components and hooks before creating new abstractions.
- Preserve server/client component boundaries and routing conventions.
- Skip this skill for a mechanical change already determined by the contract.

## Components and state

- Keep components focused on one responsibility; prefer composition over
  configuration-heavy components.
- Keep state as local as possible and lift it only for real shared ownership.
- Derive values during render when possible instead of synchronizing duplicate
  state in an effect.
- Use reducers for related transitions with invariants, not as a default for
  every group of fields.
- Keep list keys stable and based on identity, never array position when items
  can move, appear, or disappear.

## Effects and async data

- Use effects only to synchronize with something outside React. Include all
  dependencies and clean up subscriptions, timers, observers, and in-flight
  work where relevant.
- Avoid request races and stale updates. Reuse the repository's query/cache
  layer rather than creating an ad hoc second cache.
- Represent loading, empty, error, and success states explicitly. Preserve old
  data during refresh only when that interaction is intentional.
- Do not put secrets or trusted authorization decisions in client code.

## Forms and interactions

- Give controls programmatic labels, keyboard behavior, visible focus, and
  appropriate semantic elements before adding ARIA.
- Keep validation messages tied to their fields and preserve entered data after
  recoverable failures.
- Disable duplicate submission while preserving a clear progress state.
- Treat server validation as authoritative; client validation improves feedback
  but is not a security boundary.

## Performance

- Measure or identify an actual expensive path before adding memoization.
- Keep memo dependencies correct; unstable object/function props can erase the
  benefit.
- Avoid copying large dependencies into the client bundle. Prefer route or
  component-level lazy loading only where it improves a real boundary.
- Virtualize only genuinely large lists and preserve accessibility semantics.

## Focused verification

Choose checks proportional to the changed interaction:

- the expected state renders from the public props or data contract;
- keyboard and focus behavior work for changed controls;
- loading, empty, error, and success paths remain reachable;
- effects clean up and do not loop or race;
- changed responsive layouts remain usable at their supported breakpoints; and
- repository-native type, lint, component, and focused browser tests pass.

Report full-suite or cross-browser verification as an optional finishing action
unless the user already selected it.
