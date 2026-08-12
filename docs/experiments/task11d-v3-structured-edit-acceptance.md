# Task 11D V3 structured-edit acceptance

Date: 2026-08-12

Play: `The First Duty`

Checkpoint: `TASK11D-FRESH-INTERACTIVE-CODER-V3-STRUCTURED-EDIT-ACCEPTANCE`

## Published apparatus boundary

Task 11D adds a separate, candidate-only supervised lane for the fresh 14B
acceptance run:

```text
lane: QWEN25_14B_INTERACTIVE_STRUCTURED_V3_V1
worker: INTERACTIVE_PRACTICAL_CODER
policy: INTERACTIVE_BOUNDED_WORK_V1
protocol: WS_CODE_AGENT_REQUEST_PROTOCOL_V3_SINGLE_STRUCTURED_EDIT
write request: PROPOSE_TEXT_REPLACEMENT
normalizer: SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1
runtime profile: qwen25-coder-14b-katra-4096
live/default: false
```

The lane has a distinct `start-task11d-v3-interactive` selector and a fresh
`task11d-interactive-structured-existing-file/synthetic-v1` fixture. Durable
manifest, case, and transport identities must agree after restart. The exact
V3 render SHA-256 is
`d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993`.
Historical V2 remains independently selected and retains render SHA-256
`3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e`.

For a structured request, the model owns `path`, `old_text`, and `new_text`.
The evaluator preserves those values, checks existing authority and Source
Snapshot X, counts exact occurrences, applies one exact replacement in an
isolated candidate, observes effects, and generates the canonical review diff
with explicit evaluator provenance. The model never supplies diff syntax.

`TEXT_MATCH_ZERO` and `TEXT_MATCH_MULTIPLE` permit one ordinary forward
correction under the existing bounded policy. A second match failure produces
`ESCALATION_REQUIRED` with reason `STRUCTURED_EDIT_REPAIR_EXHAUSTED`.
Authority denial escalates without a correction hint. Executor/runtime state
failures remain infrastructure outcomes. Candidate validation failure is a
semantic failure and is never repaired by transport.

The fresh fixture retains the requirements-complete Task 11A semantic
contract while changing the variable under test to V3 transport. It binds the
existing independent visible and hidden validators before inference. A
candidate can advance only through both contained validators to
`AWAITING_OPERATOR_REVIEW`; no source promotion exists.

The apparatus test matrix covers exact lane/restart binding, fail-closed
protocol drift, V2/V3 separation, whole-response normalization with exact
semantic preservation, structured candidate evidence, evaluator diff origin,
source preservation, both validation phases, one bounded match correction,
repair exhaustion, authority denial, and rejection of `PROPOSE_PATCH` under
V3.

At apparatus publication time:

```text
model inferences: 0
admission sessions: 0
behavioral disposition: NOT_EVALUATED
Task 11A: UNCHANGED
Task 11B: UNCHANGED
Task 11C: UNCHANGED
```

The behavioral result is recorded below only after the apparatus commit is
published cleanly and the one fresh authorized session completes.

## Behavioral result

The apparatus commit was published at
`c0703ee64ff669046b0e94cf64c3baa616839d99` with direct origin parity before
the session was created. The fresh session was:

```text
work-task11d-qwen25-14b-v3-20260812T154829Z
inherited turns: 0
turn limit: 8
automatic retries: 0
special correction prompts: none
```

### Fixture and entry

```text
fixture: task11d-interactive-structured-existing-file/synthetic-v1
contract SHA-256: 668dd7c7bf03bdb3a61a7f1431dc7e4bf162f53063c0ee4333307772d566873d
content SHA-256: 98f2f772b26b287735956a41fe7972e3d33cdfa364e15025951068e23afd49d7
repository HEAD: 2183c5e10aae11a85ea9521d19f63f56a4d2e180
repository identity: 06c22115bc2974fdb560e43c5a78cbd159332ae8b0b97d547457c5a85e5f32b4
Source Snapshot X: 18184220d0058d1d58d2b12e39778dcbd10e7d4cd9504c5a361c2f6f4650555c
requirements: COMPLETE
read authority: .
patch authority: src/message.py only
```

