# Coding Agent Foundation Contract

Status: **operator-authorized foundation contract**

Foundation date: **2026-08-09**

Application authority: **`ws-code-agent`**

## A. Purpose

`ws-code-agent` exists to explore and implement a locally governed coding-agent
capability using governance lessons proven in `ws-doc-writer`. It is a separate
application authority for bounded repository inspection, patch generation,
validation, and, only with explicit authority, future Git actions.

This foundation explicitly rejects **"Doc Writer plus unrestricted shell
access."** The coding executor is a separate bounded capability. This contract
does not claim implementation completeness, autonomous coding safety, or a
deployed service.

## B. Architectural lineage

| Item | Record |
|---|---|
| Authoritative source repository | `/home/louis/src/ws-doc-writer` |
| Source branch at fork | `work/multi-backend-multi-model-v1-20260809` |
| Actual source/fork head | `dfb759afb7826a2b849fa95bf40ce6f06cd3cd05` |
| Independently verified Doc Writer checkpoint | `7ae3d5794691fd769446702015f331367344df9d` |
| Reason for fork | Preserve proven governance while establishing separate coding-agent authority. |

The fork preserves Git lineage but has independent Git objects and working-tree
state. It inherits architectural concepts, not automatic semantic equivalence:

- versioned operator intent;
- immutable provenance;
- structured model output;
- clarification instead of invention;
- a proposed → validated → reviewed → accepted lifecycle discipline;
- frozen evaluation;
- human review gates; and
- explicit separation between generated output and operator-approved work.

Writing-specific schemas, prompts, review semantics, application routes, and
runtime assumptions are not automatically valid coding-agent equivalents. They
remain visibly inherited until explicitly redesigned.

The supplied independent verification
`ws-doc-writer-writing-setup-verification-20260804.md` characterized the
writing-setup and clarification workflow at the verified checkpoint as
implemented, self-enforcing, immutable/versioned, hashed, test-backed, and
operator-gated. Its terms remain distinct: `VERIFIED-IN-CODE`, `TEST-BACKED`,
and `OPERATOR-DECISION`. Its outstanding Alpha Trial mapping belongs to Doc
Writer and is not runtime state for this repository.

## C. Core architectural boundary

```text
                         OPERATOR
                            |
                            v
                   coding task / intent
                            |
                            v
                 +---------------------+
                 | governance layer    |
                 |                     |
                 | task setup/version  |
                 | prompts             |
                 | provenance          |
                 | review lifecycle    |
                 | benchmark/eval      |
                 +----------+----------+
                            |
                     proposed action
                            |
                            v
                 +---------------------+
                 | bounded executor    |
                 |                     |
                 | repo read/search    |
                 | bounded commands    |
                 | patch application   |
                 | tests/lint/build    |
                 | git inspection      |
                 +----------+----------+
                            |
                         evidence
                            |
                            v
                       human review
```

The lineage is architectural. Long-term governance need not physically remain
inside the Doc Writer application. `ws-doc-writer` remains authority for its
document-writing system; `ws-code-agent` does not gain authority over it.
Peer `*-cp` repositories retain their own domain authority. Reading, testing,
or proposing a patch does not grant authority over any repository. Cross-domain
disagreement or an unresolved boundary returns to the operator.

## D. Coding lifecycle

The following conceptual distinctions are frozen. Names may evolve only through
explicit design review; their semantic separation must not collapse silently.

```text
TASK_CAPTURED
    ↓
REPOSITORY_OBSERVED
    ↓
PATCH_PROPOSED
    ↓
PATCH_APPLIED_TO_SANDBOX
    ↓
VALIDATION_RUN
    ↓
VALIDATION_PASSED / VALIDATION_FAILED
    ↓
CODE_REVIEWED
    ↓
OPERATOR_ACCEPTED
    ↓
COMMIT_AUTHORIZED
    ↓
COMMITTED
    ↓
PUBLISH_AUTHORIZED
    ↓
PUBLISHED
```

```text
tests passed       ≠ operator accepted
operator accepted  ≠ commit authorized
commit authorized  ≠ push authorized
push authorized    ≠ deployment authorized
```

Each line is a separate evidence and authority transition.

## E. Code-specific artifact model

Future design needs first-class objects analogous to `CodingTask`,
`RepositorySnapshot`, `ToolInvocation`, `ToolResult`, `PatchProposal`,
`PatchApplication`, `ValidationRun`, `ReviewDecision`, and `GitAction`. These
are conceptual names only; this foundation intentionally creates no premature
database schema.

