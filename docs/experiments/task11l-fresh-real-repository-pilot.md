# Task 11L fresh real-repository pilot under repaired apparatus

Date: 2026-08-12

Play: `Cause and Effect`

Checkpoint: `TASK11L-FRESH-REAL-REPOSITORY-PILOT-UNDER-REPAIRED-APPARATUS`

## Foundation and publication boundary

Task 11L began at clean direct-origin parity:

```text
ws-code-agent: 8aae6a669640b8fd98fb5d6f912b29f247c44f23
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp:         a1688be4535fb52237d62a58819ac69685e4478a
ws-doc-writer: d52c923d4a13949a2345fb5791ee59a82d389c4e
```

The fresh immutable pilot instance and explicit selector were published before
inference as:

```text
apparatus commit: af686319062e3b002c3dfc001edf52fd17503115
subject: test: bind fresh ws-doc-writer real repository pilot
pilot instance: task11l-ws-doc-writer-src-readme-stale-boundary/v1
pilot manifest SHA-256: 2488d0cdffc19501e72b50cdb9fedf1c87e9d5536eca694c636afdf3b8e8e2f6
```

The published tree was clean and at direct origin parity before the new
session was created. The post-publication hard gate passed 220 ws-code-agent
tests, two private-material checks, real containment, lineage, invariant,
YAML, publication-tree hygiene, diff, the eight gpu-compute suites, all three
ws-cp containment-contract tests, and the eight-case validator calibration.
The calibration result remained `CANDIDATE_SPECIFIC_OVERFIT_CHECK = PASS`.

## Fresh-session and entry binding

```text
session: work-task11l-ws-doc-writer-20260812T212019Z
session manifest SHA-256: 5d4ff2fbf05dc8dc79185b0356e47ecf1cea1580bdd7a17122deaa9ae385fbac
created turns: 0
inherited turns: 0
turn limit: 8
fixture contract SHA-256: f99a4b811728c8fe870399e61f48c47507f7fe06326bf23b6cfadfbacf8e4a3e
requirements status: COMPLETE
read authority: src/README.md
patch authority: src/README.md
promotion authority: OPERATOR_ONLY
```

The exact model-visible objective was byte-identical to Task 11J and remained
bound by the fresh pilot manifest. No Task 11J turn, grounding fact, candidate,
validation state, or Task 11K recovery record was inherited.

Every entry gate passed. The immutable session validation contract resolved:

```text
VISIBLE:       task11j-ws-doc-writer-src-readme-visible-v1 / v1
identity:      4f2f865bf1734b1117a5fc56eeb046b87e244b2bb5f0c35a1e20ba00a453550a
HIDDEN_ORACLE: task11j-ws-doc-writer-src-readme-hidden-v1 / v1
identity:      e172f6ae72baadc989d0440ab331a3fcfb04a2a977368bd6e695704b1d76dd3f
```

There was no Task 10 descriptor fallback. The frozen V3 render remained
`d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993`.

The read-only live gate matched the exact selected artifact, 8,988,110,784-byte
model blob, patched Ollama binary, accepted `qwen25-coder-14b-katra-4096`
profile, context 4096, and `GPU_ONLY / 100% GPU / 0% CPU` policy.

## Fresh model turns

All three inferences completed normally with `done=true`, `done_reason=stop`,
the exact selected artifact, context 4096, and 100% GPU placement. Each raw
response was retained before the approved whole-response JSON-fence
normalization.

### Turn 1: bounded write before read

```text
invocation: alpha-28274eb0f966-WORK-t0001-56968ecaab46
gpu-compute job: job-20260812T212106Z-958563
raw bytes / SHA-256: 301 / 96de2f6e8160df8833bb2bc54fb9d71345104ecda3510aa52a150562afd2bd93
normalized bytes / SHA-256: 289 / 5cc4059fd85bab99c06e344ce6d7bef33d98f012e810076b1d89879e1c6fbf36
normalization: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
request: PROPOSE_TEXT_REPLACEMENT
grounding: NOT_GROUNDED
authority: SOURCE_READ_REQUIRED
executor / match count: NOT_RUN / NOT_COMPUTED
policy: CONTINUE
prompt / eval tokens: 673 / 77
load / prompt-eval / eval / total: 3.474456 / 0.238088 / 1.045095 / 4.762157 seconds
decode: 73.68 tokens/second
completion metadata SHA-256: 9ab522e66276685f703d88e592c4b15f4be4fd0a976fdd60c243f6ec9e7a2288
```

No candidate or match attempt occurred, and the repair allowance was not
consumed.

### Turn 2: exact source grounding

```text
invocation: alpha-28274eb0f966-WORK-t0002-8fe14196d560
gpu-compute job: job-20260812T212121Z-958720
raw bytes / SHA-256: 90 / b890af154f747cd953c8a6cbabc0083d1704c92b2f80c28802375be464a12e62
normalized bytes / SHA-256: 78 / be2c0467d26e2db62fde2a87cf163d532237a6183c79f1e3de8a2073cee8aa7b
normalization: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
request / executor: READ / READ_FILE
grounding after: SOURCE_GROUNDED
path SHA-256: e1d5879ce3e222eb0cdd43051fb8c34c00796467acb091d0b3fa939ee3355cb5
file SHA-256: a52645c6f822f7a4a845ed971e4bab7de70898997c1e195d90e26dd331eee970
grounding fact: d80aff732adcdd0d36b104a4e75195fd2244a60ce9360a9aef48a6d806d2f9ce
prompt / eval tokens: 690 / 32
load / prompt-eval / eval / total: 0.194607 / 0.022604 / 0.428172 / 0.649661 seconds
decode: 74.74 tokens/second
completion metadata SHA-256: f4f4556c06400029ada21be839148d37826afe155ff9b1120804967d8d4df444
```

