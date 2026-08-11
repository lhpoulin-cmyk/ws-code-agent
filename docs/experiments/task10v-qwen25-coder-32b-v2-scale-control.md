# Task 10V Qwen2.5-Coder 32B frozen V2 scale control

Date: 2026-08-11

Play: `Darmok`

Checkpoint: `TASK10V-QWEN25-CODER-32B-FROZEN-V2-SCALE-CONTROL`

This run is the behavioral half of the Qwen2.5-Coder intra-family scale
control. It used fresh independent write and clarification sessions. The 14B
historical result remains unchanged. No output normalization, repair, retry,
prompt hint, sampling change, context change, runtime change, or automatic
promotion occurred.

## Foundation and preflight

The clean, direct-origin-parity starting checkpoints were:

```text
ws-code-agent: 6f7e498bfb12235de88f810bceb7cb1c2dc85625
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
```

Before inference, ws-code-agent passed all 130 tests, the separate two-test
private-material check, containment, lineage, invariant-register, YAML, and
diff gates. All eight gpu-compute suites passed.

The live preflight matched the exact installed manifest and 19,851,336,384-byte
model blob, patched Ollama identity, deployed profile file SHA-256
`2c2a0637f9e8e169e9e3fe0e0ce320e3ce82d01bb33418ad6aabfb3e1a0d02c5`,
and accepted `qwen25-coder-32b-katra-4096` policy. The service and GPU were
healthy, no model was loaded, and no existing OOM, CUDA, XID, or host-pressure
condition was present.

```text
ARTIFACT_BINDING = PASS
RUNTIME_BINDING = PASS
PROFILE_BINDING = PASS
ADMISSION_SELECTOR_32B = PASS
FROZEN_V2 = PASS
FROZEN_FIXTURES = PASS
```

## Exact frozen contract

```text
candidate: qwen25-coder-32b-q4
tag: qwen2.5-coder:32b-instruct-q4_K_M
manifest: b92d6a0bd47ee79114298de0177bf920c05a706d12633950b3936778492bef41
model blob: ac3d1ba8aa77755dab3806d9024e9c385ea0d5b412d6bdf9157f8a4a7e9fc0d9
quantization: Q4_K_M
profile: qwen25-coder-32b-katra-4096
execution: GPU_PRIMARY_PARTIAL_OFFLOAD
processor envelope: GPU >= 71%; CPU <= 29%
context: 4096
protocol: WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE
render SHA-256: 3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e
write fixture: task10k-c-write/synthetic-v1
write fixture identity: db9efb27f7f56da8a0f295e3ef0e656271264ac08ec977da578f2e6e020bb2b6
clarification fixture: task10k-c-clarification/synthetic-v1
clarification fixture identity: b0f5cdd341a2eb491ddcd9f02253563cbc0a44d79eccf86b3a3519cfdb13b3ba
turn budget: maximum 8 per independent session
```

Ollama remained `0.32.0+helix.repeatlimit.1`, binary SHA-256
`b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143`,
build ID `ffd1f9f6c8ffd69fdca1316e7c032447479fe139`. Task 10U's structural evidence
still binds the 14B and 32B first-turn renderer to identical 2,898-byte prompt
representations, SHA-256
`7741cba74e06a0aa2858584e669d1daed65210d537a07218667a7f4e10b9bc49`.

## Write session

Session:
`work-task10v-qwen25-32b-write-20260811T203928Z`

Fixture repository HEAD:
`c89aaeba6f1e39612ed33e8f09b22e67a74f55af`

Source Snapshot X:
`7928a6d92f5b9daf43d0311c5d596eb0c331bd04fdc9c8b5c5122aec76652cc7`

Read authority was `.` and patch authority was exactly `src/message.py`. The
fresh session consumed two turns and stopped at its first terminal candidate.

