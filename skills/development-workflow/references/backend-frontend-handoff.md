# Backend-to-frontend handoff

Use this contract only when a Large task contains dependent backend and
frontend implementation. The artifact transfers verified integration facts; it
is not a general progress report or a substitute for source-controlled API
documentation.

## Location and lifecycle

Write `.relayforge/handoffs/<task-slug>/backend-to-frontend.md`, using a short,
stable task slug. The repository ignores `.relayforge/`, so the handoff remains
a local workflow artifact unless the user explicitly requests a durable public
document.

Export it after backend implementation and backend minimal checks. Update it
after any later contract change, and have the frontend owner reread the changed
sections before continuing. The Controller owns consistency between the
artifact and the implemented backend.

## Required content

Keep the document compact and include:

1. **Scope and status** — task outcome, backend readiness, and what is not
   implemented.
2. **Frontend-facing contract** — operations or events, paths/topics, methods,
   authentication and authorization expectations, request fields, response
   fields, nullability, enums, formats, and compatibility behavior. Explicitly
   state when no public contract changed.
3. **Failure and state behavior** — relevant errors, status codes or error
   identifiers, validation behavior, loading/empty-state implications, and
   externally visible side effects.
4. **Integration instructions** — repository-native local startup or fixture
   path, required non-secret configuration names, mocks or sample values, and
   ordering constraints.
5. **Evidence and risks** — backend files or source-controlled specifications
   that define the behavior, exact minimal checks and results, known gaps, and
   unresolved decisions.

Include a generated-at timestamp and a contract revision identifier when the
repository has one; otherwise use the current backend commit or `working-tree`.

## Boundaries

- Record only facts supported by the implemented backend or explicitly label
  an item unresolved.
- Do not copy whole source files, logs, credentials, tokens, production data,
  or unrelated backend internals.
- Do not invent endpoint examples or field values that the implementation does
  not support.
- Prefer links or repository-relative paths to canonical schemas and generated
  clients instead of duplicating long definitions.
- A generated handoff does not authorize deployment, production access, or
  other external mutations.

## Completion signal

The frontend owner should acknowledge the artifact path and contract revision
in its result. Before integration, the Controller compares the consumed
revision with the latest backend handoff and resolves any drift.
