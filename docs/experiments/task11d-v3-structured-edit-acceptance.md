# Task 11D V3 structured-edit acceptance

Date: 2026-08-12

Play: `The First Duty`

Checkpoint: `TASK11D-FRESH-INTERACTIVE-CODER-V3-STRUCTURED-EDIT-ACCEPTANCE`

## Published apparatus boundary

Task 11D adds a separate, candidate-only supervised lane for the fresh 14B
acceptance run:

```text
lane: QWEN25_14B_INTERACTIVE_STRUCTURED_V3_V1
worker: INTERACTIVE_PRACTICAL_CODER
policy: INTERACTIVE_BOUNDED_WORK_V1
protocol: WS_CODE_AGENT_REQUEST_PROTOCOL_V3_SINGLE_STRUCTURED_EDIT
write request: PROPOSE_TEXT_REPLACEMENT
normalizer: SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1
runtime profile: qwen25-coder-14b-katra-4096
live/default: false
```

The lane has a distinct `start-task11d-v3-interactive` selector and a fresh
`task11d-interactive-structured-existing-file/synthetic-v1` fixture. Durable
manifest, case, and transport identities must agree after restart. The exact
V3 render SHA-256 is
`d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993`.
Historical V2 remains independently selected and retains render SHA-256
`3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e`.

For a structured request, the model owns `path`, `old_text`, and `new_text`.
The evaluator preserves those values, checks existing authority and Source
Snapshot X, counts exact occurrences, applies one exact replacement in an
isolated candidate, observes effects, and generates the canonical review diff
with explicit evaluator provenance. The model never supplies diff syntax.

`TEXT_MATCH_ZERO` and `TEXT_MATCH_MULTIPLE` permit one ordinary forward
correction under the existing bounded policy. A second match failure produces
`ESCALATION_REQUIRED` with reason `STRUCTURED_EDIT_REPAIR_EXHAUSTED`.
Authority denial escalates without a correction hint. Executor/runtime state
failures remain infrastructure outcomes. Candidate validation failure is a
semantic failure and is never repaired by transport.

The fresh fixture retains the requirements-complete Task 11A semantic
contract while changing the variable under test to V3 transport. It binds the
existing independent visible and hidden validators before inference. A
candidate can advance only through both contained validators to
`AWAITING_OPERATOR_REVIEW`; no source promotion exists.

The apparatus test matrix covers exact lane/restart binding, fail-closed
protocol drift, V2/V3 separation, whole-response normalization with exact
semantic preservation, structured candidate evidence, evaluator diff origin,
source preservation, both validation phases, one bounded match correction,
repair exhaustion, authority denial, and rejection of `PROPOSE_PATCH` under
V3.

At apparatus publication time:

```text
model inferences: 0
admission sessions: 0
behavioral disposition: NOT_EVALUATED
Task 11A: UNCHANGED
Task 11B: UNCHANGED
Task 11C: UNCHANGED
```

The behavioral result is recorded below only after the apparatus commit is
published cleanly and the one fresh authorized session completes.

## Behavioral result

`PENDING_FRESH_TASK11D_SESSION`
