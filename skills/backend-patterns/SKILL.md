---
name: backend-patterns
description: Use only for nontrivial Node.js, Express, or Next.js API architecture involving validation, middleware, data access, transactions, caching, or error handling. Never use for Java or Spring code, a mechanical DTO or field change, or an existing straightforward handler that needs no architectural decision.
metadata:
  origin: ECC
---

# Backend Patterns

Apply repository-native backend conventions before introducing a pattern. This
skill supplies decision checks, not a mandatory layered architecture.

## Scope first

- Confirm this is Node.js, Express, or a Next.js API surface.
- Read the existing route, service, data-access, validation, error, and test
  conventions that touch the change.
- Identify the public contract, trust boundaries, persisted state, and failure
  behavior before editing.
- Skip this skill when the change is mechanical and the repository already
  determines the implementation.

## Contract and validation

- Keep transport DTOs separate from database rows when their stability or
  exposure differs.
- Validate untrusted path, query, body, header, and external-service data at
  the boundary. Normalize only when the contract explicitly allows it.
- Preserve status codes, error shapes, pagination, ordering, idempotency, and
  compatibility unless the task changes them.
- Never expose stack traces, internal identifiers, secrets, or raw database
  errors to clients.

## Ownership and layers

- Keep routing thin when business rules are reused or complex; put those rules
  in the smallest existing service/module that owns them.
- Keep persistence details behind the repository's established data-access
  boundary. Do not add a repository abstraction for a single simple query if
  the codebase does not use one.
- Pass explicit dependencies where testability or lifecycle matters. Avoid new
  global mutable state.
- Keep one source of truth for authorization and tenant scoping; enforce it
  before reading or mutating protected records.

## Data, concurrency, and side effects

- Select only required columns and avoid unbounded reads or N+1 query loops.
- Use a transaction when multiple writes must succeed or fail together.
- Make retries safe: distinguish idempotent operations and prevent duplicate
  external effects.
- Cache only with an explicit key, lifetime, invalidation rule, and ownership.
  Do not cache sensitive data by default.
- Bound queues, pagination, payload sizes, timeouts, and concurrency at the
  closest reliable boundary.

## Errors and observability

- Map expected domain failures to stable client responses in one established
  error boundary.
- Preserve the original cause for internal logging without leaking it to the
  response.
- Log operational context, not credentials or complete sensitive payloads.
- Make timeout, cancellation, and partial-failure behavior explicit when
  calling downstream services.

## Focused verification

Choose the cheapest checks that exercise the changed contract and failure path:

- validation accepts valid boundary cases and rejects invalid input;
- authorization and tenant scope cannot be bypassed;
- the success response preserves its documented shape;
- expected failures keep their status and error shape;
- transactions, retries, and cache invalidation behave as designed; and
- the repository-native type, lint, and focused test commands pass.

Report any broader checks as optional finishing verification rather than
silently running them.
