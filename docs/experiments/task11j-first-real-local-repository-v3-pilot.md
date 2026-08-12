# Task 11J first real local-repository V3 pilot

Date: 2026-08-12

Play: `Where No One Has Gone Before`

Checkpoint: `TASK11J-FIRST-REAL-LOCAL-REPOSITORY-V3-PILOT`

## Foundation and publication boundary

Task 11J started from clean direct-origin parity at:

```text
ws-code-agent: 197bb0608b1cd4512df1f309c0c210a323519469
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp:         c6138913d39502dbf1507c7318002b4ab748d0b1
ws-doc-writer: d52c923d4a13949a2345fb5791ee59a82d389c4e
```

The real-pilot manifest, explicit selector, independent visible and hidden
validators, registry bindings, and source-state checks were implemented and
tested before inference. The ws-cp containment authority required a real peer
change so the two new fixed descriptor IDs could use the existing staged
systemd sandbox. That peer change was published as
`a1688be4535fb52237d62a58819ac69685e4478a`; the installed launcher and
published launcher both had SHA-256
`0fa9fa4e63879a7f495e068a2a1d0d32007f6fc0e0d0fec93323b1259b6822bc`.

The ws-code-agent apparatus was then published before inference as
`f58ec61ebab8a69b31482680ad784bd928903987` (`feat: bind ws-doc-writer first
real repository pilot`). Both repositories were clean and at direct origin
parity before the first model turn. No apparatus was changed after a model
response was observed. The post-run gate subsequently established that the
publication gate had a blind spot: the live-tree hygiene test inspects tracked
files, so it had not examined the then-untracked manifest during the
pre-commit test run. The published tree itself therefore was not gate-clean.

The publication gate passed 209 ws-code-agent tests, the separate two-test
private-material check, real containment, lineage, invariant-register, YAML,
and diff checks. All eight gpu-compute suites and all three ws-cp containment
tests passed.

## Target and source identity

```text
repository: ws-doc-writer
canonical path: /home/louis/src/ws-doc-writer
origin: git@github.com:lhpoulin-cmyk/ws-doc-writer.git
branch: work/multi-backend-multi-model-v1-20260809
HEAD: d52c923d4a13949a2345fb5791ee59a82d389c4e
repository identity: 253abe844e08a8e5cc311326406fae24a3233c7ecd4e1a98ee92cb73788ec0a2
Source Snapshot X: 6a4a913f0258a0e35c812d147ee2a5e4b1830684bfae56978e41911202d82047
index identity: 96c5ca9f06bc21817c4de1a3ac9430b7dae760322bc316077643d3b27994d0d4
tracked-worktree identity: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
untracked identity: 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
submodule identity: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
src/README.md SHA-256: a52645c6f822f7a4a845ed971e4bab7de70898997c1e195d90e26dd331eee970
```

Direct `ls-remote` parity passed without fetching or changing local refs. The
same identities were checked after every turn, after candidate construction,
and after the validation apparatus failure. They remained exact. No file,
index, ref, untracked inventory, or commit in ws-doc-writer changed.

## Pilot manifest and validation calibration

```text
session: work-task11j-ws-doc-writer-20260812T194000Z
pilot policy: INTERACTIVE_PRACTICAL_CODER_REAL_REPOSITORY_PILOT_V1
pilot instance: task11j-ws-doc-writer-src-readme-stale-boundary/v1
fixture contract SHA-256: c808d88c81a2cfe204a02665c32b4ef2dcb8edfb6b2007124f9a358b30c7200c
requirements status: COMPLETE
read authority: src/README.md
patch authority: src/README.md
promotion authority: OPERATOR_ONLY
turn limit: 8
inherited turns: 0
```

The exact model-visible objective was:

```text
Replace the stale paragraph in src/README.md with exactly:

The `src/docwriter_web` package contains the Doc Writer application
implementation. It must not execute infrastructure commands.

Make no other change.
```

The manifest bound the frozen
`INTERACTIVE_PRACTICAL_CODER_V3_PRODUCTION_ENVELOPE_V1`, exact Qwen2.5-Coder
14B artifact, `qwen25-coder-14b-katra-4096`, V3 render
`d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993`,
`SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1 / v1`,
`SOURCE_GROUNDED_STRUCTURED_EDIT_V1`, and
`INTERACTIVE_BOUNDED_WORK_V1`.

The pre-bound validation contract was:

```text
VISIBLE:       task11j-ws-doc-writer-src-readme-visible-v1 / v1
HIDDEN_ORACLE: task11j-ws-doc-writer-src-readme-hidden-v1 / v1
containment required: true
repository writes allowed: false
```

