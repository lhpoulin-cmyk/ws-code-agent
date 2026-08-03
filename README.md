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

The frozen ten-case benchmark implementation is prepared in the application
repository. The runner requires a clean committed revision, validates all
frozen hashes and host gates, executes 30 sequential model/case runs, and
produces raw evidence plus a blinded review bundle. Generated prose remains
`REVIEW_REQUIRED`; no model winner or document acceptance is automatic.

The first complete 30-output run is recorded as `benchmark-20260802T234320Z`; operator scoring and
disposition remain outstanding.

## Local review surface

The prepared local review surface is documented in
[`docs/web-review-surface.md`](docs/web-review-surface.md). It is an
authenticated, operator-only draft and review UI with SQLite state under the
existing `/srv/ws-doc-writer` storage boundary. Model execution is disabled;
all generated prose remains `REVIEW_REQUIRED`.

## Layout

- `docs/` lifecycle and integration contracts
- `prompts/` model-neutral prompt contracts
- `benchmarks/` frozen cases and evaluation design
- `manifests/` candidate model metadata
- `schemas/` small machine-readable validation contracts
- `implementation/` blocked coordinated packet foundation
- `tests/` repository checks
