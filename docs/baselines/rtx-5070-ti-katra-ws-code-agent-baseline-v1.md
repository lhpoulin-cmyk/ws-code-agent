# RTX 5070 Ti Katra ws-code-agent baseline v1

Baseline ID: `RTX_5070_TI_KATRA_WS_CODE_AGENT_BASELINE_V1`

Status: `FROZEN`

This baseline preserves existing Task 11F, 11L, 11M, and 11N evidence. It did
not rerun a model and is not a production qualification or a single composite
speed score.

## Interactive/practical 14B binding

```text
GPU: NVIDIA GeForce RTX 5070 Ti
worker: INTERACTIVE_PRACTICAL_CODER
model: qwen2.5-coder:14b-instruct-q4_K_M
manifest: 9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849
runtime profile: qwen25-coder-14b-katra-4096
context: 4096
placement: 100% GPU / 0% CPU
typical loaded VRAM: 9,312 MiB
```

Per-task evidence:

| Task | Surface / validation | Cold load / cold total | Warm turn totals | Prompt / eval tokens by turn | Decode tokens/s by turn | Peak VRAM / placement / context |
|---|---|---|---|---|---|---|
| 11F | synthetic existing-file code; visible PASS; hidden PASS | 3.977 / 5.121 s | 0.631, 0.947 s | 651/67, 667/31, 700/53 | 73.99, 74.78, 74.25 | 9,312 MiB; 100% GPU / 0% CPU; 4096 |
| 11L | real documentation; visible FAIL; hidden not run | 3.474 / 4.762 s | 0.650, 1.798 s | 673/77, 690/32, 756/115 | 73.68, 74.74, 73.14 | 9,312 MiB; 100% GPU / 0% CPU; 4096 |
| 11M | real state documentation; visible PASS; hidden PASS | 3.731 / 4.927 s | 0.577, 2.272 s | 668/71, 684/27, 3359/91 | 74.25, 75.11, 70.41 | 9,312 MiB; 100% GPU / 0% CPU; 4096 |
| 11N | real executable Python; visible FAIL; hidden not run | 3.712 / 4.443 s | 1.977 s | 685/36, 2078/100 | 74.25, 72.14 | 9,312 MiB; 100% GPU / 0% CPU; 4096 |

The retained descriptive decode range for these unlike governed tasks is
`70.41–75.11 tokens/second`. It is a range, not an averaged quality or speed
score.

## Deliberative/overnight 32B Katra runtime baseline

```text
role: DELIBERATIVE_OVERNIGHT_CODER
model: qwen2.5-coder:32b-instruct-q4_K_M
manifest: b92d6a0bd47ee79114298de0177bf920c05a706d12633950b3936778492bef41
runtime profile: qwen25-coder-32b-katra-4096
context: 4096
placement: 71% GPU / 29% CPU
accepted runtime peak: 14,634 MiB VRAM
Task 10V loaded observation: 14,664 MiB VRAM
```

Task 10V retained write-turn totals of 105.884 and 49.493 seconds and a
clarification-turn total of 22.066 seconds. The corresponding decode rates,
derived from the retained evaluation counts and durations, are approximately
1.559, 1.562, and 1.615 tokens/second. This is a runtime comparison baseline,
not production qualification.

## Interpretation boundary

The Katra record demonstrates governance, containment, source grounding,
structured exact replacement, and at least one bounded real edit. It does not
establish broad `INTERACTIVE_PRACTICAL_CODER` capability or grant general
production use. Task 11N's remaining observed failure is semantic reasoning,
not patch transport or edit-span mechanics.
