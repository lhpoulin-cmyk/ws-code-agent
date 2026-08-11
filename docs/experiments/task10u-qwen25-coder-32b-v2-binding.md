# Task 10U Qwen2.5-Coder 32B V2 binding

Date: 2026-08-11

Play: `Second Chances`

Checkpoint: `TASK10U-BIND-QWEN25-CODER-32B-V2-SCALE-CONTROL`

This checkpoint binds the already runtime-accepted 32B scale control to the
frozen V2 admission apparatus. It performs no model inference, creates no
operational admission session, and assigns no behavioral score.

## Foundation

The clean, direct-origin-parity starting checkpoints were:

```text
ws-code-agent: ffc01dc8fdfa84dc4fd0e23476683219bbb4e4cf
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
```

The starting ws-code-agent gate passed 127 tests plus the separate two-test
private-material check, containment, lineage, invariant-register, YAML, and
diff gates. All eight gpu-compute suites passed. gpu-cp remained clean and its
applicable checks passed.

The 14B practical baseline remains independently bound to its exact tag,
manifest, `qwen25-coder-14b-katra-4096` GPU-only profile, historical
`start-qwen25-v2` command, and `QWEN25_V2_SUPERVISED_PRODUCTION_ADMISSION`
session kind. Its runtime acceptance and strict V2 admission failure are
unchanged and were not rescored.

## Exact 32B binding

The new candidate manifest is
`docs/qualification/qwen25-coder-32b-v2-admission-candidate.yaml`. Its validator
requires every binding below and fails with `CHALLENGER_BINDING_MISMATCH` on a
stale candidate ID, status, tag, full digest, model blob, quantization, context,
generation override, profile, execution class, GPU/CPU envelope, Ollama
version, binary SHA, build ID, runtime deviation, protocol, or admission state.

```text
candidate: qwen25-coder-32b-q4
tag: qwen2.5-coder:32b-instruct-q4_K_M
manifest: b92d6a0bd47ee79114298de0177bf920c05a706d12633950b3936778492bef41
model blob: ac3d1ba8aa77755dab3806d9024e9c385ea0d5b412d6bdf9157f8a4a7e9fc0d9
quantization: Q4_K_M
context: 4096
generation overrides: NONE
profile: qwen25-coder-32b-katra-4096
execution: GPU_PRIMARY_PARTIAL_OFFLOAD
minimum GPU: 71%
maximum CPU: 29%
```

The accepted runtime identity remains:

```text
Ollama: 0.32.0+helix.repeatlimit.1
binary SHA-256: b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143
build ID: ffd1f9f6c8ffd69fdca1316e7c032447479fe139
runtime deviation: OLLAMA_V0_32_0_REPEAT_LIMIT_TERMINALIZATION_V1
```

## Selector and durable separation

`QWEN25_32B_RUNTIME_PROFILE` is a distinct `FixedKatraRuntimeProfile` and
`Qwen25_32BKatraOllamaDispositionBackend` is a distinct subclass of the shared
Katra backend. It does not alias the 14B constants or profile. The operator
command `start-qwen25-32b-v2` points only to the 32B candidate manifest and the
new `start_qwen25_32b_v2_admission` method.

The durable session kind is:

`QWEN25_32B_V2_SUPERVISED_PRODUCTION_ADMISSION`

During `step`, only the exact full 32B manifest digest selects the 32B backend.
Cross-binding tests prove a 32B durable invocation cannot execute through the
14B backend and a 14B invocation cannot execute through the 32B backend. Wrong
tag, digest, or profile identities fail before transport. Historical Qwen3,
Devstral, and Qwen2.5-Coder 14B selectors remain unchanged.

## Frozen surfaces

The V2 render remains:

```text
protocol: WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE
render SHA-256: 3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e
write fixture identity: db9efb27f7f56da8a0f295e3ef0e656271264ac08ec977da578f2e6e020bb2b6
clarification fixture identity: b0f5cdd341a2eb491ddcd9f02253563cbc0a44d79eccf86b3a3519cfdb13b3ba
turn limit: 8
```

Byte comparison against starting checkpoint `ffc01dc` proves no change to
`request_protocol.py`, `disposition_harness.py`, `isolated_patch.py`,
`readonly_executor.py`, `validation.py`, or `alpha_experiment.py`. AST hashes
also match for the shared backend `generate`, `_render_prompt`, `_ssh`, and
`_validate_evidence` methods and for the shared fixture initializer,
`_start_bound`, `step`, `_process_turn`, and `review` paths.

For identical first-turn fixture messages, the 14B and 32B subclasses use the
same inherited renderer and produce identical 2,898-byte model-visible prompt
bytes, SHA-256
`7741cba74e06a0aa2858584e669d1daed65210d537a07218667a7f4e10b9bc49`.
There is no candidate-specific prompt, Markdown normalization, output repair,
retry, continuation, parser change, or executor change.

```text
FROZEN_V2 = PASS
FROZEN_FIXTURES = PASS
PARSER_EXECUTOR_FREEZE = PASS
MODEL_VISIBLE_FIRST_TURN_EQUIVALENCE = PASS
```

## Live profile and no-inference preflight

The canonical deployed profile file remained SHA-256
`2c2a0637f9e8e169e9e3fe0e0ce320e3ce82d01bb33418ad6aabfb3e1a0d02c5`.
The established read-only profile checker selected the exact 32B manifest and
reported `GPU_PRIMARY_PARTIAL_OFFLOAD`, minimum GPU 71%, and maximum CPU 29%.
The deployed file was verified, not rematerialized. Ollama reported no loaded
model.

After the binding change, ws-code-agent passed all 130 tests with no
regression, the separate two-test private-material check, containment, lineage,
invariant-register, YAML, and diff gates. All eight gpu-compute suites passed
again; neither peer repository changed.

The canonical durable work store contained no 32B candidate manifest or 32B
session root before or after this play. Focused unit tests used only disposable
temporary directories and fake transports. They did not call SSH, the remote
runner, Ollama, `/api/generate`, or `/api/chat`.

```text
ARTIFACT_BINDING = PASS
RUNTIME_BINDING = PASS
PROFILE_BINDING = PASS
ADMISSION_SELECTOR_32B = PASS
ADMISSION_SELECTOR_14B = PASS
FROZEN_V2 = PASS
FROZEN_FIXTURES = PASS
PARSER_EXECUTOR_FREEZE = PASS
MODEL_VISIBLE_FIRST_TURN_EQUIVALENCE = PASS
MODEL_INFERENCE_COUNT = 0
ADMISSION_SESSION_COUNT = 0
```

## Disposition

```text
role = INTRA_FAMILY_SCALE_CONTROL
runtime = ACCEPTED
production_admission = NOT_EVALUATED
TASK10U_32B_ADMISSION_APPARATUS_READY
NEXT: RUN QWEN2.5-CODER 32B FROZEN V2 SCALE-CONTROL ADMISSION
```

No inference, protocol or fixture change, parser/executor change, Markdown
normalization, output repair, candidate-specific prompt, retry, context change,
Ollama change, 14B rescore, or authority broadening occurred.
