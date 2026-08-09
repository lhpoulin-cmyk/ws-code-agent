# Coding-Domain Contracts

Status: **operator-authorized design contract; no implementation authorized**

## Purpose and boundary

This contract defines the conceptual objects and trust boundaries required for a
future bounded coding agent. It implements nothing: no schema, database,
executor, lease enforcement, model selection, benchmark, or shell protocol is
created by this document.

The governing foundation contract remains authoritative where this document is
silent. In particular, validation passing, operator acceptance, commit
authorization, push authorization, and deployment authorization remain separate
transitions.

```text
operator intent
    ↓
identified repository state
    ↓
bounded authority
    ↓
model proposal
    ↓
executor-observed fact
    ↓
validation evidence
    ↓
human authority
```

## Trust and authority model

| Source | Trust role |
|---|---|
| Operator | authority |
| `CodingTask` contract | recorded operator intent |
| Model | untrusted proposal and reasoning source |
| Executor | observer of performed operations |
| OS/filesystem/Git | underlying state |
| Validator/test tool | evidence producer |
| Human reviewer | review judgment |
| `CapabilityLease` | bounded delegated authority |

Truth about state and authority to change state are distinct. An executor may
observe what happened without authority to approve it. A model may recommend an
action without authority to perform it. A validator may produce a result without
authority to accept, commit, publish, or deploy it.

## 1. `RepositorySnapshot`

`RepositorySnapshot` is the immutable observation identity supporting the claim
“this task observed repository state X.” It identifies more than a path and more
than a HEAD commit. Its minimum conceptual content is:

- repository identity and repository root;
- HEAD commit and branch name or detached-HEAD state;
- index state;
- tracked working-tree modifications;
- untracked-file set; and
- submodule state where present.

HEAD alone is insufficient: staged or unstaged tracked changes, untracked files,
and submodule revisions can materially affect a patch, build, or validation
result while leaving HEAD unchanged. A dirty tree is therefore a valid but
explicitly identified snapshot, never an implicit approximation of clean HEAD.

Repository identity must distinguish a replacement clone at the same filesystem
path. The root is an observation location, not sole identity. The design must
record enough repository/Git identity to detect materially different repositories
or worktrees sharing a path. Git worktrees must be distinguished by their own
working state even when they share object storage. Submodule state includes the
recorded commit and material local state for each applicable submodule.

Ignored files are not automatically part of a snapshot identity. Their presence
must be explicitly treated as either irrelevant or material for the requested
operation; if they can influence a build or test, that influence must be recorded
or the task must be clarified. Symlinks are filesystem entries whose tracked or
observed target semantics may be material; an implementation must not silently
follow them outside the authorized repository/path scope.

No hashing algorithm is frozen here. Snapshot identity must invalidate whenever
any material component it records changes: repository identity, HEAD,
branch/detached state where relevant, index, tracked modifications, relevant
untracked-file set, or applicable submodule state. State drift after observation
requires a new snapshot; it cannot be normalized away.

## 2. `CodingTask` and task versions

`CodingTask` records operator intent. A `CodingTaskVersion` is immutable and
contains a task/version identity, operator-supplied objective, repositories in
scope, allowed and prohibited path scope where appropriate, requested outcome,
validation expectations, clarification state, and authority references.

Operator intent is authoritative. Inferred implementation detail is a hypothesis
that must remain labeled as such. A model suggestion is untrusted proposal
content. Neither may silently promote itself into task authority.

Material changes supersede rather than mutate a task version: objective,
repository scope, allowed/prohibited paths, requested outcome, validation
expectations, clarification answer that changes meaning, or authority reference.
A correction that changes the recorded operator meaning likewise creates a
successor while preserving the prior record. A later task version does not
retroactively authorize an attempt bound to an earlier version.

## 3. `PatchProposal`

`PatchProposal` is an **untrusted model-originated desired mutation**. It is not
a `PatchApplication`, a filesystem event, or validation evidence. It must be
attributable to its `CodingTaskVersion`, source `RepositorySnapshot`,
model/backend identity, prompt/version, proposed modified paths, proposed patch
content or immutable identity, blast-radius metrics, dependency changes, and
parent attempt where relevant.

```text
PatchProposal
    ≠ PatchApplication

proposed modified paths
    ≠ observed modified paths

model prediction
    ≠ validation result
```

If the source `RepositorySnapshot` no longer matches, the proposal is stale for
application. It may remain historical evidence or be re-evaluated against a new
snapshot, but it cannot silently apply under the prior authority.

## 4. `ExecutorFact` and execution evidence

`ExecutorFact` is executor-originated evidence about an observable operation.
It may represent the operation requested, operation actually executed, working
directory, repository snapshot before and after, exit status, retained stdout or
stderr identity, filesystem changes observed, Git changes observed, validation
result, and material tool/runtime identity.

