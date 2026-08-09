# Writing setup and clarification workflow — acceptance evidence

Status: prepared and validated in disposable test databases

This evidence is sanitized. It contains no live operator prose, private
steering, credentials, raw model output, or runtime database contents.

## Scope

The implementation adds versioned writing setup for the first conversational
proposal and a bounded clarification lane. No live runtime database was opened,
changed, or migrated. No model was invoked.

## Implementation evidence

- Design decisions: `docs/writing-setup-clarification-design.md`
- Setup serialization and validation: `src/docwriter_web/writing_setup.py`
- Versioned response schema: `schemas/conversational-proposal-v3.schema.json`
- Request/parser implementation: `src/docwriter_web/generation.py`
- Additive schema and immutability migration: `src/docwriter_web/migrations.py`
- Trial/setup/clarification routes and provenance: `src/docwriter_web/app.py`
- Synthetic workflow tests: `tests/test_writing_setup.py`

## Durable evidence demonstrated by tests

1. New trials receive an immutable `writing_setup_versions` identity linked to
   the source version.
2. Setup serialization is deterministic JSON with sorted keys and compact
   separators; its SHA-256 is persisted.
3. The exact serialized setup appears in the first-generation request payload.
4. Attempts persist setup version, hash, serialized setup, all five setup
   fields, and optional clarification question/answer identities.
5. A v3 response is either `PROPOSAL` or `CLARIFICATION_REQUIRED`; the parser
   never returns a proposal with a clarification question.
6. An unresolved clarification blocks ordinary proposal generation.
7. A question is answered in an immutable answer row before explicit resume.
8. Resumption creates a new attempt linked to the question and answer.
9. Changing setup creates a new source/setup version while the prior attempt
   retains its original setup hash.
10. Primary conversational audience remains separate from downstream audience
    adaptations; no adaptation row is created by setup capture.
11. Existing legacy attempt rows retain NULL setup identity and remain readable
    under their original provenance.

## Validation

```text
python -m pytest -q
82 passed in 1.14s
```

The suite includes all prior Phase A–G tests plus four writing-setup tests.

## Runtime boundary

No runtime database interaction occurred. The previous read-only attempt to
open `/srv/ws-doc-writer/app/state/docwriter.sqlite3` was denied by the
execution environment; no privilege escalation was requested. Live migration
and deployment are outside this bounded repository implementation.