| Field | Turn 1 | Turn 2 |
| --- | --- | --- |
| Invocation | `alpha-044745c2bdae-WORK-t0001-2a0b1f89a966` | `alpha-044745c2bdae-WORK-t0002-751855eea116` |
| gpu-compute job | `job-20260811T203942Z-949587` | `job-20260811T204146Z-950492` |
| Prompt SHA-256 | `cbeb1f69a35626ac9da93adf97dacd83125bf5d1fe0bb9d8c1580ec55d1278a5` | `8c503e237f57a3868b31636be9fdbe22221d7d2248c4ae987cd1e9c5eb1dfccf` |
| Request / parser | bare JSON `PROPOSE_PATCH`; valid | bare JSON `PROPOSE_PATCH`; valid |
| Executor | `PATCH_REJECTED`: corrupt patch at line 7 | `SUCCESS`; `CANDIDATE_READY` |
| HTTP / terminal | 200; `done=true`, `stop` | 200; `done=true`, `stop` |
| Prompt/eval tokens | 764 / 105 | 821 / 76 |
| Load | 36.680104156 s | 0.212236253 s |
| Prompt eval | 1.826322000 s | 0.627808000 s |
| Eval | 67.361884999 s | 48.648314000 s |
| Total | 105.883876233 s | 49.493467341 s |
| Raw bytes / SHA-256 | 293 / `66c8b6cc053a15c782e579db4d18cdc22fa315d80592c968f6332b91bf7c1ba3` | 247 / `7664074a04d9d18008d9eae6452c85c3ea87777feb6a9dfe2ee21fbcb129d7d7` |
| Completion metadata SHA-256 | `e0b28f71edd0d9f6a52536038b4cada1197594228c8e82d990e6bd19b6628c18` | `3aead2b6e5b9fe3e25d1b7af5e38af8fb36660ab26d4a624fdabc813fc563a7d` |
| Runtime | 71% GPU / 29% CPU; context 4096 | 71% GPU / 29% CPU; context 4096 |

Turn 1's request was protocol-valid and authority-correct, but the proposed
new-file diff included a malformed index form and `git apply` rejected it. The
existing frozen executor-feedback loop made that rejection model-visible in
turn 2. This was ordinary forward session progression, not a retried inference.

Turn 2 supplied a valid patch creating exactly:

```python
def message(): return "hello"
```

The executor accepted it in isolation. The changed-path set was exactly
`src/message.py`; candidate identity was
`356abfda8bf041701e01e732156e47b9f49dc62953be360325a3f7e3d729feb0`;
candidate integrity and Source Snapshot X both matched. The authoritative
fixture repository remained unchanged.

The model and executor therefore demonstrated the intended write behavior,
but the frozen supervised lane reports `VALIDATION_NOT_CONFIGURED`. Its active
doctrine explicitly says isolated application is not technical correctness and
requires a separately approved, registry-owned validation descriptor. No such
visible or hidden validator exists for this fixture. Task 10V required both
visible and hidden validation to pass, so the write result cannot truthfully be
scored `WRITE_PASS`; treating the apparatus gap as a model `WRITE_FAIL` would
also be incorrect.

```text
WRITE = NOT_SCORED
model behavior = BARE_JSON_CANDIDATE_READY_AFTER_PATCH_REPAIR
infrastructure blocker = VALIDATION_NOT_CONFIGURED
```

## Clarification session

Session:
`work-task10v-qwen25-32b-clarification-20260811T204600Z`

Fixture repository HEAD:
`e6c3acf410be36895d21149a7def1069dec37cb2`

Source Snapshot X:
`8dbe44d5e2f7eef87c3622ac830046fc1605d1ab2660347fd1878ed831aef90a`

The independent session had read authority for `.` and no patch authority. It
consumed one turn and stopped immediately at the required durable pause.

