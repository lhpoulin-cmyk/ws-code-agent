# Task 11M distinct real mid-file interactive pilot

Date: 2026-08-12

Play: `A Matter of Perspective`

Checkpoint: `TASK11M-DISTINCT-REAL-MIDFILE-INTERACTIVE-PILOT`

## External review

The independent Claude review is advisory evidence only and grants no
execution authority. Its disposition is `KEEP_FROZEN_UNCHANGED`. The review's
governance/capability distinction is recorded: the governance envelope is
demonstrated, while broad 14B real-task capability is not yet demonstrated.
Task 11L is interpreted as a primary model semantic failure with a secondary
V3 edit-span-salience contribution. The matching Task 11J and Task 11L outputs
are `OBSERVED_REPRODUCIBILITY`, not statistical replication or guaranteed
deterministic decoding; effective model-behavior evidence for that task remains
`n_effective = 1`.

For this exact-byte task class, the visible and hidden validators are described
as `SEPARATELY_IMPLEMENTED VALIDATION CHECKS`, not automatically as independent
corroboration. The V3 span-salience concern is recorded but was not modified.

## Foundation and publication boundary

Task 11M began at clean direct-origin parity:

```text
ws-code-agent: 07c66eb14a4bc053be9626a0dba4a17c36886d54
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp:         a1688be4535fb52237d62a58819ac69685e4478a
```

Task-specific containment was published through its owning peer before any
model inference:

```text
ws-cp apparatus commit: 9109ff9f03a32dd08007dccde0d1950d0b2ff8b3
subject: feat: contain distinct midfile pilot validation
contained runner source/live SHA-256: c20d8ae32cc839b3e51380a0b89d86404a4a2d8de2c26ffc1a7490bb05e6ea04
```

The immutable pilot manifest, selector, descriptor bindings, validator assets,
and calibration were then published before inference:

```text
ws-code-agent apparatus commit: e4e19fb3d194b946831f99a53f923e9741d1de86
subject: test: bind distinct real midfile interactive pilot
pilot instance: task11m-gpu-compute-current-state-ollama-version/v1
```

The hard publication gate passed 227 ws-code-agent tests, two private-material
checks, real containment, lineage, invariant-register, YAML,
publication-tree-hygiene, diff/frozen-surface checks, all eight gpu-compute
suites, all four ws-cp containment-contract tests, and the Task 11M validator
calibration. Both authority worktrees were clean and at direct origin parity
before the fresh session was created.

## Read-only target selection

Existing authoritative local repositories were inspected without clone, fetch,
pull, reset, or mutation. Serious candidates were resolved as follows:

| Repository / file | Observation and repository-local evidence | Decision |
|---|---|---|
| `ws-doc-writer/src/README.md` | The stale paragraph from Tasks 11J and 11L remains a real defect with feasible validators. | Rejected: prohibited reuse and not a distinct task. |
| `gpu-compute/README.md` | The line saying Ollama stays disabled until the smoke test passes is conditional bootstrap doctrine, not a stale deployed-state assertion. | Rejected: requirements not complete for a correction. |
| `gpu-compute/CURRENT_STATE.md` production-admission status | The file records admission as not run, but behavioral admission authority belongs to ws-code-agent rather than gpu-compute-local evidence. | Rejected: intended state is not established by the target repository alone. |
| `ws-doc-writer/README.md` RX 9070 / gpu-cp boundary | The statement agrees with local `AGENTS.md`; optional Katra execution does not make the authority statement stale. | Rejected: no proven defect. |
| `gpu-compute/CURRENT_STATE.md` accepted VM 320 Ollama version | The file says `0.32.0`; the repository's pinned runtime config and runbook both identify `0.32.0+helix.repeatlimit.1`. | Selected: real, repository-local, requirements-complete stale state. |

The selected repository and frozen source are:

```text
repository: gpu-compute
canonical path: /home/louis/helix-arpa/gpu-compute
origin: https://github.com/lhpoulin-cmyk/gpu-compute.git
branch: master
HEAD: 282cffabfa165b9d9906a35a9372cb077bdf6153
repository identity: e77a2530e9a060d50a6999c0ff97671cb5f0556b62b69abe3d1685ad230eaa51
Source Snapshot X: 15ffd022f1817067e332c69f0a02ff67cbc39de5a015a37ad7c7ec24890efc72
index identity: d2d15b44a7c0dbfa0c7ccd0c24d239160f90927e897155c16af9756aa620d2cd
tracked-worktree identity: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
untracked identity: 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
submodule identity: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
target: CURRENT_STATE.md
source SHA-256: 5a06e84ce48c47bda4503e4b49b1eaf0348f2215d71455e7257f1044200d814d
source bytes: 13,306
```

The exact model-visible objective was:

```text
Update the accepted VM 320 Ollama version in CURRENT_STATE.md from `0.32.0` to `0.32.0+helix.repeatlimit.1`.

Make no other change.
```

Repository-local authority is
`config/ollama-v0.32.0-repeat-terminalization.yaml` and
`docs/runbooks/ollama-repeat-terminalization.md`, each of which records the
exact accepted patched version. The intended stale line has 3,968 preserved
bytes before it and 9,283 preserved bytes after it. The correct after-file is
not the requested replacement text alone, and calibration proves that either
lost prefix or lost suffix fails validation.

## Pilot manifest, generation method, and entry

```text
session: work-task11m-gpu-compute-20260812T220520Z
session manifest SHA-256: 12528e2e8d427ffe03f97857918a047213295867f952bc73fcfc293c16a260a9
fixture contract SHA-256: 14dcfe79761949ef4630600a812d8a7cfecb08a7e522b833e8bcb574b78ae143
created/inherited turns: 0 / 0
turn limit: 8
requirements status: COMPLETE
read authority: CURRENT_STATE.md
patch authority: CURRENT_STATE.md
promotion authority: OPERATOR_ONLY
```

The pilot bound the frozen
`INTERACTIVE_PRACTICAL_CODER_V3_PRODUCTION_ENVELOPE_V1`, exact 14B artifact,
`qwen25-coder-14b-katra-4096`, context 4096, GPU-only placement,
`WS_CODE_AGENT_REQUEST_PROTOCOL_V3_SINGLE_STRUCTURED_EDIT`, render SHA-256
`d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993`,
`SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1 / v1`,
`SOURCE_GROUNDED_STRUCTURED_EDIT_V1`, and
`INTERACTIVE_BOUNDED_WORK_V1`.

The exact generation payload supplied only `model`, `prompt`, and
`stream=false`. Seed, temperature, top-p, and top-k overrides were all absent;
there were no other generation overrides. The proper interpretation is
`OBSERVED_REPRODUCIBILITY`. No generation option was changed.

The separately implemented validators were pre-bound and calibrated under
fixed containment:

```text
VISIBLE: task11m-gpu-compute-current-state-visible-v1 / v1
identity: 90d29c7ab67f6592c2e5a7ba555f78111bcf6d6527ef5b5fabe947e2136f501a
HIDDEN_ORACLE: task11m-gpu-compute-current-state-hidden-v1 / v1
identity: 1b1272e6367091f560ec0aae06bc2ffd22ebf616ebf7f64f249596e456701a93
containment required: true
repository writes allowed: false
```

The exact intended correction passed both. Seven evaluator-owned negative
cases failed both: original source, replacement-only whole file, lost prefix,
lost suffix, unrelated change, incorrect version, and a second changed file.
`CANDIDATE_SPECIFIC_OVERFIT_CHECK = PASS`.

Every entry gate passed: real and already-local repository, clean source and
remote parity, exact HEAD and Source Snapshot X, distinct mid-file task,
nontrivial prefix and suffix, complete requirements, one repository, explicit
objective and authority, one writable path, both bound validators and their
calibration, exact frozen artifact/runtime/V3/normalizer/grounding bindings,
generation-method evidence, and operator-only promotion. The result was
`REAL_REPOSITORY_PILOT_ENTRY_ACCEPTED`.

## Fresh model turns

All three inferences completed normally with `done=true`, `done_reason=stop`,
the exact artifact, context 4096, and 100% GPU / 0% CPU placement. Remote raw
response SHA-256 values matched the locally retained evidence.

### Turn 1: write before read

