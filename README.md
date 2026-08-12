# ws-code-agent

`ws-code-agent` is an operator-authorized foundation and Alpha harness for a
locally governed, bounded coding-agent capability. It is a separate application
authority derived architecturally from `ws-doc-writer`; it is not a conversion
of Doc Writer into an autonomous coding agent.

The governing foundation contract is
[`docs/contracts/CODING_AGENT_FOUNDATION_CONTRACT.md`](docs/contracts/CODING_AGENT_FOUNDATION_CONTRACT.md).

## Current status

Alpha v1 is frozen and the executor/harness is qualified for model evaluation.
The exact tested `qwen3-coder:30b` artifact has completed Alpha evaluation and
demonstrated useful bounded `OBSERVE_ONLY`, `CLARIFY_AND_REPORT`, and narrow
`SUPERVISED_SINGLE_REPO` capabilities. Those capability findings are preserved,
but the artifact is `NOT_ADMITTED` to the supervised production lane after it
failed both required value-free V2 synthetic behaviors. Autonomous single- and
multi-repository operation remain `NOT_QUALIFIED`; C05 remains a confirmed
model failure under explicit authority and effect-state semantics. See the
[qualification statement](docs/qualification/qwen3-coder-30b-alpha-v1.md).

`WS_CODE_AGENT_REQUEST_PROTOCOL_V1_SINGLE` remains frozen for Alpha v1.
`WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE` is the frozen candidate
supervised-production interface: its interface design is accepted, but this
Qwen artifact did not qualify it for production use. Task 10K is closed for
Qwen with admission failed; it is not waiting for another Qwen-specific repair.
The operator-gated lane and challenger admission contract are documented in
[supervised single-repository work](docs/work/supervised-single-repo.md).

```text
Alpha v1: FROZEN
Qwen: ALPHA COMPLETE; PRODUCTION NOT ADMITTED
V2 single-repository protocol: FROZEN CANDIDATE INTERFACE
Task 10K: CLOSED FOR QWEN — ADMISSION FAILED
```

Devstral's historical challenger evaluation is settled: runtime acceptance
passed, clarification passed, write failed with terminal `MODEL_REPEAT_LIMIT`,
and Task 10N production admission failed without an authorized retry. The
Ollama reporting defect exposed by that outcome is repaired and governed; the
model result was not rescored.

`gpt-oss-20b-mxfp4` was then evaluated as the retained control candidate. Its
official artifact and patched-runtime compatibility resolved, but its enforced
8192-token minimum cannot honor the frozen 4096 comparison context. It is
therefore ineligible for this exact comparison seam, not rejected as a model or
runtime failure.

`qwen25-coder-14b-q4` remains the practical coding baseline, with operator-use
role `INTERACTIVE_PRACTICAL_CODER`, after completing its frozen V2 challenger
evaluation. Katra
retained the exact accepted `qwen2.5-coder:14b-instruct-q4_K_M` artifact and
`qwen25-coder-14b-katra-4096` profile at effective context 4096 and 100% GPU.
The write response proposed a plausible authorized patch but wrapped it in
Markdown; the clarification response both used Markdown and chose `NO_CHANGE`
instead of `REQUEST_CLARIFICATION`. The strict parser accepted neither request,
so production admission failed without changing the model's accepted runtime or
practical-baseline disposition.

Task 10X calibrated
`SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1` for the 14B interactive lane.
The exact historical write response became parser-valid after its sole Markdown
wrapper was removed, then the unchanged executor truthfully rejected the
unmodified corrupt patch. The clarification response became parser-valid
`NO_CHANGE`, preserving its separate semantic failure. This establishes a
defensible representation-only candidate adapter without rescoring history,
repairing output, or changing the `STRICT_RAW` benchmark behavior. Task 10Y
then bound that adapter to a separate `INTERACTIVE_NORMALIZED` lane and ran two
fresh fixtures. The write session produced a fenced, authority-correct but
corrupt patch, then chose bare `NO_CHANGE` after executor rejection; no
candidate existed to validate. The clarification session investigated with
valid search/read requests, then proposed an invented implementation despite
patch authority being `NONE`. The authority layer denied it. Both are semantic
failures, so the normalized lane is `NOT_ACCEPTED`; the adapter remains bounded
and the historical strict score remains unchanged.