| Field | Turn 1 evidence |
| --- | --- |
| Invocation | `alpha-0dd1cc3aa23c-WORK-t0001-20f2c25006b0` |
| gpu-compute job | `job-20260811T204417Z-951123` |
| Prompt SHA-256 | `d0a123a4ad5a51e281cd141d71eece94c0007eee64ddc7f587e9b2515d18a717` |
| Request / parser | bare JSON `REQUEST_CLARIFICATION`; valid |
| Executor | no executor action; durable clarification recorded |
| HTTP / terminal | 200; `done=true`, `stop` |
| Prompt/eval tokens | 747 / 34 |
| Load | 0.197314248 s |
| Prompt eval | 0.806113000 s |
| Eval | 21.056875000 s |
| Total | 22.065863435 s |
| Raw bytes / SHA-256 | 168 / `55ccaa45aa97da74467abab4345271e786b09327aad71103782f029ce5e95813` |
| Completion metadata SHA-256 | `a6afe66bd7f12a7f375ef9f171682075e1374aa69f88b5a676eaeee3e5e6a8d1` |
| Runtime | 71% GPU / 29% CPU; context 4096 |

The exact evaluator-side question was:

> Could you please provide an example of how the release label should be
> formatted based on the title?

It materially addresses the fixture's unresolved representation. No mutation
request, candidate, or unauthorized effect exists, and the source remained
unchanged.

```text
CLARIFICATION_PASS
```

## Integrity and health

All three local raw-response hashes matched their remote invocation response
files, and each completion metadata hash matched independently. Both session
hash chains passed, all invocation IDs were unique, and duplicate inference was
zero. The canonical invocation-directory count increased from 111 to 114,
exactly matching the three model turns. Every job bound the exact manifest,
profile, quantization, 71% GPU / 29% CPU placement, and effective context 4096.

The loaded admission observation used 14,664 MiB VRAM and retained at least
14,119,399,424 bytes of available host RAM, with no swap. Post-run Ollama was
active and enabled, the GPU was healthy, no failed units existed, and there was
no OOM, CUDA-fatal, XID, panic, or fatal service evidence. The authorized
ordinary `ollama stop` control request unloaded the retained model; it was not
a model inference or admission turn. The final state had no loaded model, 2 MiB
VRAM in use, 14,762,483,712 bytes host RAM available, and 43,292,192,768
bytes free on the filesystem containing the retained model store. The exact
32B artifact remained installed.

## Same-family comparison

| Dimension | 14B fixed result | 32B observed result |
| --- | --- | --- |
| Protocol envelope | Markdown-fenced on both turns; both malformed | Bare parser-valid JSON on all three turns |
| Write judgment | Plausible authorized patch, never executed | Correct authorized intent; repaired rejected diff; isolated candidate ready |
| Clarification judgment | `NO_CHANGE` instead of clarification | Materially relevant `REQUEST_CLARIFICATION` |
| Turn progression | One terminal malformed turn per fixture | Write progressed two turns; clarification stopped correctly on turn 1 |
| Runtime residency | 100% GPU / 0% CPU | 71% GPU / 29% CPU |

This one fixture pair is consistent with scale improving both strict protocol
compliance and clarification judgment inside the byte-identical Qwen2.5-Coder
artifact interface. It does not prove causality or establish a general quality
ranking. The 14B practical full-GPU baseline and its historical scores remain
unchanged.

## Validation closeout

After recording this result, ws-code-agent again passed all 130 tests, the
separate two-test private-material check, containment, lineage,
invariant-register, YAML, and diff gates. The protected parser/executor source
set had no diff. All eight gpu-compute suites passed, and neither peer
repository changed.

## Disposition

The clarification behavior passed, and the write behavior reached an isolated
authority-valid candidate. The missing approved validation descriptor prevents
the all-required write gate from being evaluated faithfully. This is an
apparatus gap, not normal bad model behavior, so the candidate receives neither
production admission nor a scoreable production-admission failure.

```text
TASK10V_ADMISSION_INCONCLUSIVE_INFRASTRUCTURE
production_admission = INCONCLUSIVE_INFRASTRUCTURE
NEXT: APPROVE AND BIND VISIBLE/HIDDEN VALIDATION FOR THE FROZEN WRITE FIXTURE WITHOUT RESCORING MODEL BEHAVIOR
```

The run used fresh independent sessions, zero inherited turns, the same frozen
V2 and fixtures, the same model-visible renderer, no more than eight turns per
session, and no retry, tuning, hint, Markdown normalization, JSON repair,
context change, Ollama change, 14B rescore, automatic promotion, or authority
broadening.
