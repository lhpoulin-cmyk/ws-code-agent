# Operator-access doctrine

When an approved lab filesystem or secret vault is mounted read-only, an agent
may request task-scoped read-only access. The operator grants that access.

This may include sudo/root privileges for task-relevant metadata and
configuration inspection. It does not authorize remounting read-write,
modifying mounts, writing vaults, changing ownership or permissions, enrolling
keys, changing LUKS keyslots, altering GPT/filesystems/crypttab/fstab/systemd/
Ollama/ROCm/GPU state, or reading unrelated secret contents. If sudo requests
a password, the operator enters it interactively; it is never pasted into
chat, stored, placed in arguments, or logged.
