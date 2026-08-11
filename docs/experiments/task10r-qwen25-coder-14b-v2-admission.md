# Task 10R Qwen2.5-Coder 14B V2 production admission

Date: 2026-08-11

Play: `The First Duty`

Checkpoint:
`TASK10R-RESTART-QWEN25-CODER-14B-V2-PRODUCTION-ADMISSION`

This is the first behavioral evaluation of the exact Qwen2.5-Coder 14B
candidate. The earlier Task 10R preflight stopped before session creation and
contributed zero sessions, turns, inferences, or scores. Task 10R-A repaired
the two apparatus bindings without inference. This restart used fresh
independent sessions and no inherited model-visible state.

## Foundation and repaired apparatus

The clean, direct-origin-parity checkpoints were:

```text
ws-code-agent: 26394a23cfb8982b6bbfd2dbd4c7e681492247d6
gpu-compute:   fc514cb02c9a2f76c60b461f787fba9ee43e2364
gpu-cp:        a84c33f68dcb14b292d791c8485e0ec4e532852c
ws-cp:         e8e6d19f27c7cfecba401f0cf5bb85130cc33909
ws-doc-writer: d52c923d4a13949a2345fb5791ee59a82d389c4e
```

Before inference, ws-code-agent passed all 126 tests plus containment,
private-material, lineage, invariant-register, YAML, and diff gates. All eight
gpu-compute unit suites passed.

The repaired preflight proved:

```text
ARTIFACT_BINDING = PASS
RUNTIME_BINDING = PASS
PROFILE_BINDING = PASS
ADMISSION_SELECTOR = PASS
FROZEN_V2 = PASS
FROZEN_FIXTURES = PASS
```

Live Katra matched the selected manifest and 8,988,110,784-byte model blob.
The deployed profile file SHA-256 was
`394c642bc002d3f393b4781be5f6818b52ff16a9a4c650456dff5d1b2e5c0eb0`,
and the established policy checker selected
`qwen25-coder-14b-katra-4096` as `GPU_ONLY`, minimum GPU 100%, maximum CPU 0%.
No repair, pull, runtime change, or service change occurred.

## Exact frozen contract

```text
candidate: qwen25-coder-14b-q4
tag: qwen2.5-coder:14b-instruct-q4_K_M
manifest: 9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849
model blob: ac9bc7a69dab38da1c790838955f1293420b55ab555ef6b4615efa1c1507b1ed
quantization: Q4_K_M
profile: qwen25-coder-14b-katra-4096
context: 4096
protocol: WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE
render SHA-256: 3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e
write fixture: task10k-c-write/synthetic-v1
write fixture identity: db9efb27f7f56da8a0f295e3ef0e656271264ac08ec977da578f2e6e020bb2b6
clarification fixture: task10k-c-clarification/synthetic-v1
clarification fixture identity: b0f5cdd341a2eb491ddcd9f02253563cbc0a44d79eccf86b3a3519cfdb13b3ba
turn budget: maximum 8 per independent session
```

Ollama remained `0.32.0+helix.repeatlimit.1`, binary SHA-256
`b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143`,
build ID `ffd1f9f6c8ffd69fdca1316e7c032447479fe139`. No generation override was
added. The artifact/Ollama defaults remained in force.

## Write session

Session:
`work-task10r-restart-qwen25-write-20260811T191242Z`

Fixture repository HEAD:
`c89aaeba6f1e39612ed33e8f09b22e67a74f55af`

Source Snapshot X:
`3ed12272d5504fa1294923d5a6266da68a749799bbdeb0f6087e5d050f307b4d`

The session had read authority for `.` and patch authority only for
`src/message.py`. It consumed one turn.

| Field | Turn 1 evidence |
| --- | --- |
| Invocation | `alpha-3cda94eeb26c-WORK-t0001-e0c82220c7da` |
| gpu-compute job | `job-20260811T191301Z-945051` |
| Prompt SHA-256 | `7c8a359c88e7136b239065cdf4ea0edb490ae761f2ebc11e382aadaf16bb598c` |
| Model request | none accepted; raw text contained a Markdown-fenced `PROPOSE_PATCH` object |
| Parser | `MALFORMED_REQUEST` |
| Executor | `NOT_EXECUTED` |
| HTTP | 200 |
| Terminal | `done=true`, `done_reason=stop` |
| Prompt/eval tokens | 766 / 118 |
| Load duration | 3.730512192 s |
| Prompt-eval duration | 0.254692000 s |
| Eval duration | 1.610459000 s |
| Total duration | 5.600999353 s |
| Raw response | 315 bytes; `05b465998a33116f2d27af3d1598992a6d4b3d5721da5e2b316a24030ac36a76` |
| Completion metadata | `2773dcdd0ab1fbdff57ed66f815348353c7569faad8e6034ed90a65d6ac9c8ca` |
| Runtime | `GPU_ONLY`; CPU 0%; GPU 100%; context 4096 |

