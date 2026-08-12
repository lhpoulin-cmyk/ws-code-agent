# Task 10Z interactive/practical coder boundary

Date: 2026-08-11

Play: `Chain of Command`

Checkpoint: `TASK10Z-DEFINE-14B-INTERACTIVE-WORK-BOUNDARY`

Task 10Z defines `INTERACTIVE_BOUNDED_WORK_V1`, the supervisor-owned operating
boundary for the Qwen2.5-Coder 14B `INTERACTIVE_PRACTICAL_CODER`. It changes
routing and durable state only. It does not alter model-visible content, the
bounded fence normalizer, parsing, execution, validation, or authority.

## Foundation

The clean, direct-origin-parity starting checkpoints were:

```text
ws-code-agent: 9efdeda131662252dfcf41793be79617ad1893df
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp:         c6138913d39502dbf1507c7318002b4ab748d0b1
```

Before implementation, ws-code-agent passed all 148 tests, the separate
two-test private-material gate, containment, lineage, invariant-register,
YAML, and diff gates. All eight gpu-compute suites and both ws-cp containment
tests passed. The peers remained read-only and unchanged.

## Interactive entry contract

The durable entry binding requires every gate below before inference:

```text
policy: INTERACTIVE_BOUNDED_WORK_V1
work role: INTERACTIVE_PRACTICAL_CODER
requirements_status: COMPLETE
repository count: 1
objective: explicit
read authority: explicit
patch authority: explicit
validation descriptors: bound before inference
source snapshot: clean and frozen
artifact/runtime: accepted exact 14B binding
runtime profile: qwen25-coder-14b-katra-4096
adapter: SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1 only
```

An absent or unresolved requirements assertion fails before fixture/session
materialization as
`INTERACTIVE_ENTRY_DENIED_REQUIREMENTS_UNRESOLVED`. The recommended target is
`DELIBERATIVE_OVERNIGHT_CODER_OR_OPERATOR`; the application does not invoke a
worker automatically. A missing validation contract also denies entry. The
entry binding is persisted in the session manifest, case journal, and session
state so restart cannot silently alter it.

Requirements-complete small functions, bounded named-file changes, approved
mechanical refactors, explicit bug fixes, explicit tests, and repairs against a
declared expected result are appropriate operator-classified shapes. Unresolved
product decisions, architecture selection, cross-repository authority,
requirements discovery, conflicting specifications, open-ended redesign,
security-policy interpretation, and high-consequence migrations default to
operator review or the deliberative/overnight worker. These examples are
operator-facing routing doctrine and are not added to model-visible prompts.

## Progression and state transitions

Normal progression remains:

```text
READ / SEARCH
authorized PROPOSE_PATCH
isolated candidate
visible validation
hidden validation
operator review
```

One `PATCH_REJECTED` produces `REPAIR_OPPORTUNITY`, permitting exactly one
ordinary next turn with the existing bounded executor projection. It is not an
inference retry. Two rejected patches, or a rejected patch followed by
`NO_CHANGE` or unrelated non-progress, stop the session.

The supervisor preserves distinct durable states:

| Evidence | Classification/state | Reason or next authority |
| --- | --- | --- |
| accepted candidate, validation pending | `VALIDATION_REQUIRED` | evaluator validation |
| candidate and both validators pass | `INTERACTIVE_CANDIDATE_VALIDATED` / `AWAITING_OPERATOR_REVIEW` | operator |
| valid `REQUEST_CLARIFICATION` | `OPERATOR_CLARIFICATION_REQUIRED` | operator pause |
| two rejected patches | `ESCALATION_REQUIRED` | `PATCH_REPAIR_EXHAUSTED` |
| rejected patch then `NO_CHANGE` | `INTERACTIVE_RECOVERY_FAILED` / `ESCALATION_REQUIRED` | `NO_CHANGE_AFTER_PATCH_REJECTED` |
| true authority violation | `INTERACTIVE_AUTHORITY_MISJUDGMENT` / `ESCALATION_REQUIRED` | `AUTHORITY_MISJUDGMENT` |
| invalid ambiguity handling | `INTERACTIVE_REQUIREMENTS_JUDGMENT_FAILED` / `ESCALATION_REQUIRED` | `REQUIREMENTS_JUDGMENT_FAILED` |
| turn limit | `ESCALATION_REQUIRED` | `TURN_LIMIT` |
| model repeat limit | `ESCALATION_REQUIRED` | `MODEL_REPEAT_LIMIT` |
| validation contract failure | `ESCALATION_REQUIRED` | `VALIDATION_FAILED` |
| validation/executor apparatus failure | `INFRASTRUCTURE_REPAIR_REQUIRED` | operator repairs infrastructure |

The complete structured escalation reason enum is:

