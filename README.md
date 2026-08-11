# ws-code-agent

`ws-code-agent` is an operator-authorized foundation and Alpha harness for a
locally governed, bounded coding-agent capability. It is a separate application
authority derived architecturally from `ws-doc-writer`; it is not a conversion
of Doc Writer into an autonomous coding agent.

The governing foundation contract is
[`docs/contracts/CODING_AGENT_FOUNDATION_CONTRACT.md`](docs/contracts/CODING_AGENT_FOUNDATION_CONTRACT.md).

## Current status

Alpha v1 is frozen and the executor/harness is qualified for model evaluation.
The exact tested `qwen3-coder:30b` artifact has completed Alpha evaluation and
demonstrated useful bounded `OBSERVE_ONLY`, `CLARIFY_AND_REPORT`, and narrow
`SUPERVISED_SINGLE_REPO` capabilities. Those capability findings are preserved,
but the artifact is `NOT_ADMITTED` to the supervised production lane after it
failed both required value-free V2 synthetic behaviors. Autonomous single- and
multi-repository operation remain `NOT_QUALIFIED`; C05 remains a confirmed
model failure under explicit authority and effect-state semantics. See the
[qualification statement](docs/qualification/qwen3-coder-30b-alpha-v1.md).

`WS_CODE_AGENT_REQUEST_PROTOCOL_V1_SINGLE` remains frozen for Alpha v1.
`WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE` is the frozen candidate
supervised-production interface: its interface design is accepted, but this
Qwen artifact did not qualify it for production use. Task 10K is closed for
Qwen with admission failed; it is not waiting for another Qwen-specific repair.
The operator-gated lane and challenger admission contract are documented in
[supervised single-repository work](docs/work/supervised-single-repo.md).

```text
Alpha v1: FROZEN
Qwen: ALPHA COMPLETE; PRODUCTION NOT ADMITTED
V2 single-repository protocol: FROZEN CANDIDATE INTERFACE
Task 10K: CLOSED FOR QWEN — ADMISSION FAILED
```

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
