# Alpha turn journal

Real Alpha families use the repository-owned `AlphaExperimentController`.
`start` creates an immutable family manifest and per-case state; `status` is
read-only; each `step` performs at most one inference.

Each turn moves through `TURN_STARTED`, `INFERENCE_INTENT_DURABLE`,
`RAW_RESPONSE_DURABLE`, `HARNESS_RESULT_DURABLE`, and `TURN_COMMITTED`. Raw text, its hash, job ID,
and runtime evidence are atomically written and fsynced by the backend evidence
sink before the Katra disposable output can be removed. A committed turn also
has a small previous-turn digest chain.

On restart, a raw durable response may be processed without a new inference;
a durable harness result may be committed without a new inference. An
interruption during executor processing is explicitly `INVALIDATED`, never
guessed or retried. Case metadata persists C04 transition state and C05
authority mappings rather than recalculating them from a live filesystem.

Task 10E uses the fixed registry in `alpha_case_adapters.py`. Each family owns
fresh C03/C04/C05 workspaces. Serialized snapshots are verified against live
workspaces before inference; committed successful patches are replayed by the
executor to reconstruct isolated effects. C04's transition has a separate
atomic marker, and C05's alias/capability map is persisted rather than inferred
from variant names during resume.

The bounded operator entrypoint is `tools/run_alpha_experiment.py` with
`start-task10e`, `status`, and one-turn `step` commands. Unknown cases are not
loadable and case progression is enforced by committed case status.

Before any remote call, the controller also commits
`INFERENCE_INTENT_DURABLE` with a deterministic turn-bound invocation ID and
the exact rendered-prompt digest. gpu-compute uses that ID as an idempotent
execution key. Re-presenting it returns the existing running, failed, or
successful invocation; it never creates a second model execution. A retained
successful remote response can therefore be captured after client restart.
