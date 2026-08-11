# Task 10M Devstral challenger selection

Date: 2026-08-11

Selection foundation: `623259fa982f4e38e42aebea73814f49c7b39473`

This is selection and read-only discovery evidence. It performs no pull,
inference, runtime acceptance, production admission, Alpha evaluation, model
tuning, or peer mutation.

## Selection

```text
candidate id: devstral-small-2-q4
status: SELECTED_FOR_EVALUATION
canonical upstream: mistralai/Devstral-Small-2-24B-Instruct-2512
Ollama tag: devstral-small-2:24b-instruct-2512-q4_K_M
```

The selection rationale is bounded:

1. Devstral is independent of the previously tested Qwen family.
2. The model is explicitly specialized for agentic software engineering.
3. The official Ollama registry publishes a local-execution artifact for the
   exact selected tag.
4. Its approximately 15 GB artifact class is appropriate for Katra fit
   characterization.
5. Selection avoids immediately testing another Qwen-family artifact.
6. `gpt-oss:20b` remains an unselected later control.

These facts do not predict superiority or qualification.

## Resolved artifact

The official Ollama registry manifest was read without downloading any model
layer. The selected tag resolved on 2026-08-11 as:

```text
manifest digest: 24277f07f62db8f9cb68e9dfc679ea1818a7fbac47a50eff0a701d3f645b63c8
manifest config: sha256:cc6f162f94fe1e564f0c639e31fd4f16db2a89a99b0559b0348573d7884b24ec
model layer: sha256:c580819bed79c92d01a42227bd6d8fd66b9ec60d5329f5eb73f812f156af7807
model-layer bytes: 15177370240
model family: mistral3
parameter class: 24.0B
quantization: Q4_K_M
context metadata: 393216 tokens
comparison context: 4096
explicit generation parameters: temperature = 0.15
```

The parameter layer contains only `temperature: 0.15`; other generation
parameters are not explicitly set by the artifact and remain Ollama defaults.
The live Katra model list did not contain the selected tag. No pull was needed
to establish identity, so no acquisition was performed.

Official metadata endpoints:

- `https://registry.ollama.ai/v2/library/devstral-small-2/manifests/24b-instruct-2512-q4_K_M`
- `https://ollama.com/library/devstral-small-2/tags`

## Read-only Katra observation

Observed at approximately `2026-08-11T04:20Z` on
`cuda-compute-katra` / VM 320:

| Surface | Observation |
| --- | --- |
| GPU | NVIDIA GeForce RTX 5070 Ti |
| VRAM | 16,303 MiB total; 15,880 MiB free |
| GPU health | 37 C; 0% utilization; 17.37 W |
| Host RAM | 16,692,588,544 bytes total; 15,548,469,248 bytes available; no swap |
| Driver | NVIDIA 610.57.04 |
| CUDA | 13.3 / nvcc 13.3.73 |
| Kernel | Linux 7.0.0-22-generic x86_64 |
| Ollama | 0.32.0; service active/running |
| Loaded models | none |
| Root storage | 44,755,161,088 bytes available |
| Model storage | `/dev/sdb` ext4 at `/mnt/models`; 114,576,482,304 bytes available |
| Failed systemd units | none |
| Host load | 0.00 / 0.00 / 0.00 |

Ollama `0.32.0` exceeds the artifact's required minimum `0.13.3`.

The source authority is gpu-compute HEAD
`d7f30f14f2cf4f7ec376c96441ce2370bbf9230f`. The canonical deployment omits
`.git`; deployed `bin/run`, `bin/run-status`, and
`config/model-runtime-profiles.tsv` hashes matched that source checkout:

```text
bin/run: 01df6117f172e92e5986b67566f7e40734c052ad84f235b0538810e10e355109
bin/run-status: 1ef3028cea29929bda7de4de9108be7080b53e20b2f690a7b4877be1e0f56468
model-runtime-profiles.tsv: 5a655926cb6cff375cbd61a401ab494b7f456fa558713f99c8a63e93d0b189c5
```

## Expected fit

`PARTIAL_OFFLOAD_EXPECTED`

This is planning evidence, not runtime acceptance. The 15,177,370,240-byte
model layer plus 4096-context KV state and runtime buffers leaves a narrow
margin against 16,303 MiB VRAM. Host RAM also has limited headroom and no swap,
so the next play must observe pressure and fail closed rather than infer fit
from size alone. gpu-compute currently has no accepted exact-artifact runtime
profile for Devstral; no execution-policy or gpu-cp acceptance change occurs
here.

## Frozen comparison contract

The challenger must receive:

- `WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE`, unchanged;
- the Task 10K-C synthetic write and clarification fixtures, unchanged;
- identical authority and eight-turn budgets;
- identical P11 executor semantics, durability, parser, and containment;
- no candidate-specific prompt, hint, repair, or schema broadening; and
- the both-required production-admission rule.

The evaluation order is frozen:

1. runtime/artifact acceptance on Katra;
2. V2 synthetic write admission;
3. V2 synthetic clarification admission;
4. only if both admission behaviors pass, broader Alpha/challenger
   qualification under separate authorization.

The next executable boundary is runtime/artifact acceptance. This record does
not authorize a pull or inference.
