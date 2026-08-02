# ws-doc-writer

`ws-doc-writer` is the application control plane for evidence-led technical
document writing. It turns approved source material into reviewable proposed
documents; it does not own workstation or accelerator infrastructure.

## Peer boundary

```text
ws-doc-writer  application behavior, prompts, validation, scoring, provenance
ws-cp          ws-matriarch and Ollama service mechanics
gpu-cp         RX 9070 XT accelerator contract and acceptance
```

The peers retain authority in their domains. A disagreement stops the packet
and returns to the operator.

## Current status

Foundation only. No model has been pulled, no service has been changed, and no
benchmark has run. The initial workload is `ws-doc-writer` on `ws-matriarch`.

## Layout

- `docs/` lifecycle and integration contracts
- `prompts/` model-neutral prompt contracts
- `benchmarks/` frozen cases and evaluation design
- `manifests/` candidate model metadata
- `schemas/` small machine-readable validation contracts
- `implementation/` blocked coordinated packet foundation
- `tests/` repository checks
