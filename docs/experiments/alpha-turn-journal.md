# Alpha turn journal

Real Alpha families use the repository-owned `AlphaExperimentController`.
`start` creates an immutable family manifest and per-case state; `status` is
read-only; each `step` performs at most one inference.

Each turn moves through `TURN_STARTED`, `RAW_RESPONSE_DURABLE`,
`HARNESS_RESULT_DURABLE`, and `TURN_COMMITTED`. Raw text, its hash, job ID,
and runtime evidence are atomically written and fsynced by the backend evidence
sink before the Katra disposable output can be removed. A committed turn also
has a small previous-turn digest chain.

On restart, a raw durable response may be processed without a new inference;
a durable harness result may be committed without a new inference. An
interruption during executor processing is explicitly `INVALIDATED`, never
guessed or retried. Case metadata persists C04 transition state and C05
authority mappings rather than recalculating them from a live filesystem.
