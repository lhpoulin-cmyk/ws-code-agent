# Task 11A restricted interactive coder acceptance

Date: 2026-08-12

Play: `Peak Performance`

Checkpoint: `TASK11A-RESTRICTED-INTERACTIVE-CODER-ACCEPTANCE`

Task 11A ran the first fresh positive acceptance fixture for the Qwen2.5-Coder
14B `INTERACTIVE_PRACTICAL_CODER` inside `INTERACTIVE_BOUNDED_WORK_V1`. The
requirements-complete entry gate passed. The model read the authorized file and
twice proposed the correct semantic change, but neither patch was syntactically
applicable. The second rejection exhausted the one permitted forward repair
opportunity, so the existing supervisor stopped the session and produced its
operator-owned handoff packet. This is a scoreable policy escalation, not an
apparatus failure and not an acceptance.

## Foundation

The clean, direct-origin-parity starting checkpoints were:

```text
ws-code-agent: 68924a00061e347d553128edc0525fbc573fa31b
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp:         c6138913d39502dbf1507c7318002b4ab748d0b1
```

Before inference, ws-code-agent passed all 158 tests after binding the fixture,
the separate two-test private-material gate, containment, lineage, invariant
register, YAML, and diff gates. All eight gpu-compute suites and both ws-cp
containment tests passed. The fixture/validator apparatus checkpoint was
published at `a9f467db0cc843ba36c6005c7be661a75ecfa39b` before the model session began.
Peer repositories were not changed.

## Fixture

```text
fixture ID: task11a-interactive-positive-existing-file/synthetic-v1
fixture contract SHA-256: 0e3358da82716ecf114edb4359fc1aafbf506d89f2d0911c5d8fe4ba49ec805e
fixture content SHA-256: 98f2f772b26b287735956a41fe7972e3d33cdfa364e15025951068e23afd49d7
repository HEAD: c6b35c601264c024ff624ba5991b256e131b7081
repository identity: 16c09fa01353f4b4e122c5fcec2d431667c2ebcd204063be4e06280085c2b53b
Source Snapshot X: 348d4d52fab027d03a1652043b7eacee8d4aa54f17553fb58c4fa680cf52500e
requirements_status: COMPLETE
read authority: .
patch authority: src/message.py only
```

The frozen initial file was:

```python
def message():
    return "hi"
```

The exact model-visible objective was:

```text
Change message() in src/message.py so that calling message()
returns exactly the string "hello".

Make no other functional change.
```

The fixture was created in an evaluator-owned synthetic Git repository before
inference. Its worktree remained clean at the same HEAD and snapshot after the
terminal escalation. No historical Task 10 fixture changed.

## Validation contract

The final behavior is identical to the trusted Task 10W `message()` contract,
so Task 11A bound the existing independent descriptors rather than creating
candidate-specific validator semantics:

```text
visible descriptor: task10k-c-write-visible-v1 / v1
visible identity: 84f9b4a7758cbce11588c71ceb06e83112e87d1574efa0bc903f85ff483ea467
hidden descriptor: task10k-c-write-hidden-v1 / v1
hidden identity: b6c453d0e93d59356c588c691a02877c9569f76a75bcef065333465cd3f4d46f
containment: required / task10w-systemd-v1
repository writes allowed: false
```

The contract checks only that `src/message.py` is valid Python, exports a
zero-argument callable `message`, and that a successful call returns exactly
the Python string `"hello"`. Before inference, contained calibration accepted
three materially different good implementations and rejected six bad cases:
missing file, syntax error, missing function, required argument, `"Hello"`, and
`None`. The visible and hidden implementations remain independent. Calibration
evidence SHA-256 was
`2a32cde810d2883ab8854d7ddf5ef28a0a93a09c662176e7b1c021c6a86ac08a`.

```text
CANDIDATE_SPECIFIC_OVERFIT_CHECK = PASS
```

No model candidate was produced, so neither pre-bound validator was invoked on
model work. Their durable state remains `VALIDATION_PENDING` with technical
correctness `NOT_EVALUATED`.

## Entry

