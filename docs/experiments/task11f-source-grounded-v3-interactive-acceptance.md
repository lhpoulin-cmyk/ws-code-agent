# Task 11F source-grounded V3 interactive acceptance

Date: 2026-08-12

Play: `The Mind's Eye`

Checkpoint: `TASK11F-FRESH-V3-SOURCE-GROUNDED-INTERACTIVE-ACCEPTANCE`

## Foundation and apparatus publication

The task started from clean direct-origin parity at:

```text
ws-code-agent: 72beb412ad9257797ab8fb126666dd8351898cae
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp:         c6138913d39502dbf1507c7318002b4ab748d0b1
```

Task 11F needed a distinct fixture/start selector so it could not reuse Task
11D identity. That minimal apparatus was tested and published before inference
as `930da27553282c048f2ded21910b2bc70463c71c` (`feat: bind source grounding
to V3 interactive lane`). The worktree was clean and at direct origin parity.
The commit changed no V3 text, grounding behavior, structured executor,
normalizer, validator, authority, work boundary, or repair rule.

The pre-inference gate passed 194 ws-code-agent tests, two private-material
tests, real containment, lineage, invariant-register, YAML, and diff checks.
All eight gpu-compute suites and both ws-cp containment-contract tests passed.
The V2 and V3 renders retained their exact hashes.

## Fixture and entry

```text
session: work-task11f-qwen25-14b-grounded-20260812T170353Z
fixture: task11f-source-grounded-structured-existing-file/synthetic-v1
contract SHA-256: 2e11f5fac2952ee90dba867e129466a7f6b619c057a952348713035ddc33ed16
content SHA-256: 98f2f772b26b287735956a41fe7972e3d33cdfa364e15025951068e23afd49d7
repository HEAD: 59b2b777fae1f446da337576b96de6e4b33a2400
repository identity: fcee082334c9ad47c50ebecba6b58600ce9b8728861f5b200046e9cf6513778d
Source Snapshot X: b1e5f6c43fe763645bb62f349e42661b6f2402cf94d29cc405d10dcb160e297f
requirements: COMPLETE
read authority: .
patch authority: src/message.py only
turn limit: 8
inherited turns: 0
```

The exact model-visible objective remained:

```text
Change message() in src/message.py so that calling message()
returns exactly the string "hello".

Make no other functional change.
```

Every entry gate passed: complete requirements, one repository, explicit
objective, explicit read and patch authority, pre-bound validators, clean
frozen source, exact artifact/runtime profile, V3, normalizer, structured
executor, interactive boundary, and source-grounding policy.
`INTERACTIVE_ENTRY_ACCEPTED` was durable before the first inference.

The candidate-independent validator calibration accepted three materially
different good implementations and rejected six bad implementations under
containment. `CANDIDATE_SPECIFIC_OVERFIT_CHECK = PASS`; the report SHA-256 was
`8d0e0e2dd236ab4162b7f1e9c4fef5babb112e6f3652bb507649dd4deed537fa`.

## Exact runtime binding

The read-only live gate established:

```text
host: cuda-compute-katra
model: qwen2.5-coder:14b-instruct-q4_K_M
manifest: 9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849
model blob: ac9bc7a69dab38da1c790838955f1293420b55ab555ef6b4615efa1c1507b1ed
model blob bytes: 8988110784
profile: qwen25-coder-14b-katra-4096
placement policy: GPU_ONLY / 100% GPU / 0% CPU
context: 4096
Ollama: 0.32.0+helix.repeatlimit.1
binary SHA-256: b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143
build ID: ffd1f9f6c8ffd69fdca1316e7c032447479fe139
deployed profile SHA-256: 2c2a0637f9e8e169e9e3fe0e0ce320e3ce82d01bb33418ad6aabfb3e1a0d02c5
```

The model manifest and full blob were rehashed. Ollama was active/enabled,
failed units were absent, no model was loaded, the RTX 5070 Ti had 15,880 MiB
free VRAM, host memory was healthy, and swap remained absent.

## Turn 1 — bounded write-before-read