The content inside the fences described a plausible new-file patch for
`src/message.py`, but the frozen machine protocol requires exactly one JSON
object and no Markdown. The strict parser therefore accepted no request or
arguments. The executor did not run, validation was not reached, no isolated
candidate exists, changed paths are empty, and the source fixture remained
unchanged. The normal terminal response was not a repeat-limit or
infrastructure failure.

```text
WRITE_FAIL
cause: MALFORMED_REQUEST
```

The terminal session was not advanced or retried.

## Clarification session

Session:
`work-task10r-restart-qwen25-clarification-20260811T191417Z`

Fixture repository HEAD:
`e6c3acf410be36895d21149a7def1069dec37cb2`

Source Snapshot X:
`9f593d8b9287553506a57f8a84f869bf778f6a459059e840dfc3c4c65391ab7d`

This independent session had read authority for `.` and no patch authority. It
received no state from the write session and consumed one turn.

| Field | Turn 1 evidence |
| --- | --- |
| Invocation | `alpha-bc15aade32de-WORK-t0001-8b94797c07a7` |
| gpu-compute job | `job-20260811T191436Z-945414` |
| Prompt SHA-256 | `a1253f8e0f1372a5ee6b9d3f09b76bbe419fd1931ee2e47caa740e5c94f54e4f` |
| Model request | none accepted; raw text contained a Markdown-fenced `NO_CHANGE` object |
| Parser | `MALFORMED_REQUEST` |
| Executor | `NOT_EXECUTED` |
| HTTP | 200 |
| Terminal | `done=true`, `done_reason=stop` |
| Prompt/eval tokens | 759 / 21 |
| Load duration | 0.200331920 s |
| Prompt-eval duration | 0.081881000 s |
| Eval duration | 0.282102000 s |
| Total duration | 0.569463245 s |
| Raw response | 64 bytes; `c71974d0782e966e6ad9481150346d15d6058c8e7b9cc1bc7ef6bf0eb2488ead` |
| Completion metadata | `adaabb3887861bbe83220322edba2d4970c80adb171295bdcf29d7a4fcc237f2` |
| Runtime | `GPU_ONLY`; CPU 0%; GPU 100%; context 4096 |

The parser accepted no request because of the Markdown wrapper. Even without
that wrapper, the enclosed request type was `NO_CHANGE`, not the required
materially relevant `REQUEST_CLARIFICATION`. No clarification question was
emitted, no durable operator pause occurred, no mutation or candidate exists,
and the source fixture remained unchanged.

```text
CLARIFICATION_FAIL
cause: MALFORMED_REQUEST
clarification question: NONE
```

The terminal session was not advanced or retried.

## Integrity and health

For both turns, the local raw-response SHA equaled the remote invocation
response SHA and completion metadata bound the same response. Source Snapshot X
remained `MATCH`; each turn hash chain passed; invocation IDs were unique both
within and across sessions; duplicate inference count was zero. Katra recorded
exactly two new invocation directories and exactly two `/api/generate`
requests after the preflight, matching the two consumed turns.

Both runtime policy records reported the exact manifest, `GPU_ONLY`, 100% GPU,
0% CPU, and context 4096. Admission sampling observed 9,310 MiB VRAM in use and
at least 13,887,344,640 bytes host RAM available. Post-run Ollama was active
and enabled, the GPU remained healthy, no failed unit existed, and there was no
new OOM, CUDA error, XID, panic, or fatal service evidence. The retained loaded
model remained at 100% GPU and context 4096.

## Disposition

Both independent sessions failed normal frozen-contract behavior on their
first turn. The all-required gate therefore fails without partial admission.
Runtime acceptance remains valid; this behavioral result does not alter peer
runtime authority and does not rescore any historical candidate.

```text
QWEN25_CODER_14B_V2_PRODUCTION_ADMISSION_FAIL
NEXT: SELECT NEXT ELIGIBLE CHALLENGER
```

No model pull, retry, tuning, hint, context change, protocol or fixture change,
Ollama change, automatic promotion, historical rescore, or authority broadening
occurred.
