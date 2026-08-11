# Task 10Q Qwen2.5-Coder 14B runtime acceptance

Date: 2026-08-11

Play: `Peak Performance`

Checkpoint: `TASK10Q-QWEN25-CODER-14B-RUNTIME-ACCEPTANCE`

This is exact-artifact acquisition and runtime acceptance only. It performs no
V2 production admission, Alpha evaluation, coding fixture, parser evaluation,
executor invocation, protocol change, context change, or model tuning.

## Foundation and peer authority

The clean, direct-origin-parity starting checkpoints were:

```text
ws-code-agent: 25c104a451b5f19e44300223f8ec398b082ba2fd
gpu-compute:   0752c5d11b94df48ed01d78807e1012a53d1f92c
gpu-cp:        36851481e841048d7318060fe2a8e2a2c4b7f5b4
```

Before acquisition, ws-code-agent passed 122 tests plus containment, private
material, lineage, invariant, YAML, and diff checks. All eight gpu-compute
suites passed. The runtime-critical canonical deployment files matched the
published gpu-compute checkpoint byte-for-byte.

The resulting peer checkpoints are:

```text
gpu-compute implementation/profile: fc514cb02c9a2f76c60b461f787fba9ee43e2364
gpu-cp profile acceptance:           a84c33f68dcb14b292d791c8485e0ec4e532852c
```

gpu-compute owns the acquisition, invocation evidence, measured profile, and
operational classification. gpu-cp owns acceptance of that exact profile.
This repository records candidate state and the next admission boundary; it
does not duplicate peer runtime authority.

## Exact acquired artifact

One authorized pull acquired exactly
`qwen2.5-coder:14b-instruct-q4_K_M`. It ran from 17:37:15Z through 17:39:27Z
and returned status zero. No model was removed and no store pruning occurred.

The canonical local store proved:

```text
manifest: 9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849
model blob: ac9bc7a69dab38da1c790838955f1293420b55ab555ef6b4615efa1c1507b1ed
model blob bytes: 8,988,110,784
config: 0578f229f23ad620e123654fd0b4708405e7af3629ec1aecf3f553f54e06bc40
template: 1e65450c30670713aa47fe23e8b9662bdf4065e81cc8e3cbfaa98924fcc0d320
architecture: qwen2
parameters: 14.8B
quantization: Q4_K_M
context metadata: 32768
```

Every selected identity matched. A friendly tag was not accepted as proof.

## Runtime and context

The runtime remained unchanged:

```text
Ollama: 0.32.0+helix.repeatlimit.1
binary SHA-256: b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143
build ID: ffd1f9f6c8ffd69fdca1316e7c032447479fe139
semantic deviation: OLLAMA_V0_32_0_REPEAT_LIMIT_TERMINALIZATION_V1
```

The loaded runner bound the exact model blob and reported `-c 4096`.
`ollama ps` independently reported effective context 4096. No compensation,
YaRN, or model-specific substitution was used.

## Three neutral probes

The exact 64-byte prompt had SHA-256
`85ddfe377986086032d89c3ae84628b17dc5f54c85a1bda720dfacb74f2f7bba`.
Each non-streaming request used the canonical loopback `/api/generate` machine
endpoint and specified only `num_ctx=4096`.

An initial client wrapper had a Python syntax error and exited before creating
an evidence directory or issuing an HTTP request. It did not load the model or
consume a probe. The runtime series then made exactly three API requests. None
was retried and no fourth request occurred.

| Probe | Invocation / job | HTTP | Terminal | Prompt/eval tokens | Load | Prompt eval | Eval | Total | Response bytes / SHA-256 |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `task10q-qwen25-14b-probe-1-20260811` / `job-20260811T174231Z-task10q-p1` | 200 | `done=true`, `stop` | 42 / 6 | 4.516 s | 0.107 s | 0.079 s | 4.705 s | 21 / `0c0798e15e34cfd496072aa8c7efc1958758710b3ce4b66064d9358c63ac26b8` |
| 2 | `task10q-qwen25-14b-probe-2-20260811` / `job-20260811T174319Z-task10q-p2` | 200 | `done=true`, `stop` | 42 / 6 | 0.200 s | 0.024 s | 0.070 s | 0.297 s | 21 / `0c0798e15e34cfd496072aa8c7efc1958758710b3ce4b66064d9358c63ac26b8` |
| 3 | `task10q-qwen25-14b-probe-3-20260811` / `job-20260811T174348Z-task10q-p3` | 200 | `done=true`, `stop` | 42 / 6 | 0.188 s | 0.024 s | 0.070 s | 0.284 s | 21 / `0c0798e15e34cfd496072aa8c7efc1958758710b3ce4b66064d9358c63ac26b8` |

All three returned the exact diagnostic text `RUNTIME_ACCEPTANCE_OK`. The text
was retained evaluator-side and was not parsed or executed. No repeat-limit
event occurred.

## Residency and health

The empirical classification is `FULL_GPU`. `ollama ps` reported 100% GPU / 0%
CPU. NVIDIA telemetry observed 9,304 MiB peak VRAM; the exact runner process was
`/usr/lib/ollama/llama-server` bound to the selected blob and context 4096.

Available host RAM stayed at or above 13,849,677,824 bytes with no swap.
Ollama's cold-load headroom heuristic disabled mmap, but there was no
host-pressure abort or service degradation. Closeout found Ollama active and
enabled, a healthy GPU, no OOM/CUDA/XID evidence, no failed units, and
90,410,938,368 bytes free in the model store. The acquired artifact was
retained.

Raw peer evidence remains under:

- `/srv/gpu-compute/evidence/20260811T173705Z-task10q-qwen25-acquisition/`;
- `/srv/gpu-compute/evidence/task10q-qwen25-14b-runtime-20260811/`.

## Disposition

```text
profile_id = qwen25-coder-14b-katra-4096
empirical_fit = FULL_GPU
QWEN25_CODER_14B_RUNTIME_ACCEPTED
production_admission = NOT_EVALUATED
NEXT: RUN QWEN2.5-CODER 14B V2 PRODUCTION ADMISSION
```

Exactly the selected artifact was acquired. Exactly three neutral probes ran,
with no retry or tuning. No V2 admission, protocol or fixture change, context
change, Ollama upgrade, historical rescore, or authority broadening occurred.
