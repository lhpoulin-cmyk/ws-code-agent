# Frozen benchmark run evidence

Status: **executed / operator review required**

Run ID: `benchmark-20260802T234320Z`
Benchmark revision: `ws-doc-writer-frozen-10/v1`
Application commit: `3a02a2e1c78426aab3dbcc655ebfdd103e37b7fd`
Runner version: `ws-doc-writer-benchmark-runner/v1`
Runner SHA-256: `129ec25668804191fdbfc5f533c03df3721eaf48cf312049711e16b58de30511`
Fixture-manifest SHA-256: `d7733f19769a8bdde199250c24829186394559e6fd50128524fd803f2bd9ab1d`

The complete matrix ran sequentially: three pinned candidates by ten frozen
application cases, for 30 outputs. All 30 raw responses were retained under
`/srv/ws-doc-writer/benchmarks/runs/benchmark-20260802T234320Z/`; the protected blind mapping is
`mapping.json` with mode `0600`. The anonymous review bundle is under
`/srv/ws-doc-writer/benchmarks/blinded/benchmark-20260802T234320Z/`.

Every record used context `8192`, temperature `0.2`, top-p `0.9`, seed `42`,
streaming disabled, and thinking disabled. Every record reported `100% GPU`.
Observed generation rates were approximately 51-53 tok/s for blind amber,
52-54 tok/s for blind cobalt, and 59-61 tok/s for blind verdant. The mapping
remains protected from the ordinary review bundle.

The runtime remained XFS, mounted read-write with project quotas. Benchmark
project usage after the run was 688 KiB of the 20 GiB hard limit. No winner was
selected automatically. All generated prose remains `REVIEW_REQUIRED` pending
operator scoring and disposition.
