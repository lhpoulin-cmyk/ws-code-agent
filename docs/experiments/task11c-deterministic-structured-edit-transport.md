# Task 11C deterministic structured-edit transport

Date: 2026-08-12

Play: `Relics`

Checkpoint: `TASK11C-DESIGN-DETERMINISTIC-STRUCTURED-EDIT-TRANSPORT`

Task 11C implements a candidate transport for existing-file text replacement.
It does not run a model, change the live interactive lane, or rescore history.
The design follows Task 11B's preserved finding:
`PATCH_SERIALIZATION_INTERFACE_MISMATCH_CONFIRMED`.

## Foundation

The clean, direct-origin-parity starting checkpoints were:

```text
ws-code-agent: dcd46a101a2e98f000bade3541d35c078fd059a2
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp:         c6138913d39502dbf1507c7318002b4ab748d0b1
```

Before mutation, ws-code-agent passed all 163 tests, the separate two-test
private-material gate, containment, lineage, invariant-register, YAML, and
diff gates. All eight gpu-compute suites and both ws-cp containment-contract
tests passed. Peer repositories remained read-only.

## Transport

```text
protocol: WS_CODE_AGENT_REQUEST_PROTOCOL_V3_SINGLE_STRUCTURED_EDIT
request: PROPOSE_TEXT_REPLACEMENT
arguments: path, old_text, new_text
file class: existing regular UTF-8 text without NUL
match rule: old_text occurrence count == 1
transport state: CANDIDATE
live/default protocol: UNCHANGED
```

V3 retains `READ`, `SEARCH`, `REQUEST_CLARIFICATION`, and `NO_CHANGE`. It does
not offer `PROPOSE_PATCH`, new-file creation, occurrence indexes, replace-all,
or a populated model-visible example. Its general instruction says that
`old_text` must exactly match one contiguous current region, `new_text` is the
exact desired replacement, and the model must not generate unified diff
syntax.

The value-free V3 candidate render is 1,493 bytes with SHA-256
`d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993`.

The strict V2 render remains SHA-256
`3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e`.

## Semantic authority and evidence

The model owns, and the evaluator does not alter:

```text
path
old_text
new_text
```

The parser accepts V3 only when the caller explicitly selects V3; historical
V1/V2 parsing rejects `PROPOSE_TEXT_REPLACEMENT`. The existing whole-response
Markdown-fence normalizer can precede parsing without changing any argument
bytes.

`StructuredTextReplacement` binds the exact parsed values to Source Snapshot X
and records:

```text
raw request SHA-256
structured request SHA-256
path SHA-256
old_text SHA-256
new_text SHA-256
```

Successful executor evidence adds before/after file SHA-256 values, canonical
diff SHA-256, candidate identity, candidate snapshot, exact match count, and
independently observed changed paths. The diff is marked `origin: evaluator`;
it is never represented as model output.

## Executor and failure semantics

The executor first rechecks Source Snapshot X and request/repository binding.
It then checks exact path authority, rejects absolute/traversing/`.git` paths
and symlinks, requires an existing supported file, counts literal string
occurrences, and performs one exact replacement in the existing isolated-copy
mechanism. It independently inventories effects before accepting the result.

```text
STRUCTURED_EDIT_ACCEPTED
TEXT_MATCH_ZERO
TEXT_MATCH_MULTIPLE
TEXT_REPLACEMENT_NO_EFFECT
TEXT_ENCODING_UNSUPPORTED
DENIED_AUTHORITY
STATE_STALE
REPOSITORY_MISMATCH
EXECUTOR_ERROR
```

An empty `old_text` is malformed at the parser/proposal boundary. Empty
`new_text` is an ordinary exact region deletion and never deletes the file.
Invalid resulting Python is still a transport success; visible/hidden
validation then truthfully fails. This keeps code quality out of the transport
layer.

The implementation uses no regex, fuzzy matching, whitespace approximation,
AST guess, model-provided line number, occurrence selection, semantic repair,
or source-repository mutation. A changed path outside the sole selected and
authorized path fails closed.

## Determinism

Focused tests run the same source snapshot and structured request through two
independent isolated workspaces. They produce identical after-file bytes,
canonical-diff bytes and SHA-256, and logical candidate identity. The logical
identity is bound to Source Snapshot X, structured-request identity,
before/after identities, canonical-diff identity, and changed paths; temporary
workspace names are excluded.

The test matrix also covers zero and multiple matches, no effect, empty old
text, exact deletion, traversal, absolute and `.git` paths, symlink escape,
unsupported byte encoding and NUL, stale source, foreign repository binding,
newline evidence, and invalid-code validation failure.

