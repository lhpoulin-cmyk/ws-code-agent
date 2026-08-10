# Helix Alpha calibration fixtures

These five synthetic fixtures pressure the Helix Code Agent Alpha evaluation
contract before cases are frozen. They are not the frozen Alpha benchmark, a
benchmark runner, model results, or a containment result. No model or
containment layer has run them; isolated executor tests exercise bounded C01
fixture mechanics only, and containment is `NOT_TESTED`.

`cases/<case>/target/` is the future model-visible synthetic repository material.
Evaluator-only oracle and answer material is held outside the repository in the
local operator-private store described by `PRIVATE_MATERIAL.md`; it must never be
exposed to a tested model. Case documents describe model-visible initial state,
authority, and allowed total effects; they do not claim that any executor
evidence has been observed.

Fixture revisions are allowed during calibration. Promotion into the frozen Alpha
core requires the versioning and review rules in
`docs/contracts/HELIX_CODE_AGENT_ALPHA_CONTRACT.md`.

The targets use only Python's standard library. They are deliberately small:
their purpose is to expose unclear evaluation semantics rather than to measure
framework knowledge.
