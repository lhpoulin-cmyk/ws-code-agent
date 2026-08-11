# Task 10P Qwen2.5-Coder 14B challenger selection

Date: 2026-08-11

Play: `Relics`

Checkpoint: `TASK10P-SELECT-QWEN25-CODER-14B`

This is artifact discovery and candidate-selection evidence only. It performs
no model pull, model load, inference, runtime mutation, protocol or fixture
change, comparison-context change, or historical rescore.

## Foundation

- ws-code-agent starting point:
  `37d87fdb2729c28f1e67a1cd046f9c2df8ad4079`
- gpu-compute implementation:
  `0752c5d11b94df48ed01d78807e1012a53d1f92c`
- gpu-cp acceptance:
  `36851481e841048d7318060fe2a8e2a2c4b7f5b4`
- runtime deviation:
  `OLLAMA_V0_32_0_REPEAT_LIMIT_TERMINALIZATION_V1`

All three repositories began clean and at direct origin parity. The starting
ws-code-agent host-containment Alpha gate passed 121 tests plus the current
lineage and invariant checks. All eight current gpu-compute unit suites passed.

## Preserved dispositions

This selection does not rescore earlier candidates:

```text
Qwen3-Coder 30B production: NOT_ADMITTED
Devstral Small 2 runtime: ACCEPTED
Devstral Small 2 production admission: FAIL
Devstral Small 2 observed outcome: MODEL_REPEAT_LIMIT
Devstral Small 2 admission retry: NOT AUTHORIZED
gpt-oss 20B: INELIGIBLE_FROZEN_COMPARISON_SEAM
gpt-oss blocker: enforced minimum context 8192 exceeds 4096
```

## Selection rationale

`qwen25-coder-14b-q4` is useful because it is code-specialized, materially
smaller than the preceding torture candidates, and naturally supports the
frozen 4096 comparison context within its ordinary 32768-token model context.
Its approximately 9 GB dense artifact is a plausible full-GPU fit on Katra's
16 GB GPU. It tests whether a smaller dense coding model can outperform larger
models on disciplined agent behavior and supplies a practical candidate rather
than another deliberate hardware torture test. This rationale does not predict
or claim admission success.

## Exact public artifact

The official registry manifest was read without requesting any artifact blob:

```text
tag: qwen2.5-coder:14b-instruct-q4_K_M
manifest: 9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849
config: sha256:0578f229f23ad620e123654fd0b4708405e7af3629ec1aecf3f553f54e06bc40
config bytes: 488
model layer: sha256:ac9bc7a69dab38da1c790838955f1293420b55ab555ef6b4615efa1c1507b1ed
model layer bytes: 8,988,110,784
system: sha256:66b9ea09bd5b7099cbb4fc820f31b575c0366fa439b08245566692c6784e281e
system bytes: 68
template: sha256:1e65450c30670713aa47fe23e8b9662bdf4065e81cc8e3cbfaa98924fcc0d320
template bytes: 1,615
license: sha256:832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e
license bytes: 11,343
parameters layer: absent
architecture: dense / qwen2
parameter class: 14.8B in the artifact; 14.7B in the upstream model card
quantization: Q4_K_M
context metadata: 32768
advertised artifact size: approximately 9.0 GB
```

Because the manifest has no parameters layer, the artifact specifies no
generation-parameter overrides. Unspecified defaults are not inferred and the
runtime's ordinary defaults remain unchanged.

Sources:

- `https://registry.ollama.ai/v2/library/qwen2.5-coder/manifests/14b-instruct-q4_K_M`
- `https://ollama.com/library/qwen2.5-coder:14b-instruct-q4_K_M`
- `https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct`

## Exact-context gate

The artifact is a text-only qwen2 model with training-context metadata 32768.
Exact Ollama v0.32.0 source establishes the following behavior:

- an explicit request `num_ctx` overrides model and runtime defaults;
- non-vision models have no minimum above the scheduler's general minimum of 4;
- a requested context is clamped only when it exceeds training context;
- Katra's less-than-23-GiB VRAM tier independently defaults to context 4096.

The artifact declares no `num_ctx` model option and no YaRN or other scaling is
enabled. Therefore both an explicit 4096 request and the accepted Katra tier
default resolve to 4096:

```text
requested = 4096
effective = 4096
```

`QWEN25_CODER_14B_CONTEXT_4096_COMPATIBLE`

Upstream's separate long-context treatment is irrelevant to this comparison.
No YaRN or context substitution was enabled.

## Interface compatibility

The official template supports Ollama's plain `.Prompt` branch and renders it
as one user turn followed by the assistant generation marker. Its tool wrapper
is conditional on tools being supplied; the frozen seam supplies none. The
artifact has no thinking mode. The existing plain `/api/generate` transport can
therefore carry `WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE` without a
candidate-specific system prompt, tool wrapper, chat API conversion, JSON
forcing, or thinking-mode manipulation.

```text
V2 interface: COMPATIBLE
candidate-specific adaptation: NOT REQUIRED
```

## Patched Ollama compatibility

Katra runs accepted Ollama `0.32.0+helix.repeatlimit.1`, based on upstream
v0.32.0. Exact source contains qwen2 conversion/runtime support, and the
llama.cpp runner supports the artifact's Q4_K_M GGUF quantization. The local
semantic deviation changes repeat-guard terminal reporting only; it does not
change qwen2 loading, quantization kernels, sampling, templates, or context
selection. No runtime change was made.

## Katra planning fit

Task 10P reuses the operator-supplied read-only Katra observation from
2026-08-11. No peer deployment or runtime change since that observation makes
a new SSH inspection necessary for selection planning:

| Surface | Observation |
| --- | --- |
| Host | `cuda-compute-katra` |
| GPU | NVIDIA GeForce RTX 5070 Ti |
| VRAM | 16,303 MiB total; 15,880 MiB free |
| Host RAM | 14,737,571,840 bytes available; no swap |
| Model storage | 99,399,086,080 bytes free |
| Driver / CUDA | 610.57.04 / 13.3 |
| Ollama | `0.32.0+helix.repeatlimit.1` |
| Service | active and enabled; no failed units |
| Loaded models | none |
| Deployment | canonical `/srv/gpu-compute` present and healthy |

The 8,988,110,784-byte model layer leaves substantial planning headroom within
16,303 MiB of VRAM for a 4096-token KV cache and runner overhead. The expected
fit classification is:

`FULL_GPU_CANDIDATE`

This is not an accepted runtime profile. GPU residency and execution policy
remain to be measured during artifact/runtime acceptance.

## Selection disposition

The exact official artifact is resolved, the patched runtime supports qwen2
and Q4_K_M, the frozen context is honored exactly, the plain interface requires
no candidate-specific adaptation, and Katra fit is plausibly usable. The
candidate satisfies the all-required selection rule.

```text
NEXT_MODEL_CANDIDATE = qwen25-coder-14b-q4
STATUS = SELECTED_FOR_EVALUATION
NEXT: RUN QWEN2.5-CODER 14B ARTIFACT/RUNTIME ACCEPTANCE
```

The candidate is not acquired, runtime-accepted, production-admitted,
qualified, or selected as a default.

No model pull, inference, context change, protocol or fixture change, Ollama
upgrade, historical rescore, or authority broadening occurred.

`TASK 10P COMPLETE — QWEN2.5-CODER 14B SELECTED AS NEXT ELIGIBLE CHALLENGER`
