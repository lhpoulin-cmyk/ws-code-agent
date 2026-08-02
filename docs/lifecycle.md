# Document lifecycle

```text
source material
  → normalized source record
  → draft request
  → model-generated candidate
  → factual validation
  → voice review
  → authority-boundary review
  → operator acceptance
  → export
```

The lifecycle is documented, not a workflow engine. A successful generation is
never authoritative by itself.

| State | Meaning |
|---|---|
| `PROPOSED` | Request or document has been scoped but not generated. |
| `GENERATED` | Candidate text exists and awaits validation. |
| `VALIDATION_FAILED` | Factual, schema, provenance, or safety validation failed. |
| `REVIEW_REQUIRED` | Validation passed; human voice/authority review remains. |
| `ACCEPTED` | Operator accepted the reviewed document. |
| `REJECTED` | Candidate is explicitly not accepted. |
| `SUPERSEDED` | A later accepted artifact replaces it without erasing history. |

`ACCEPTED` requires both validation evidence and explicit operator acceptance.


## Benchmark lifecycle

The frozen benchmark lifecycle is: commit application fixtures and contracts;
validate hashes and runtime gates; execute the 3-by-10 matrix sequentially;
retain unmodified raw responses; produce anonymous review outputs; complete
operator scoring; and record an explicit disposition. A generated response is
never `ACCEPTED` without factual, voice, authority-boundary, and operator
review.
