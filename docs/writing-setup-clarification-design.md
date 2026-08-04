# Versioned writing setup and clarification workflow

Status: design decision recorded for implementation

This document settles the bounded design for first-proposal writing setup and
clarification. It does not change historical attempts or live runtime data.

## Decisions

1. Writing setup is stored in an append-only `writing_setup_versions` table.
   Each row has a stable setup ID, canonical serialized JSON, SHA-256, the
   trial ID, and the exact source-version ID it describes. Existing trial rows
   remain a compatibility projection; they are not the authority for setup.
2. A source version and setup version are linked one-to-one for new drafts.
   `trial_versions.writing_setup_version_id` records that link. Historical
   source versions may remain NULL because they predate this feature.
3. Setup fields are bounded text:
   - primary audience: 400 characters;
   - tone: 400 characters;
   - purpose: 2,000 characters;
   - preservation instructions: 4,000 characters;
   - clarification policy: 1,000 characters.
   Blank values are represented by deterministic application defaults for
   compatibility with older callers; the UI presents the fields before the
   first generation.
4. Canonical setup serialization is UTF-8 JSON with sorted keys, compact
   separators, and no runtime paths or timestamps. The setup hash is SHA-256
   over those exact serialized bytes.
5. Every new setup-aware attempt stores the setup ID, setup hash, exact
   serialized setup, each setup field, and optional clarification question and
   answer IDs. The exact request JSON remains the request-byte provenance.
6. Changing source or setup creates a new source-version/setup-version pair.
   Existing attempts remain unchanged. Legacy attempts without setup IDs remain
   valid under their original prompt/schema contract.
7. The response contract is `conversational-proposal-v3`. Its result is a
   mutually exclusive tagged object: `PROPOSAL` contains one proposal, while
   `CLARIFICATION_REQUIRED` contains one focused question. Neither result may
   contain the other field.
8. A clarification question is an immutable row linked to the completed
   attempt, source version, and setup version. An operator answer is a separate
   immutable row linked to that question. One open question is allowed per
   trial; an answer is required before resumption.
9. Integrity analysis and proposal/clarification remain one bounded model
   exchange in this phase. The structured result makes the outcome explicit;
   no hidden second model request is issued.
10. Resumption is an explicit authenticated POST. It creates a new immutable
    generation attempt linked to the question and answer. The original
    clarification attempt is never reused or mutated into a proposal.
11. Private steering is not accepted by setup or clarification forms and is
    never copied into setup, question, answer, or generation request fields.
12. Existing downstream audience adaptations remain baseline-derived and
    independent. Primary audience is conversational setup, not an audience
    adaptation profile.

## Authority chain

```text
trial
  -> source version + writing setup version
  -> completed clarification-result attempt (optional)
  -> immutable clarification answer (optional)
  -> resumed generation attempt
  -> integrity/review evidence
```

## Compatibility

Historical attempts have NULL setup fields and retain their original prompt,
schema, request, and lifecycle evidence. They are displayed as legacy attempts
without inferred setup. No historical setup is backfilled.

## Tradeoff

Keeping integrity analysis and proposal/clarification in one exchange avoids a
new model stage and preserves the current generation boundary. The tagged v3
result is more explicit than treating a question as task-adherence failure,
while the immutable question/answer records provide a clean future split if a
separate integrity stage becomes necessary.
