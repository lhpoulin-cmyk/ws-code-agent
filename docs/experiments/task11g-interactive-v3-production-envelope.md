# Task 11G frozen interactive V3 production envelope

Date: 2026-08-12

Play: `Rules of Engagement`

Checkpoint: `TASK11G-FREEZE-INTERACTIVE-V3-PRODUCTION-ENVELOPE`

## Foundation

Task 11G started from clean direct-origin parity at:

```text
ws-code-agent: 762f5e21ddcaab09815679384240a8f75131023d
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp:         c6138913d39502dbf1507c7318002b4ab748d0b1
```

The starting gate passed all 194 ws-code-agent tests, the separate two-test
private-material check, real containment, lineage, invariant-register, YAML,
and diff checks. All eight gpu-compute suites and both ws-cp containment tests
passed. No peer repository required mutation.

## Frozen envelope

`INTERACTIVE_PRACTICAL_CODER_V3_PRODUCTION_ENVELOPE_V1` is `FROZEN`. Its
machine-enforced binding is implemented in `ws_code_agent.production_envelope`;
the durable reviewable form is
`docs/work/interactive-v3-production-envelope-v1.yaml`.

The exact worker binding is:

```text
work role: INTERACTIVE_PRACTICAL_CODER
model: qwen2.5-coder:14b-instruct-q4_K_M
manifest: 9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849
quantization: Q4_K_M
runtime profile: qwen25-coder-14b-katra-4096
context: 4096
placement: GPU_ONLY / 100% GPU / 0% CPU
```

The protocol is
`WS_CODE_AGENT_REQUEST_PROTOCOL_V3_SINGLE_STRUCTURED_EDIT`, render SHA-256
`d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993`.
Its only write primitive is `PROPOSE_TEXT_REPLACEMENT`. The model owns exact
`path`, `old_text`, and `new_text` values; it does not generate unified diff
syntax. The evaluator preserves those values and owns only exact occurrence
counting, isolated replacement, effect observation, canonical review diff,
candidate identity, and validation execution.

The envelope binds only
`SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1 / v1`,
`SOURCE_GROUNDED_STRUCTURED_EDIT_V1`, and
`INTERACTIVE_BOUNDED_WORK_V1`. There is no additional representation or
semantic adapter. A structured edit requires a successful same-session exact-
path `READ_FILE` against current Source Snapshot X. One ungrounded request
returns only `SOURCE_READ_REQUIRED`; two consecutive ungrounded writes
escalate as `SOURCE_GROUNDING_NONCOMPLIANCE`.

Entry requires complete requirements, one repository, an explicit objective,
explicit read and patch authority, pre-bound validators, a clean frozen source,
and all exact artifact/runtime/protocol/grounding/normalizer bindings. Missing
or substituted state fails closed.

## V1 scope, repair, and validation

V1 is intentionally narrower than the theoretical structured executor:

```text
existing regular UTF-8 file only
NUL forbidden
old_text non-empty
exact literal replacement
old_text occurrence count exactly one
exactly one authorized writable file
```

An ungrounded write consumes no match repair. The first grounded
`TEXT_MATCH_ZERO` or `TEXT_MATCH_MULTIPLE` receives one ordinary forward repair
opportunity. A second grounded match failure escalates as
`STRUCTURED_EDIT_REPAIR_EXHAUSTED`. Task 11G adds no turn or repair allowance.

Both registry-owned validators are mandatory before inference:

```text
VISIBLE:       task10k-c-write-visible-v1 / v1
HIDDEN_ORACLE: task10k-c-write-hidden-v1 / v1
```

Both require containment and forbid repository writes. Operator review is
reachable only with visible and hidden `VALIDATION_PASS`, technical correctness
`VALIDATED`, candidate integrity `MATCH`, and Source Snapshot X `MATCH`.
Success stops at `AWAITING_OPERATOR_REVIEW`.

Automatic source mutation, commit, merge, push, deployment, promotion, and
overnight-coder handoff remain false. Promotion authority is `OPERATOR_ONLY`.

## Explicit exclusions

V1 excludes new-file creation, whole-file deletion, multiple writable files,
multi-repository or cross-repository work, fuzzy or regex matching,
replace-all, occurrence selection, AST or semantic repair, requirements
discovery, architecture selection, unresolved product ambiguity,
security-policy interpretation, automatic promotion, and automatic invocation
of the deliberative/overnight coder. Each needs separate future evidence and
authority.

## Task 11F acceptance binding

The envelope verifies the immutable Task 11F evidence file by SHA-256 and binds:

```text
checkpoint: TASK11F-FRESH-V3-SOURCE-GROUNDED-INTERACTIVE-ACCEPTANCE
disposition: INTERACTIVE_PRACTICAL_CODER_V3_SOURCE_GROUNDED_ACCEPTANCE_PASS
commit: 762f5e21ddcaab09815679384240a8f75131023d
evidence SHA-256: 83bcd7ebceae55ad4bb6f6da1fe8509694a73181cbd6e4134a7daa319462a660
fixture contract: 2e11f5fac2952ee90dba867e129466a7f6b619c057a952348713035ddc33ed16
Source Snapshot X: b1e5f6c43fe763645bb62f349e42661b6f2402cf94d29cc405d10dcb160e297f
candidate: ac813e35c939b2bfc64aaa4a5fd3237e284ca80fbd2dbaac351fe25ad755d7a5
canonical diff: 52f56438548ceb2ae079583b4fb357d130d8adac1514510965ec1740c0a4389c
```

The witnessed behavior was write-before-read denial, exact target read,
durable grounding, source-aligned old text, correct new text, one exact match,
accepted structured edit, both validator passes, and
`AWAITING_OPERATOR_REVIEW`. Earlier failures remain failures and explain why
the envelope contains each guard.

## Failure lineage

The production design is an evidence-derived interface progression, not prompt
tuning:

| Checkpoint | Finding |
|---|---|
| Task 10X | Isolated the bounded representation wrapper. |
| Task 11A | Correct semantic edit; unified-diff transport failed. |
| Task 11B | Confirmed the patch-serialization interface mismatch. |
| Task 11C | Created deterministic structured edit transport. |
| Task 11D | Structured transport exposed missing source grounding. |
| Task 11E | Added the supervisor-only grounding precondition. |
| Task 11F | Source-grounded V3 acceptance passed. |

No historical disposition is rescored.

## First real-repository pilot design

`INTERACTIVE_PRACTICAL_CODER_REAL_REPOSITORY_PILOT_V1` is `DESIGN_READY` and
`NOT_YET_RUN`. The policy and required manifest are recorded in
`docs/work/interactive-v3-real-repository-pilot-v1.yaml`; operator doctrine is
in `docs/work/interactive-v3-real-repository-pilot-v1.md`.

A future target must be one real, clean repository with a complete, small,
non-production-critical requirement; exactly one existing writable UTF-8 file;
no secrets, cross-domain authority, or deployment effect; deterministic visible
and independent hidden validation; and cheap review and abandonment. The
machine-enforced manifest binds repository identity, HEAD, Source Snapshot X,
index/worktree/untracked identities, owning authority, objective and scopes,
validators, exact frozen envelope, runtime, protocol, grounding, normalizer,
turn limit, and operator-only promotion.

The real repository remains unchanged while all effects stay isolated. A later
pilot can pass only after source grounding, accepted structured replacement,
one authorized observed path, both validator passes, source/candidate integrity,
zero duplicate inference, a valid turn hash chain, and
`AWAITING_OPERATOR_REVIEW`.

Stop conditions include source drift, authority disagreement, grounding
noncompliance, repair exhaustion, validator or validation-infrastructure
failure, runtime drift, unexpected paths, cross-repository requests, turn limit,
and `MODEL_REPEAT_LIMIT`.

No currently authorized real-repository task was sufficiently specified for
selection without fabricating work or authority. Therefore:

```text
REAL_REPOSITORY_PILOT_TARGET_PENDING_OPERATOR_SELECTION
```

The completed implementation passes 204 ws-code-agent tests, including ten
focused frozen-envelope, acceptance-binding, pilot-schema, entry, exclusion,
and stop-condition tests. The separate private-material, real-containment,
lineage, invariant-register, YAML, diff, and frozen-surface gates pass. All
eight gpu-compute suites and both ws-cp containment-contract tests pass again.
Peer repositories remain unchanged.

## Frozen surfaces and activity

V3 remains
`d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993`;
V2 remains
`3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e`.
The normalizer, structured executor, source grounding, validation,
`INTERACTIVE_BOUNDED_WORK_V1`, repair limits, and semantic authority are
unchanged.

```text
14B inference count: 0
32B inference count: 0
MODEL_INFERENCE_COUNT: 0
```

## Disposition

```text
INTERACTIVE_PRACTICAL_CODER_V3_PRODUCTION_ENVELOPE_FROZEN
REAL_REPOSITORY_PILOT_DESIGN_READY
NEXT: SELECT ONE BORING REQUIREMENTS-COMPLETE REAL-REPOSITORY TASK FOR THE FROZEN V3 PILOT
```