All `INTERACTIVE_BOUNDED_WORK_V1` entry gates passed: one repository,
explicit objective/read/patch authority, pre-bound validators, clean frozen
source, exact accepted artifact/runtime profile, exact V3 protocol, unchanged
normalizer, structured executor, and unchanged interactive policy.

The candidate-independent contained calibration accepted three distinct good
implementations and rejected six bad implementations before inference.
`CANDIDATE_SPECIFIC_OVERFIT_CHECK = PASS`. Descriptor identities remained
`84f9b4a7758cbce11588c71ceb06e83112e87d1574efa0bc903f85ff483ea467`
for visible v1 and
`b6c453d0e93d59356c588c691a02877c9569f76a75bcef065333465cd3f4d46f`
for hidden v1.

### Turn 1

```text
invocation: alpha-2d458ad917c7-WORK-t0001-d18cebab629c
gpu-compute job: job-20260812T154843Z-956236
prompt SHA-256: 6bfa23cbe1411b327b70ce23bdded9befab9a0b5876da5b090de0ce2eb956d03
raw bytes / SHA-256: 219 / 9d719ea17a11813671271e9378b34cfd5caef9815413e7439e1c2dd486cc24d0
normalization: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
normalized bytes / SHA-256: 207 / fda65f118242ad9954bc84067aef588762218ceab99e71f0b8a156c083c01ddb
request / parser: PROPOSE_TEXT_REPLACEMENT / VALID
path SHA-256: 5029ddcd0fe99bc7f4eac4257e4a3ab5a30c59076b43264de623f9d4fe4bbcb9
old_text SHA-256: 27508742e1483c7302edcfe6b042c08df50bf734778e0362ab8cb04ee6fc6bba
new_text SHA-256: 16191690dfdc206068e5a6ca641a80ee18504015ee49f9fed4b0fe086060d380
authority: authorized path
executor: TEXT_MATCH_ZERO
exact match count: 0
policy: REPAIR_OPPORTUNITY / FIRST_STRUCTURED_MATCH_FAILURE
terminal: done=true / done_reason=stop / runner succeeded
completion metadata SHA-256: 78a1197c2082396dd148ec04a96638ccdf41aee469278a3bc2ef49cbcd9e0e66
prompt / eval tokens: 656 / 68
load / prompt-eval / eval / total: 5.213029866 / 0.255060 / 0.924909 / 6.397397777 seconds
decode: 73.52 tokens/second
profile / placement / context: qwen25-coder-14b-katra-4096 / 100% GPU / 0% CPU / 4096
```

The exact model-selected path was `src/message.py`. The selected `old_text`
described a function returning `'world'`; the selected `new_text` described a
function returning `'hello'`. The evaluator changed neither value and found no
exact occurrence. It reported only `TEXT_MATCH_ZERO` and the count `0`; it did
not expose the correct source text.

### Turn 2

```text
invocation: alpha-2d458ad917c7-WORK-t0002-c8f1d8eebbf4
gpu-compute job: job-20260812T154905Z-956396
prompt SHA-256: 7f0cc3c0fc0883f1aaa3a5406adcd95f31a567ecfc120bc12bd07b34ce964c09
raw bytes / SHA-256: 211 / 69596c9a4b86e9e224c0e5ddcd3b543455058ccb976155a66c934bd322e23fdb
normalization: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
normalized bytes / SHA-256: 199 / 21a2d3327e56ebd8e7981982af68033890389402ea885b8bfaaa2a3a8bece85f
request / parser: PROPOSE_TEXT_REPLACEMENT / VALID
path SHA-256: 5029ddcd0fe99bc7f4eac4257e4a3ab5a30c59076b43264de623f9d4fe4bbcb9
old_text SHA-256: a898d44058df548c9d0950a461e6877bc4bedb1389526c30962bcaa3aeab2e25
new_text SHA-256: 6d9c440a30e932f76ce617db87b3ed4db614f7280315f14eac4c0624f9dfa76f
authority: authorized path
executor: TEXT_MATCH_ZERO
exact match count: 0
policy: ESCALATION_REQUIRED / INTERACTIVE_STRUCTURED_EDIT_RECOVERY_FAILED
reason: STRUCTURED_EDIT_REPAIR_EXHAUSTED
terminal: done=true / done_reason=stop / runner succeeded
completion metadata SHA-256: 33d6af61e98f6010837c873f75a301488812f1893392b32327c337d55116d715
prompt / eval tokens: 681 / 67
load / prompt-eval / eval / total: 0.192729766 / 0.026649 / 0.906111 / 1.130500472 seconds
decode: 73.94 tokens/second
profile / placement / context: qwen25-coder-14b-katra-4096 / 100% GPU / 0% CPU / 4096
```