Task 10Z converts those results into supervisor routing policy rather than a
broader adapter. `INTERACTIVE_BOUNDED_WORK_V1` admits the interactive/practical
coder only for requirements-complete, single-repository work with explicit
authority, pre-bound validators, a frozen clean source snapshot, the accepted
14B runtime profile, and the existing fence-only normalizer. One rejected patch
gets one ordinary forward repair opportunity; a second construction failure,
`NO_CHANGE` after rejection, an authority mistake, a turn/repeat limit, or
another semantic failure produces durable `ESCALATION_REQUIRED` evidence.
Escalation recommends the deliberative/overnight coder or operator but never
invokes either automatically. A validated candidate remains
`AWAITING_OPERATOR_REVIEW` and is never promoted automatically.

Task 11A exercised that boundary on a fresh requirements-complete, bounded,
single-repository change. Entry passed and the 14B worker made a valid read,
then proposed the correct semantic change twice; both patch envelopes were
corrupt. The second rejection exhausted the one ordinary repair opportunity,
so the supervisor stopped after three inferences with durable
`ESCALATION_REQUIRED` / `PATCH_REPAIR_EXHAUSTED` evidence and no candidate.
This is `INTERACTIVE_PRACTICAL_CODER_RESTRICTED_ACCEPTANCE_ESCALATED`, not an
infrastructure failure or acceptance. No overnight worker was invoked and no
source effect was promoted.

Task 11B then bound the exact preserved patch bytes from Tasks 10R, 10Y, 10V,
and 11A and separated code intent from unified-diff grammar. Every analyzed 14B
patch selected `src/message.py` and represented the objective-correct edit;
each rejected patch became `git apply` compatible through a unique mechanical
correction to counts, file envelope, context prefix, or terminal newline. The
32B control preserved identical semantics between its rejected and accepted
turns and crossed the executor boundary by correcting serialization. The
result is `PATCH_SERIALIZATION_INTERFACE_MISMATCH_CONFIRMED`. This is a
forensic finding only: production patch transport, authority, and the Task 11A
escalation remain unchanged.

Task 11C responds to that interface finding with the candidate-only,
value-free `WS_CODE_AGENT_REQUEST_PROTOCOL_V3_SINGLE_STRUCTURED_EDIT` and its
`PROPOSE_TEXT_REPLACEMENT` operation. The model owns the authorized path and
the exact old/new text. A dedicated executor requires one exact match in an
existing UTF-8 file, applies the unchanged values only in an isolated
candidate, observes the resulting path set, and generates the review diff as
evaluator evidence. It performs no fuzzy match, semantic repair, occurrence
selection, new-file creation, or source promotion. Both preserved Task 11A
edits replayed through this transport and passed the independent visible and
hidden validators; historical new-file cases correctly remained outside V3's
narrow scope. The result is `STRUCTURED_EDIT_TRANSPORT_CANDIDATE_READY`.
V2, `INTERACTIVE_BOUNDED_WORK_V1`, and the live interactive lane remain
unchanged pending a fresh V3 acceptance run.

Task 11D prepares that fresh run through a separate candidate lane,
`QWEN25_14B_INTERACTIVE_STRUCTURED_V3_V1`. The lane durably binds the accepted
14B artifact/profile, `INTERACTIVE_BOUNDED_WORK_V1`, the unchanged fence-only
normalizer, the value-free V3 render, the exact Task 10W validators, and the
existing isolated candidate/review machinery. `PROPOSE_PATCH` is unavailable;
accepted replacements retain the model's exact path and old/new text while the
evaluator owns occurrence counting and canonical review-diff construction.
This apparatus is not the default interactive lane. Its separately published
fresh acceptance session then emitted two parser-valid, authority-valid
structured requests. Both selected `src/message.py` and replacement code that
returns `"hello"`, but neither selected `old_text` that existed in the frozen
source: turn 1 selected a `return 'world'` body and turn 2 selected `pass`.
Both exact-match counts were zero. The second failure exhausted the one
ordinary forward correction opportunity, producing
`ESCALATION_REQUIRED / STRUCTURED_EDIT_REPAIR_EXHAUSTED` after two inferences.
No candidate or validation run existed. The result is
`INTERACTIVE_PRACTICAL_CODER_V3_RESTRICTED_ACCEPTANCE_ESCALATED`; V3 removed
diff serialization from the test, exposing a source-alignment failure without
repairing it or broadening the lane.

