# Task 11N distinct real-code interactive pilot

Date: 2026-08-12

Play: `The Next Phase`

Checkpoint: `TASK11N-DISTINCT-REAL-CODE-INTERACTIVE-PILOT`

## Scientific state and foundation

Task 11N preserved the external-review disposition `KEEP_FROZEN_UNCHANGED`.
The prior evidence remains unchanged: Task 11F passed synthetically, Task 11L
failed a real documentation task after selecting the whole file, and Task 11M
passed a distinct real state-documentation task with a bounded target region.
Task 11M's advisory finding remains
`REAL_TASK_EDIT_SCOPE_FAILURE_NOT_SYSTEMATIC_IN_CURRENT_EVIDENCE`; broad
interactive-coder capability is not established.

The play began from clean, direct-origin-parity authority:

```text
ws-code-agent: e789e762f5bea31be13af1860ad83fa6b0b2f9a4
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp:         9109ff9f03a32dd08007dccde0d1950d0b2ff8b3
```

Task-specific containment was published through its owning peer before model
inference:

```text
ws-cp apparatus commit: 313b2eb6a474edcff321799bac4b17b8c1e1128d
subject: feat: contain distinct code pilot validation
contained runner source/live SHA-256: 94a9572ab1a19a7cd32747952f4289650c28cbf713079518f2b8a869593f0945
```

The immutable pilot manifest, selector, validator assets, registry binding,
and calibration were then published before inference:

```text
ws-code-agent apparatus commit: 48403b7d0bb58a5f25d5f8477286ddc6ed8cb14c
subject: test: bind distinct real code interactive pilot
pilot instance: task11n-ws-doc-writer-writing-setup-custom-policy/v1
```

The publication gate passed 227 or more ws-code-agent tests, two
private-material checks, containment, lineage, invariant-register, YAML,
publication-tree-hygiene, diff/frozen-surface checks, all eight gpu-compute
suites, all five ws-cp containment-contract tests, and the Task 11N contained
validator calibration. The authority worktrees were clean and at direct origin
parity before the fresh session began.

## Read-only real-code target selection

Only existing authoritative local checkouts were inspected. No repository was
cloned, fetched, pulled, reset, or modified to create work.

| Repository / file | Observation and repository-local evidence | Decision |
|---|---|---|
| `ws-doc-writer/src/docwriter_web/app.py` | An implementation-absence docstring appears stale, but its intended replacement and scope are not established as a small behavioral contract. | Rejected: requirements not complete and broader than the preferred task. |
| `ws-doc-writer/tools/benchmark_runner*.py` | Several parsing paths warranted inspection, but no repository-local failing contract established a real bounded defect. | Rejected: suspected code is not authority for intended behavior. |
| `gpu-compute/bootstrap/*` | These are executable scripts, but they govern appliance deployment and no small requirements-complete defect was established. | Rejected: deployment-sensitive and no proven defect. |
| `ws-cp/tools/validate-workstation-node-record.sh` | This is executable validation code, but it is control-plane and storage/network adjacent; no repository-local defect was established. | Rejected: blast radius and requirements evidence do not fit the first code pilot. |
| `ws-doc-writer/src/docwriter_web/writing_setup.py` | `from_form` prefers the selected standard clarification policy over a nonblank custom value. The rendered form explicitly labels the second input as a custom policy for cases where a standard choice does not fit, while the design records the form values as operator intent. A direct read-only function check reproduces the incorrect precedence. | Selected: real executable Python defect, one file, complete requirements, deterministic behavioral validation. |

The selected repository was:

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
target: src/docwriter_web/writing_setup.py
source SHA-256: f6031119600919e4004c57c6229b7bd911f6befb9e67af04ce719da99f444a6f
source bytes: 5,109
```

The exact model-visible requirement was:

```text
Update from_form in src/docwriter_web/writing_setup.py so a nonblank custom clarification policy takes precedence over a selected standard clarification policy. Preserve the selected standard policy when the custom policy is blank.

