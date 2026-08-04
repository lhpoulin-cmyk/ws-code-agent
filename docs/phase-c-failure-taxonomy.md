# Phase C generation failure taxonomy

Doc Writer classifies generation through `generation_attempt_events`. The
mutable attempt status is retained for compatibility, while
`canonical_failure_class` and the append-only event stream provide the
current interpretation.

The classifier version is `generation-failure-taxonomy-v1`. Existing `FAILED`
records are not rewritten. Their status/error pair is interpreted by the
compatibility map in `src/docwriter_web/failure_taxonomy.py`.

Raw response evidence is retained whenever it reached the application. If a
database transaction fails before durable persistence, the application-owned
recovery spool under the runtime root’s `recovery/` directory is the bounded
reconciliation channel. It is mode `0700` for the directory and `0600` for
files, contains hashes and the stable attempt identity, and explicitly has no
replay operation. Reconciliation is an operator-visible persistence recovery,
never an automatic second model request.

Presentation failure is separate from generation failure. A durable completed
attempt remains `COMPLETED` while `presentation_result=failed`; its fallback
attempt view exposes only structural provenance and safe hashes.

Startup recovery checks the bounded lease and compares both worker PID and
process-start identity. An old queued/running attempt with no matching worker
is classified `INTERRUPTED`; it is never rerun automatically.
