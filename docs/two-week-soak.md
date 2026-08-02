# Two-week soak

The soak begins only after the 128 GB XFS filesystem, project quotas, AMD
ROCm/Ollama acceptance, full-GPU model acceptance, one complete benchmark run,
and monitoring/evidence capture are accepted. Documentation commit time is not
day one.

Duration: **14 calendar days**. Review cadence: **daily for all 14 days**.

Each review uses `benchmarks/daily-soak-record.template.yaml` and records
filesystem/project-quota usage, category growth, reserve, model tags/digests,
Ollama health, loopback bind state, GPU residency/performance/temperature/power,
model loading, benchmark progress, accepted/rejected outputs, evidence
encryption/recoverability, prompt and voice revisions, errors, fallback events,
discrepancies, and operator observations.

There is no automatic promotion, missed-day reset rule, or anomaly reset rule.
Record the condition and return final acceptance to the operator. Promotion
requires all daily records plus explicit review of capacity, evidence quality,
model consistency, service/GPU stability, voice fidelity, and unresolved issues.
