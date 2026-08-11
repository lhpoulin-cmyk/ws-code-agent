# Task 10S Qwen2.5-Coder 32B scale-control selection

Date: 2026-08-11

Play: `The Measure of a Man`

Checkpoint: `TASK10S-SELECT-QWEN25-CODER-32B-SCALE-CONTROL`

Task 10S selected Qwen2.5-Coder 32B Q4_K_M as a same-family scale
control against the retained practical Qwen2.5-Coder 14B baseline. This was
read-only artifact, source, interface, and Katra discovery followed by a matrix
selection. No artifact acquisition, model load, inference, or runtime mutation
occurred.

## Foundation

The clean, direct-origin-parity checkpoints were:

```text
ws-code-agent: 2e79f4af5d7283d6a5594e4be317227125e7516e
gpu-compute:   fc514cb02c9a2f76c60b461f787fba9ee43e2364
gpu-cp:        a84c33f68dcb14b292d791c8485e0ec4e532852c
```

Before the selection change, ws-code-agent passed all 126 tests plus the
containment, private-material, lineage, invariant-register, YAML, and diff
gates. All eight gpu-compute suites passed. The peer repositories remained
unchanged.

After the matrix, evidence, and focused regression update, ws-code-agent passed
all 127 tests with no reduction, the separate two-test private-material check,
containment, lineage, invariant-register, YAML, and diff gates. Only
ws-code-agent required a source-authority change.

## Retained 14B practical baseline

The exact 14B artifact remains runtime accepted under the
`qwen25-coder-14b-katra-4096` profile at effective context 4096, 100% GPU,
0% CPU, and 9,304 MiB observed VRAM. Its role as the practical coding baseline
is retained.

Its strict V2 results remain failed without rescore. In the write fixture it
produced a semantically plausible authorized `PROPOSE_PATCH`, but wrapped the
object in Markdown, yielding `MALFORMED_REQUEST`. In the clarification fixture
it produced a Markdown-fenced `NO_CHANGE`, also yielding `MALFORMED_REQUEST`;
independently of formatting, `NO_CHANGE` did not satisfy the required
`REQUEST_CLARIFICATION` judgment. These semantic, protocol, and parser
dimensions remain separate.

## Exact 32B artifact

The current official registry manifest resolved as:

```text
candidate: qwen25-coder-32b-q4
canonical upstream: Qwen/Qwen2.5-Coder-32B-Instruct
tag: qwen2.5-coder:32b-instruct-q4_K_M
manifest SHA-256: b92d6a0bd47ee79114298de0177bf920c05a706d12633950b3936778492bef41
manifest bytes: 859
config: sha256:f0676bd3c336a0f995e270c5e2c80ce09aa5cfcab0c59ff574088eca52da32ee
config bytes: 488
model layer: sha256:ac3d1ba8aa77755dab3806d9024e9c385ea0d5b412d6bdf9157f8a4a7e9fc0d9
model layer bytes: 19,851,336,384
system: sha256:66b9ea09bd5b7099cbb4fc820f31b575c0366fa439b08245566692c6784e281e
system bytes: 68
template: sha256:1e65450c30670713aa47fe23e8b9662bdf4065e81cc8e3cbfaa98924fcc0d320
template bytes: 1,615
license: sha256:832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e
license bytes: 11,343
parameters layer: ABSENT
architecture: dense qwen2
parameter class: 32.8B artifact / 32.5B upstream
quantization: Q4_K_M
context metadata: 32768
generation overrides: NONE_SPECIFIED
```

The manifest digest is the SHA-256 of the exact registry response bytes. Only
the small manifest, config, system, and template evidence blobs were inspected;
the 19.85 GB model layer was not downloaded.

## Same-family control and interface

The exact 14B and 32B manifests refer to the same 68-byte system layer and the
same 1,615-byte template layer. Their system message, FIM/plain/messages prompt
branches, instruction formatting, assistant marker, and conditional tool
formatting are therefore byte-identical. Neither artifact has a parameters
layer, so neither specifies a generation override. The config blobs differ in
model type (`14.8B` versus `32.8B`) and model-layer identity; both identify
`qwen2` and `Q4_K_M`.

