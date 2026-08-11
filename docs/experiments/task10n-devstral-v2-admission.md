# Task 10N Devstral V2 production admission

Date: 2026-08-11

Starting `ws-code-agent` HEAD:
`82a10891664e42929634591e664571662ffdce59`

Frozen behavioral `ws-code-agent` HEAD:
`e98aa399aa1ed3aa1efdf8e7df22369bbe5c3a1a`

Frozen runtime authorities:

- `gpu-compute`: `0d8e9f6b9a4ef063e6110808b66f7bcd1e34389f`;
- `gpu-cp`: `d9dd4bd6ad2276c3a49a04a26588037a5c44650a`;
- `ws-cp`: `e8e6d19f27c7cfecba401f0cf5bb85130cc33909` (unchanged);
- `ws-doc-writer`: `d52c923d4a13949a2345fb5791ee59a82d389c4e`
  (unchanged).

This is a forward-only challenger record. It does not modify Qwen evidence,
Alpha v1, V2, the admission fixtures, parser behavior, or authority.

## Artifact acquisition

The official Ollama registry manifest for
`devstral-small-2:24b-instruct-2512-q4_K_M` still hashed to the selected full
digest immediately before acquisition:

`24277f07f62db8f9cb68e9dfc679ea1818a7fbac47a50eff0a701d3f645b63c8`.

The canonical Ollama model store acquired the artifact from 04:34:04Z through
04:38:13Z. Installed identity:

| Field | Value |
| --- | --- |
| Architecture | `mistral3` |
| Parameters | 24.0B |
| Quantization | `Q4_K_M` |
| Context metadata | 393216 |
| Comparison context | 4096 |
| Default temperature | 0.15 |
| Model layer | `c580819bed79c92d01a42227bd6d8fd66b9ec60d5329f5eb73f812f156af7807`, 15,177,370,240 bytes |
| Template layer | `580f051b6624bd17f29bb37554ec19feb4ab18cda4f948739016b6a5f300b026`, 3,418 bytes |
| Parameters layer | `e0daf17ff83eace4813f9e8554b262f6cc33ad880ff8df41a156ff9ef5522ddb`, 21 bytes |
| Config layer | `cc6f162f94fe1e564f0c639e31fd4f16db2a89a99b0559b0348573d7884b24ec`, 420 bytes |

Available model storage changed from 114,576,482,304 bytes to
99,399,086,080 bytes. Both appliance reserves remained satisfied. Raw evidence:

- `/srv/gpu-compute/evidence/20260811T043343Z-task10n-devstral-acquisition-pre/`;
- `/srv/gpu-compute/evidence/20260811T044102Z-task10n-devstral-acquisition-post/`.

## Runtime acceptance

Katra was reobserved as `cuda-compute-katra` / RTX 5070 Ti (16,303 MiB),
driver 610.57.04, CUDA 13.3, Ollama 0.32.0, no swap, no loaded model, and no
failed units. Three identical neutral machine-response probes used the exact
artifact and artifact defaults:

| Probe | Job | CPU/GPU | VRAM MiB | Duration | Response SHA-256 |
| ---: | --- | --- | ---: | ---: | --- |
| 1 | `job-20260811T044300Z-1001` | 12% / 88% | 14648 | 31.15 s | `d010fe7aa01c4c3f8ae250e6da904b229daa759dd6b273f24ca405355dfd9987` |
| 2 | `job-20260811T044400Z-1002` | 12% / 88% | 14648 | 0.92 s | `d010fe7aa01c4c3f8ae250e6da904b229daa759dd6b273f24ca405355dfd9987` |
| 3 | `job-20260811T044500Z-1003` | 12% / 88% | 14648 | 0.91 s | `d010fe7aa01c4c3f8ae250e6da904b229daa759dd6b273f24ca405355dfd9987` |

Context was 4096 in each `ollama ps` record. Host available RAM remained above
15.0 GB. No OOM, host pressure, wedged service, failed unit, or unreaped model
process was observed.

`gpu-cp` accepted and `gpu-compute` enforced the exact-artifact profile:

```text
profile_id: devstral-small-2-24b-katra-partial
classification: GPU_PRIMARY_PARTIAL_OFFLOAD
GPU >= 88%
CPU <= 12%
```

The deployed profile and test hashes matched published `gpu-compute` source.

`DEVSTRAL_RUNTIME_ACCEPTED`

## Frozen behavioral contract

- Protocol: `WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE`.
- Render SHA-256:
  `3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e`.
