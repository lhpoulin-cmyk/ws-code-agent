# Helix Alpha calibration fixtures

These five synthetic fixtures pressure the Helix Code Agent Alpha evaluation
contract before cases are frozen. They are not the frozen Alpha benchmark, a
benchmark runner, an executor, or model results. No model, validation executor,
or containment layer has run them; containment is `NOT_TESTED`.

`cases/<case>/target/` is the future model-visible synthetic repository material.
`oracles/` is evaluator-only material and must not be exposed to a tested model,
even though both are versioned in this repository. Case documents also describe
future initial state, authority, allowed total effects, and expected evidence;
they do not claim that any such evidence has been observed.

Fixture revisions are allowed during calibration. Promotion into the frozen Alpha
core requires the versioning and review rules in
`docs/contracts/HELIX_CODE_AGENT_ALPHA_CONTRACT.md`.

The targets use only Python's standard library. They are deliberately small:
their purpose is to expose unclear evaluation semantics rather than to measure
framework knowledge.