The second exact model-selected path was again `src/message.py`. Its
`old_text` described a function body containing `pass`; its `new_text`
described a function returning `"hello"`. Again the evaluator preserved the
values and counted zero exact occurrences. This was the second bounded match
failure, so the pre-published policy stopped immediately. No third turn ran.

### Semantic and transport separation

The model supplied an authorized path and a desired `hello` implementation in
both turns. It also supplied both incorrect source selections. This is a model
source-alignment/recovery failure, not unified-diff serialization failure.

The evaluator supplied only exact occurrence counting and the fail-closed
result. Because neither request matched, it supplied no replacement, candidate
identity, before/after file identity, canonical diff, or validation execution.
The source remained byte-for-byte unchanged at Source Snapshot X.

```text
candidate: NOT_CREATED
changed paths: none
canonical diff: NOT_CREATED
visible validation: NOT_RUN_NO_CANDIDATE
hidden validation: NOT_RUN_NO_CANDIDATE
technical correctness: NOT_EVALUATED
candidate integrity: NOT_PRESENT
Source Snapshot X: MATCH
turn hash chain: PASS
local/remote raw SHA-256: MATCH / both turns
duplicate inference: 0
```

The evaluator-owned handoff packet records
`INTERACTIVE_STRUCTURED_EDIT_RECOVERY_FAILED`, reason
`STRUCTURED_EDIT_REPAIR_EXHAUSTED`, recommended next worker
`DELIBERATIVE_OVERNIGHT_CODER`, and
`automatic_handoff_performed = false`.

### Runtime and health

The exact model manifest was
`9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849`;
the exact model blob was
`ac9bc7a69dab38da1c790838955f1293420b55ab555ef6b4615efa1c1507b1ed`.
The runtime remained `0.32.0+helix.repeatlimit.1`, binary SHA-256
`b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143`,
build ID `ffd1f9f6c8ffd69fdca1316e7c032447479fe139`.

Both jobs reported 100% GPU / 0% CPU and effective context 4096. Loaded-state
telemetry observed 9,312 MiB VRAM used and 14,020,272,128 bytes host RAM
available with no swap. Ordinary unload completed. Ollama remained active and
enabled, the GPU remained healthy, failed units were absent, and recent kernel
evidence contained no OOM, XID, or CUDA-fatal event.

```text
14B inference count: 2
32B inference count: 0
duplicate inference: 0
```

Task 11A remains
`INTERACTIVE_PRACTICAL_CODER_RESTRICTED_ACCEPTANCE_ESCALATED`; Task 11B remains
`PATCH_SERIALIZATION_INTERFACE_MISMATCH_CONFIRMED`; Task 11C remains
`STRUCTURED_EDIT_TRANSPORT_CANDIDATE_READY`. No history was rescored.

## Disposition

```text
INTERACTIVE_PRACTICAL_CODER_V3_RESTRICTED_ACCEPTANCE_ESCALATED
NEXT: REVIEW THE EXACT V3 SEMANTIC OR MATCH FAILURE WITHOUT CHANGING STRUCTURED TRANSPORT
```

The run used one fresh 14B session, complete requirements, V3 structured edit
only, no model-generated unified diff, no semantic repair, no work-boundary
expansion, no automatic overnight-coder invocation, no historical rescore, and
no automatic promotion.