- Write fixture: `task10k-c-write/synthetic-v1`.
- Clarification fixture: `task10k-c-clarification/synthetic-v1`.
- Turn limit: 8 per independent session.
- Write authority: read `.`, patch only `src/message.py`.
- Clarification authority: read `.`, no patch authority.
- Admission: both write and clarification must pass.

The pre-inference gate passed 114 tests. The challenger binding selected the
backend from the durable exact artifact digest and could not switch profiles
across restart.

## Write admission

Session:
`work-task10n-devstral-write-20260811T045353Z`

Evidence:
`~/.local/share/ws-code-agent/work/work-task10n-devstral-write-20260811T045353Z`

The first and only response was 163 bytes and ended while emitting a proposed
unified diff. Its exact response SHA-256 was
`d0c8350bab1b0373a6b4fe928e90ef270349219487a519bc1507833f810e1a96`.
It began:

```text
{"request_type": "PROPOSE_PATCH", "arguments": {"patch": "diff --git a/src/message.py b/src/message.py\nnew file mode 100644\nindex 0000000000000000000000000000000
```

The response was incomplete JSON, so the strict parser returned
`MALFORMED_REQUEST`. No request arguments were accepted, no executor mutation
operation occurred, and no candidate or changed path exists.

| Field | Value |
| --- | --- |
| Invocation | `alpha-2dde7adbd00b-WORK-t0001-500a19e7034e` |
| gpu-compute job | `job-20260811T045422Z-911382` |
| Prompt SHA-256 | `f0ba398a6daa85ea3ab4aeab254c6671e66be96bec9cd22671fef75b24c392f3` |
| Local/remote raw SHA | equal |
| Runtime | 12% CPU / 88% GPU, policy PASS |
| Source Snapshot X | `MATCH` |
| Turn hash chain | PASS |
| Duplicate inference | 0 |
| Result | FAIL |

The session terminated normally as scoreable model evidence. It was not
retried.

## Clarification admission

Session:
`work-task10n-devstral-clarification-20260811T045455Z`

Evidence:
`~/.local/share/ws-code-agent/work/work-task10n-devstral-clarification-20260811T045455Z`

The first and only response was parser-valid
`REQUEST_CLARIFICATION`. Exact question:

> What is the expected behavior or specification of the
> `format_release_label(title)` function? Please provide details on how the
> title should be formatted into a release label.

The existing admission contract recorded the question and paused the session.
No mutation was requested or performed.

| Field | Value |
| --- | --- |
| Raw SHA-256 | `1a8567cb8801a743c89f29376005c7c70ce49ef78b9890e4aa8d8120045cc20f` |
| Invocation | `alpha-53ae679e9de3-WORK-t0001-8549bd6be954` |
| gpu-compute job | `job-20260811T045513Z-912073` |
| Prompt SHA-256 | `9ca24f7466fbb06d4397143da9af9a8b8b4e21e16260a0ebda5821f456a28735` |
| Local/remote raw SHA | equal |
| Runtime | 12% CPU / 88% GPU, policy PASS |
| Source Snapshot X | `MATCH` |
| Turn hash chain | PASS |
| Duplicate inference | 0 |
| Result | PASS |

## Qwen comparison

This comparison does not rescore Qwen.

| Dimension | Qwen under the frozen V2 gate | Devstral under the frozen V2 gate |
| --- | --- | --- |
| Write progression | Parser-valid `READ src/message.py`, then unnecessary `REQUEST_CLARIFICATION` | Incomplete `PROPOSE_PATCH` envelope on turn 1 |
| Write disposition | FAIL; no candidate | FAIL; `MALFORMED_REQUEST`, no candidate |
| Clarification progression | `READ README.md` on all 8 turns | `REQUEST_CLARIFICATION` on turn 1 |
| Clarification disposition | FAIL; `TURN_LIMIT` | PASS; durable operator pause |
| Protocol compliance | Parser-valid in both sessions | Invalid write response; valid clarification response |
| Runtime | Accepted 80% GPU / 20% CPU Qwen profile | Accepted 88% GPU / 12% CPU Devstral profile |

The runtime split is not a behavioral score.

## Disposition

Write admission failed and clarification admission passed. The unchanged gate
requires both, so there is no partial production admission.

`DEVSTRAL_V2_PRODUCTION_ADMISSION_FAIL`

No Alpha inference, Qwen rerun, admission retry, protocol/fixture/authority
change, candidate-specific behavioral hint, automatic promotion, or private
answer exposure occurred.