### Turn 3: grounded structured candidate

```text
invocation: alpha-28274eb0f966-WORK-t0003-60892fc82aea
gpu-compute job: job-20260812T212131Z-958823
raw bytes / SHA-256: 536 / 9eb85eb2428c5a15a04d8aa78148feee2298fd8458e3e19cc40c62f83261852b
normalized bytes / SHA-256: 524 / 4a9931bbca4d1619752839fe46002e28864aefa719f1f97c3f0f8c74c1face0e
normalization: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
request: PROPOSE_TEXT_REPLACEMENT
authority / executor: AUTHORIZED / STRUCTURED_EDIT_ACCEPTED
exact match count: 1
prompt / eval tokens: 756 / 115
load / prompt-eval / eval / total: 0.188390 / 0.032420 / 1.572285 / 1.797793 seconds
decode: 73.14 tokens/second
completion metadata SHA-256: 06232ca17e8bc3c0b15bccf7ae9510b9d919ae1697672d6725b40efe601d2d7d
```

The model selected the entire source file as `old_text` and supplied the exact
requested replacement paragraph as `new_text`. The evaluator changed neither
value. A fresh isolated candidate was constructed. Its content-addressed
structured identity equals the Task 11J candidate because the selected bytes
were identical; it was not reused. The Task 11L candidate snapshot and evidence
chain are new and session-specific.

## Candidate and validation

```text
structured request: d61bdeab9a2dc4e24bc392371cb0499cf4b9dcdae2e9f4993d3835e3be43874a
path SHA-256: e1d5879ce3e222eb0cdd43051fb8c34c00796467acb091d0b3fa939ee3355cb5
old_text SHA-256: a52645c6f822f7a4a845ed971e4bab7de70898997c1e195d90e26dd331eee970
new_text SHA-256: 664c835405b0e130c094573c359b6d0a3dd4f1d2d009488f023484f159ab6eb2
candidate: 8bd0a654963314f0f4850fee710c2053180b2419d5e80a191bdee8886ffb4910
candidate snapshot: d9408769979a41bcfbe352c34d609a71d7ec1bc95404bde5e7ca315b10a1bc55
changed paths: src/README.md only
canonical diff: 6944e1313c86f56b25a2c9dabe3919ace3ece976659ae9558614d3a973cd4755
canonical diff origin: evaluator
candidate integrity: MATCH
Source Snapshot X: MATCH
```

The repaired controller selected the exact bound visible descriptor from the
Task 11L session contract and completed it under fixed systemd containment:

```text
visible descriptor: task11j-ws-doc-writer-src-readme-visible-v1 / v1
visible identity: 4f2f865bf1734b1117a5fc56eeb046b87e244b2bb5f0c35a1e20ba00a453550a
visible result: VALIDATION_FAIL
exit code: 1
evidence identity: 316965cf5de4902c9c9bcabf61ba80933b6c70cb2b8ff29ed0a0d9ec3fe1870c
evidence file SHA-256: 1e14d5994bd27abb3f0e02015eebd1914fc6d1d463e38aed076e4f8a4c626e73
result snapshot before/after: 49fb5c27c24c736ec3a77a284153148f9c47a4f3d60a1ccf14849d4e93b22c38
hidden validation: NOT_RUN
technical correctness: FAILED
```

The visible failure was terminal under unchanged doctrine. No hand scoring,
model repair turn, or hidden-oracle execution occurred. The policy state became
`ESCALATION_REQUIRED / VALIDATION_FAILED`; automatic handoff and automatic
promotion remained false.

## Integrity, comparison, and health

The turn hash chain passed, duplicate inference was zero, and each remote raw
SHA matched the local retained response. The authoritative source remained
exact after every turn and validation transition:

```text
HEAD: d52c923d4a13949a2345fb5791ee59a82d389c4e
Source Snapshot X: 6a4a913f0258a0e35c812d147ee2a5e4b1830684bfae56978e41911202d82047
index: 96c5ca9f06bc21817c4de1a3ac9430b7dae760322bc316077643d3b27994d0d4
tracked worktree: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
untracked inventory: 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
README SHA-256: a52645c6f822f7a4a845ed971e4bab7de70898997c1e195d90e26dd331eee970
```

Task 11J produced a candidate before its validation apparatus failed; Task 11K
later ran the preserved candidate through the repaired visible validator and
recorded `VALIDATION_FAIL`. Task 11L independently produced the same semantic
bytes and the functioning apparatus returned the same visible result from the
fresh session. Task 11J remains historically infrastructure-blocked.

Peak observed admission VRAM was 9,312 MiB. Placement remained 100% GPU / 0%
CPU at context 4096. Ollama remained active and enabled, host memory remained
healthy without swap, failed units were absent, and no OOM, NVIDIA XID, or CUDA
fatal evidence appeared. Ordinary model unload completed and VRAM returned to
2 MiB used.

```text
Task 11L 14B inference count: 3
Task 11L 32B inference count: 0
duplicate inference: 0
automatic handoff: false
automatic promotion: false
source promotion: false
```

Disposition:

```text
FIRST_REAL_LOCAL_REPOSITORY_INTERACTIVE_PILOT_ESCALATED
reason: VALIDATION_FAILED
```

Next boundary:

```text
NEXT: REVIEW TWO INDEPENDENT REAL-TASK MODEL ATTEMPTS BEFORE CHANGING THE FROZEN INTERACTIVE ENVELOPE
```