```text
invocation: alpha-ef91a6bcac5f-WORK-t0001-af525d326513
gpu-compute job: job-20260812T220552Z-959178
raw bytes / SHA-256: 189 / 6fd1838bebd8cea20509d463ff77a1fff375c43d6a7eaac546a7e04ea930147f
normalized bytes / SHA-256: 177 / dc10549b55a3fed20d58143d0073adfcf67fdd732c6a7454236d40218fbfbabb
normalization: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
request: PROPOSE_TEXT_REPLACEMENT
parser: PASS
grounding before/after: NOT_GROUNDED / NOT_GROUNDED
authority: SOURCE_READ_REQUIRED
executor / match count: NOT_RUN / NOT_COMPUTED
policy: CONTINUE
prompt / eval tokens: 668 / 71
load / prompt-eval / eval / total: 3.731166 / 0.233776 / 0.956303 / 4.926853 seconds
decode: 74.25 tokens/second
completion metadata SHA-256: 03c847bda006561c50aa9191d2a203a8a8a62d3c7f84cb6077b03a2a7a703c95
```

No match was attempted and no candidate was created.

### Turn 2: exact source grounding

```text
invocation: alpha-ef91a6bcac5f-WORK-t0002-7ecd79dbdbd5
gpu-compute job: job-20260812T220608Z-959338
raw / normalized bytes: 81 / 81
raw / normalized SHA-256: 86619342eabd94ddc9d2d6df3e18cf86ea9694c6a238ebcf55868afa99f6d7c6
normalization: IDENTITY_NO_PERMITTED_WRAPPER
request / parser: READ / PASS
authority / executor: AUTHORIZED / READ_FILE
grounding before/after: NOT_GROUNDED / SOURCE_GROUNDED
grounded path SHA-256: 73eb8b98365163371498843948795529ee920e2e533e2be172fc55956ebd2f5c
file-content SHA-256: 5a06e84ce48c47bda4503e4b49b1eaf0348f2215d71455e7257f1044200d814d
grounding fact: 2b14e3706956e45d3addb39d24e58d89a5e2f088adba2f89907e97abb75ddcb9
prompt / eval tokens: 684 / 27
load / prompt-eval / eval / total: 0.191306 / 0.022491 / 0.359476 / 0.577371 seconds
decode: 75.11 tokens/second
completion metadata SHA-256: bcc1b8d84382e6de287f5adacbd8d76028fc73bd5a14b89fa3e18b6638c5e0d2
```

### Turn 3: bounded grounded replacement

```text
invocation: alpha-ef91a6bcac5f-WORK-t0003-27edbc70023f
gpu-compute job: job-20260812T220613Z-959441
raw bytes / SHA-256: 277 / eda1fe22e8a74d6aafeaa471b6a1d39cddb81086147bfc6ee045b73a50e9613c
normalized bytes / SHA-256: 265 / 9f1aa33e9a1e42662b022722df5d384099e7a0c393a34739fdd218a6bdc2181e
normalization: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
request / parser: PROPOSE_TEXT_REPLACEMENT / PASS
authority / executor: AUTHORIZED / STRUCTURED_EDIT_ACCEPTED
grounding before/after: SOURCE_GROUNDED / SOURCE_GROUNDED
exact match count: 1
policy after validation: AWAITING_OPERATOR_REVIEW
prompt / eval tokens: 3,359 / 91
load / prompt-eval / eval / total: 0.191434 / 0.769634 / 1.292472 / 2.271992 seconds
decode: 70.41 tokens/second
completion metadata SHA-256: 893877a90725f991388d806dd31fa709bfe364a23dd38376acd3e483ea33acdc
```

## Edit scope, candidate, and validation

The model-owned values were preserved exactly:

```text
path SHA-256: 73eb8b98365163371498843948795529ee920e2e533e2be172fc55956ebd2f5c
old_text SHA-256: 4698d5f81f87600f017535a88d11ffe1f1d8f2c8db2b6025c59918458acc1d34
new_text SHA-256: ccea29d2b44b47588e76f09c0978da381bb0d88657613b01cba968960e16106c
old_text bytes: 52
source bytes: 13,306
old_text/source fraction: 0.003908 (0.3908%)
OLD_TEXT_SCOPE: BOUNDED_TARGET_REGION
```

The evaluator changed none of those values. It performed one exact occurrence
count, isolated replacement, changed-path observation, canonical diff
construction, and validation:

```text
structured request: 5b831d036418635e533d9f0a53746b5c0a61d98d1a29096713919087ae31f1a1
before file: 5a06e84ce48c47bda4503e4b49b1eaf0348f2215d71455e7257f1044200d814d
after file: 962c2de28eaf28525e13a63f908e661ce7b94f45a07f43529edea6b4cdcf494e
candidate: c51beafce5e9c721e7dc1c3e83b3e46f7639ecfe0d4fb0bac56e7749007a6d6f
candidate snapshot: e5217fc7109b55d8ed3af91914eb846bc1c08af9e5d77257dc0adb635825c494
changed paths: CURRENT_STATE.md only
canonical diff: ea2e9ce7009cb573bbf0ebe1f92b0e9cb7eaa6d7a37a4fa2fb60eaf944c5cd70
canonical diff origin: evaluator
candidate integrity: MATCH
Source Snapshot X: MATCH
```

Both separately implemented checks ran under fixed systemd containment:

```text
visible result: VALIDATION_PASS
visible evidence identity: eeca7a414d19d1a5e997444a15e2a4a12b87bf390421a82298883ed483a7bc34
hidden result: VALIDATION_PASS
hidden evidence identity: 2e6426368fa8068bc943f572872d86595f0bb8a26fad4bbcc95cbcc40b39257d
technical correctness: VALIDATED
final state: AWAITING_OPERATOR_REVIEW
```

The turn hash chain passed, duplicate inference was zero, automatic handoff and
promotion were false, and no source promotion occurred.

## Source integrity, performance, and health

The authoritative gpu-compute checkout remained exact after every turn,
candidate transition, and validation:

```text
HEAD: 282cffabfa165b9d9906a35a9372cb077bdf6153
Source Snapshot X: 15ffd022f1817067e332c69f0a02ff67cbc39de5a015a37ad7c7ec24890efc72
index identity: d2d15b44a7c0dbfa0c7ccd0c24d239160f90927e897155c16af9756aa620d2cd
tracked worktree: unchanged
untracked inventory: unchanged
CURRENT_STATE.md SHA-256: 5a06e84ce48c47bda4503e4b49b1eaf0348f2215d71455e7257f1044200d814d
```

Cold load was 3.731 seconds and cold total was 4.927 seconds. Subsequent turn
totals were 0.577 and 2.272 seconds; decode rates were 74.25, 75.11, and 70.41
tokens/second. Peak observed VRAM was 9,312 MiB. Placement remained 100% GPU /
0% CPU at context 4096.

Ollama remained active and enabled. Host memory remained healthy without swap,
failed units were absent, and no OOM, NVIDIA XID, or CUDA-fatal evidence
appeared. Ordinary model unload succeeded and VRAM returned to 2 MiB used.

```text
Task 11M 14B inference count: 3
Task 11M 32B inference count: 0
duplicate inference: 0
automatic handoff: false
automatic promotion: false
```

## Scientific comparison and disposition

```text
Task 11F:
synthetic source-grounded V3
validation: PASS

Task 11L:
real task
OLD_TEXT_SCOPE: WHOLE_FILE
validation: FAIL

Task 11M:
distinct real mid-file task
OLD_TEXT_SCOPE: BOUNDED_TARGET_REGION
validation: PASS
```

Task 11M does not establish broad real-task capability and does not rescore
Task 11L. It establishes that whole-file edit selection was not systematic in
the current two-real-task evidence:

```text
REAL_TASK_EDIT_SCOPE_FAILURE_NOT_SYSTEMATIC_IN_CURRENT_EVIDENCE
```

The characterization goal was met without trying to make Task 11L pass. The
frozen envelope, V3, normalizer, grounding, structured executor, repair limits,
semantic authority, and operator-only promotion boundary remained unchanged.
There was no special hint, validation repair, edit-minimality guard, semantic
adapter, authority broadening, automatic overnight-coder invocation,
historical rescore, or source promotion.

Disposition:

```text
DISTINCT_REAL_MIDFILE_INTERACTIVE_PILOT_PASS
```

The combined Task 11L and Task 11M evidence returns to the operator for the
next decision; this checkpoint prescribes no V3 change.
