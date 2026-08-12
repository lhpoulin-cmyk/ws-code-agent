# Supervised single-repository work

Status: **implemented; strict V2 Qwen admission remains `NOT_ADMITTED`; the
separate source-grounded V3 envelope is `FROZEN` pending its first real pilot**.
The exact tested artifact did not pass both historical V2 synthetic behaviors,
including after P11 and the value-free V2 interface removed independently
demonstrated defects. Task 10K remains closed and unchanged. Later forward-only
evidence produced the distinct
`INTERACTIVE_PRACTICAL_CODER_V3_PRODUCTION_ENVELOPE_V1`; it does not rescore V2
or grant general production use. Do not start a real-repository session until
an operator authorizes a complete Pilot V1 packet.

The legacy ordinary `start` lane is authorized only for the exact
`qwen3-coder:30b` artifact and profile recorded in
`docs/qualification/qwen3-coder-30b-alpha-v1.yaml`. It creates an isolated
candidate for operator review. It never writes, commits, merges, or pushes the
authoritative repository.

The ordinary `start` path uses only a protocol and artifact admitted by the
qualification manifest. The value-free V2 protocol is frozen as the candidate
production interface, but its synthetic result for Qwen is `FAIL`; the current
manifest therefore fails closed for operator repositories.

## Start

The source must be a clean Git worktree at the exact expected HEAD. Authority
is immutable after start and must name every readable scope and patchable path.

```bash
python3 tools/run_supervised_work.py start \
  --repo /path/to/repository \
  --expected-head COMMIT_SHA \
  --objective /path/to/objective.txt \
  --allow-read src \
  --allow-read tests \
  --allow-patch src/file.py
```

The command returns the generated session ID. Evidence is stored separately
from Alpha experiments under:

```text
~/.local/share/ws-code-agent/work/<session-id>/
```

Only one repository is accepted. Absolute/traversing authority paths fail
`SUPERVISION_REQUIRED_CROSS_REPOSITORY`. Start a new session if authority must
change.

## Operate one turn at a time

```bash
python3 tools/run_supervised_work.py status SESSION
python3 tools/run_supervised_work.py step SESSION
```

Each `step` performs at most one idempotent model invocation. The durable
intent, raw response, harness result, and committed turn remain authoritative
after client interruption. The first isolated patch application with status
`SUCCESS` becomes the candidate and ends model work. A clarification also ends
model work and pauses for the operator; this v1 lane does not answer it in
place.

The bounded Task 10K-C acceptance surface was:

```bash
python3 tools/run_supervised_work.py start-synthetic-v2 --fixture write
python3 tools/run_supervised_work.py start-synthetic-v2 --fixture clarification
```

These commands create fixed synthetic repositories, objectives, and authority.
They accept no operator repository and grant neither production qualification
nor promotion authority. The completed Qwen one-shot evaluation is historical;
the failed qualification state prevents another Qwen run through this surface.

## Strict and normalized lanes

The historical benchmark command `start-qwen25-v2` remains `STRICT_RAW` and
uses no adapter. The separate operator command
`start-qwen25-interactive-normalized` binds the Qwen2.5-Coder 14B interactive
lane to `SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1`. Both the mode and exact
adapter version are durable session state and are checked again after restart.

The normalized lane removes only one whole-response unlabeled or
lowercase-`json` Markdown fence after raw response evidence is durable. It
stores the normalized parser input and independent SHA-256 evidence, then calls
the unchanged strict parser. It does not search prose, select objects, repair
JSON or patches, rename requests, change values, convert `NO_CHANGE`, or retry
a model. The model-visible prompt, authority, isolation, validation, and review
safeguards are shared with the strict lane.

## Frozen source-grounded structured-edit envelope

`INTERACTIVE_PRACTICAL_CODER_V3_PRODUCTION_ENVELOPE_V1` freezes the exact
source-grounded V3 combination accepted by Task 11F. It is production-capable
inside that envelope, but general production use remains `NOT_YET_GRANTED` and
the first real-repository pilot remains `NOT_YET_RUN`. Existing V2 commands and
historical dispositions are unchanged; no command is silently replaced.

`WS_CODE_AGENT_REQUEST_PROTOCOL_V3_SINGLE_STRUCTURED_EDIT` exposes
`PROPOSE_TEXT_REPLACEMENT` with one existing authorized path, one non-empty
exact `old_text` value, and one exact `new_text` value. The model owns those
three semantic values and never supplies a unified diff. The evaluator requires
a prior same-session exact-path `READ_FILE` bound to current Source Snapshot X,
then counts occurrences, applies an exactly-once replacement in a disposable
candidate, independently observes the changed path, and creates the canonical
review diff with evaluator provenance.

V1 permits exactly one authorized writable regular UTF-8 existing file. It does
not fuzzy-match, select an occurrence, infer whitespace, create files, repair
code, or expand authority. `new_text` may be empty as an exact region deletion,
but the file itself remains present. Both pre-bound contained validators must
pass before `AWAITING_OPERATOR_REVIEW`; promotion is never automatic.

The first real-repository pilot is defined by
`INTERACTIVE_PRACTICAL_CODER_REAL_REPOSITORY_PILOT_V1`. Its target is pending
operator selection. A complete exact manifest and a separate authorized pilot
play are required before any real-repository inference.

## Challenger admission

A different artifact may be evaluated only after explicit selection. It must
receive the frozen V2 render and the same Task 10K-C fixtures, authority,
eight-turn budgets, durable controller, executor, P11 behavior, containment,
and criteria. The write task must produce an isolated accepted
`src/message.py` candidate, and the ambiguity task must produce
`REQUEST_CLARIFICATION`. Both are required. No challenger is currently
designated, and this document authorizes no pull or inference.

## Review and disposition

```bash
python3 tools/run_supervised_work.py review SESSION
python3 tools/run_supervised_work.py approve SESSION
# or
python3 tools/run_supervised_work.py reject SESSION
```

Review reports the frozen source identity, objective, request sequence,
candidate diff, changed paths, application status, runtime evidence, authority
anomalies, validation state, and isolated result location. For the frozen
synthetic write fixture, the session manifest binds the exact visible and hidden
descriptor identities before inference. Once a candidate is ready, the
evaluator advances one restart-stable validation phase per command:

```bash
python3 tools/run_supervised_work.py validate SESSION  # visible
python3 tools/run_supervised_work.py validate SESSION  # hidden
```

The validators run only against a disposable reconstruction of the isolated
candidate. They recheck candidate and source snapshots before and after each
phase. A successful pair records `technical_correctness: VALIDATED`; it does
not promote the candidate. `approve` and `reject` only record an operator
disposition. Neither promotes the candidate.

If the source no longer equals Snapshot X, review records
`SOURCE_STATE_STALE`; approval fails closed. The lane never rebases, refreshes
authority, or regenerates the candidate. Clarification fixtures and ordinary
operator sessions remain `VALIDATION_NOT_CONFIGURED`; isolated application by
itself is not technical correctness.

## Restrictions

- one repository and the frozen single-repository protocol only;
- no automatic promotion, commit, push, network, dependency, shell, or service authority;
- no runtime/model substitution or qualification broadening;
- no retry after ambiguous executor work;
- no multi-repository or autonomous remediation.
