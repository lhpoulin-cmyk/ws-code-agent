# Local web review surface

Status: **prepared / deployment pending host verification**

The application surface is a dependency-free WSGI service at loopback
`127.0.0.1:8787`. It uses SQLite under the runtime storage boundary and has no
model execution endpoint. The reverse proxy and TLS listener are owned by
`ws-cp`; DNS and network policy remain peer-owned.

The initial workflow stores a source paragraph, model identifier and digest,
generation metadata, integrity findings, operator-supplied raw and normalized
proposals, reviewer notes, decisions, and immutable version snapshots. New and
edited material remains `REVIEW_REQUIRED` until an operator decision is
recorded. Decisions are `ACCEPTED`, `REVISION_REQUIRED`, or `REJECTED`.

Runtime secrets are protected files outside Git:

- operator password: `DOCWRITER_OPERATOR_PASSWORD_FILE`
- session secret: `DOCWRITER_SESSION_SECRET_FILE`

The current application intentionally does not import benchmark runtime data,
execute a model, promote a model, publish generated prose, or modify frozen
benchmark evidence.
