# Task 11K real-pilot validation apparatus repair

Date: 2026-08-12

Play: `The Drumhead`

Checkpoint: `TASK11K-REPAIR-REAL-PILOT-VALIDATION-APPARATUS`

## Foundation and preserved evidence

Task 11K started from clean direct-origin parity at:

```text
ws-code-agent: 1df1d10452c56a9f088d735bd335c018945b0fc0
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp:         a1688be4535fb52237d62a58819ac69685e4478a
ws-doc-writer: d52c923d4a13949a2345fb5791ee59a82d389c4e
```

Before mutation, the preserved Task 11J session and source were reverified:

```text
session: work-task11j-ws-doc-writer-20260812T194000Z
source HEAD: d52c923d4a13949a2345fb5791ee59a82d389c4e
Source Snapshot X: 6a4a913f0258a0e35c812d147ee2a5e4b1830684bfae56978e41911202d82047
structured request: d61bdeab9a2dc4e24bc392371cb0499cf4b9dcdae2e9f4993d3835e3be43874a
candidate: 8bd0a654963314f0f4850fee710c2053180b2419d5e80a191bdee8886ffb4910
candidate snapshot: 6ea5c1a2f5e8bba35dfbcbdfaddcffdfba269f73e5a3e39cd85ed47dccfd791e
before README: a52645c6f822f7a4a845ed971e4bab7de70898997c1e195d90e26dd331eee970
after README: 664c835405b0e130c094573c359b6d0a3dd4f1d2d009488f023484f159ab6eb2
canonical diff: 6944e1313c86f56b25a2c9dabe3919ace3ece976659ae9558614d3a973cd4755
```

All identities matched. The validation state was
`VISIBLE_VALIDATION_STARTED / VALIDATION_PENDING`; visible and hidden results
were null and no evaluator validation evidence file existed. This confirms the
Task 11J exception occurred before descriptor execution.

## Defect 1: session-bound validation routing

The historical implementation selected the module constants
`task10k-c-write-visible-v1` and `task10k-c-write-hidden-v1` for every session.
The repaired implementation first verifies the complete trusted validation
contract against the registry, then resolves exactly one `VISIBLE` and one
`HIDDEN_ORACLE` descriptor from the immutable session binding. There is no
fallback to Task 10 identifiers.

The Task 11J bindings remain byte-identical to their pre-inference state:

```text
visible ID: task11j-ws-doc-writer-src-readme-visible-v1
visible version: v1
visible identity: 4f2f865bf1734b1117a5fc56eeb046b87e244b2bb5f0c35a1e20ba00a453550a
visible source SHA-256: fcc09165982a520b264fe880635d9fc2eac9ca3fcd020b90e77b4440c344b315

hidden ID: task11j-ws-doc-writer-src-readme-hidden-v1
hidden version: v1
hidden identity: e172f6ae72baadc989d0440ab331a3fcfb04a2a977368bd6e695704b1d76dd3f
hidden source SHA-256: f5bd302451767c7102396183be6f0ae5dad8d0120d53e7ba8338b2b0f5eb3155
```

Missing, unknown, duplicate-role, wrong-version, wrong-identity, changed
containment, or changed repository-write bindings fail closed as
`VALIDATION_DESCRIPTOR_BINDING_MISMATCH`. Focused tests proved that a Task 11J
contract selects the Task 11J pair in order across a controller restart.

The existing ambiguous-start doctrine remains fail-closed. Task 11K added a
separate operator-invoked pre-execution recovery operation. It requires the
exact candidate and descriptor identities, current source and candidate
integrity, a pending `*_VALIDATION_STARTED` state, null result state, and no
evaluator evidence file. It emits a one-shot durable recovery record and
refuses any existing evidence or repeated recovery.

## Defect 2: publication-tree hygiene

The original invariant prohibited inherited Doc Writer runtime identity by
scanning `git ls-files`. It conflated the Task 11J external pilot-target record
with active runtime inheritance and could not see a new untracked publication
candidate before commit.

The repaired gate inventories the deterministic union of tracked and
not-ignored untracked publication candidates. Its exception is narrow:

- the exact Task 11J manifest must retain its schema version, checkpoint,
  canonical external path, origin, and owning-domain authority;
- marker values remain forbidden in active runtime, backend, model, executor,
  worker, provider, package, and implementation authority fields;
- only exact Task 11J validator/calibration surfaces and the exact historical
  record are classified as external-target evidence.

Positive controls pass the frozen external repository, HEAD, Source Snapshot
X, and owning-authority record. Negative controls still reject runtime backend,
model provider, executor dependency, production-worker authority, active
package import, and inherited application implementation. A temporary Git
control proves the gate sees and rejects an untracked publication candidate
before commit.

