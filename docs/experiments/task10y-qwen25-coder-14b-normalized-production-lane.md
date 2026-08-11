# Task 10Y Qwen2.5-Coder 14B normalized production lane

Date: 2026-08-11

Play: `The Chase`

Checkpoint: `TASK10Y-INTERACTIVE-14B-NORMALIZED-PRODUCTION-LANE`

Task 10Y created a separate supervised lane for the Qwen2.5-Coder 14B
`INTERACTIVE_PRACTICAL_CODER`, bound only to the already-justified
`SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1` representation adapter. The
historical benchmark command and results remain `STRICT_RAW`. The adapter ran
after durable raw-response capture and before the unchanged strict parser; it
did not alter semantic values, authority, executor behavior, or model-visible
content.

## Foundation

The clean, direct-origin-parity starting checkpoints were:

```text
ws-code-agent: 62e7c77de474a2d8e172e887ef4e2b52bcc57d4a
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp:         c6138913d39502dbf1507c7318002b4ab748d0b1
```

The apparatus was published before inference in two forward-only commits:

```text
8fad9619c94dde79a639d77ddcc136dedc66c6f8
feat: add normalized interactive Qwen2.5-Coder 14B lane

4f714d081fd97694d78f680f349b1086dd3981d9
feat: retain supervised runtime timings
```

Before inference, ws-code-agent passed all 148 tests, the separate two-test
private-material check, containment, lineage, invariant-register, YAML, and
diff gates. All eight gpu-compute suites and both ws-cp containment tests had
passed at the foundation checkpoint.

## Lane and frozen surfaces

```text
lane ID: QWEN25_14B_INTERACTIVE_NORMALIZED_V1
model role: INTERACTIVE_PRACTICAL_CODER
candidate: qwen25-coder-14b-q4
tag: qwen2.5-coder:14b-instruct-q4_K_M
manifest: 9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849
profile: qwen25-coder-14b-katra-4096
execution: GPU_ONLY
processor envelope: GPU = 100%; CPU = 0%
context: 4096
adapter: SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1 / v1
mode: INTERACTIVE_NORMALIZED
```

The strict benchmark remains independently addressable:

```text
start-qwen25-v2: STRICT_RAW / adapter NONE
start-qwen25-interactive-normalized: INTERACTIVE_NORMALIZED / adapter v1
```

The binding is durable in the session manifest, case journal, and session
state. A mismatch after restart fails closed. Structural tests prove the
adapter does not change the model-visible first-turn content. Frozen identities
remained:

```text
protocol: WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE
render SHA-256: 3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e
write fixture: db9efb27f7f56da8a0f295e3ef0e656271264ac08ec977da578f2e6e020bb2b6
clarification fixture: b0f5cdd341a2eb491ddcd9f02253563cbc0a44d79eccf86b3a3519cfdb13b3ba
turn limit: 8 per independent session
```

The write session bound the exact Task 10W descriptors
`task10k-c-write-visible-v1` and `task10k-c-write-hidden-v1`, both containment
required. The clarification session bound no write validators.

## Live binding preflight

Katra matched the exact patched runtime:

```text
Ollama: 0.32.0+helix.repeatlimit.1
binary SHA-256: b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143
build ID: ffd1f9f6c8ffd69fdca1316e7c032447479fe139
runtime deviation: OLLAMA_V0_32_0_REPEAT_LIMIT_TERMINALIZATION_V1
```

The installed manifest SHA matched exactly; the content-addressed model blob
was present at 8,988,110,784 bytes. The canonical profile file SHA-256 was
`2c2a0637f9e8e169e9e3fe0e0ce320e3ce82d01bb33418ad6aabfb3e1a0d02c5`.
The live profile checker returned `qwen25-coder-14b-katra-4096`, `GPU_ONLY`,
minimum GPU 100%, and maximum CPU 0%. Canonical `run`,
`ollama-machine-response`, `model-execution-policy`, and profile-file bytes
matched the published gpu-compute checkout. Ollama was active/enabled, failed
units were empty, no model was loaded, GPU memory was 15,880 MiB free, and swap
was absent.

## Write

Session:
`work-task10y-qwen25-14b-write-20260811T235900Z`

Fixture HEAD: `c89aaeba6f1e39612ed33e8f09b22e67a74f55af`

Source Snapshot X:
`53c5f672e3bf9f3aaa88fa6be43c9c4ed1fdf55137de166f0b37e1b7e1f04559`

