# Task 10T Qwen2.5-Coder 32B runtime acceptance

Date: 2026-08-11

Play: `The Most Toys`

Checkpoint: `TASK10T-QWEN25-CODER-32B-RUNTIME-ACCEPTANCE`

This is exact-artifact acquisition and runtime acceptance for the same-family
scale control only. It performs no V2 production admission, Alpha evaluation,
coding fixture, parser evaluation, executor invocation, protocol change,
context change, or model tuning.

## Foundation and peer authority

The clean, direct-origin-parity starting checkpoints were:

```text
ws-code-agent: 2b9e72c2ae34f395f445c5a24ef72cabb0b56263
gpu-compute:   fc514cb02c9a2f76c60b461f787fba9ee43e2364
gpu-cp:        a84c33f68dcb14b292d791c8485e0ec4e532852c
```

Before acquisition, ws-code-agent passed 127 tests plus containment,
private-material, lineage, invariant, YAML, and diff checks. All eight
gpu-compute suites passed, and gpu-cp's applicable repository checks passed.

The resulting peer checkpoints are:

```text
gpu-compute implementation/profile: 282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp profile acceptance:           e64e39c029616d69ec4523500facd20e7a75c9f2
```

gpu-compute owns acquisition, invocation evidence, measured placement, and the
runtime profile. gpu-cp owns acceptance of that exact profile. This repository
records candidate state and the next behavioral boundary; it does not replace
either peer authority.

## Exact acquired artifact

One authorized pull acquired exactly
`qwen2.5-coder:32b-instruct-q4_K_M` and returned status zero. No model was
removed and no store pruning occurred. The canonical local store proved:

```text
manifest: b92d6a0bd47ee79114298de0177bf920c05a706d12633950b3936778492bef41
manifest bytes: 859
model blob: ac3d1ba8aa77755dab3806d9024e9c385ea0d5b412d6bdf9157f8a4a7e9fc0d9
model blob bytes: 19,851,336,384
config: f0676bd3c336a0f995e270c5e2c80ce09aa5cfcab0c59ff574088eca52da32ee
template: 1e65450c30670713aa47fe23e8b9662bdf4065e81cc8e3cbfaa98924fcc0d320
system: 66b9ea09bd5b7099cbb4fc820f31b575c0366fa439b08245566692c6784e281e
architecture: qwen2
parameters: 32.8B
quantization: Q4_K_M
context metadata: 32768
generation overrides: NONE
```

Every selected identity matched. A friendly tag was not accepted as proof.
An attempted `ollama show --json` metadata command was rejected by this pinned
client before inference because that option is unsupported; the supported
read-only show interfaces supplied the metadata. This did not issue an HTTP
request, load the model, or consume a probe.

## Runtime and context

The runtime remained unchanged:

```text
Ollama: 0.32.0+helix.repeatlimit.1
binary SHA-256: b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143
build ID: ffd1f9f6c8ffd69fdca1316e7c032447479fe139
semantic deviation: OLLAMA_V0_32_0_REPEAT_LIMIT_TERMINALIZATION_V1
```

The loaded runner was PID 946229, parent Ollama PID 942456, running as
`ollama`. It bound the exact model blob, used the ordinary `llama-server`
path, and included `-c 4096`; `ollama ps` independently reported context 4096.
No context compensation or model-specific substitution was used.

## Three neutral probes

The exact 64-byte prompt had SHA-256
`85ddfe377986086032d89c3ae84628b17dc5f54c85a1bda720dfacb74f2f7bba`.
Each 163-byte non-streaming request body had SHA-256
`7a21646ad3a604fba5e87981e59c68ea0c8c0a6051e919bedfeb2044e2a9e816`
and used the canonical loopback `/api/generate` endpoint with only
`num_ctx=4096` specified. Exactly three API requests ran; none was retried and
no fourth request occurred.