The 32B artifact can therefore face
`WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE` through the existing
plain machine-response transport. This is interface eligibility, not a claim
that the model will obey the protocol. No Markdown stripping, JSON repair or
forcing, candidate-specific prompt, format or path hint, sampling change,
retry, continuation, tool wrapper, or chat conversion is required or was
implemented.

```text
frozen V2 compatible: YES
candidate-specific accommodation required: NO
```

## Exact context and runtime compatibility

The upstream model config sets `max_position_embeddings` to 32768, disables
sliding-window use, and does not configure YaRN. Ollama v0.32.0 source gives an
explicit request `num_ctx` priority over model, environment, and VRAM-derived
defaults. The runner path only reduces a request above the model training
context; it does not raise a smaller request, and it passes the resulting
context directly to the llama-server `-c` argument. No qwen2-specific minimum
context branch exists.

Therefore:

```text
requested = 4096
effective = 4096
QWEN25_CODER_32B_CONTEXT_4096_COMPATIBLE
```

The patched runtime remains `0.32.0+helix.repeatlimit.1`, based on v0.32.0.
That source supports qwen2, the generic Q4_K_M path, and request context 4096;
the already accepted exact 14B artifact exercises the same architecture and
quantization. The local semantic deviation changes repeat-limit terminal
reporting only and is irrelevant to loading or sampling. No Ollama upgrade or
runtime change occurred.

## Katra planning fit

The read-only observation was captured on `cuda-compute-katra` at
2026-08-11T19:32:16Z:

```text
GPU: NVIDIA GeForce RTX 5070 Ti
VRAM: 16,303 MiB total / 15,880 MiB free
host RAM: 16,301,356 kB total / 14,337,976 kB available
swap: none
model-store free: 90,410,938,368 bytes
Ollama: 0.32.0+helix.repeatlimit.1, active and enabled
loaded models: none
failed units: none
GPU health: no XID, OOM, or CUDA failure evidence
```

The 19,851,336,384-byte model layer alone exceeds physical VRAM, so full-GPU
placement is not plausible. Allowing for runtime and 4096-context overhead
leaves a minority of weights for host placement. Current available RAM can
plausibly contain that spill, so the expected mode remains GPU-primary rather
than CPU-dominated. No swap makes host pressure a material acceptance risk,
but not an evidence-based selection blocker; the next play must measure actual
placement and stop on unsafe pressure.

```text
planning fit: GPU_PRIMARY_PARTIAL_OFFLOAD_EXPECTED
host-pressure assessment: ELEVATED_BUT_BOUNDED_FOR_RUNTIME_ACCEPTANCE
```

This differs operationally from the 14B full-GPU baseline, so later behavioral
differences cannot be attributed to scale alone without retaining the measured
runtime profile as a possible confound. The experiment nevertheless preserves
family, Instruct lineage, dense qwen2 architecture, Q4_K_M quantization,
normal 32768 context metadata, exact 4096 comparison context, template,
transport, protocol, parser, executor, and fixtures.

## Selection

The candidate remains useful as an explicit scale control and is eligible for
artifact/runtime acceptance:

```text
NEXT_MODEL_CANDIDATE = qwen25-coder-32b-q4
ROLE = INTRA_FAMILY_SCALE_CONTROL
STATUS = SELECTED_FOR_EVALUATION
NEXT: RUN QWEN2.5-CODER 32B ARTIFACT/RUNTIME ACCEPTANCE
```

The candidate is not acquired, runtime accepted, production admitted,
preferred, default, or a replacement for the retained 14B practical baseline.
No pull, inference, safeguard relaxation, Markdown normalization, output
repair, retry, protocol or fixture change, context change, Ollama change,
historical rescore, or authority broadening occurred.

```text
model pull count: 0
model load count: 0
model inference count: 0
```

## Sources

- [Official Ollama Qwen2.5-Coder tags](https://ollama.com/library/qwen2.5-coder/tags)
- [Exact official registry manifest](https://registry.ollama.ai/v2/library/qwen2.5-coder/manifests/32b-instruct-q4_K_M)
- [Official upstream model card](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct)
- [Pinned upstream model configuration](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct/blob/2c4471c2c2f8c4813358c59a3c91c9f34ad6bf70/config.json)
- [Ollama v0.32.0 source](https://github.com/ollama/ollama/tree/v0.32.0)