Model-originated claims and executor-observed facts may reference each other but
must retain incompatible provenance roles. When model prose conflicts with
executor evidence, the executor evidence is authoritative for whether that
external operation occurred and what it observed. It does not independently
grant approval authority. A validation result is the result produced by the
actual validator/tool, not a model restatement of that result.

This contract does not define arbitrary shell execution or command
serialization. It requires that any eventual implementation retain origin,
subject, and observation boundary instead of collapsing a claim into a fact.

## 5. `CapabilityLease`

`CapabilityLease` is bounded delegated authority for a single task/attempt. It
must identify its lease, authority issuer, bound `CodingTaskVersion`, repository,
bound `RepositorySnapshot`, capability scope, path scope, expiry/backstop,
revocation state, and non-transferability. Parent/child delegation, if later
allowed, must be explicit, narrower than the parent, and independently
attributable; it is not implicit delegation.

Capabilities are distinct, including repository read, deterministic search,
approved validation commands, isolated patch application, working-tree write,
dependency modification, Git status/diff, Git commit, Git push, and network
access. Granting one does not grant another.

A lease authorizes only the repository snapshot and scope recorded in it.
Repository state drift invalidates relevant authority unless it is explicitly
reissued against the new state. A wall-clock expiry is a secondary backstop, not
a replacement for snapshot binding. Revocation prevents further action but does
not erase evidence already observed.

## 6. Multi-repository boundary

Authority is granted per repository/snapshot scope and does not leak across
repository boundaries. A task may reference multiple repositories, but each
retains its own identity, snapshot, authority scope, observed mutations, and
evidence. Discovering that a peer repository owns work needed by a task grants no
read or write authority over that peer; a separately scoped authority decision is
required.

## 7. State-change dispositions

| Event | Required disposition |
|---|---|
| Repository changes after observation | Snapshot and relevant lease/proposal become stale; observe again and reissue authority if appropriate. |
| Operator edits task intent | Create a superseding `CodingTaskVersion`; do not mutate the prior version. |
| Operator manually edits a proposed patch | Record a distinct operator/manual mutation or new proposal/application basis; do not attribute it to the model. |
| Capability lease becomes stale | Stop the covered action; require a new snapshot and explicit reissue. |
| Patch application partially succeeds | Record observed partial state and executor facts; do not call it applied or validated; require review/recovery decision. |
| Validation cannot run | Record unavailable/not-run executor evidence; no validation-passed transition. |
| Validation fails | Record the result; no validation-passed transition and no implied review acceptance. |
| Executor evidence contradicts model | Retain both origins; executor facts govern what executed and model claim remains untrusted. |
| One repository in a multi-repository task changes | Invalidate only the affected repository's snapshot/authority by default; do not silently extend another repository's authority or evidence. |
| Untracked files influence a build/test | Treat the snapshot as materially incomplete or changed; obtain a clarified/re-observed basis before relying on the result. |

## 8. Artifact relationships

```text
CodingTaskVersion
        │
        ├──────────────┐
        ▼              ▼
RepositorySnapshot   CapabilityLease
        │              │
        └──────┬───────┘
               ▼
         ModelAttempt
               │
               ▼
        PatchProposal
               │
               ▼
        PatchApplication
               │
               ▼
        ExecutorFacts
               │
               ▼
        ValidationRun
               │
               ▼
        ReviewDecision
```

The graph is conceptual only. It does not prescribe tables, serialization, or
implementation order. Identity links preserve provenance; they do not themselves
confer authority.

## 9. Review challenge outcomes

The contract resolves the required challenge cases as follows:

1. Unchanged HEAD with a changed working tree invalidates the snapshot.
2. A different clone at the same path fails repository identity continuity and
   requires a new snapshot and authority decision.
3. A nonzero executor exit overrides a model claim that tests passed.
4. Two observed changed files are executor evidence; the one-file proposal does
   not relabel them and requires review of scope/partial application.
5. A second repository requires separately scoped authority; discovery is not a
   grant.
6. An operator working-tree edit makes the lease snapshot stale.
7. An operator patch edit is distinctly attributable and cannot remain a pure
   model proposal.
8. An unavailable validation tool records validation-not-run, not success.
9. Partial application records partial observed state and stops for recovery or
   review.
10. Material untracked build/test inputs require a clarified or re-observed
   snapshot before reliance.

## 10. Unresolved questions

- Which stable repository identity signals and snapshot comparison rules best
  distinguish clone replacement without overfitting to one Git hosting model?
- How should material ignored files and symlink traversal be declared per task
  without granting implicit access outside scope?
- Which executor evidence should be retained directly versus represented by
  content-addressed references, and what privacy/redaction rules apply?
- What review and recovery contract governs a partially applied patch?
- Under what explicit conditions, if any, may a parent lease delegate a narrower
  child lease?

These questions require later explicit design. They do not authorize Task 2
implementation work.
