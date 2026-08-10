# Descriptor-only validation

Status: **implemented isolated validation slice; no general containment claim**

Validation accepts only trusted registry IDs. Descriptors fix executable, argv,
relative working directory, timeout, role, and write policy; no caller provides a
shell command, environment, or working directory. Runs use `shell=False` and a
small environment (`PATH`, `LC_ALL`, `PYTHONDONTWRITEBYTECODE`, plus trusted
isolated `PYTHONPATH` for an oracle). They bind an expected isolated result
snapshot before execution and capture after-state, executable path, argv, cwd,
timing, exit, timeout, stdout, and stderr. Exit zero with an unexpected
repository write is `EFFECT_VIOLATION`.

For the Task 10A C01 descriptors marked `containment_required`, direct process
execution is not a fallback. They use the ws-cp fixed systemd transient-unit
runner as `louis:louis`, with `PrivateNetwork=yes` and
`RestrictAddressFamilies=AF_UNIX`. The unit receives a read-only isolated result
tree. A hidden oracle receives only a fresh read-only staging directory bound at
`/run/ws-code-agent/oracle`, containing exactly `oracle.py`; it never receives
the evaluator-private root or its host-side path. The staging artifact digest,
unit identity, uid/gid, network/address-family policy, and timeout result are
retained as containment evidence. If that runner cannot establish containment,
the result is `VALIDATION_CONTAINMENT_UNAVAILABLE`.

This proves the specific Task 10A socket-family, private-path, read-only-result,
process-tree, and single-artifact-oracle gates. It does not prove general
production containment for arbitrary executable workloads.

Validation executes model-influenced code and is not general production
containment. Before any model run, its host environment must be unprivileged and
disposable, free of production secrets, SSH-agent access, and cloud/API
credentials, with network denial enforced operationally. A future Task 10 packet
must verify those host conditions before inference.

> Task 9 proves bounded execution of predeclared validation descriptors against
> isolated repository state and causal attribution of their results. It does not
> yet prove general process, child-process, filesystem, or network containment
> for arbitrary executable workloads.
