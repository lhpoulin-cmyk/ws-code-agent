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

Hidden oracle source remains outside the isolated model-visible target tree.
Descriptors require no network, but OS-level network and child-process
containment remain unproven.

> Task 9 proves bounded execution of predeclared validation descriptors against
> isolated repository state and causal attribution of their results. It does not
> yet prove general process, child-process, filesystem, or network containment
> for arbitrary executable workloads.
