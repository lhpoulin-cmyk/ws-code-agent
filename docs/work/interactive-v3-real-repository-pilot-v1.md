# Interactive/practical coder V3 real-repository pilot V1

Status: **design ready; target pending operator selection; not yet run**.

Policy: `INTERACTIVE_PRACTICAL_CODER_REAL_REPOSITORY_PILOT_V1`

Envelope: `INTERACTIVE_PRACTICAL_CODER_V3_PRODUCTION_ENVELOPE_V1`

This policy defines the first real-repository use of the frozen source-grounded
V3 interactive envelope. It grants no model, repository, promotion, or
deployment authority by itself. A future play must name an operator-authorized
repository and task, bind a complete manifest, and pass the entry gate before
inference.

## Selection boundary

Choose one real repository with a clean frozen worktree and one boring,
non-production-critical existing-file change. Requirements must already be
complete. The objective, readable scopes, and exactly one writable UTF-8
regular file must be explicit. The task must require no secret material,
cross-domain authority, deployment, architecture judgment, security-policy
interpretation, or product decision.

Both a deterministic visible validator and an independently implemented hidden
validator must exist and be bound before inference. Failure must be cheap: the
task should be easy to review manually and easy to abandon without promotion.

Architecture, credentials, network or hypervisor changes, production service
behavior, migrations, storage changes, cross-repository coordination,
multiple writable files, new-file creation, and ambiguous requirements are
ineligible for Pilot V1.

## Required manifest

The machine-enforced schema lives in
`ws_code_agent.production_envelope.validate_pilot_manifest`. Its durable packet
must contain:

```text
pilot ID and pilot policy ID
repository identity, HEAD, Source Snapshot X
index, tracked-worktree, and untracked identities
clean/frozen assertions
owning domain and operator authorization reference
requirements_status = COMPLETE
objective
read scopes
exactly one patch path
exact visible/hidden validator bindings
worker envelope ID
runtime profile
protocol ID and render SHA
grounding policy
normalizer ID/version
turn limit
promotion_authority = OPERATOR_ONLY
```

Unknown, missing, substituted, unsafe, stale, or broadened fields fail closed.
Manifest validation and entry binding do not start a session or invoke a model.

## Source protection and success

The authoritative repository remains read-only to model and executor. All
effects occur in the existing isolated candidate mechanism. HEAD, index,
tracked worktree, and untracked inventory must remain unchanged.

A future pilot passes only after exact target grounding, an accepted structured
edit, one independently observed authorized changed path, both validators,
candidate and source integrity, zero duplicate inference, and a valid turn hash
chain. The terminal success state is `AWAITING_OPERATOR_REVIEW`.

Operator review is not promotion. Commit, source mutation, merge, push, deploy,
and cross-model handoff all require separate authority and are never automatic.

## Stop conditions

Stop on source drift, authority disagreement, grounding noncompliance,
structured repair exhaustion, validation failure or infrastructure failure,
runtime-binding drift, an unexpected changed path, a cross-repository request,
turn limit, or `MODEL_REPEAT_LIMIT`. Do not improvise around a failed pilot.

No appropriate real task was selected in Task 11G. Current target state:

```text
REAL_REPOSITORY_PILOT_TARGET_PENDING_OPERATOR_SELECTION
```
