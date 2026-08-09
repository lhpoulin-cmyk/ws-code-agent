# ws-code-agent

`ws-code-agent` is an operator-authorized foundation for a locally governed,
bounded coding-agent capability. It is a separate application authority derived
architecturally from `ws-doc-writer`; it is not a conversion of Doc Writer into
an autonomous coding agent, and no coding executor exists yet.

The governing foundation contract is
[`docs/contracts/CODING_AGENT_FOUNDATION_CONTRACT.md`](docs/contracts/CODING_AGENT_FOUNDATION_CONTRACT.md).

## Current status

Foundation only. The contract, voice, agent, and escalation doctrine are in
place. There is no executor, no capability-lease implementation, no coding
schema, and no benchmark. The inherited Doc Writer implementation has been
removed from the live tree; witnessed history and reusable references are
preserved under `lineage/`. The test suite is intentionally empty.

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
- `src/` coding-agent implementation home (empty; none built yet)
- `tests/` coding-agent tests (empty; none written yet)
- `lineage/` inherited Doc Writer history and reference material (no authority)