| Probe | Invocation / job | HTTP | Terminal | Prompt/eval tokens | Load | Prompt eval | Eval | Total | Response bytes / SHA-256 |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | `task10t-qwen25-32b-probe-1-20260811` / `job-20260811T200038Z-task10t-p1` | 200 | `done=true`, `stop` | 42 / 6 | 47.580 s | 0.715 s | 3.244 s | 51.547 s | 21 / `0c0798e15e34cfd496072aa8c7efc1958758710b3ce4b66064d9358c63ac26b8` |
| 2 | `task10t-qwen25-32b-probe-2-20260811` / `job-20260811T200142Z-task10t-p2` | 200 | `done=true`, `stop` | 42 / 6 | 0.201 s | 0.713 s | 3.322 s | 4.238 s | 21 / `0c0798e15e34cfd496072aa8c7efc1958758710b3ce4b66064d9358c63ac26b8` |
| 3 | `task10t-qwen25-32b-probe-3-20260811` / `job-20260811T200156Z-task10t-p3` | 200 | `done=true`, `stop` | 42 / 6 | 0.191 s | 0.674 s | 3.183 s | 4.049 s | 21 / `0c0798e15e34cfd496072aa8c7efc1958758710b3ce4b66064d9358c63ac26b8` |

All three returned the exact diagnostic text `RUNTIME_ACCEPTANCE_OK`. The text
was retained evaluator-side and never passed to ws-code-agent. The completion
metadata SHA-256 values, in probe order, are:

```text
87b7ec78d5aec42a45e9ba869967545231390263b6fd4ffda7026ed6ad228027
303837d8dceef53986377d12472c28defa10190579a734f3c3a596b2baf9a059
e30d33a5326de2fd22447e7cb8e48175e3fe64bb32a38b3c05f890d57a6c8d5b
```

No repeat-limit event occurred.

## Residency and health

The empirical classification is `GPU_PRIMARY_PARTIAL_OFFLOAD`. Every probe's
loaded observation reported 29% CPU / 71% GPU and effective context 4096.
NVIDIA telemetry observed 14,634 MiB peak VRAM; per-probe minimum available
host RAM was 14,040,117,248, 14,044,844,032, and 14,011,752,448 bytes.
The series minimum was therefore 14,011,752,448 bytes, with no swap.

The runner used 47 of 65 layers on CUDA. mmap remained in its ordinary enabled
state; the process had no `--no-mmap` override. The placement is genuinely
GPU-primary under gpu-compute policy because GPU percentage is strictly greater
than CPU percentage, and the host remained healthy.

Closeout found Ollama active and enabled, a healthy GPU, no OOM/CUDA/XID
evidence, no failed units, sane host memory, and 70,559,580,160 bytes free in
the model store. The acquired artifact was retained.

Raw peer evidence remains under:

- `/srv/gpu-compute/evidence/20260811T194534Z-task10t-qwen25-32b-acquisition/`;
- `/srv/gpu-compute/evidence/task10t-qwen25-32b-runtime-20260811/`.

## Scale-control and disposition

The Qwen2.5-Coder 14B practical baseline remains unchanged: runtime accepted,
full-GPU on Katra, and strict V2 admission failed. Task 10T supplies only 32B
runtime evidence; no behavioral comparison has run.

```text
profile_id = qwen25-coder-32b-katra-4096
empirical_fit = GPU_PRIMARY_PARTIAL_OFFLOAD
QWEN25_CODER_32B_RUNTIME_ACCEPTED
production_admission = NOT_EVALUATED
NEXT: BIND QWEN2.5-CODER 32B SCALE CONTROL TO FROZEN V2 ADMISSION SEAM
```

Exactly the selected artifact was acquired in one pull. Exactly three neutral
probes ran, with no retry or tuning. No V2, safeguard relaxation, Markdown
normalization, protocol or fixture change, context change, Ollama change, 14B
rescore, or authority broadening occurred.