A patch must eventually be attributable to its task/setup version, repository
identity, base revision, allowed path scope, modified paths, patch content or
hash, model identity/version, prompt version, parent attempt, commands used to
derive or validate it, validation results, and reviewer decision. Invented APIs
and unverifiable execution claims are unacceptable.

## F. Capability leases

A capability lease is short-lived, machine-readable authority for one bounded
task or attempt. It prevents authority from living only in a model prompt.

```yaml
capability_lease:
  repository: /example/repository
  task_id: CA-00017
  allow:
    read: true
    search: true
    test: true
  write:
    paths:
      - docs/**
      - tools/**
    patch_only: true
  git:
    status: true
    diff: true
    commit: false
    push: false
  external_network: false
  expires_after_attempt: true
```

An operator may later expand one permission without silently expanding another:

```yaml
git:
  commit: true
  push: false
```

No production capability-lease implementation is part of this foundation.

## G. Execution evidence

Tool execution must become provenance. An eventual command record must be able
to represent:

```yaml
command:
working_directory:
execution_class:
started_at:
exit_code:
stdout_sha256:
stderr_sha256:
repository_before:
repository_after:
```

Execution classes must eventually distinguish read/search, validation/test,
bounded working-tree write, Git write, and external/network action. A model may
report evidence but may not manufacture it; actual executor results are
authoritative for execution.

## H. Review philosophy

Model findings inform human gates; they do not grant themselves authority. A
model may identify a security issue or label a finding blocking. A test runner
may report success. An evaluator may score a patch highly. None independently
authorizes acceptance, commit, publication, or deployment. Operator/reviewer
decisions remain structurally distinct.

## I. Benchmark requirement

The future frozen benchmark is tentatively named **Helix Code Agent Alpha**.
It is not built by this foundation. Before use, it must be versioned, frozen,
repository-aware, and resistant to silent training by editing its tests.

It must include cases for inspecting ownership without editing; repairing a
deterministic bug; modifying exactly one authorized file; rejecting an
unauthorized sibling-repository change; following authority into an explicitly
authorized peer repository; discovering rather than inventing an API; repairing
a failing test; preserving unrelated dirty work; detecting writes outside scope;
proposing a patch but stopping before commit; committing only when allowed;
refusing push under commit-only authority; accurately reporting command
failure; requesting clarification for material ambiguity; distinguishing failed
validation from rejected review; and proving successful tests do not imply
acceptance.

## J. Non-goals for the foundation phase

This fork does not prove autonomous coding safety, arbitrary shell safety,
repository-general competence, deployment authority, GitHub publication
authority, infrastructure mutation authority, production readiness, or
benchmark success. It establishes governance and evaluation architecture first.

## K. Fork hygiene and current boundary

No Doc Writer runtime database, local cache, generated model output, secret,
API credential, TLS material, host-specific configuration, deployment state,
machine-specific runtime path, or live application state was copied as runtime
identity. The source repository's tracked benchmark evidence and inbox README
remain historical lineage material only. This repository performs no model-driven
code execution, live database mutation, deployment, push, or external
repository mutation under this contract.

The current inherited `docwriter_web` implementation, prompt contracts,
writing schemas, model adapter settings, test names, and integration documents
are deliberately left unchanged. They are not evidence that a coding executor
exists. A later, explicitly reviewed coding design must decide which portions
are reusable and what coding-specific replacements are required.

## L. Fork provenance and baseline record

Before fork mutation, the source working tree was clean on
`work/multi-backend-multi-model-v1-20260809` at
`dfb759afb7826a2b849fa95bf40ce6f06cd3cd05`. Its configured `origin` was
`git@github.com:lhpoulin-cmyk/ws-doc-writer.git` for fetch and push; no tag
pointed at that HEAD. The only tracked items matching runtime-artifact review
terms were benchmark evidence records and `workspace/inbox/README.md`; no
tracked runtime database, cache, secret, credential, TLS material, or
environment file was found.

The inherited test command, `python3 -m pytest -q`, was attempted before the
fork and again in the fork. It could not begin in this environment because
`pytest` is not installed (`No module named pytest`). This is an environment
limitation, not a passing baseline or a claim of an inherited test failure.
Git whitespace and object-integrity checks completed cleanly. The source tree
was rechecked after the fork and remained clean at the same HEAD.