## Retrospective controls

`tools/analyze_task11c_structured_edit.py` rereads exact preserved response
bytes, revalidates every Task 11B raw/normalized/patch identity, and extracts
only the model-selected path and added/removed semantic lines. Its output at
`/tmp/task11c-structured-controls.json` had SHA-256
`079960a57a36dc4f164635a4189eecd80151fb8fe515b991e44981d7711edf8a`.

| Historical edit | Semantic extraction | Structured request | Match | Candidate / paths | Visible | Hidden |
| --- | --- | --- | --- | --- | --- | --- |
| Task 10R turn 1 | exact new-file added lines | none | 0 | `STRUCTURED_REPLAY_MATCH_FAILED`; none | not evaluated | not evaluated |
| Task 10Y turn 1 | exact new-file added lines | none | 0 | `STRUCTURED_REPLAY_MATCH_FAILED`; none | not evaluated | not evaluated |
| Task 11A turn 2 | exact path and removed/added line; retain frozen source line boundary | `b73e061048ab1b3d8567bf75ee34e32fc021f4e6541871f4299319debc6d2992` | 1 | `STRUCTURED_EDIT_ACCEPTED`; `src/message.py` only | PASS | PASS |
| Task 11A turn 3 | same exact semantic selection | same | 1 | `STRUCTURED_EDIT_ACCEPTED`; `src/message.py` only | PASS | PASS |

The Task 10R/10Y failures are expected scope evidence: those fixtures create a
new file, while V3 deliberately supports existing-file replacement only. They
are not coerced into V3 and no `old_text` is invented.

Both Task 11A controls use:

```text
old_text SHA-256: 55df00a7273431e2698ea2fce6fe058ada59e3e1d1493e8dbf21f7c1a83d5b68
new_text SHA-256: b7c1d2d95b864ac04bf7d74976829869bbcbd2b95c4de54a206bbf1088723bba
before-file SHA-256: 98f2f772b26b287735956a41fe7972e3d33cdfa364e15025951068e23afd49d7
after-file SHA-256: 34d5d612343d6fe37aed652790ec4536339bd6025c31c5364f7c85197f83febc
canonical-diff SHA-256: 52f56438548ceb2ae079583b4fb357d130d8adac1514510965ec1740c0a4389c
changed paths: src/message.py only
technical correctness: VALIDATED
containment: task10w-systemd-v1
source snapshot: MATCH
validator effect: UNCHANGED
```

The model supplied the path, the selected old source line, and the desired new
source line. The evaluator supplied exact occurrence counting, isolated byte
replacement, source-derived line boundaries, the Git review envelope, hunk
location/counts, effect observation, candidate evidence, and validation. It
did not select a different value or create omitted code.

This makes the central comparison explicit:

```text
original Task 11A PROPOSE_PATCH:
  semantic information = sufficient and correct
  transport information = malformed

equivalent V3 control:
  semantic information = unchanged
  transport information = constructed deterministically by evaluator
  technical result = VALIDATED
```

## Historical and live boundaries

```text
Task 11A disposition: INTERACTIVE_PRACTICAL_CODER_RESTRICTED_ACCEPTANCE_ESCALATED / UNCHANGED
Task 11B disposition: PATCH_SERIALIZATION_INTERFACE_MISMATCH_CONFIRMED / UNCHANGED
V2 historical results: UNCHANGED
INTERACTIVE_BOUNDED_WORK_V1: UNCHANGED
SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1: UNCHANGED
live supervised protocol: UNCHANGED
automatic promotion: NONE
MODEL_INFERENCE_COUNT = 0
```

No production patch repair, live protocol promotion, work-boundary expansion,
automatic overnight-coder invocation, or historical rescore occurred.
The executor contains no model identity or scale-specific branch; the same
candidate transport is available for a later separately authorized control.

## Validation

After implementation, all 176 ws-code-agent tests passed, including the new
protocol, exact-replacement, determinism, authority, encoding, diff, and
validation controls. The separate two-test private-material gate, real
containment tests, lineage, invariant register, YAML parse over 13 files, and
diff check passed. All eight gpu-compute suites and both ws-cp containment
contract tests passed. No peer repository changed.

## Disposition

```text
STRUCTURED_EDIT_TRANSPORT_CANDIDATE_READY
NEXT: RUN FRESH INTERACTIVE/PRACTICAL CODER ACCEPTANCE THROUGH V3 STRUCTURED EDIT TRANSPORT
```