```text
invocation: alpha-99c42a5d4369-WORK-t0001-8e10cfc3e31e
gpu-compute job: job-20260812T170416Z-956962
prompt SHA-256: 91cebb14f73ebe9db385ddca2972dea14b7c7a36048b75d38066dc6fca604390
raw bytes / SHA-256: 211 / 69596c9a4b86e9e224c0e5ddcd3b543455058ccb976155a66c934bd322e23fdb
normalization: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
normalized bytes / SHA-256: 199 / 21a2d3327e56ebd8e7981982af68033890389402ea885b8bfaaa2a3a8bece85f
request / parser: PROPOSE_TEXT_REPLACEMENT / VALID
grounding before: NOT_GROUNDED
authority result: SOURCE_READ_REQUIRED
executor operation: NOT_RUN
match count: NOT_COMPUTED
policy: CONTINUE / SOURCE_READ_REQUIRED
done / reason: true / stop
completion metadata SHA-256: 18fa90913fd823946beefb72c974c9d2d5eca8e33801e318dff1ef804cefa248
prompt / eval tokens: 651 / 67
load / prompt-eval / eval / total: 3.977172404 / 0.233290 / 0.905547 / 5.120957802 seconds
decode: 73.99 tokens/second
placement / context: 100% GPU / 0% CPU / 4096
```

The projection contained only `SOURCE_READ_REQUIRED` and the model-requested
`src/message.py` path. It disclosed no source content or correct old text. No
candidate or match failure existed, and the match-repair allowance was not
consumed.

## Turn 2 — source grounding

```text
invocation: alpha-99c42a5d4369-WORK-t0002-b8d403090eb4
gpu-compute job: job-20260812T170436Z-957120
prompt SHA-256: 579f25ff273b27df16433dcaa71bc8be2e2f440a567efcb335e5135d8afebcf2
raw bytes / SHA-256: 91 / f52783b9c7e1b6cabdc432c68e9384e66da391aa1f201051802127857b9962fb
normalization: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
normalized bytes / SHA-256: 79 / 8a1ecde4ee82cc32b416acd39fdaedb6eac92d25682db43e2aa42f12c925be0d
request / parser: READ / VALID
executor: READ_FILE / AUTHORIZED
grounding result: SOURCE_GROUNDED
done / reason: true / stop
completion metadata SHA-256: 0f0e6d0f4746f13ac098375586e795889ef93836b2bebcf9d37e942983361f45
prompt / eval tokens: 667 / 31
load / prompt-eval / eval / total: 0.189920565 / 0.022564 / 0.414552 / 0.631257867 seconds
decode: 74.78 tokens/second
placement / context: 100% GPU / 0% CPU / 4096
```

Durable grounding evidence:

```text
policy/version: SOURCE_GROUNDED_STRUCTURED_EDIT_V1 / source-grounding-read/v1
path: src/message.py
path SHA-256: 5029ddcd0fe99bc7f4eac4257e4a3ab5a30c59076b43264de623f9d4fe4bbcb9
file-content SHA-256: 98f2f772b26b287735956a41fe7972e3d33cdfa364e15025951068e23afd49d7
Source Snapshot X: b1e5f6c43fe763645bb62f349e42661b6f2402cf94d29cc405d10dcb160e297f
read turn: 2
executor-fact identity: 77a38e9b1a02c5391f162568178b3bf68cee791f96ba8bfa941432158b5db448
```

## Turn 3 — structured edit

```text
invocation: alpha-99c42a5d4369-WORK-t0003-4ce0955b5521
gpu-compute job: job-20260812T170455Z-957224
prompt SHA-256: 1c10de48ee388a4ed235f44c0ae110e9090dafa30d153b8e9665f8c0bd00f101
raw bytes / SHA-256: 168 / 56f843b95b391c8246754dbe3af1f9288e155e84a18fa938fc0d21b6eb8a7a6f
normalization: IDENTITY_NO_PERMITTED_WRAPPER
normalized bytes / SHA-256: 168 / 56f843b95b391c8246754dbe3af1f9288e155e84a18fa938fc0d21b6eb8a7a6f
request / parser: PROPOSE_TEXT_REPLACEMENT / VALID
grounding before: SOURCE_GROUNDED
authority: authorized exact path
executor: STRUCTURED_EDIT_ACCEPTED
exact match count: 1
terminal: CANDIDATE_READY
done / reason: true / stop
completion metadata SHA-256: afa5a3028e95537113d591c647ddf2564f07ee69ff817e5e4a76f0e318168007
prompt / eval tokens: 700 / 53
load / prompt-eval / eval / total: 0.193565527 / 0.034053 / 0.713762 / 0.946516267 seconds
decode: 74.25 tokens/second
placement / context: 100% GPU / 0% CPU / 4096
```

Model-owned values were preserved exactly:

```text
path SHA-256: 5029ddcd0fe99bc7f4eac4257e4a3ab5a30c59076b43264de623f9d4fe4bbcb9
old_text SHA-256: b2dc9a8114b09ccf81da8555c03a2f3d55d40c6c1109d8e0ab3b0f48511799f6
new_text SHA-256: 9afa0682767cc7c91eaeadebd8268a9ca2bbee64666ae5e322a7182ca1b8a07e
structured request SHA-256: 93d7be5bfd23591fc6e5e8e9820c93dd23cd3a24c4481ad6e62de81cdf7c085b
```

The evaluator supplied only exact occurrence counting, isolated replacement,
effect observation, canonical diff construction, candidate identity, and
validation execution. It did not change path, old text, or new text.

## Candidate and validation

```text
logical structured candidate: ac813e35c939b2bfc64aaa4a5fd3237e284ca80fbd2dbaac351fe25ad755d7a5
candidate snapshot: bfa53b8adfd885e10b69eb4a64d4174316f1b60b7e64d3a15fd749509ef988a4
changed paths: src/message.py only
before-file SHA-256: 98f2f772b26b287735956a41fe7972e3d33cdfa364e15025951068e23afd49d7
after-file SHA-256: 34d5d612343d6fe37aed652790ec4536339bd6025c31c5364f7c85197f83febc
canonical-diff SHA-256: 52f56438548ceb2ae079583b4fb357d130d8adac1514510965ec1740c0a4389c
canonical-diff origin: evaluator
candidate integrity: MATCH
source state: MATCH
```

The contained visible validator passed with evidence identity
`2e1bdb044a9786d90a13e00fddb8edc278476f8037d48a6e84a94246c7b35093`.
The independently staged contained hidden oracle passed with evidence identity
`4cd1909d797bc27ab50678b5f7a093ef37e070ce72091930720bdc46b7cc2c0e`.
Both observed unchanged validation snapshots. Technical correctness is
`VALIDATED`; the final state is `AWAITING_OPERATOR_REVIEW`. No promotion was
performed.

## Integrity, performance, and health

All local raw response hashes equal their gpu-compute runtime evidence hashes.
The turn hash chain passed, duplicate inference was zero, Source Snapshot X
remained `MATCH`, and the authoritative fixture source was unchanged.

Cold load duration was 3.977 seconds and cold total latency was 5.121 seconds.
Warm total turn latencies were 0.631 and 0.947 seconds, with decode throughput
74.78 and 74.25 tokens/second. Loaded-state telemetry observed 9,312 MiB VRAM,
100% GPU / 0% CPU placement, context 4096, and 13,683,624 kB host memory
available with no swap.

Ollama remained active/enabled, failed units were absent, and recent kernel
evidence contained no OOM, NVIDIA XID, or CUDA-fatal event. Ordinary unload
completed; post-unload VRAM returned to 2 MiB used / 15,880 MiB free.

```text
14B inference count: 3
32B inference count: 0
duplicate inference: 0
automatic handoff: false
automatic promotion: false
```

## Scientific comparison

| Task | Source grounding | Semantic edit | Transport | Validation |
|---|---|---|---|---|
| 11A | READ target: yes | correct `hi` to `hello` | unified-diff serialization failed | no candidate |
| 11D | READ target: no | desired `hello`, hallucinated old text | structured transport was not the failure | no candidate |
| 11F | write-first denial, then exact READ | exact source-aligned `hi` to `hello` | structured replacement accepted, one match | visible and hidden PASS |

This single fixture is evidence that the source-grounding precondition resolved
the demonstrated source-alignment workflow failure while preserving model and
evaluator ownership. It is not a general model score and does not rescore any
historical result.

## Frozen surfaces and disposition

V3 remains
`d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993`;
V2 remains
`3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e`.
Structured-edit semantics, normalizer, validators, semantic authority,
read/patch authority, `INTERACTIVE_BOUNDED_WORK_V1`, and its match-repair
allowance are unchanged. Tasks 11A through 11E remain unchanged.

The post-run gate repeated all 194 ws-code-agent tests, the two private-material
tests, real containment, lineage, invariant-register, YAML, diff, frozen-source,
and Task 11E replay checks. All eight gpu-compute suites and both ws-cp
containment-contract tests also passed. The peer repositories remained
unchanged.

```text
INTERACTIVE_PRACTICAL_CODER_V3_SOURCE_GROUNDED_ACCEPTANCE_PASS
NEXT: FREEZE THE INTERACTIVE/PRACTICAL CODER V3 SOURCE-GROUNDED PRODUCTION ENVELOPE AND DESIGN THE FIRST REAL-REPOSITORY PILOT
```