## Frozen surfaces and publication gate

No peer repository mutation was required. The repair was committed and pushed
before validation resumed:

```text
repair commit: f6d2fe5524806c096ab2c66833f09328057ee455
commit subject: fix: resolve pilot validators from bound session contract
```

The published hard gate passed:

```text
ws-code-agent: 216 tests PASS
private-material: 2 PASS
focused validator routing/restart/fail-closed controls: PASS
publication-tree hygiene controls: PASS
Task 11J contained validator calibration: PASS
containment: PASS
lineage: PASS
invariant register: PASS
YAML: PASS
diff: PASS
gpu-compute: 8 suites PASS
ws-cp containment: 3 PASS
```

Frozen hashes remained:

```text
V3: d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993
V2: 3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e
```

The normalizer, grounding, structured executor, semantic authority, read/patch
authority, repair limits, envelope, validators, and Task 11J turns were not
changed.

## Zero-inference validation resume

The explicit recovery record bound:

```text
prior phase: VISIBLE_VALIDATION_STARTED
recovered phase: NOT_STARTED
candidate snapshot: 6ea5c1a2f5e8bba35dfbcbdfaddcffdfba269f73e5a3e39cd85ed47dccfd791e
visible descriptor: task11j-ws-doc-writer-src-readme-visible-v1
visible identity: 4f2f865bf1734b1117a5fc56eeb046b87e244b2bb5f0c35a1e20ba00a453550a
evaluator evidence present before recovery: false
recovery record SHA-256: de74905b702d11cdc05569aade9f8231f907d8236a3e637bbb021439a1c57098
```

The exact bound visible validator then ran under the original fixed systemd
containment:

```text
descriptor: task11j-ws-doc-writer-src-readme-visible-v1 / v1
descriptor identity: 4f2f865bf1734b1117a5fc56eeb046b87e244b2bb5f0c35a1e20ba00a453550a
status: VALIDATION_FAIL
exit code: 1
evidence identity: 2d5c06896f19fe24ede36635aef29c75cd05a7c91c8ff27b9d132562d8f1ee18
evidence-file SHA-256: 62c79ca8955e60491b45710a899ed2864bfc500dee969293053a5613c4453b24
result snapshot before: a271756d31aafcfdca4f39d39edfd0c8ab39701d9728c3001e51ddf31d10b00e
result snapshot after:  a271756d31aafcfdca4f39d39edfd0c8ab39701d9728c3001e51ddf31d10b00e
containment profile: task11j-systemd-v1
```

The candidate and validation snapshot were unchanged by the validator. Under
the existing validation doctrine, visible failure made the state terminal;
the hidden validator did not run. No human correctness assignment was used.

Final preserved-candidate state:

```text
visible validation: VISIBLE_VALIDATION_FAIL
hidden validation: NOT_RUN
technical correctness: FAILED
candidate integrity: MATCH
Source Snapshot X: MATCH
policy: ESCALATION_REQUIRED / VALIDATION_FAILED
automatic handoff: false
automatic promotion: false
```

## Source and historical integrity

The authoritative ws-doc-writer checkout remained exact throughout:

```text
HEAD: d52c923d4a13949a2345fb5791ee59a82d389c4e
Source Snapshot X: 6a4a913f0258a0e35c812d147ee2a5e4b1830684bfae56978e41911202d82047
index: 96c5ca9f06bc21817c4de1a3ac9430b7dae760322bc316077643d3b27994d0d4
tracked worktree: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
untracked inventory: 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945
README SHA-256: a52645c6f822f7a4a845ed971e4bab7de70898997c1e195d90e26dd331eee970
```

No source promotion, commit, or push occurred. Task 11J remains historically
`TASK11J_REAL_LOCAL_REPOSITORY_PILOT_INFRASTRUCTURE_BLOCKED`. Tasks 11F through
11I and the frozen envelope remain unchanged.

```text
Task 11K 14B inference: 0
Task 11K 32B inference: 0
Task 11J historical inference: 3 / unchanged
duplicate inference: 0
```

Apparatus disposition:

```text
TASK11K_REAL_PILOT_VALIDATION_APPARATUS_REPAIRED
```

Preserved-candidate result:

```text
TASK11J_PRESERVED_CANDIDATE_VALIDATION_FAILED
```

Next boundary:

```text
NEXT: RUN A FRESH REAL-REPOSITORY PILOT UNDER THE REPAIRED APPARATUS; DO NOT MODIFY THE FROZEN ENVELOPE
```
