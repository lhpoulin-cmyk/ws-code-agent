# Isolated patch application

Status: **implemented bounded isolated patch slice; no validation or source-tree patching**

`IsolatedPatchExecutor` builds a disposable workspace outside the authoritative
repository only after its source snapshot still compares `MATCH`. V1 supports
standalone Git worktrees with no submodules: it copies the `.git` directory plus
tracked and `--exclude-standard` untracked paths, preserving HEAD, index, dirty
working tree, and included untracked state. Linked worktrees and submodules fail
closed rather than being approximated.

`PatchProposal` is immutable, proposer-originated, and bound to source snapshot
and repository identities. It never becomes application, validation, acceptance,
or commit evidence. The executor uses fixed noninteractive `git apply --index`
with `shell=False`, direct patch stdin, no model-controlled flags, and captures
exit status/stdout/stderr. It prechecks supported relative paths against exact
allowed paths and rejects mutation through any symlinked target or parent.

Successful application produces an isolated result snapshot Y plus actual changed
paths. Rejection is `PATCH_REJECTED` when unchanged and `PATCH_PARTIAL` if an
unexpected changed state is observed. Cleanup removes only the executor-owned
workspace after evidence is returned; it is not rollback of authoritative state.

Task 8 observes isolated repository mutation effects produced by the fixed patch
application mechanism. It does not yet establish general containment for
arbitrary executable actions.

> A successful Task 8 result proves only that a particular proposed patch was
> applied to an isolated copy derived from a particular snapshot and produced an
> observed result state. It does not prove technical correctness, acceptance,
> authoritative applicability, commit authority, or deployment safety.

Validation, hidden-oracle execution, network, Git commit/push, authoritative
tree mutation, model execution, and automatic rollback are absent.