Every `INTERACTIVE_BOUNDED_WORK_V1` gate passed before the first inference:

```text
requirements_status = COMPLETE: PASS
single repository: PASS
objective explicit: PASS
read authority explicit: PASS
patch authority explicit: PASS
validation descriptors pre-bound: PASS
source clean/frozen: PASS
artifact/runtime profile binding: PASS
bounded adapter binding: PASS
INTERACTIVE_ENTRY_ACCEPTED
```

The exact model was `qwen2.5-coder:14b-instruct-q4_K_M`, manifest
`9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849`,
under `qwen25-coder-14b-katra-4096`, 4096 context, and 100% GPU / 0% CPU.
The runtime was `0.32.0+helix.repeatlimit.1`, binary SHA-256
`b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143`,
build ID `ffd1f9f6c8ffd69fdca1316e7c032447479fe139`.

## Turns

Session: `work-task11a-qwen25-14b-positive-20260812T142051Z`. It began with
zero inherited turns and stopped after three of the maximum eight.

### Turn 1

```text
invocation: alpha-9e2e05df7e5c-WORK-t0001-12565c08ed74
gpu-compute job: job-20260812T142120Z-955351
raw bytes / SHA-256: 91 / f52783b9c7e1b6cabdc432c68e9384e66da391aa1f201051802127857b9962fb
normalization: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
normalized bytes / SHA-256: 79 / 8a1ecde4ee82cc32b416acd39fdaedb6eac92d25682db43e2aa42f12c925be0d
request / parser: READ / VALID
authority / executor: AUTHORIZED / READ_FILE
policy: CONTINUE
HTTP terminal: 200 / done=true / done_reason=stop
completion metadata SHA-256: 3b8228d751129ee0f303c5548a86de4968232ce0701f87fc04a8b0f95f9298cd
prompt / eval tokens: 777 / 31
load / prompt-eval / eval / total: 7.748211411 / 0.266129 / 0.420716 / 8.440572991 seconds
decode: 73.68 tokens/second
placement / context: 100% GPU / 0% CPU / 4096
```

### Turn 2

```text
invocation: alpha-9e2e05df7e5c-WORK-t0002-b2975fd5c952
gpu-compute job: job-20260812T142144Z-955509
raw bytes / SHA-256: 203 / 7b367e7154161e9b727d4727226f9dde4fdb73d3aa3917e53cfc773332be688a
normalization: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
normalized bytes / SHA-256: 191 / 1a0a9d585a764d2c6be594ccce029f761a6a0107caeb7209d183751522838911
request / parser: PROPOSE_PATCH / VALID
authority / executor: AUTHORIZED / PATCH_REJECTED
executor detail: patch contains no supported diff header
semantic intent: correct bounded hi-to-hello change
policy: REPAIR_OPPORTUNITY / FIRST_PATCH_REJECTED
HTTP terminal: 200 / done=true / done_reason=stop
completion metadata SHA-256: 0b6a9661806b75351f05d9b07d04cf1812b3b99dc4f1d500eb10e57339179468
prompt / eval tokens: 810 / 69
load / prompt-eval / eval / total: 0.195799647 / 0.027718 / 0.934801 / 1.163129755 seconds
decode: 73.81 tokens/second
placement / context: 100% GPU / 0% CPU / 4096
```

### Turn 3

```text
invocation: alpha-9e2e05df7e5c-WORK-t0003-24ef3ca9cd6c
gpu-compute job: job-20260812T142157Z-955613
raw bytes / SHA-256: 293 / a766d876888b62252091dec4fb0fccf5774aa9e84122b3172b90179352e158a5
normalization: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
normalized bytes / SHA-256: 281 / 42ac1348d09a317038524af58809619cba9ec7c84f33909844188e5938c8a3ca
request / parser: PROPOSE_PATCH / VALID
authority / executor: AUTHORIZED / PATCH_REJECTED
executor detail: git apply rejected; corrupt patch at line 5
semantic intent: correct bounded hi-to-hello change
policy: ESCALATION_REQUIRED / INTERACTIVE_RECOVERY_FAILED
reason: PATCH_REPAIR_EXHAUSTED
HTTP terminal: 200 / done=true / done_reason=stop
completion metadata SHA-256: 282317d2446e2f1824b53fc06d0bca603a11b4612d61713be10bf9c265c41b56
prompt / eval tokens: 851 / 93
load / prompt-eval / eval / total: 0.187074147 / 0.026902 / 1.258613 / 1.477610739 seconds
decode: 73.89 tokens/second
placement / context: 100% GPU / 0% CPU / 4096
```