Make no other functional change.
```

Repository-local authority was the existing custom-policy form contract in
`src/docwriter_web/app.py` and the operator-intent doctrine in
`docs/writing-setup-explicit-intent-design.md`. A read-only execution of the
original `from_form` returned the standard policy when both standard and custom
values were present, reproducing the defect before inference.

## Generation, validation, and entry

```text
session: work-task11n-ws-doc-writer-20260812T223509Z
session manifest SHA-256: 799da5affca0ae962ee1cbfe11bed4f833af346ab9ced2ff50cda1f1816a44da
fixture contract SHA-256: 30117a195509de858111fa34b0ea0912ea7a84b487555365e046b7f2a27e40ad
created/inherited turns: 0 / 0
turn limit: 8
requirements status: COMPLETE
read authority: src/docwriter_web/writing_setup.py
patch authority: src/docwriter_web/writing_setup.py
promotion authority: OPERATOR_ONLY
```

The frozen `INTERACTIVE_PRACTICAL_CODER_V3_PRODUCTION_ENVELOPE_V1` bound the
exact 14B artifact, `qwen25-coder-14b-katra-4096`, context 4096, GPU-only
placement, `WS_CODE_AGENT_REQUEST_PROTOCOL_V3_SINGLE_STRUCTURED_EDIT`, render
SHA-256 `d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993`,
`SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1 / v1`,
`SOURCE_GROUNDED_STRUCTURED_EDIT_V1`, and
`INTERACTIVE_BOUNDED_WORK_V1`.

The generation request supplied only `model`, `prompt`, and `stream=false`.
Seed, temperature, top-p, and top-k overrides were absent, and there were no
other generation overrides. The interpretation remains
`OBSERVED_REPRODUCIBILITY`; generation semantics were not changed.

The separately implemented contained validators were bound before inference:

```text
VISIBLE: task11n-ws-doc-writer-writing-setup-visible-v1 / v1
identity: 78a13296363dbb8c1c1ae55d4fadae50f459b225df7c5e6fe55dc0a7d109b773
source SHA-256: 407c910fafb1d9d379f8005194f1a3291840ead37176746fc1a1d505edb0c277
HIDDEN_ORACLE: task11n-ws-doc-writer-writing-setup-hidden-v1 / v1
identity: c4ae8b0953ff977f0c02690f767884fa6b2e985f13616ef1aeb370238ebce88a
source SHA-256: 8fd4937baedc7e9b017ee0817c26273eeaa39ca97f1855f8cf1135972903a253
containment required: true
repository writes allowed: false
```

The known-good implementation passed both checks. Five requirement-derived
negative cases failed both: the original defect, a wrong value, a partial raw
custom-value precedence fix that mishandles blank whitespace, an unrelated
code change, and a second changed path. The checks use different evaluation
structures and inputs. `CANDIDATE_SPECIFIC_OVERFIT_CHECK = PASS` and
`behavioral_diversity = PASS`.

Every entry gate passed: real local executable-code target, clean source and
remote parity, exact HEAD and snapshot, complete requirements, one repository,
explicit objective and authority, one writable path, both validators and their
calibration, exact frozen envelope/artifact/runtime/V3/normalizer/grounding
bindings, and operator-only promotion. The result was
`REAL_REPOSITORY_PILOT_ENTRY_ACCEPTED`.

## Fresh model turns

Both inferences completed with `done=true`, `done_reason=stop`, the exact model
artifact, context 4096, and 100% GPU / 0% CPU placement. Remote response hashes
matched locally retained raw evidence. Each response used the approved single
whole-response JSON-fence normalization.

### Turn 1: exact source grounding

```text
invocation: alpha-4bc9811f5b36-WORK-t0001-699b194864a6
gpu-compute job: job-20260812T223521Z-959877
raw bytes / SHA-256: 111 / 52e8ac1c57e067663fc7413e97e5fae584c5993c875e4e256a07dd97322cb01c
normalized bytes / SHA-256: 99 / 89ec472153194b28a87647df72e3a5fb9f618d13fcc8454664f6396ef7db6a16
normalization: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
request / parser: READ / PASS
authority / executor: AUTHORIZED / READ_FILE
grounding before/after: NOT_GROUNDED / SOURCE_GROUNDED
grounded path SHA-256: f7c3d62d6ec50b774392e52e9840c8fac3afac7cb2bebcc676d9541cdaa2b8af
file-content SHA-256: f6031119600919e4004c57c6229b7bd911f6befb9e67af04ce719da99f444a6f
grounding fact: 1ba7440985d30e7963b23bf062c2f90e8563433847e0c1aa424a0a48ad79fb8a
prompt / eval tokens: 685 / 36
load / prompt-eval / eval / total: 3.712360 / 0.241077 / 0.484839 / 4.442733 seconds
decode: 74.25 tokens/second
completion metadata SHA-256: d039616cc408da5e2879f635656db1dba37b16927b33c104723dfbb93d8955a2
```

The worker read the exact target first. No write-before-read denial occurred.

### Turn 2: bounded but incomplete semantic correction

```text
invocation: alpha-4bc9811f5b36-WORK-t0002-4f353a492d21
gpu-compute job: job-20260812T223531Z-960034
raw bytes / SHA-256: 394 / 2f205dde4a996c4215cd9f298196076a014b7a2f7edbad437bc09bdb554ba692
normalized bytes / SHA-256: 382 / 25be0726517c8a430fa6f670158f8c1a53b775cdc11e9711e824bbaef3d04904
normalization: SINGLE_MARKDOWN_JSON_FENCE_REMOVED
request / parser: PROPOSE_TEXT_REPLACEMENT / PASS
authority / executor: AUTHORIZED / STRUCTURED_EDIT_ACCEPTED
grounding before/after: SOURCE_GROUNDED / SOURCE_GROUNDED
exact match count: 1
policy after validation: ESCALATION_REQUIRED / VALIDATION_FAILED
prompt / eval tokens: 2,078 / 100
load / prompt-eval / eval / total: 0.189199 / 0.388735 / 1.386273 / 1.977397 seconds
decode: 72.14 tokens/second
completion metadata SHA-256: c7eb0625d56ece9346b5efec0c328d010dea21bbbdf186decb338cd905f8aa33
```

## Edit scope, candidate, and validation

The model-owned values were preserved exactly:

```text
path SHA-256: f7c3d62d6ec50b774392e52e9840c8fac3afac7cb2bebcc676d9541cdaa2b8af
old_text SHA-256: 5349a792ac23b25d486b16a549ac00adccda7945ff98a33574781aa5437ab26c
new_text SHA-256: 0df6ce924471dfb016c1734ce8b561794e6d86ad52cd65442dce9ea9c948d672
old_text bytes: 84
source bytes: 5,109
old_text/source fraction: 0.016442 (1.6442%)
OLD_TEXT_SCOPE: BOUNDED_TARGET_REGION
```

The evaluator did not alter the path, old text, or new text. It performed one
exact occurrence count, isolated replacement, changed-path observation,
canonical diff construction, and validation:

```text
structured request: 97c563c1d36b4b0c78d5a3175909768566c1dcf809d899feafb3097f9a012e12
before file: f6031119600919e4004c57c6229b7bd911f6befb9e67af04ce719da99f444a6f
after file: 7bb80f399845752fa899b9f59fd8c3c00ead1f603cd7be93ec1c77d583a5390c
candidate: b64d8a8b96fc1e92e846add8875c6c13d4d7aed7ea52503d7a104f65bf9670ab
candidate snapshot: 1782b42b3bdecb9ac71a635c168bf949362b77ca166899384d66531c2d14b6f0
changed paths: src/docwriter_web/writing_setup.py only
canonical diff: 71c71cb0dc84088abc4e750a5e98b62a224bee183dba4cea89d97534c2ba5470
canonical diff origin: evaluator
candidate integrity: MATCH
Source Snapshot X: MATCH
```

The model changed raw field precedence to choose a truthy custom form value
before the standard value. That satisfies the nonblank case, but whitespace is
truthy before `_clean`; a blank custom value containing whitespace is selected,
then cleaned to empty, instead of preserving the selected standard policy. The
pre-bound visible validator therefore returned a genuine contract failure:

```text
visible descriptor: task11n-ws-doc-writer-writing-setup-visible-v1 / v1
visible result: VALIDATION_FAIL
visible evidence identity: 3dac4eb7d3d236ed5bd5c2b4a51cb9c3d8eb321f78249bf5b92e6df4db1c42fe
containment result: completed
candidate repository effect: unchanged during validation
hidden result: NOT_RUN
technical correctness: FAILED
final state: ESCALATION_REQUIRED
reason: VALIDATION_FAILED
handoff packet SHA-256: ea6dcafada21faae1b4034ef9841e8e7c8beb9ef051dd15bcd40ec2b523f2881
```

Hidden validation did not run because visible validation failed. This was a
scoreable model semantic failure, not validation infrastructure failure. The
frozen envelope authorizes no validation-repair turn. The turn hash chain
passed, duplicate inference was zero, automatic handoff was false, and
automatic promotion was false.

## Source integrity, performance, and health

The authoritative `ws-doc-writer` checkout remained exact throughout:

```text
HEAD: d52c923d4a13949a2345fb5791ee59a82d389c4e
Source Snapshot X: 6a4a913f0258a0e35c812d147ee2a5e4b1830684bfae56978e41911202d82047
index identity: 96c5ca9f06bc21817c4de1a3ac9430b7dae760322bc316077643d3b27994d0d4
tracked-worktree identity: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
untracked identity: 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
target SHA-256: f6031119600919e4004c57c6229b7bd911f6befb9e67af04ce719da99f444a6f
```

Cold load was 3.712 seconds and cold total was 4.443 seconds. The warm turn
total was 1.977 seconds. Decode rates were 74.25 and 72.14 tokens/second. Peak
observed VRAM was 9,312 MiB. Placement remained 100% GPU / 0% CPU at context
4096.

Ollama remained active and enabled, host memory remained healthy without swap,
failed units were absent, and no OOM, NVIDIA XID, or CUDA-fatal evidence was
observed. Ordinary unload succeeded and VRAM returned to 2 MiB used.

```text
Task 11N 14B inference count: 2
Task 11N 32B inference count: 0
duplicate inference: 0
automatic handoff: false
automatic promotion: false
```

## Capability matrix and disposition

| Task | Surface | Result | Edit scope |
|---|---|---|---|
| 11L | real documentation | FAIL | WHOLE_FILE |
| 11M | real state documentation | PASS | BOUNDED_TARGET_REGION |
| 11N | real executable code | FAIL | BOUNDED_TARGET_REGION |

Task 11N shows that source grounding and bounded edit selection can work on a
real executable source file while the semantic change still fails its complete
behavioral contract. It neither reopens V3 nor establishes broad capability.
The exact failure class is retained for later role-boundary analysis.

The frozen envelope, V3 protocol and render, normalizer, grounding, structured
executor, repair limits, semantic authority, and operator-only promotion
boundary remained unchanged. There was no fabricated work, special hint,
validation repair, semantic adapter, authority broadening, overnight-coder
invocation, historical rescore, or source promotion.

Disposition:

```text
DISTINCT_REAL_CODE_INTERACTIVE_PILOT_ESCALATED
reason: VALIDATION_FAILED
```

The Task 11L, Task 11M, and Task 11N evidence returns to the operator. This
checkpoint makes no protocol or authority change.
