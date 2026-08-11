# Descriptor-only validation

Status: **implemented fixed-descriptor validation slices; no general containment claim**

Validation accepts only trusted registry IDs. Descriptors fix executable, argv,
relative working directory, timeout, role, and write policy; no caller provides a
shell command, environment, or working directory. Runs use `shell=False` and a
small environment (`PATH`, `LC_ALL`, `PYTHONDONTWRITEBYTECODE`, plus trusted
isolated `PYTHONPATH` for an oracle). They bind an expected isolated result
snapshot before execution and capture after-state, executable path, argv, cwd,
timing, exit, timeout, stdout, and stderr. Exit zero with an unexpected
repository write is `EFFECT_VIOLATION`.

For descriptors marked `containment_required`, direct process execution is not
a fallback. The Task 10A C01 descriptors and the frozen Task 10K-C write
descriptors use the ws-cp fixed systemd transient-unit runner as `louis:louis`,
with `PrivateNetwork=yes` and `RestrictAddressFamilies=AF_UNIX`. The unit
receives a read-only isolated result tree. A visible validator or hidden oracle
receives only its own fresh read-only staging directory, containing exactly
`validator.py` or `oracle.py`; it never receives the evaluator-private root or
its host-side path. The staging artifact digest, unit identity, uid/gid,
network/address-family policy, and timeout result are retained as containment
evidence. If that runner cannot establish containment, the result is
`VALIDATION_CONTAINMENT_UNAVAILABLE`.

The frozen synthetic write objective has two independently implemented trusted
descriptors:

```text
task10k-c-write-visible-v1  VISIBLE
task10k-c-write-hidden-v1   HIDDEN_ORACLE
```

Both verify only the objective-defined behavior of `src/message.py`: a callable
zero-argument `message` whose return value is exactly the Python string
`"hello"`. Neither imposes formatting, annotation, docstring, or AST-style
requirements. Both prohibit repository writes. The visible implementation uses
a fresh module import; the hidden implementation separately compiles and
executes the file in a fresh namespace and repeats the call. They share trusted
containment and snapshot machinery, not assertion logic.

This proves the specific Task 10A and Task 10W socket-family, private-path,
read-only-result, process-tree, and single-artifact validator/oracle gates. It
does not prove general production containment for arbitrary executable
workloads.

Validation executes model-influenced code and is not general production
containment. Before any model run, its host environment must be unprivileged and
disposable, free of production secrets, SSH-agent access, and cloud/API
credentials, with network denial enforced operationally. A future Task 10 packet
must verify those host conditions before inference.

> Task 9 proves bounded execution of predeclared validation descriptors against
> isolated repository state and causal attribution of their results. It does not
> yet prove general process, child-process, filesystem, or network containment
> for arbitrary executable workloads.
