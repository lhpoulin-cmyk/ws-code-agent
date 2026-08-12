# Task 11E source-grounded structured-edit precondition

Date: 2026-08-12

Play: `The Arsenal of Freedom`

Checkpoint: `TASK11E-DESIGN-SOURCE-GROUNDED-STRUCTURED-EDIT-PRECONDITION`

## Foundation and validation

The work started from clean direct-origin parity at:

```text
ws-code-agent: eaf0dca62117c49bc9f424563a539304574c4ae5
gpu-compute:   282cffabfa165b9d9906a35a9372cb077bdf6153
gpu-cp:        e64e39c029616d69ec4523500facd20e7a75c9f2
ws-cp:         c6138913d39502dbf1507c7318002b4ab748d0b1
```

The completed implementation passes 193 ws-code-agent tests, including the
new source-grounding policy, restart, staleness, authority, replay, and repair-
allowance controls. The separate two-test private-material gate, real
containment, lineage, invariant-register, YAML, and diff gates pass. All eight
gpu-compute unit suites and both ws-cp containment-contract tests pass. No peer
repository was changed.

## Evidence basis

Task 11E preserves every historical result. Task 11A remains
`INTERACTIVE_PRACTICAL_CODER_RESTRICTED_ACCEPTANCE_ESCALATED`; Task 11B remains
`PATCH_SERIALIZATION_INTERFACE_MISMATCH_CONFIRMED`; Task 11C remains
`STRUCTURED_EDIT_TRANSPORT_CANDIDATE_READY`; and Task 11D remains
`INTERACTIVE_PRACTICAL_CODER_V3_RESTRICTED_ACCEPTANCE_ESCALATED`.

The forward-only supervisor interpretation is narrower. Task 11A first read
`src/message.py`, selected the correct `hi` to `hello` edit, and then failed
unified-diff serialization. Task 11D never read the target. Its two structured
requests instead selected nonexistent source bodies (`return 'world'`, then
`pass`), producing two exact-match-zero results. Task 11D is therefore also
classified prospectively as:

```text
primary: INTERACTIVE_SOURCE_GROUNDING_FAILED
observed consequence:
  TEXT_MATCH_ZERO
  TEXT_MATCH_ZERO
  STRUCTURED_EDIT_REPAIR_EXHAUSTED
```

That interpretation does not replace or rescore the published Task 11D
disposition.

## Grounding contract

`SOURCE_GROUNDED_STRUCTURED_EDIT_V1` is evaluator-owned supervisor state. A
`PROPOSE_TEXT_REPLACEMENT` may reach the existing structured executor only
when a prior turn in the same durable session contains a successful executor
`READ_FILE` fact for the exact requested path and current Source Snapshot X.
The evidence record binds:

```text
version
policy ID and SOURCE_GROUNDED status
path and path SHA-256
file-content SHA-256
Source Snapshot X identity
turn number
executor-fact identity
```

Only the evaluator's successful read result creates this record. Search,
directory reads, reads of another path, prior-session evidence, model claims,
and the proposed `old_text` do not establish grounding. Evidence from another
snapshot is rejected. Any later Source Snapshot X drift invalidates recorded
grounding before another inference is launched; reads are never silently
rebound to a new snapshot.

Grounding grants no authority. Read scope, patch-path authority, traversal and
repository checks, Source Snapshot X, and the structured executor's path rules
remain independent. In particular, an unauthorized write remains
`DENIED_AUTHORITY` even if a file was readable.

## Write-before-read transition

An authorized-path replacement without valid grounding follows:

```text
PROPOSE_TEXT_REPLACEMENT
  -> SOURCE_READ_REQUIRED
  -> CONTINUE
```

The bounded model projection contains only:

```text
status: SOURCE_READ_REQUIRED
path: the exact path requested by the model
```

No file content, correct `old_text`, surrounding context, line number, or
replacement suggestion is exposed. The structured executor is not called,
the occurrence count is not computed, and no candidate is created. This event
does not consume the structured-match repair allowance because no match was
attempted.

