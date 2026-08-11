# Task 10R-A Qwen2.5-Coder 14B admission binding repair

Date: 2026-08-11

Play: `Booby Trap`

Checkpoint: `TASK10R-A-REPAIR-QWEN25-ADMISSION-BINDING`

Task 10R stopped before session creation because its published runtime profile
was absent from canonical Katra deployment and ws-code-agent had no exact
Qwen2.5 admission selector. This checkpoint repairs only those apparatus
bindings. It performs no model inference and assigns no behavioral score.

## Foundation

The clean, direct-origin-parity starting checkpoints were:

```text
ws-code-agent: 78b6840c9dbbd5d4224296dd1fd242f6129528b9
gpu-compute:   fc514cb02c9a2f76c60b461f787fba9ee43e2364
gpu-cp:        a84c33f68dcb14b292d791c8485e0ec4e532852c
```

The historical Task 10R result remains `TASK10R_RUNTIME_BINDING_STALE`.
No write or clarification session existed, and no production-admission score
was assigned.

## Canonical profile materialization

The authoritative bytes were obtained directly from
`fc514cb02c9a2f76c60b461f787fba9ee43e2364:config/model-runtime-profiles.tsv`.

```text
published SHA-256: 394c642bc002d3f393b4781be5f6818b52ff16a9a4c650456dff5d1b2e5c0eb0
published bytes: 1026
previous deployed SHA-256: 88bc9f0348ee7a8b4b68b3bf54fadd0122b50775c44b84fd3882b913b1655f09
previous deployed bytes: 808
previous Qwen2.5 row: ABSENT
new deployed SHA-256: 394c642bc002d3f393b4781be5f6818b52ff16a9a4c650456dff5d1b2e5c0eb0
new deployed bytes: 1026
```

The exact published file was staged under the bounded Katra evidence directory,
verified by hash, installed as a root-owned mode-0644 sibling, synchronized,
and atomically renamed over
`/srv/gpu-compute/config/model-runtime-profiles.tsv`. The live file was not
hand-edited, appended, or regenerated. Pre- and post-repair evidence is under
`/srv/gpu-compute/evidence/20260811T181328Z-task10ra-profile-materialization/`.
One preliminary command stopped at its pre-install row check because of shell
quoting; it did not touch the target. The corrected materialization then passed
all stage and destination identity checks.

The exact deployed row is:

```text
qwen25-coder-14b-katra-4096	qwen2.5-coder:14b-instruct-q4_K_M	9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849	Q4_K_M	cuda-compute-katra	hv-katra	NVIDIA GeForce RTX 5070 Ti	GPU_ONLY	100	0	9304	ACCEPTED
```

The established `model-execution-policy --check-profile` command selected
`qwen25-coder-14b-katra-4096` for the exact tag and manifest and reported
`GPU_ONLY`, minimum GPU 100%, and maximum CPU 0%. This identity/policy check did
not load or generate with the model. gpu-compute source was already
authoritative and remained unchanged; gpu-cp policy also remained unchanged.

## Exact ws-code-agent selector

The existing fixed-profile backend and V2 candidate-session mechanisms now bind:

```text
candidate: qwen25-coder-14b-q4
tag: qwen2.5-coder:14b-instruct-q4_K_M
manifest: 9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849
quantization: Q4_K_M
runtime profile: qwen25-coder-14b-katra-4096
comparison context: 4096
execution: GPU_ONLY, GPU 100%, CPU 0%
```

The selector reuses the same prompt renderer, transport, parser, executor,
fixture initializer, isolation, validation, review, termination, and durable
evidence paths as the historical bindings. It adds no model-specific prompt,
example, hint, sampling value, tool setting, retry, continuation, or repair.
Focused tests prove the positive binding, reject a wrong tag, digest, or
profile, and retain the historical Qwen3 and Devstral paths.

## Frozen surfaces and no-inference preflight

Structural checks retained:

```text
V2 render SHA-256: 3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e
write fixture identity: db9efb27f7f56da8a0f295e3ef0e656271264ac08ec977da578f2e6e020bb2b6
clarification fixture identity: b0f5cdd341a2eb491ddcd9f02253563cbc0a44d79eccf86b3a3519cfdb13b3ba
```

Protected parser/executor and candidate-review functions were AST-identical to
the starting checkpoint. The repaired preflight proved the local manifest and
8,988,110,784-byte model blob identities, patched Ollama version/binary/build,
deployed profile, policy, candidate selector, V2 render, and both fixtures.
The durable work-store directory count remained unchanged at 11.

```text
ARTIFACT_BINDING = PASS
RUNTIME_BINDING = PASS
PROFILE_BINDING = PASS
ADMISSION_SELECTOR = PASS
FROZEN_V2 = PASS
FROZEN_FIXTURES = PASS
INFERENCE_COUNT = 0
SESSION_COUNT = 0
```

Katra closeout found Ollama active and enabled, no failed units, no loaded
models, a healthy idle RTX 5070 Ti, and no OOM/CUDA/XID evidence.

## Validation

The ws-code-agent host-containment gate passed all 126 tests, including the
focused selector and frozen-surface additions. The separate private-material
check, lineage verifier, invariant register, YAML parse, and diff check passed.
All eight gpu-compute unit suites passed. gpu-cp's applicable document/YAML and
diff checks passed. The three source repositories remained otherwise clean and
their peer authority checkpoints did not change.

## Disposition

```text
runtime = ACCEPTED
production_admission = NOT_EVALUATED
TASK10R_APPARATUS_REPAIRED
NEXT: RESTART TASK 10R WITH FRESH QWEN2.5-CODER 14B ADMISSION SESSIONS
```

The later Task 10R restart must use two fresh independent sessions, zero prior
turns or inherited model state, the same frozen V2 and fixtures, and the same
eight-turn budgets.
