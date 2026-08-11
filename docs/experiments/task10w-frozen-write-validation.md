# Task 10W frozen write validation

Play: **Quality of Life**  
Checkpoint: **TASK10W-BIND-FROZEN-WRITE-VALIDATION**  
Date: 2026-08-11

## Foundation

Task 10W began from clean direct-origin parity at:

```text
ws-code-agent  4deb99baeba94d2d2c99ffea8449371110920150
gpu-compute    282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp         e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp          e8e6d19f27c7cfecba401f0cf5bb85130cc33909
```

The pre-change ws-code-agent gate passed 130 tests, two private-material tests,
containment, lineage, invariant-register, YAML, and diff checks. All eight
gpu-compute suites passed. The existing fixed containment launcher required a
peer-owned allowlist extension for the two new descriptor IDs. That bounded
ws-cp change was published as `c613891`; its deployed launcher and tmpfiles
configuration are byte-identical to the published files. It did not add a
caller-selected command surface.

## Validation contract

The trusted registry binds:

| Role | Descriptor | Version | Descriptor identity |
| --- | --- | --- | --- |
| Visible | `task10k-c-write-visible-v1` | `v1` | `84f9b4a7758cbce11588c71ceb06e83112e87d1574efa0bc903f85ff483ea467` |
| Hidden oracle | `task10k-c-write-hidden-v1` | `v1` | `b6c453d0e93d59356c588c691a02877c9569f76a75bcef065333465cd3f4d46f` |

Both descriptors derive only from the frozen objective: `src/message.py` must
exist as valid Python and expose a callable zero-argument `message()` whose
result is exactly the Python string `"hello"`. Repository writes are forbidden,
post-patch state is required, timeout is 10 seconds, and containment is
required. Neither descriptor imposes whitespace, layout, type annotation,
docstring, or other style requirements.

The visible implementation imports the file as a fresh module and checks its
signature and result. The hidden implementation independently compiles and
executes the file in a fresh namespace, verifies zero-argument binding and
one-argument rejection, and checks two calls. They share snapshot and
containment infrastructure but not assertion logic. Hidden source and failure
details are not model-visible.

## Candidate-independent calibration

Calibration ran before the preserved candidate. Both validators passed all
three materially distinct good forms:

```text
multiline function                         PASS / PASS
one-line function                          PASS / PASS
annotated function with docstring          PASS / PASS
```

Both validators rejected every bad form:

```text
missing src/message.py                     FAIL / FAIL
syntax error                               FAIL / FAIL
missing message                            FAIL / FAIL
message requiring an argument              FAIL / FAIL
message returning "Hello"                  FAIL / FAIL
message returning None                     FAIL / FAIL
```

`CANDIDATE_SPECIFIC_OVERFIT_CHECK = PASS`

## Plumbing

Future frozen synthetic write sessions record the authorized IDs, versions,
executable/argv, role, timeout and write/containment policies, validator source
hashes, and aggregate descriptor identities in the durable session manifest
before inference. Unknown IDs and identity substitution fail closed. The
clarification fixture binds no write validators.

Candidate validation advances one durable phase at a time:

```text
CANDIDATE_READY
VISIBLE_VALIDATION
HIDDEN_VALIDATION
VALIDATION_PASS
```

An interrupted `*_VALIDATION_STARTED` phase is ambiguous and cannot be rerun.
Validation uses a disposable reconstruction of the isolated candidate, never
the authoritative source repository. Pre/post candidate and Source Snapshot X
checks, result-snapshot binding, timeout, containment, and effect detection are
mandatory. Review packets report visible and hidden descriptor/version/status,
exit and evidence identities independently, plus `technical_correctness`.
Passing validation does not promote the candidate.

## Frozen surfaces

```text
V2 render SHA-256:
3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e

write model-visible fixture identity:
db9efb27f7f56da8a0f295e3ef0e656271264ac08ec977da578f2e6e020bb2b6

clarification fixture identity:
b0f5cdd341a2eb491ddcd9f02253563cbc0a44d79eccf86b3a3519cfdb13b3ba
```

The request parser, request types, isolated patch executor, authority
interpretation, candidate construction, candidate review, and model-visible
renderer are unchanged. Validator binding changes evaluator-owned metadata,
not fixture task bytes.

## Preserved Task 10V candidate

Only after calibration and publication of the validator implementation at
`09a17ca9f34b71956a316ee81f947584fa51d28b` was the preserved candidate bound
for `RETROSPECTIVE_TECHNICAL_VALIDATION`:

```text
session:
work-task10v-qwen25-32b-write-20260811T203928Z

candidate identity:
356abfda8bf041701e01e732156e47b9f49dc62953be360325a3f7e3d729feb0

candidate integrity: MATCH
Source Snapshot X: MATCH
```

Results:

| Gate | Status | Exit | Evidence identity |
| --- | --- | --- | --- |
| Visible | `VALIDATION_PASS` | 0 | `39e451aaff702c68638ce5bca687c9d824d4f4cbd0878b7e11d949ceda26edb3` |
| Hidden | `VALIDATION_PASS` | 0 | `014dba5fff941b8d47cbaf502de3b25ea8f1049692701cc24527b37f0b6b256c` |

Each validator's result snapshot was identical before and after its run. The
review packet reports `technical_correctness: VALIDATED`. No source promotion
or operator disposition occurred.

## Historical integrity and roles

```text
Qwen2.5-Coder 14B work role: INTERACTIVE_PRACTICAL_CODER
Qwen2.5-Coder 32B work role: DELIBERATIVE_OVERNIGHT_CODER

Task 10V historical disposition: `UNCHANGED`
Task 10V model turns: UNCHANGED
Task 10V clarification: UNCHANGED / PASS

14B model inferences: 0
32B model inferences: 0
total Task 10W model inferences: 0
```

The role labels describe operator use only. They do not alter runtime
acceptance, strict V2 scores, qualification, authority, preference, or
promotion.

## Disposition

```text
TASK10W_VALIDATION_APPARATUS_READY
TASK10V_PRESERVED_CANDIDATE_TECHNICALLY_VALIDATED

NEXT: CALIBRATE THE MINIMUM PRODUCTION ADAPTER FOR THE 14B INTERACTIVE/PRACTICAL CODER
```

No model inference, historical rescore, candidate-specific validator, style
requirement, protocol change, Markdown normalization, output repair, authority
broadening, or automatic promotion occurred.
