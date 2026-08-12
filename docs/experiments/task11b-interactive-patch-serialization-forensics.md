# Task 11B interactive patch-serialization forensics

Date: 2026-08-12

Play: `The Measure of a Man`

Checkpoint: `TASK11B-INTERACTIVE-PATCH-SERIALIZATION-FORENSICS`

Task 11B separates coding intent from unified-diff serialization using only
immutable historical evidence and evaluator controls. It adds an
evaluator-only classifier and no production import or behavior. No model was
invoked, no historical session was stepped, and no patch was repaired in the
production lane.

## Foundation

The clean, direct-origin-parity starting checkpoints were:

```text
ws-code-agent: 0a67b0b5236baa2b3f12bf0daae4baf1394a1b9f
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp:         c6138913d39502dbf1507c7318002b4ab748d0b1
```

Before mutation, ws-code-agent passed all 158 tests, the separate two-test
private-material gate, containment, lineage, invariant-register, YAML, and diff
gates. All eight gpu-compute suites and both ws-cp containment tests passed.
Peer repositories remained read-only.

## Evidence binding

`tools/analyze_task11b_patch_forensics.py` read each exact durable response from
the session store, recalculated its raw and normalized identities, parsed the
same normalized bytes where normalization historically applied, and compared
the resulting request and patch arguments with durable harness evidence. The
analysis output was written outside the repository at
`/tmp/task11b-patch-forensics.json`, SHA-256
`b533e0d0887958ed656fce671e4749ad1e6e3a7815ccc199e5d2a3d5313285a6`.

| Experiment | Session / turn | Raw SHA-256 | Normalized SHA-256 | Patch SHA-256 | Request / paths | Historical executor result |
| --- | --- | --- | --- | --- | --- | --- |
| Task 10R 14B | `work-task10r-restart-qwen25-write-20260811T191242Z` / 1 | `05b465998a33116f2d27af3d1598992a6d4b3d5721da5e2b316a24030ac36a76` | `829ccc3ffcec594e3af0e17a275914ed964b96d27c2beb193699a438a8b4070b` | `c74b4378fdb032c7accb7405665702a988b749381908a6d2c16d3fa363efca3d` | `PROPOSE_PATCH` after the preserved Task 10X normalization replay / `src/message.py` | strict raw `MALFORMED_REQUEST`; normalized replay `PATCH_REJECTED` |
| Task 10Y 14B | `work-task10y-qwen25-14b-write-20260811T235900Z` / 1 | `c71599a739e700cab11516bb8f82e7e6ca8a7566966c6e9c44f4d87cdd955a91` | `e1c63e910a36a175ee5c07635f7c092834ca9cf7f15452812f0b18a4c4311b55` | `e6c95167412085836fb880f42b51bf571f600dc2b2d88251c0357df26478cfa2` | `PROPOSE_PATCH` / `src/message.py` | `PATCH_REJECTED` |
| Task 11A 14B | `work-task11a-qwen25-14b-positive-20260812T142051Z` / 2 | `7b367e7154161e9b727d4727226f9dde4fdb73d3aa3917e53cfc773332be688a` | `1a0a9d585a764d2c6be594ccce029f761a6a0107caeb7209d183751522838911` | `4d4ec9023252de2f1997c77c2df1db5f1fed8b89d9e88337db686c54e0902752` | `PROPOSE_PATCH` / `src/message.py` | `PATCH_REJECTED` |
| Task 11A 14B | same session / 3 | `a766d876888b62252091dec4fb0fccf5774aa9e84122b3172b90179352e158a5` | `42ac1348d09a317038524af58809619cba9ec7c84f33909844188e5938c8a3ca` | `08344b89080431907a13260dde38ab5af46c4ac2c62c22bb57f0a1b74a10bd72` | `PROPOSE_PATCH` / `src/message.py` | `PATCH_REJECTED` |
| Task 10V 32B | `work-task10v-qwen25-32b-write-20260811T203928Z` / 1 | `66c8b6cc053a15c782e579db4d18cdc22fa315d80592c968f6332b91bf7c1ba3` | same as raw | `b9ac785eaf771e743c0d343f3b64cf35c3f8b8ff6a988d2e9360ce69b0654624` | `PROPOSE_PATCH` / `src/message.py` | `PATCH_REJECTED` |
| Task 10V 32B | same session / 2 | `7664074a04d9d18008d9eae6452c85c3ea87777feb6a9dfe2ee21fbcb129d7d7` | same as raw | `d0ba6193c65c7abd20101d74b98dc1bec23d41239b7b380a983cbf7500f8f44b` | `PROPOSE_PATCH` / `src/message.py` | `CANDIDATE_READY` |