The independent calibration accepted the exact intended replacement and
rejected the original stale source, missing infrastructure prohibition, wrong
package, unrelated wording, modified heading, partially retained stale text,
and a second changed file. Both descriptors returned the expected result for
all eight cases under systemd containment.
`CANDIDATE_SPECIFIC_OVERFIT_CHECK = PASS`.

Every entry gate passed and `REAL_REPOSITORY_PILOT_ENTRY_ACCEPTED` was durable
before inference.

## Model turns

All three turns completed normally with the exact artifact manifest, context
4096, and observed `100% GPU / 0% CPU`. Each response used the approved whole-
response JSON-fence normalization; raw evidence remained canonical.

### Turn 1: bounded write before read

```text
invocation: alpha-7c4a69ef8b04-WORK-t0001-ad714aff1033
gpu-compute job: job-20260812T193641Z-957789
prompt SHA-256: 34ef7215ea4529377db220f9e360c33f00d3a56739be4b29fe8986ba458395c9
raw bytes / SHA-256: 300 / 18d8f29b71046906faaf14157fc5ad713fe78b86e0366188702cbfac50baec51
normalized bytes / SHA-256: 288 / fb158dff905e67f5d32f21dc0dd37ce7f329793bc495b638462d1ec28e255b95
request / parser: PROPOSE_TEXT_REPLACEMENT / VALID
grounding before / after: NOT_GROUNDED / NOT_GROUNDED
authority / executor: SOURCE_READ_REQUIRED / NOT_RUN
match count: NOT_COMPUTED
policy: CONTINUE / SOURCE_READ_REQUIRED
done / reason: true / stop
completion metadata SHA-256: 98eec0a80d36b8b0c3f5e96d135dcab2fefc65e546647713d256245f4ddb696f
prompt / eval tokens: 673 / 76
load / prompt-eval / eval / total: 3.715037031 / 0.241263 / 1.031432 / 4.992384295 seconds
decode: 73.69 tokens/second
```

The projection contained only `SOURCE_READ_REQUIRED` and the requested path.
No source content was leaked and no candidate or match attempt occurred.

### Turn 2: exact source grounding

```text
invocation: alpha-7c4a69ef8b04-WORK-t0002-f1d207c0619b
gpu-compute job: job-20260812T193656Z-957949
prompt SHA-256: a0e4665fb5d05d8e3a4a33016a72508b2e3ecf7f79c8a75c584fe5608369adc1
raw bytes / SHA-256: 90 / b890af154f747cd953c8a6cbabc0083d1704c92b2f80c28802375be464a12e62
normalized bytes / SHA-256: 78 / be2c0467d26e2db62fde2a87cf163d532237a6183c79f1e3de8a2073cee8aa7b
request / parser: READ / VALID
authority / executor: AUTHORIZED / READ_FILE
grounding after: SOURCE_GROUNDED
grounded path SHA-256: e1d5879ce3e222eb0cdd43051fb8c34c00796467acb091d0b3fa939ee3355cb5
file-content SHA-256: a52645c6f822f7a4a845ed971e4bab7de70898997c1e195d90e26dd331eee970
grounding fact: d80aff732adcdd0d36b104a4e75195fd2244a60ce9360a9aef48a6d806d2f9ce
policy: CONTINUE / ORDINARY_INTERACTIVE_PROGRESSION
done / reason: true / stop
completion metadata SHA-256: ac2d09872e00a8298d0add904e007a690249d98dd7549c4cdf2d3ccc460df5a0
prompt / eval tokens: 690 / 32
load / prompt-eval / eval / total: 0.196011754 / 0.022614 / 0.427761 / 0.650863359 seconds
decode: 74.81 tokens/second
```

### Turn 3: isolated structured candidate

```text
invocation: alpha-7c4a69ef8b04-WORK-t0003-c0473646dd5b
gpu-compute job: job-20260812T193705Z-958051
prompt SHA-256: d17a1a77a43b26bfe0cf7bfeb061f50df645f61afc7105ebd96c310849ae127c
raw bytes / SHA-256: 536 / 9eb85eb2428c5a15a04d8aa78148feee2298fd8458e3e19cc40c62f83261852b
normalized bytes / SHA-256: 524 / 4a9931bbca4d1619752839fe46002e28864aefa719f1f97c3f0f8c74c1face0e
request / parser: PROPOSE_TEXT_REPLACEMENT / VALID
authority / executor: AUTHORIZED / STRUCTURED_EDIT_ACCEPTED
grounding before / after: SOURCE_GROUNDED / SOURCE_GROUNDED
exact match count: 1
policy: VALIDATION_REQUIRED / CANDIDATE_READY
done / reason: true / stop
completion metadata SHA-256: 239bfec1d437f6d6afcaeb2b026d391da628eda7174e92ca63e4f1a599bcc4bd
prompt / eval tokens: 756 / 115
load / prompt-eval / eval / total: 0.187123774 / 0.032411 / 1.569059 / 1.793313825 seconds
decode: 73.29 tokens/second
```