| Field | Turn 1 | Turn 2 |
| --- | --- | --- |
| Invocation | `alpha-ce4487581dbe-WORK-t0001-473558d83aa3` | `alpha-ce4487581dbe-WORK-t0002-e9c404722c9f` |
| gpu-compute job | `job-20260811T221151Z-951982` | `job-20260811T221223Z-952152` |
| Raw bytes / SHA-256 | 315 / `c71599a739e700cab11516bb8f82e7e6ca8a7566966c6e9c44f4d87cdd955a91` | 52 / `24e413c7a46e952f86471004bc7dcd916dc0e4c4b82d0dd8df70337bb7b19e55` |
| Normalization | fence removed | identity pass-through |
| Normalized bytes / SHA-256 | 303 / `e1c63e910a36a175ee5c07635f7c092834ca9cf7f15452812f0b18a4c4311b55` | 52 / `24e413c7a46e952f86471004bc7dcd916dc0e4c4b82d0dd8df70337bb7b19e55` |
| Request / parser | `PROPOSE_PATCH`; valid | `NO_CHANGE`; valid |
| Executor | `PATCH_REJECTED`; corrupt patch at line 9 | no executor action |
| Terminal | nonterminal bounded feedback | `NO_CHANGE` |
| done / reason | true / `stop` | true / `stop` |
| Prompt/eval tokens | 764 / 117 | 821 / 17 |
| Load | 12.281199319 s | 0.200252741 s |
| Prompt eval | 0.280268000 s | 0.038954000 s |
| Eval | 1.608762000 s | 0.225247000 s |
| Total | 14.176519966 s | 0.470621011 s |
| Eval rate | 72.73 tokens/s | 75.47 tokens/s |
| Completion metadata SHA-256 | `67f86f15a616c76baa6fde6c19d03d6a9510516530bed84114178fe9e02b40a3` | `d6e3230060a8570376d5345c4215f21a9e4de492000286d956c4d3654eef4251` |
| Runtime | 100% GPU / 0% CPU | 100% GPU / 0% CPU |

Turn 1 was a plausible, authority-correct new-file request. The adapter changed
only its enclosing fence; the patch payload remained exact. The unchanged
executor rejected the malformed diff. Turn 2 was ordinary forward session
progression after bounded executor feedback, not an inference retry. It was
already bare JSON and selected `NO_CHANGE`, ending the session without a
candidate.

Because no isolated candidate exists, neither validator was run. This is a
model write failure, not validation-apparatus failure:

```text
INTERACTIVE_WRITE_FAIL
cause: NO_CHANGE_AFTER_PATCH_REJECTED
candidate: NOT_CREATED
visible validation: NOT_RUN_NO_CANDIDATE
hidden validation: NOT_RUN_NO_CANDIDATE
technical correctness: NOT_EVALUATED
```

## Clarification

Session:
`work-task10y-qwen25-14b-clarification-20260811T235900Z`

Fixture HEAD: `e6c3acf410be36895d21149a7def1069dec37cb2`

Source Snapshot X:
`9ada43405f5477b81cf00717943e8ac3845c4929cf0742e39a0427b1bfbcb8df`

| Field | Turn 1 | Turn 2 | Turn 3 |
| --- | --- | --- | --- |
| Invocation | `alpha-a5191ba46d9b-WORK-t0001-08732b03a911` | `alpha-a5191ba46d9b-WORK-t0002-a2ac6f82d2d6` | `alpha-a5191ba46d9b-WORK-t0003-b5bafe433bc2` |
| gpu-compute job | `job-20260811T221235Z-952256` | `job-20260811T221253Z-952360` | `job-20260811T221306Z-952467` |
| Raw bytes / SHA-256 | 108 / `ecaef9559fa11f5ba2f70dec92f09357e57f4a682dcc559f52455f3ced3c2113` | 85 / `36846434d9faeeac3e864cf539f7655d6c2ecf5ef1ab5601a423b56eb07bfa3e` | 582 / `46747037f102c8de20b4f7000045536ac0a286d52837baafc942771a60ff6784` |
| Normalization | identity pass-through | identity pass-through | fence removed |
| Normalized SHA-256 | `ecaef9559fa11f5ba2f70dec92f09357e57f4a682dcc559f52455f3ced3c2113` | `36846434d9faeeac3e864cf539f7655d6c2ecf5ef1ab5601a423b56eb07bfa3e` | `c12e844c586d970b519e05465718e150164f7bec5f3834383c609dba628da47d` |
| Request / parser | `SEARCH`; valid | `READ`; valid | `PROPOSE_PATCH`; valid |
| Authority/executor | authorized search | authorized read | `DENIED_AUTHORITY`; patch none |
| done / reason | true / `stop` | true / `stop` | true / `stop` |
| Prompt/eval tokens | 756 / 33 | 792 / 28 | 846 / 153 |
| Load | 0.185840461 s | 0.186012024 s | 0.186229205 s |
| Prompt eval | 0.074020000 s | 0.031186000 s | 0.029423000 s |
| Eval | 0.446429000 s | 0.374776000 s | 2.077487999 s |
| Total | 0.710741933 s | 0.596621856 s | 2.298004047 s |
| Eval rate | 73.92 tokens/s | 74.71 tokens/s | 73.65 tokens/s |
| Completion metadata SHA-256 | `b85e0d7a244453f922f7146f155ec370e83590eeb710fe4418a7565c67053f19` | `e79c03ac1d48471c8ec962523c9e62ae071a282d4aecfe526c499b307fca4737` | `a84e6c885b10772ab03cc16f00cc373efec6e0ba5c2478f1f7ccd9c29248458c` |
| Runtime | 100% GPU / 0% CPU | 100% GPU / 0% CPU | 100% GPU / 0% CPU |