After a successful target read, normal V3 exact-match behavior resumes without
semantic change. A first actual `TEXT_MATCH_ZERO` or `TEXT_MATCH_MULTIPLE`
still allows one ordinary forward correction; a second still escalates as
`STRUCTURED_EDIT_REPAIR_EXHAUSTED`. Two consecutive write-before-read requests
instead stop as:

```text
classification: INTERACTIVE_SOURCE_GROUNDING_FAILED
state: ESCALATION_REQUIRED
reason: SOURCE_GROUNDING_NONCOMPLIANCE
recommended next worker: DELIBERATIVE_OVERNIGHT_CODER
automatic handoff: false
```

## Retrospective controls

`tools/replay_task11e_source_grounding.py` binds the exact durable session
records and verifies their raw response hashes before applying this policy in
memory. It performs no model generation and does not rewrite historical
evidence. The resulting evaluator report at `/tmp/task11e-replay.json` has
SHA-256 `103f854574f1e51e9bda5d8809e0df842b16c3e38db97004a9d14aca5c42eebb`.

Task 11A session
`work-task11a-qwen25-14b-positive-20260812T142051Z` has Source Snapshot X
`348d4d52fab027d03a1652043b7eacee8d4aa54f17553fb58c4fa680cf52500e`.
Turn 1 is the successful exact-path READ with raw SHA-256
`f52783b9c7e1b6cabdc432c68e9384e66da391aa1f201051802127857b9962fb`.
The reconstructed evaluator read fact binds `src/message.py`, path SHA-256
`5029ddcd0fe99bc7f4eac4257e4a3ab5a30c59076b43264de623f9d4fe4bbcb9`,
and content SHA-256
`98f2f772b26b287735956a41fe7972e3d33cdfa364e15025951068e23afd49d7`.
Both later writes target that exact path, so their new grounding precondition
is `PASS`; their historical results remain `PATCH_REJECTED`. The conclusion is
`GROUNDING_PRECONDITION_PASS_PATCH_TRANSPORT_FAILED`.

Task 11D session
`work-task11d-qwen25-14b-v3-20260812T154829Z` has no READ turn. The preserved
turn raw hashes are
`9d719ea17a11813671271e9378b34cfd5caef9815413e7439e1c2dd486cc24d0`
and
`69596c9a4b86e9e224c0e5ddcd3b543455058ccb976155a66c934bd322e23fdb`.
Policy replay yields `SOURCE_READ_REQUIRED` for each turn, then
`SOURCE_GROUNDING_NONCOMPLIANCE / ESCALATION_REQUIRED`. No historical third
turn is manufactured. Under the new policy the structured executor would not
have been attempted, so the conclusion is
`GROUNDING_PRECONDITION_FAIL_STRUCTURED_TRANSPORT_NOT_ATTEMPTED`.

Together these controls separate the discovered defects:

```text
Task 11A: source grounding PASS; patch transport failed
Task 11D: source grounding FAIL; structured transport was not reached
```

## Frozen surfaces and scope

The V3 protocol text is unchanged and retains render SHA-256
`d060b7b15538ce781ecd50cee1478a3395a1122c3476047e8e02efc6b7f36993`.
Historical V2 retains
`3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e`.
The exact-match executor, fence normalizer, validators, semantic ownership,
read/patch authority, candidate isolation, and
`INTERACTIVE_BOUNDED_WORK_V1` entry boundary are unchanged. The only new
surface is supervisor grounding state and routing.

No 14B or 32B inference was run. No semantic adapter, transport repair, extra
match opportunity, authority expansion, automatic overnight invocation,
historical rescore, or automatic promotion occurred.

## Disposition

```text
SOURCE_GROUNDED_STRUCTURED_EDIT_PRECONDITION_READY
NEXT: RUN FRESH INTERACTIVE/PRACTICAL CODER V3 ACCEPTANCE WITH SOURCE-GROUNDING PRECONDITION
```