Local raw hashes equal the remote runtime evidence hashes for every turn. The
turn hash chain passed and duplicate inference was zero.

## Candidate and transport evidence

The model-owned structured request retained:

```text
path SHA-256: e1d5879ce3e222eb0cdd43051fb8c34c00796467acb091d0b3fa939ee3355cb5
old_text SHA-256: a52645c6f822f7a4a845ed971e4bab7de70898997c1e195d90e26dd331eee970
new_text SHA-256: 664c835405b0e130c094573c359b6d0a3dd4f1d2d009488f023484f159ab6eb2
structured-request SHA-256: d61bdeab9a2dc4e24bc392371cb0499cf4b9dcdae2e9f4993d3835e3be43874a
```

The evaluator changed none of these values. It counted one exact occurrence,
performed the replacement in isolation, observed only `src/README.md`, and
generated the review diff:

```text
before README SHA-256: a52645c6f822f7a4a845ed971e4bab7de70898997c1e195d90e26dd331eee970
after README SHA-256: 664c835405b0e130c094573c359b6d0a3dd4f1d2d009488f023484f159ab6eb2
canonical-diff SHA-256: 6944e1313c86f56b25a2c9dabe3919ace3ece976659ae9558614d3a973cd4755
canonical-diff origin: evaluator
candidate snapshot: 6ea5c1a2f5e8bba35dfbcbdfaddcffdfba269f73e5a3e39cd85ed47dccfd791e
structured candidate identity: 8bd0a654963314f0f4850fee710c2053180b2419d5e80a191bdee8886ffb4910
candidate integrity: MATCH
changed paths: src/README.md only
```

The preserved candidate selected the entire file, including the heading, as
`old_text`, while its `new_text` contained only the requested paragraph and no
terminal newline. This observable candidate state is retained for review; it
is not assigned a technical-correctness disposition because the frozen
validation transition could not run.

## Infrastructure block

The first evaluator-owned validation transition failed before launching either
descriptor. `advance_validation()` selected the historical constant
`task10k-c-write-visible-v1` rather than the visible descriptor durably bound in
the Task 11J session. Looking that ID up in the exact Task 11J contract raised:

```text
KeyError: 'task10k-c-write-visible-v1'
```

The durable validation state stopped at:

```text
phase: VISIBLE_VALIDATION_STARTED
status: VALIDATION_PENDING
visible validation: NOT_RUN
hidden validation: NOT_RUN
technical correctness: NOT_EVALUATED
```

No manual validator invocation, alternate routing, apparatus patch, retry, or
model inference was used to bypass the published seam. This is a validation-
routing apparatus defect that prevents faithful pilot scoring. It is not a
model failure and does not produce a pilot PASS.

The post-run application gate also failed one of 209 tests:
`test_active_tracked_tree_excludes_inherited_doc_writer_runtime_identity`.
After publication, the new pilot manifest became part of `git ls-files`; the
hygiene test then rejected the manifest's intentional `ws-doc-writer` target
identity. Before publication the same test had passed because the manifest was
untracked and therefore outside that test's inventory. No hygiene exception,
manifest relocation, or other repair was made after observing model output.
The private-material, containment-calibration, lineage, invariant, YAML, and
diff evidence otherwise remained clean, but the required all-tests PASS gate
was not met.

## Runtime health and disposition

Cold load was 3.715 seconds; warm total turn latencies were 0.651 and 1.793
seconds. Decode throughput was 73.69, 74.81, and 73.29 tokens/second. Loaded
telemetry observed 9,312 MiB VRAM, 100% GPU / 0% CPU, context 4096, 13,677,360
kB host memory available, and no swap. Ollama remained active and enabled;
failed units and recent OOM, NVIDIA XID, and CUDA-fatal evidence were absent.
Ordinary unload completed and GPU memory returned to 2 MiB used / 15,880 MiB
free.

```text
14B inference count: 3
32B inference count: 0
duplicate inference: 0
automatic handoff: false
automatic promotion: false
ws-doc-writer source promotion: NOT_PERFORMED
ws-doc-writer commit: NOT_PERFORMED
ws-doc-writer push: NOT_PERFORMED
```

Tasks 11F through 11I and all earlier historical dispositions remain
unchanged. The frozen V3 envelope was not changed.

Primary disposition:

```text
TASK11J_REAL_LOCAL_REPOSITORY_PILOT_INFRASTRUCTURE_BLOCKED
```

Next boundary:

```text
NEXT: REPAIR THE PILOT APPARATUS WITHOUT RESCORING MODEL BEHAVIOR
```
