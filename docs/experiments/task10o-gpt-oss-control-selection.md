# Task 10O gpt-oss control selection

Date: 2026-08-11

Play: `The Neutral Zone`

Checkpoint: `TASK10O-SELECT-GPT-OSS-CONTROL`

This is artifact discovery and candidate-selection evidence only. It performs
no model pull, model load, inference, runtime mutation, protocol or fixture
change, comparison-context change, or historical rescore.

## Foundation

- ws-code-agent starting point:
  `1a8b556676d21b79ed1387bff38a918b19130a20`
- gpu-compute implementation:
  `0752c5d11b94df48ed01d78807e1012a53d1f92c`
- gpu-cp acceptance:
  `36851481e841048d7318060fe2a8e2a2c4b7f5b4`
- runtime deviation:
  `OLLAMA_V0_32_0_REPEAT_LIMIT_TERMINALIZATION_V1`

All three repositories began clean and at direct origin parity. The starting
ws-code-agent gate passed 120 tests plus the separate two-test private-material
check, lineage verification, invariant verification, and diff checks. All eight
current gpu-compute unit suites passed.

## Prior challenger reconciliation

Devstral is not rescored. Its settled record is:

```text
runtime: ACCEPTED
Task 10N production admission: FAIL
clarification: PASS
write: FAIL
observed terminal model outcome: MODEL_REPEAT_LIMIT
Ollama repeat-limit reporting defect: REPAIRED / GOVERNED
admission retry: NOT AUTHORIZED
```

The repaired terminal reporting does not convert its evaluator-only partial
content into a successful response and does not authorize another admission
attempt.

## Proposed control and rationale

The discovery target was `gpt-oss-20b-mxfp4`, canonical upstream
`openai/gpt-oss-20b`, official Ollama tag `gpt-oss:20b`, and role `CONTROL`.
It was considered because it is a different family and sparse architecture from
Qwen and Devstral, is explicitly agentic/developer-oriented, has an
approximately 14 GB artifact suitable for planning against Katra's constrained
16 GB environment, and tests whether the frozen V2 interface rewards general
agentic reasoning rather than coding specialization. This rationale makes no
superiority claim.

## Exact public artifact

The official registry manifest was read without downloading the model layer:

```text
tag: gpt-oss:20b
manifest: 17052f91a42e97930aa6e28a6c6c06a983e6a58dbb00434885a0cf5313e376f7
config: sha256:776beb3adb235076157cfea408b8ea2a2d25eae99d7f5da997f607f6b69fa0fa
model layer: sha256:e7b273f9636059a689e3ddcab3716e4f65abe0143ac978e46673ad0e52d09efb
model layer bytes: 13,793,422,144
template: sha256:fa6710a93d78da62641e192361344be7a8c0a1c3737f139cf89f20ce1626b99c
parameters: sha256:d8ba2f9a17b3bbdeb5690efaa409b3fcb0b56296a777c7a69c78aa33bbddf182
architecture: MoE / gptoss
parameter class: 20.9B
quantization: MXFP4
context metadata: 131072
advertised artifact size: approximately 14 GB
```

The parameter blob specifies only `temperature = 1`; unspecified generation
defaults are not inferred. The official Harmony template selects medium
reasoning when no reasoning level is supplied. The frozen seam supplies no
tools or structured-output request.

Sources:

- `https://registry.ollama.ai/v2/library/gpt-oss/manifests/20b`
- `https://ollama.com/library/gpt-oss:20b`
- `https://openai.com/index/introducing-gpt-oss/`
- `https://deploymentsafety.openai.com/gpt-oss/architecture`

## Runtime and interface compatibility

Katra runs accepted Ollama `0.32.0+helix.repeatlimit.1`, based on upstream
v0.32.0. That release supports the `gptoss` architecture and native MXFP4 used
by the official artifact. Its Harmony integration recognizes gpt-oss templates
and separates analysis-channel thinking from final-channel content, so the
existing plain machine-response transport does not require a candidate-specific
prompt, disabled reasoning, tool injection, or structured-output adaptation.

The local semantic deviation changes repeat-guard terminal reporting only. It
does not change model loading, gpt-oss architecture support, MXFP4 kernels,
sampling, or context behavior. No runtime change was made.

Upstream source references:

- `https://github.com/ollama/ollama/tree/v0.32.0`
- `https://github.com/ollama/ollama/blob/v0.32.0/harmony/harmonyparser.go`
- `https://github.com/ollama/ollama/blob/v0.32.0/server/routes.go`

## Exact-context gate

The frozen comparison requests context 4096. Operator-supplied upstream
implementation evidence establishes that the gpt-oss integration requires a
minimum context of 8192 and silently raises lower values. The historical
upstream reproduction independently shows a model configured with
`num_ctx=4096` loading with runner context 8192:

`https://github.com/ollama/ollama/issues/11711`

Therefore:

```text
requested comparison context = 4096
effective gpt-oss minimum     = 8192
```

`GPT_OSS_CONTEXT_MINIMUM_EXCEEDS_4096`

The comparison context cannot be changed merely to admit this control. This is
an interface-eligibility result, not a model-quality failure or runtime
incompatibility.

## Operator-supplied Katra preflight

The operator supplied the current read-only observation after sandbox policy
prevented direct SSH. It is authoritative for this checkpoint:

| Surface | Observation |
| --- | --- |
| Host | `cuda-compute-katra` |
| GPU | NVIDIA GeForce RTX 5070 Ti |
| VRAM | 16,303 MiB total; 15,880 MiB free |
| Host RAM | 14,737,571,840 bytes available; no swap |
| Model storage | 99,399,086,080 bytes free |
| Driver / CUDA | 610.57.04 / 13.3 |
| Ollama | `0.32.0+helix.repeatlimit.1` |
| Ollama binary | `b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143` |
| Build ID | `ffd1f9f6c8ffd69fdca1316e7c032447479fe139` |
| Service | active and enabled; no failed units |
| Loaded models | none |
| Deployment | canonical `/srv/gpu-compute` present and healthy |

The planning fit classification is:

`GPU_PRIMARY_PARTIAL_OFFLOAD_EXPECTED`

The 13,793,422,144-byte model layer leaves narrow VRAM headroom for compute and
the enforced 8192 context. This is planning only; no Qwen or Devstral profile is
transferred, and gpt-oss has no runtime acceptance.

## Selection disposition

The exact official artifact is resolved, patched Ollama is runtime-compatible,
the frozen plain interface requires no model-specific adaptation, and Katra fit
is plausibly usable. The candidate nevertheless fails the all-required
selection rule because it cannot honor context 4096 exactly.

```text
NEXT_MODEL_CANDIDATE = UNRESOLVED
STATUS = NEXT_SELECTION_REQUIRED
NEXT: SELECT NEXT ELIGIBLE CHALLENGER
```

`gpt-oss-20b-mxfp4` is not installed, runtime accepted, production admitted,
qualified, selected for evaluation, or selected as a default.

No model pull, inference, Ollama upgrade, runtime change, protocol or fixture
change, context change, model-specific hinting, authority broadening, or
historical rescore occurred.

`TASK 10O COMPLETE — GPT-OSS 20B REJECTED FROM THE FROZEN 4096 COMPARISON SEAM BECAUSE ITS ENFORCED MINIMUM CONTEXT IS 8192`