Task 10R's strict historical harness correctly records no parsed request because
the raw response was fenced. Its later Task 10X evidence binds the same raw
bytes, exact normalized SHA, parser-valid `PROPOSE_PATCH`, and rejected patch.
That distinction is preserved rather than rewriting Task 10R.

## 14B forensics

All four 14B patch payloads target the authorized `src/message.py`. Their exact
added and removed lines express the task-defined result independently of
whether `git apply` accepts the envelope.

| Experiment / turn | Semantic classification | Envelope and hunk findings | Exact structural defect | Historical result | Minimum correction | Class |
| --- | --- | --- | --- | --- | --- | --- |
| Task 10R / 1 | `SEMANTIC_EDIT_CORRECT` | file and diff headers present; `INCORRECT_HUNK_COUNTS` | hunk declares three new lines but contains two | normalized replay `PATCH_REJECTED`, corrupt line 9 | change the declared new count from 3 to 2 | `MECHANICAL` |
| Task 10Y / 1 | `SEMANTIC_EDIT_CORRECT` | file and diff headers present; `INCORRECT_HUNK_COUNTS` | hunk declares three new lines but contains two | `PATCH_REJECTED`, corrupt line 9 | change the declared new count from 3 to 2 | `MECHANICAL` |
| Task 11A / 2 | `SEMANTIC_EDIT_CORRECT` | `NO_SUPPORTED_DIFF_HEADER`, `MISSING_FILE_HEADER`, `INVALID_CONTEXT`, `INCORRECT_HUNK_COUNTS`, `TRUNCATED_PATCH` | the correct hunk fragment omits the file envelope, leaves the unchanged `def` line without the required context prefix, and lacks terminal LF | executor precheck `PATCH_REJECTED` | add exact path-derived headers, prefix the source-matching context line, append LF | `MECHANICAL` |
| Task 11A / 3 | `SEMANTIC_EDIT_CORRECT` | headers present; `INVALID_CONTEXT`, `INCORRECT_HUNK_COUNTS`, `TRUNCATED_PATCH` | the unchanged `def` line again lacks its context prefix and the patch lacks terminal LF | `PATCH_REJECTED`, corrupt line 5 | prefix the source-matching context line and append LF | `MECHANICAL` |

The Task 10R and 10Y new-file payloads both contain exactly:

```python
def message():
    return "hello"
```

The Task 11A payloads both remove only `return "hi"`, add only
`return "hello"`, retain `def message():`, and name only the authorized path.
Ignoring invalid unified-diff punctuation, the requested source change is the
objective-defined change and no other functional edit.

No analyzed 14B patch contains a wrong target, wrong value, invented behavior,
or missing replacement code. The failure cluster is line-count arithmetic,
required envelope production, context-line prefixing, and terminal newline
handling.

## 32B control

Task 10V turn 1 is also `SEMANTIC_EDIT_CORRECT`. Its header paths, hunk range,
and single added line are correct. The patch ends immediately after the added
source line instead of with LF, yielding `TRUNCATED_PATCH`; `git apply` reports
corrupt patch at line 7.

Turn 2 emits the same one-line function and same target path. It adds terminal
LF and omits an optional `index` metadata line. The resulting patch has no
structural finding and reaches `CANDIDATE_READY`. A control retaining the turn
1 metadata but adding only LF passes `git apply --check`, proving the metadata
omission was not necessary. The smallest effective change was terminal newline
serialization; code semantics did not change.

Thus the 32B sequence is:

```text
SEMANTIC_EDIT_CORRECT + TRUNCATED_PATCH
→ PATCH_REJECTED
→ same semantic edit + valid terminal serialization
→ CANDIDATE_READY
```

This same-family control shows recovery of transport syntax without a semantic
repair. It does not prove model scale caused the recovery.

## Canonical-diff controls

The evaluator generated one canonical diff from explicit path, frozen source,
and objective-defined result for each distinct fixture shape. These controls
were never model-visible and were not submitted to a historical session.

| Control | Patch SHA-256 / bytes | Applies | Changed paths | Result source SHA-256 | Visible | Hidden |
| --- | --- | --- | --- | --- | --- | --- |
| Task 10K new file | `2a756b5165ab53e9efdf47b4e36b34c3104d4fef06bc655d2f7a61c7868334c7` / 153 | yes | `src/message.py` only | `34d5d612343d6fe37aed652790ec4536339bd6025c31c5364f7c85197f83febc` | `VALIDATION_PASS` | `VALIDATION_PASS` |
| Task 11A existing file | `8acca1c12f6482ad9d55661f7945eb4561840a3b4e42ecf05b808c42f9f31a8a` / 156 | yes | `src/message.py` only | same | `VALIDATION_PASS` | `VALIDATION_PASS` |

