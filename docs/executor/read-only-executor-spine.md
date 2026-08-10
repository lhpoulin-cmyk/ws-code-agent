# Read-only executor spine

Status: **implemented read-only foundation slice; no write or execution authority**

`src/ws_code_agent/readonly_executor.py` implements `OBSERVE_REPOSITORY`,
`READ_FILE`, `SEARCH`, `COMPARE_SNAPSHOT`, and structured executor-originated
evidence return. It has no patch application, validation dispatch, effect
observation for executable actions, model interface, command runner, network
code, Git-write operation, or authoritative-tree mutation capability.

Snapshot v1 separately records repository identity, canonical root, HEAD,
branch/detached state, index identity, tracked working-tree identity, untracked
inventory/content identity, and recursive submodule status. Same HEAD with dirty
tracked, staged, or untracked state produces a different snapshot identity.
Ignored files are excluded by the explicit v1 `exclude-standard` policy; this
does not solve their materiality for future tasks.

Repository identity combines canonical root, common Git directory path and local
device/inode, object format, and root-commit lineage. This detects ordinary
replacement at the same path but is not a universal portable repository identity;
a deliberately identical replacement can require later stronger operator-backed
identity design.

Reads accept only non-empty relative paths. Traversal and absolute paths are
denied; resolution that escapes the canonical root through a symlink is denied.
Search is Python-native, local, literal-only, bounded, and skips symlink entries.
The only subprocesses are fixed `git` plumbing arguments constructed by the
implementation with `shell=False`; no model-controlled executable, command, or
flag surface exists. No remote is queried and no network connection is attempted.

C03 correspondence: tests construct staged tracked operator work and an
untracked draft, then prove observe/read/search leave them byte-identical. C04
correspondence: tests observe X, mutate a synthetic repository externally, and
prove `COMPARE_SNAPSHOT(X)` returns `STALE`.

This slice demonstrates trustworthy read-only repository observation. It does
not yet demonstrate write containment, patch application, validation containment,
model disposition, OS-level sandboxing, or production safety.
