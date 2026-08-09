# ws-code-agent

`ws-code-agent` is an operator-authorized foundation for a locally governed,
bounded coding-agent capability. It is a separate application authority derived
architecturally from `ws-doc-writer`; it is not a conversion of Doc Writer into
an autonomous coding agent.

The foundation preserves governance, provenance, prompting, clarification,
review, and evaluation patterns that proved useful in Doc Writer. Its future
scope is bounded repository observation, patch proposals, sandbox validation,
and explicitly authorized Git actions. It does not yet provide a general shell
executor, autonomous Git action, deployment authority, or production service.

The governing foundation contract is
[`docs/contracts/CODING_AGENT_FOUNDATION_CONTRACT.md`](docs/contracts/CODING_AGENT_FOUNDATION_CONTRACT.md).

## Foundation provenance

This repository was independently cloned with preserved Git history from
`/home/louis/src/ws-doc-writer` at source HEAD
`dfb759afb7826a2b849fa95bf40ce6f06cd3cd05` on 2026-08-09. It also records the
independent Doc Writer verification checkpoint
`7ae3d5794691fd769446702015f331367344df9d`. The inherited implementation
remains visibly writing-specific until a coding equivalent receives explicit
design and review; it is not silently relabeled as a coding executor.

## Inherited material boundary

The content below is historical lineage, not the current authority or runtime
identity of `ws-code-agent`. No inherited runtime database, cache, credentials,
TLS material, host configuration, deployment state, or generated model output
was copied into this foundation.

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

- `docs/contracts/` operator-authorized architectural contracts
- `docs/` lifecycle and integration contracts
- `prompts/` model-neutral prompt contracts
- `benchmarks/` frozen cases and evaluation design
- `manifests/` candidate model metadata
- `schemas/` small machine-readable validation contracts
- `implementation/` blocked coordinated packet foundation
- `tests/` repository checks