Both validator runs used `task10w-systemd-v1` containment, created no
post-validation repository effect, and produced exactly:

```python
def message():
    return "hello"
```

The control proves both tasks are technically straightforward once semantic
before/after state is represented without malformed transport punctuation.

## Protocol and executor contract

The unchanged model-visible V2 render says that `patch` is a unified-diff
string accepted by strict `git apply`, and lists a `diff --git` header, `---`
old-path header, `+++` new-path header, one or more `@@` hunk headers, and hunk
lines. It does explicitly require unified diff. It does not define the hunk
count arithmetic, hunk-line prefix grammar, terminal-newline rule, or the
executor's exact `a/` and `b/` path constraints. Because V2 is value-free, it
provides no populated valid diff example.

The unchanged parser verifies JSON shape, `patch` string type/size, and the
non-empty proposed-path array. It intentionally does not parse unified-diff
grammar. The unchanged executor then requires exact supported `diff --git`
paths, `+++ b/...` targets matching `proposed_paths`, safe authorized paths, and
finally successful non-interactive `git apply --index --whitespace=nowarn`.

The protocol therefore communicates the category and coarse structure but
delegates a more exact free-text transport grammar to the model. The executor
accepts the strict subset actually accepted by its path precheck and Git. Tasks
10R, 10Y, 11A, and 10V demonstrate failures on details not enumerated by the
model-visible structural list.

## Determinism and authority

Each evidence-specific minimum correction was executed twice evaluator-side
and produced identical bytes. Every corrected control passed `git apply
--check` against the exact frozen source.

| Correction class | Unique result under the specified minimum operation | Model-selected added/removed bytes changed | Authority changed |
| --- | --- | --- | --- |
| recalculate declared count from observed exact hunk lines | yes | no | no |
| add required file headers from the sole declared authorized path | yes | no | no |
| prefix an exact frozen-source line as unchanged context | yes | no | no |
| append required terminal LF | yes | no | no |

The forensic controls perform no fuzzy matching, choice among candidates, LLM
call, or inference of omitted implementation. For Task 11A, the unprefixed
line equals the exact frozen source line at the declared hunk position. If it
did not match uniquely, the proposed context transformation would be
`NOT_DETERMINISTIC` and could not qualify as mechanical.

Authority remains prior to syntax. The classifier reports target paths without
rewriting them, and a synthetic otherwise-valid patch for `src/other.py`
remains `WRONG_TARGET_PATH` when `src/message.py` is authorized. None of the
hypothetical mechanical controls can add a path, change request type, alter
semantic values, or manufacture code.

## Interface finding

The evidence answers the interface question affirmatively for this bounded
set: the model is selecting the correct source edit and is additionally being
required to hand-serialize the executor's fragile unified-diff transport.
Evaluator controls construct an exact valid diff deterministically from frozen
source, explicit authorized path, and selected before/after content. Across all
four rejected 14B patches, no semantic correction was required; only transport
grammar changed. The 32B rejected/accepted pair independently changes
serialization while retaining semantics.

This does not authorize an adapter or prove all future 14B coding semantics
correct. It establishes the primary cause of these preserved bounded write
failures.

## Frozen surfaces and historical integrity

Starting-HEAD blob identities and current SHA-256 identities remained unchanged
for the protocol, normalizer, parser, executor, validation registry, and Task
10Z policy. The forensic module is not imported by any of those production
surfaces.

```text
V2 render SHA-256: 3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e
SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1: UNCHANGED
INTERACTIVE_BOUNDED_WORK_V1: UNCHANGED
parser: UNCHANGED
executor: UNCHANGED
validation: UNCHANGED
authority: UNCHANGED

Task 11A escalation: UNCHANGED
14B historical evidence: UNCHANGED
32B historical evidence: UNCHANGED

MODEL_INFERENCE_COUNT = 0
```

No production patch repair, structured replacement, canonical-diff production
path, protocol V3, new executor operation, repair allowance, semantic adapter,
automatic overnight invocation, or historical rescore was introduced.

## Disposition

```text
PATCH_SERIALIZATION_INTERFACE_MISMATCH_CONFIRMED
NEXT: DESIGN A DETERMINISTIC STRUCTURED EDIT TRANSPORT FOR THE INTERACTIVE/PRACTICAL CODER WITHOUT CHANGING SEMANTIC AUTHORITY
```
