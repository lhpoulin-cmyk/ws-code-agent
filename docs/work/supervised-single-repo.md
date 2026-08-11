# Supervised single-repository work

Status: **implemented; not accepted for real-repository use**. The first live
synthetic acceptance on 2026-08-11 preserved all safety and durability
properties but did not produce either required model disposition. See
`task10k-synthetic-acceptance.md`. Do not start a real-repository session until
that blocker is resolved under separate authority.

This lane is authorized only for the exact `qwen3-coder:30b` artifact and
profile recorded in
`docs/qualification/qwen3-coder-30b-alpha-v1.yaml`. It creates an isolated
candidate for operator review. It never writes, commits, merges, or pushes the
authoritative repository.

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

## Review and disposition

```bash
python3 tools/run_supervised_work.py review SESSION
python3 tools/run_supervised_work.py approve SESSION
# or
python3 tools/run_supervised_work.py reject SESSION
```

Review reports the frozen source identity, objective, request sequence,
candidate diff, changed paths, application status, runtime evidence, authority
anomalies, validation state, and isolated result location. `approve` and
`reject` only record an operator disposition. Neither promotes the candidate.

If the source no longer equals Snapshot X, review records
`SOURCE_STATE_STALE`; approval fails closed. The lane never rebases, refreshes
authority, or regenerates the candidate. Validation is
`VALIDATION_NOT_CONFIGURED` unless a future registry-owned, operator-selected
descriptor is separately approved; isolated application is not technical
correctness.

## Restrictions

- one repository and the frozen single-repository protocol only;
- no automatic promotion, commit, push, network, dependency, shell, or service authority;
- no runtime/model substitution or qualification broadening;
- no retry after ambiguous executor work;
- no multi-repository or autonomous remediation.