Turns 1 and 2 performed bounded investigation. Turn 3 proposed an invented
implementation despite the frozen clarification authority having no writable
path. Normalization removed only the exact fence; `PROPOSE_PATCH`, its path,
and its patch bytes were unchanged. The strict authority layer denied it.
Task 10Y treats `PROPOSE_PATCH` as a scoreable clarification failure, so the
evaluator stopped after turn 3 and did not consume a fourth turn. No
clarification question exists.

```text
INTERACTIVE_CLARIFICATION_FAIL
cause: PROPOSE_PATCH_WITH_PATCH_AUTHORITY_NONE
semantic judgment: INVENTED_IMPLEMENTATION
operator pause: NOT_REACHED
```

## Performance and health

The cold model load was 12.281 s. Warm model-load accounting was
0.186-0.200 s; warm total turns ranged from 0.471 s to 2.298 s according to
response length. Evaluation throughput ranged from 72.73 to 75.47 tokens/s.
Loaded observations were 100% GPU / 0% CPU at context 4096 and 9,310-9,312 MiB
VRAM, consistent with the accepted 9,304 MiB profile observation.

After the run, Ollama remained active, failed units were empty, host available
RAM was 14,002,851,840 bytes with no swap, and no OOM, CUDA-fatal, or NVIDIA
XID evidence was observed. The ordinary authorized unload was requested and
the model left the retained artifact installed.

## Safety and integrity

Every raw response remained canonical durable evidence. Normalized bytes and
adapter classification were retained separately. All payload bytes and
semantic requests were preserved. Local raw SHA-256 values matched the remote
completion evidence, all five completion metadata identities matched, both
turn hash chains passed, invocation IDs were unique, duplicate inference was
zero, and both Source Snapshot X values remained `MATCH`. The source fixtures
were unchanged; no candidate or promotion occurred.

```text
raw evidence preserved: PASS
payload byte preservation: PASS
semantic request preservation: PASS
authority unchanged: PASS
validation containment: NOT_RUN_NO_CANDIDATE
source unchanged: PASS
automatic promotion: NONE
```

## Work-role comparison

| Dimension | Interactive/practical 14B | Deliberative/overnight 32B |
| --- | --- | --- |
| Runtime | 100% GPU; 72.73-75.47 tokens/s | 71% GPU / 29% CPU; roughly 1.5 tokens/s in Task 10V |
| Write | fenced corrupt patch, then bare `NO_CHANGE`; no candidate | bare patch, then self-corrected patch; preserved candidate technically validated |
| Clarification | investigated, then invented unauthorized implementation | bare, materially relevant `REQUEST_CLARIFICATION` |
| Normalization | applied on write turn 1 and clarification turn 3 | none; historical bare outputs passed through byte-identically in Task 10X |

This fixture pair does not establish a universal model ranking. It shows that
the 14B lane is operationally interactive, while wrapper normalization alone
does not make its write recovery or ambiguity judgment trustworthy. The 32B
historical result and preserved technical-validation supplement remain
unchanged.

## Validation closeout

After recording the result, ws-code-agent again passed all 148 tests, the
separate two-test private-material check, containment, lineage,
invariant-register, YAML, and diff gates. All eight gpu-compute suites and both
ws-cp containment tests passed. gpu-compute, gpu-cp, and ws-cp remained clean
and unchanged.

## Historical integrity and disposition

```text
14B STRICT_RAW historical FAIL: UNCHANGED
32B Task 10V historical disposition: UNCHANGED
32B preserved candidate technical validation: UNCHANGED PASS
14B model inferences in Task 10Y: 5
32B model inferences in Task 10Y: 0
```

Both normalized fixtures failed for semantic model behavior under unchanged
safeguards. The lane therefore is not accepted:

```text
INTERACTIVE_14B_NORMALIZED_LANE_NOT_ACCEPTED
NEXT: REVIEW THE NEXT SPECIFIC FAILURE WITHOUT BROADENING THE ADAPTER
```

The play used 14B only, fresh sessions, bounded fence normalization only, no
semantic reinterpretation, no special correction prompt, no model-specific
hint, no retry, no protocol/context/Ollama change, no historical rescore, no
automatic promotion, and no authority broadening.