Task 11E adds the supervisor-only
`SOURCE_GROUNDED_STRUCTURED_EDIT_V1` precondition. A V3 existing-file
replacement now reaches exact-match execution only after a successful
same-session `READ_FILE` of that exact path, durably bound to the current Source
Snapshot X. An ungrounded request receives only `SOURCE_READ_REQUIRED` and its
requested path; no match is counted and no source content is disclosed. A
second consecutive ungrounded write escalates as
`SOURCE_GROUNDING_NONCOMPLIANCE`, without consuming or expanding the existing
match-repair allowance. Retrospective policy replay separates the prior
failures: Task 11A was source-grounded and then failed patch transport, while
Task 11D was never source-grounded and therefore would not have reached the
structured executor. V3's render, structured-edit semantics, authority, and
all historical dispositions remain unchanged.

`qwen25-coder-32b-q4` is retained as an intra-family scale control with
operator-use role `DELIBERATIVE_OVERNIGHT_CODER`. Its
exact official Q4_K_M artifact preserves the 14B system/template interface and
the exact 4096 comparison seam, while changing model scale from 14.8B to 32.8B.
One exact pull and three no-retry neutral probes established a runtime-accepted
`qwen25-coder-32b-katra-4096` profile: 71% GPU / 29% CPU, 14,634 MiB peak VRAM,
effective context 4096, and no host-pressure or accelerator fault. Its frozen
V2 scale-control run then produced bare parser-valid JSON in all three model
turns. The write session repaired an initially corrupt patch and reached an
isolated, authority-valid `src/message.py` candidate; the independent
clarification session emitted the required materially relevant
`REQUEST_CLARIFICATION`. The run remains admission-inconclusive rather than
PASS or model FAIL because the frozen supervised lane has no approved
visible/hidden validation descriptor and reports `VALIDATION_NOT_CONFIGURED`.
Task 10W subsequently added objective-derived, independently implemented
visible and hidden validators and ran them against the immutable preserved
candidate without model inference. Both passed under fixed systemd containment,
so that candidate now has a forward-only supplemental technical-correctness
finding of `VALIDATED`. Task 10V's historical inconclusive disposition and all
historical turns remain unchanged. The candidate is not production-admitted,
preferred, or a replacement for the 14B baseline.

The inherited Doc Writer implementation remains removed from the live tree;
witnessed history and reusable references are preserved under `lineage/`.

## Foundation provenance

Independently cloned with preserved Git history from `/home/louis/src/ws-doc-writer`
at source HEAD `dfb759afb7826a2b849fa95bf40ce6f06cd3cd05` on 2026-08-09, recording
the independent Doc Writer verification checkpoint
`7ae3d5794691fd769446702015f331367344df9d`. No inherited runtime database, cache,
credential, TLS material, host configuration, deployment state, or generated
model output is part of this repository's identity.

## Peer boundary

    ws-doc-writer  document-writing application (separate authority)
    ws-cp          workstation and Ollama service mechanics
    gpu-cp         RX 9070 XT accelerator contract and acceptance

Peers retain authority in their domains. Reading, testing, or proposing a patch
grants no authority over any repository. A disagreement stops and returns to the
operator.

## Layout

- `docs/contracts/` operator-authorized architectural contracts
- `docs/` supporting doctrine (operator access, future coding lifecycle)
- `schemas/` small machine-readable validation contracts (backend plumbing)
- `config/` example runtime endpoint configuration
- `models/` model candidate matrix by VRAM tier
- `tools/` lineage verification
- `src/` bounded executor, harness, protocol, and durable experiment controller
- `tests/` deterministic and real-containment Alpha regression coverage
- `docs/qualification/` artifact-bound model qualification statements
- `lineage/` inherited Doc Writer history and reference material (no authority)