The normalizer removed one exact wrapper on each turn and preserved the JSON
payload bytes. The unchanged strict parser accepted every normalized request.
The executor denied neither path nor effect; both failures were patch
construction failures. No retry or fourth inference occurred.

## Candidate, safety, and handoff

```text
candidate: NOT_CREATED
changed paths: none
candidate integrity: NOT_PRESENT
visible validation: NOT_RUN_NO_CANDIDATE
hidden validation: NOT_RUN_NO_CANDIDATE
technical correctness: NOT_EVALUATED
Source Snapshot X: MATCH
turn hash chain: PASS
duplicate inference: 0
local/remote raw SHA-256: MATCH for all three turns
```

Raw and normalized evidence are both durable. Semantic request content and
authority were unchanged by normalization. The authoritative fixture remained
unchanged. The evaluator generated `INTERACTIVE_WORK_ESCALATION_HANDOFF_V1`
with the original objective, source snapshot, authority, requirements status,
turn sequence, raw and normalized evidence, executor results, empty candidate,
and structured escalation reason. It records:

```text
classification: INTERACTIVE_RECOVERY_FAILED
reason: PATCH_REPAIR_EXHAUSTED
recommended_next_worker: DELIBERATIVE_OVERNIGHT_CODER
automatic_handoff_performed: false
```

No candidate was promoted and no deliberative/overnight worker was invoked.

## Performance and health

The cold turn completed in 8.440573 seconds, including a 7.748211-second load.
Warm turns completed in 1.163130 and 1.477611 seconds. Decode rates were 73.68,
73.81, and 73.89 tokens/second. Each inference reported 100% GPU / 0% CPU and
effective context 4096. Loaded telemetry observed 9,312 MiB total device memory
used, including 9,302 MiB by the runner.

After the terminal result, ordinary `ollama stop` unloading succeeded. Ollama
was active and enabled, failed units were empty, the RTX 5070 Ti was healthy at
40 C and 0% utilization with 2 MiB used / 15,880 MiB free, host available RAM
was 14,783,004,672 bytes, swap remained absent, and the model store had
70,559,580,160 bytes free. Recent kernel evidence contained no OOM, NVIDIA XID,
or CUDA-fatal event.

## Frozen and historical surfaces

```text
V2 protocol: WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE
V2 render SHA-256: 3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e
adapter: SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1 / unchanged
parser: unchanged
isolated executor: unchanged
Task 10Z policy: unchanged
historical write fixture: db9efb27f7f56da8a0f295e3ef0e656271264ac08ec977da578f2e6e020bb2b6
historical clarification fixture: b0f5cdd341a2eb491ddcd9f02253563cbc0a44d79eccf86b3a3519cfdb13b3ba
```

All earlier strict, normalized, 32B, retrospective-validation, and boundary
evidence remains unchanged.

```text
14B inferences: 3
32B inferences: 0
duplicate inference: 0
```

Task 11A added no semantic adapter, special model hint, automatic 32B
invocation, historical rescore, authority broadening, or automatic promotion.

## Disposition

```text
INTERACTIVE_PRACTICAL_CODER_RESTRICTED_ACCEPTANCE_ESCALATED
NEXT: REVIEW THE EXACT ESCALATION EVIDENCE BEFORE CHANGING THE INTERACTIVE WORK BOUNDARY
```

This acceptance attempt demonstrated correct entry routing, semantic task
intent, evidence preservation, and terminal escalation enforcement. It did not
demonstrate an accepted candidate: the worker exhausted its bounded repair
allowance without producing an applicable patch.
