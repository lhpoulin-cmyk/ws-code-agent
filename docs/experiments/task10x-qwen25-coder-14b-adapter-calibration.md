# Task 10X Qwen2.5-Coder 14B adapter calibration

Play: **The Ensigns of Command**  
Checkpoint: **TASK10X-CALIBRATE-14B-MINIMUM-PRODUCTION-ADAPTER**  
Date: 2026-08-11

## Foundation

Task 10X began from clean direct-origin parity at:

```text
ws-code-agent  5b76e89254c51721010ab5c9db732e0808414614
gpu-compute    282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp         e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp          c6138913d39502dbf1507c7318002b4ab748d0b1
```

The baseline passed 138 ws-code-agent tests, two private-material tests,
containment, lineage, invariant-register, YAML, and diff gates; all eight
gpu-compute suites and both ws-cp containment tests passed. The preserved work
roles remain `INTERACTIVE_PRACTICAL_CODER` for 14B and
`DELIBERATIVE_OVERNIGHT_CODER` for 32B. They are operational labels, not scores.

## Adapter

```text
ID: SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1
version: v1
state: NORMALIZATION_CANDIDATE
live/default state: STRICT_RAW
```

The adapter accepts only a response consisting entirely of optional surrounding
ASCII whitespace, one exact opening fence (` ``` ` or lowercase ` ```json `),
one payload, one exact closing fence, and optional surrounding whitespace. It
refuses a payload containing another fence marker. Wrapper removal leaves every
payload byte unchanged.

It never searches prose, selects among objects, removes explanations, repairs
JSON or patches, adds syntax, renames keys or request types, changes values,
infers paths, converts `NO_CHANGE`, converts prose, retries generation, or sends
correction prompts. Anything outside the exact grammar is identity-preserved as
`NORMALIZATION_REFUSED`. Bare input is identity-preserved as
`IDENTITY_NO_PERMITTED_WRAPPER`.

Each result preserves both `raw_model_response` and
`normalized_parser_input`, with independent SHA-256 hashes and byte counts,
adapter ID/version, application boolean, and transformation classification.
Raw response bytes remain canonical model evidence. The candidate adapter is
not imported by or enabled in the live supervised execution path.

## Candidate-independent safety corpus

Six focused test groups establish:

- exact unlabeled and lowercase-`json` whole-response fences unwrap;
- bare JSON remains byte-identical;
- prose before/after, two blocks, `python`, `JSON`, and near-miss fences refuse;
- malformed JSON, missing/wrong schema, and unsupported request types remain
  strict parser failures after wrapper removal;
- `NO_CHANGE`, clarification questions, patch text, and proposed paths remain
  byte-for-byte and semantically identical;
- a correctly fenced request for `forbidden.py` remains `DENIED_SCOPE` under
  unchanged authority.

Normalization success is not parser, executor, validation, or admission
success.

## Historical 14B write replay

The replay read the exact durable response from
`work-task10r-restart-qwen25-write-20260811T191242Z`, not copied text.

```text
raw SHA-256:
05b465998a33116f2d27af3d1598992a6d4b3d5721da5e2b316a24030ac36a76
raw bytes: 315

transformation applied: true
classification: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
normalized SHA-256:
829ccc3ffcec594e3af0e17a275914ed964b96d27c2beb193699a438a8b4070b
normalized bytes: 303

parser: VALID
request type: PROPOSE_PATCH
```

The exact frozen write fixture identity was
`db9efb27f7f56da8a0f295e3ef0e656271264ac08ec977da578f2e6e020bb2b6`,
with read authority `.` and patch authority only for `src/message.py`. The
unchanged isolated executor returned:

```text
PATCH_REJECTED
git apply exit: 128
stderr: error: corrupt patch at line 9
changed paths: none
source snapshot: preserved
candidate: not created
visible validation: NOT_EVALUATED
hidden validation: NOT_EVALUATED
technical correctness: NOT_EVALUATED
```

The adapter fixes the presentation-layer parser rejection and exposes the next
truthful result. It does not repair or conceal the independently malformed
patch. Therefore no retrospective candidate or technical-validity claim exists.

```text
14B historical write STRICT_RAW = FAIL
14B historical write NORMALIZED_REPLAY = PARSER_VALID_PATCH_REJECTED
```

## Historical 14B clarification replay

The replay read the exact durable response from
`work-task10r-restart-qwen25-clarification-20260811T191417Z`.

```text
raw SHA-256:
c71974d0782e966e6ad9481150346d15d6058c8e7b9cc1bc7ef6bf0eb2488ead
raw bytes: 64

transformation applied: true
classification: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
normalized SHA-256:
24e413c7a46e952f86471004bc7dcd916dc0e4c4b82d0dd8df70337bb7b19e55
normalized bytes: 52

parser: VALID
semantic request: NO_CHANGE
semantic judgment: FAIL
```

`PRESENTATION_NORMALIZATION_DOES_NOT_FIX_CLARIFICATION_JUDGMENT`

No conversion to `REQUEST_CLARIFICATION` occurred.

## Preserved 32B pass-through

The preserved bare JSON responses remained exact identities:

| Response | Raw/normalized SHA-256 | Bytes | Parser |
| --- | --- | --- | --- |
| Write turn 2 | `7664074a04d9d18008d9eae6452c85c3ea87777feb6a9dfe2ee21fbcb129d7d7` | 247 / 247 | `PROPOSE_PATCH` |
| Clarification | `55ccaa45aa97da74467abab4345271e786b09327aad71103782f029ce5e95813` | 168 / 168 | `REQUEST_CLARIFICATION` |

For both, `transformation_applied = false` and normalized SHA equals raw SHA.

## Frozen and historical surfaces

The V2 render remains
`3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e`.
No prompt, renderer, fixture, sampling, context, template, parser, authority,
executor, isolation, validation, or review behavior changed.

```text
14B strict historical score: UNCHANGED / FAIL
32B Task 10V historical result: UNCHANGED / INCONCLUSIVE_INFRASTRUCTURE
32B preserved candidate validation: UNCHANGED / PASS
MODEL_INFERENCE_COUNT = 0
```

## Disposition

The transformation is deterministic, payload-preserving, semantic-identity
preserving, authority-neutral, and raw-evidence preserving. It removes only the
demonstrated representation wrapper and leaves parser, patch, authority, and
judgment failures visible.

```text
FENCE_NORMALIZATION_JUSTIFIED

NEXT: DEFINE INTERACTIVE/PRACTICAL 14B PRODUCTION LANE WITH BOUNDED REPRESENTATION NORMALIZATION AND UNCHANGED SEMANTIC SAFEGUARDS
```

This is calibration evidence, not production enablement, historical rescoring,
candidate promotion, or authority broadening.
