# Ollama and benchmark coordination packet

Status: **executed / operator review required**.

`ws-doc-writer` supplies prompts, frozen cases, scoring, and acceptance
requirements. `ws-cp` must perform any workstation/Ollama mutation. `gpu-cp`
must attest the RX 9070 XT and full-GPU behavior. No model pull or service
change occurs in this repository.

The model store requirement is 128 GB dedicated permanently to `ws-doc-writer`
on the Crucial Gen5 NVMe. It may be carved only from the unpartitioned gap;
the remaining gap must stay unassigned. Device identity, partition geometry,
filesystem, mount path, free-space proof, and recovery procedure are unresolved
until `ws-cp` performs read-only discovery and prepares its own packet.

Stop on wrong host or GPU, unresolved versions or permissions, insufficient
storage, Intel-override conflict, API exposure, CPU/partial offload, unsafe
thermals, digest mismatch, inconsistent benchmark, or peer disagreement.

Completion requires pinned digests, preserved original outputs, blinded review,
validation evidence, peer acceptance, and explicit operator disposition.

The packet must consume the storage manifest, reproducibility schema, evidence
encryption contract, and daily soak template. It remains blocked until `ws-cp`
proves disk geometry and storage acceptance and `gpu-cp` proves accelerator
acceptance.


## Implemented benchmark revision

The application owns ten frozen, provenance-labeled fixtures, scoring and
reproducibility contracts, and `tools/benchmark_runner.py`. The runner validates
all hashes, runtime gates, pinned model identities, loopback exposure, 8192
context, disabled thinking, sequential execution, 100% GPU residency, raw
output retention, blind mapping separation, and `REVIEW_REQUIRED` disposition.
It writes only beneath `/srv/ws-doc-writer/benchmarks` and never chooses a
model or marks generated prose accepted.


The first complete run succeeded as `benchmark-20260802T234320Z` with 30 outputs. Operator review and disposition remain required.
