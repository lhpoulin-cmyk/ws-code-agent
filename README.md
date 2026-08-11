# ws-code-agent

`ws-code-agent` is an operator-authorized foundation and Alpha harness for a
locally governed, bounded coding-agent capability. It is a separate application
authority derived architecturally from `ws-doc-writer`; it is not a conversion
of Doc Writer into an autonomous coding agent.

The governing foundation contract is
[`docs/contracts/CODING_AGENT_FOUNDATION_CONTRACT.md`](docs/contracts/CODING_AGENT_FOUNDATION_CONTRACT.md).

## Current status

Alpha v1 is frozen and the executor/harness is qualified for model evaluation.
The exact tested `qwen3-coder:30b` artifact has completed qualification for
`OBSERVE_ONLY`, `CLARIFY_AND_REPORT`, and `SUPERVISED_SINGLE_REPO` operation;
autonomous single- and multi-repository operation are not qualified. C05 is a
confirmed model failure under explicit authority and effect-state semantics.
See the [qualification statement](docs/qualification/qwen3-coder-30b-alpha-v1.md).
The operator-gated lane implementation and its current synthetic-acceptance
status are documented in
[supervised single-repository work](docs/work/supervised-single-repo.md). It is
not approved for real-repository use until the recorded Task 10K acceptance
blocker is resolved by a separate authorized play.

The inherited Doc Writer implementation remains removed from the live tree;
witnessed history and reusable references are preserved under `lineage/`.

## Foundation provenance

Independently cloned with preserved Git history from `/home/louis/src/ws-doc-writer`
at source HEAD `dfb759afb7826a2b849fa95bf40ce6f06cd3cd05` on 2026-08-09, recording
the independent Doc Writer verification checkpoint
`7ae3d5794691fd769446702015f331367344df9d`. No inherited runtime database, cache,
credential, TLS material, host configuration, deployment state, or generated
model output is part of this repository's identity.

## Peer boundary

    ws-doc-writer  document-writing application (separate authority)
    ws-cp          workstation and Ollama service mechanics
    gpu-cp         RX 9070 XT accelerator contract and acceptance

Peers retain authority in their domains. Reading, testing, or proposing a patch
grants no authority over any repository. A disagreement stops and returns to the
operator.

## Layout

- `docs/contracts/` operator-authorized architectural contracts
- `docs/` supporting doctrine (operator access, future coding lifecycle)
- `schemas/` small machine-readable validation contracts (backend plumbing)
- `config/` example runtime endpoint configuration
- `models/` model candidate matrix by VRAM tier
- `tools/` lineage verification
- `src/` bounded executor, harness, protocol, and durable experiment controller
- `tests/` deterministic and real-containment Alpha regression coverage
- `docs/qualification/` artifact-bound model qualification statements
- `lineage/` inherited Doc Writer history and reference material (no authority)
