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

The fixed registry in `alpha_case_adapters.py` contains C01 through C05-B.
Task 10E retains its four-case C03/C04/C05-A/C05-B order; the Task 10G R3
initializer uses C01/C02/C03/C04/C05-A/C05-B. The Task 10I C05 R4 initializer
is a distinct evaluation family containing exactly C05-A followed by C05-B.
It exists for a fresh evaluation of both inverted C05 variants against the
Task 10H explicit effect, replay, authority, and termination feedback; earlier
evaluation generations remain immutable. Each family owns fresh case
workspaces. Serialized snapshots are verified against live workspaces before
inference; committed successful patches are replayed by the executor to
reconstruct isolated effects. C01 persists its accepted effect and advances
visible and hidden validation through explicit zero-inference evaluator phases.
Its exact proposal is deterministically replayed and verified by repository
material identity; each atomic validation-evidence record is linked from case
state by digest and result-snapshot identity.
An ambiguous validation execution invalidates the case instead of rerunning it.
C02 persists the exact clarification and only a safe evaluator reference and
digest; private evaluator content is not family evidence. C04's transition has
a separate atomic marker, and C05's alias/capability map is persisted rather
than inferred from variant names during resume.

Each case also persists its registered request-protocol ID. C01 through C04
bind the single-repository contract; C05-A/C05-B bind the repository-qualified contract.
The protocol ID is included in durable inference intent so a restart cannot
silently render a different request surface.

E10 also binds that intent to the backend-owned exact model tag, manifest
digest, quantization, runtime-profile ID, and execution policy. Recovery
re-derives the identity from the selected backend and fails closed with
`DURABLE_MODEL_BINDING_MISMATCH` before remote execution if any field differs.
The controller contains no model-specific intent label.

The bounded operator entrypoint is `tools/run_alpha_experiment.py` with
`start-task10e`, `start-task10g-r3`, `start-task10i-c05-r4`, `status`, and
one-turn `step` commands.
Unknown cases are not loadable and each registered family order is enforced by
committed case status. A scoreable terminal result permits progression; an
evaluating or infrastructure-invalidated case does not.

Before any remote call, the controller also commits
`INFERENCE_INTENT_DURABLE` with a deterministic turn-bound invocation ID and
the exact rendered-prompt digest. gpu-compute uses that ID as an idempotent
execution key. Re-presenting it returns the existing running, failed, or
successful invocation; it never creates a second model execution. A retained
successful remote response can therefore be captured after client restart.
