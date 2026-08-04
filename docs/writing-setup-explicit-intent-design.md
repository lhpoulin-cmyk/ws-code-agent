# Explicit writing setup

## Authority

Writing setup is operator intent for the first conversational proposal. It is
separate from downstream audience profiles, which remain derived from an
accepted conversational baseline.

## Immutable model

`writing_setup_versions` remains append-only and is linked to one immutable
`trial_versions` row. Saving source or setup creates a new source/setup pair;
confirmation creates another pair with `completion_state=COMPLETE`. Existing
attempts retain their original setup identity and are never rebound.

New setup records use `writing-setup-explicit-intent-v1`. The five bounded text
fields are empty when undecided. Saving creates `DRAFT`; the separate
authenticated `confirm-setup` action creates `COMPLETE` only when all five
fields are nonblank and explicitly attributed to the operator.

Historical setup rows receive `LEGACY_UNVERIFIED` through additive schema
defaults. Their values and hashes are not rewritten, and they cannot authorize
a new generation attempt.

## Provenance and hashing

Canonical setup serialization includes the five values, completion state, field
provenance, and setup-contract version. It excludes timestamps, runtime paths,
and process metadata. The serialized bytes are SHA-256 hashed and copied to
each generation attempt together with the setup version and five values.

New field provenance is `OPERATOR_ENTERED`; no `SYSTEM_DEFAULT` value exists.
The literal text `Not specified` is permitted only if the operator enters it.

## Generation gate

The server resolves the current source version and its linked setup before
creating an attempt. It rejects missing, `DRAFT`, or `LEGACY_UNVERIFIED`
setup, incomplete fields, provenance mismatches, and open clarifications.
Therefore an incomplete setup creates no attempt, lifecycle event, or model
request.

## Clarification compatibility

The existing bounded clarification lane remains unchanged. Its policy is read
from the exact confirmed setup version and is included in request/provenance.
Questions, answers, and resumed attempts remain immutable and separately
linked; clarification text is never inserted into proposal text.

## Migration

`writing-setup-explicit-intent-v1` adds completion state, field provenance,
confirmation identity/time, setup-contract version, and an index. It does not
backfill complete setups or rewrite historical attempts.
