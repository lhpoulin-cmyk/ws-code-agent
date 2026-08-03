# Local web review surface

Status: **deployed / authenticated generation enabled**

The application surface is a dependency-free WSGI service at loopback
`127.0.0.1:8787`. It uses SQLite under the runtime storage boundary and runs
one server-owned, authenticated conversational-proposal generation action
through the loopback Ollama API. The reverse proxy and TLS listener are owned by
`ws-cp`; DNS and network policy remain peer-owned.

The initial workflow stores a source paragraph, model identifier and digest,
generation metadata, integrity findings, operator-supplied raw and normalized
proposals, reviewer notes, decisions, and immutable version snapshots. New and
edited material remains `REVIEW_REQUIRED` until an operator decision is
recorded. Decisions are `ACCEPTED`, `REVISION_REQUIRED`, or `REJECTED`.

Runtime secrets are protected files outside Git:

- operator password: `DOCWRITER_OPERATOR_PASSWORD_FILE`
- session secret: `DOCWRITER_SESSION_SECRET_FILE`

The generation action uses the observation-period Mistral Nemo candidate only
after reconciling its installed digest with the pinned manifest. Controlled
settings are context 8192, temperature 0.2, top-p 0.9, seed 42, streaming
disabled, and thinking disabled. Every attempt preserves source version,
prompt, request, response, parsed findings, normalized proposal, exact diff,
hashes, timing, telemetry, and review lineage. Results remain
`REVIEW_REQUIRED`; failed attempts remain immutable and retries create new
attempts. The application does not promote output, publish prose, adapt for an
audience, or modify frozen benchmark evidence.