```text
PATCH_REPAIR_EXHAUSTED
NO_CHANGE_AFTER_PATCH_REJECTED
AUTHORITY_MISJUDGMENT
REQUIREMENTS_JUDGMENT_FAILED
TURN_LIMIT
MODEL_REPEAT_LIMIT
VALIDATION_FAILED
OTHER_SEMANTIC_FAILURE
```

No approved bounded validation-feedback projection presently exists, so a
visible or hidden contract failure stops rather than inventing new model-visible
validator detail. `VALIDATION_UNAVAILABLE`, `VALIDATION_TIMEOUT`,
`VALIDATION_CONTAINMENT_UNAVAILABLE`, `EFFECT_VIOLATION`, and `EXECUTOR_ERROR`
remain infrastructure states and are never delegated to a model as a repair for
broken apparatus.

## Task 10Y retrospective policy replay

`tools/replay_task10z_policy.py` read the immutable preserved Task 10Y raw and
harness evidence, verified every historical raw SHA-256, and invoked only the
pure policy classifier. It made no session or evidence mutation.

Write session
`work-task10y-qwen25-14b-write-20260811T235900Z` replayed as:

```text
PROPOSE_PATCH / PATCH_REJECTED
NO_CHANGE / NO_EXECUTOR_ACTION
classification: INTERACTIVE_RECOVERY_FAILED
reason: NO_CHANGE_AFTER_PATCH_REJECTED
disposition: ESCALATION_REQUIRED
recommended_next_worker: DELIBERATIVE_OVERNIGHT_CODER
```

Clarification session
`work-task10y-qwen25-14b-clarification-20260811T235900Z` replayed as:

```text
SEARCH / AUTHORIZED
READ / AUTHORIZED
PROPOSE_PATCH / DENIED_AUTHORITY
primary classification: INTERACTIVE_AUTHORITY_MISJUDGMENT
reason: AUTHORITY_MISJUDGMENT
secondary evidence: INTERACTIVE_REQUIREMENTS_JUDGMENT_FAILED
disposition: ESCALATION_REQUIRED
recommended_next_worker: DELIBERATIVE_OVERNIGHT_CODER
```

This is a prospective policy classification and not a historical rescore. Task
10Y remains `INTERACTIVE_14B_NORMALIZED_LANE_NOT_ACCEPTED`, with five historical
14B inferences and its original evidence unchanged. Task 10Z inference count is
zero.

## Handoff and operator control

On escalation the evaluator writes `INTERACTIVE_WORK_ESCALATION_HANDOFF_V1`
with the original objective, frozen source snapshot, authority,
requirements-status assertion, ordered raw responses and normalized parser
inputs with hashes, executor outcomes, bounded validation outcomes, structured
reason, any existing candidate metadata, and recommended next worker. It does
not include hidden-oracle implementation details.

The packet records `automatic_handoff_performed: false`. A recommendation for
the `DELIBERATIVE_OVERNIGHT_CODER` or `OPERATOR` is evidence for an operator
decision, not authority to start another model. A technically validated
candidate similarly stops at `AWAITING_OPERATOR_REVIEW`; no source promotion is
performed.

## Frozen surfaces and validation

The implementation adds a pure supervisor classifier and routes its durable
state through the existing controller. No semantic changes were made to the
request protocol, response normalizer, parser, isolated patch executor,
validation descriptors/executor, authority logic, model backend, fixture
construction, sampling, or context.

```text
V2: WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE
render SHA-256: 3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e
adapter: SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1 / unchanged
write fixture: db9efb27f7f56da8a0f295e3ef0e656271264ac08ec977da578f2e6e020bb2b6
clarification fixture: b0f5cdd341a2eb491ddcd9f02253563cbc0a44d79eccf86b3a3519cfdb13b3ba
model inference count: 0
automatic 32B invocation: false
```

Focused tests cover entry denial, complete entry binding, first- and
second-patch outcomes, validated first/second patch candidates, legitimate
clarification, authority misjudgment, Task 10Y replay, turn/repeat limits,
validation failure, infrastructure failure, durable escalation state, and the
evaluator handoff packet. The final gate passed all 156 ws-code-agent tests,
the separate two-test private-material check, containment, lineage, invariant
register, YAML, and diff checks. All eight gpu-compute suites and both ws-cp
containment tests passed again; unchanged peer worktrees remained clean and at
direct origin parity.

## Disposition

```text
INTERACTIVE_PRACTICAL_CODER_BOUNDARY_READY
NEXT: RUN RESTRICTED INTERACTIVE/PRACTICAL CODER ACCEPTANCE ON REQUIREMENTS-COMPLETE VALIDATED WORK
```

Task 10Z used no model inference, semantic adapter, automatic 32B invocation,
historical rescore, authority broadening, or automatic promotion.
