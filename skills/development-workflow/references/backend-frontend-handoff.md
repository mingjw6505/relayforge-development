# Backend-to-frontend handoff

Use this contract when a Standard or Large task contains dependent backend and
frontend implementation. Transfer verified integration facts, not a general
progress report or a substitute for source-controlled API documentation.

For a small slice implemented by the same owner in the same context, keep the
contract/source pointers and backend check results inline; no separate file is
required. Persist the handoff when the owner or context changes, implementation
is deferred, or the contract is too broad to retain reliably in context. Reuse
canonical schemas and existing handoffs rather than duplicate them.

## Location and lifecycle

When persistence is needed, write `.relayforge/handoffs/<task-slug>/backend-to-frontend.md`, using a short,
stable task slug. The repository ignores `.relayforge/`, so the handoff remains
a local workflow artifact unless the user explicitly requests a durable public
document.

Prepare the inline or persisted handoff after backend implementation and backend
minimal checks. Update it
after any later contract change, and have the frontend owner reread the changed
sections before continuing. The Controller owns consistency between the
handoff and the implemented backend.

## Required content

Keep the handoff compact. Include only applicable changed facts below, plus
source pointers and check results; do not fill irrelevant fields mechanically:

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

For a persisted artifact include a generated-at timestamp. Identify the contract
revision when available; otherwise record the backend commit or `working-tree`
with the relevant paths/content fingerprints so later edits can be detected.

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

The frontend owner records the consumed contract revision and source pointers
(or artifact path) in its result. Before integration, the Controller compares the consumed
revision with the latest backend handoff and resolves any drift.
