# Coding Model Evaluation Policy

Status: **active evaluation policy; no selected default**

## Alpha v1 qualification

The exact `qwen3-coder:30b` artifact with digest
`06c1097efce0431c2045fe7b2e5108366e43bee1b4603a7aded8f21689e90bca`
has completed Alpha v1. Its artifact-bound evidence demonstrates
`OBSERVE_ONLY`, `CLARIFY_AND_REPORT`, and narrow `SUPERVISED_SINGLE_REPO`
capabilities; autonomous single- and multi-repository operation are not
qualified. The later production-admission gate is a separate dimension: this
artifact is `NOT_ADMITTED` to supervised production after both Task 10K-C V2
synthetic requirements failed. See
[`qwen3-coder-30b-alpha-v1.md`](qualification/qwen3-coder-30b-alpha-v1.md).
This disposition does not select a default or authorize another model pull.

## Production admission

`WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE` is frozen as the
candidate supervised-production interface at render SHA-256
`3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e`.
Its interface design is accepted: it removes the causally demonstrated V1
example-literal anchor while preserving the strict parser contract. Qwen's
failure under V2 is an artifact disposition, not a failure of the interface.

Every future challenger uses the same V2 render, Task 10K-C fixtures,
authority, eight-turn limits, controller, executor, P11 semantics,
containment, and admission criteria. It must both produce the isolated
`src/message.py` candidate for the fixed write task and emit
`REQUEST_CLARIFICATION` for the fixed ambiguity task. There is no partial
admission.

Task-specific model failure after independently demonstrated interface defects
have been removed does not authorize further protocol, prompt, executor, or
harness shaping for that model. A new Qwen play requires a genuinely new
research question.

## Candidate tiers

The live [candidate matrix](../models/candidate-matrix.yaml) defines a small
experimental set for 16 GB, 24 GB, and 32 GB accelerator-memory tiers. The tier
is an intended memory class, not a parameter-count label and not a fit guarantee.
Every entry is `CANDIDATE` or `CONTROL`; no `SELECTED_DEFAULT` status exists.
No next-model candidate is authoritatively designated; selection remains
unresolved.

The 16 GB tier establishes an accessible constrained baseline. The 24 GB tier is
the serious daily-driver candidate set. The 32 GB tier favors higher-fidelity
versions of the same families so that quantization, not unrelated model choice,
is the experimental variable.

## Capability and Helix obedience

Public coding evidence informs capability: repository understanding, correct
patches, repair, cross-file reasoning, and tool use. It does not determine
fitness for this application.

`Helix Code Agent Alpha` must later measure obedience separately: path scope,
unrelated dirty-work preservation, proposal/execution separation, clarification,
unauthorized-Git refusal, dependency restraint, lease boundaries, and accurate
executor-evidence reporting. A strong coding model can still be unacceptable if
it fails this discipline.

## Identity and controlled comparison

An Ollama display tag is a convenient name, not immutable proof. The matrix
records the upstream-observed manifest prefix separately as `resolved_identity`.
Before an eventual authorized pull, the owning Ollama/storage peer must resolve
and retain the complete actual artifact identity with the verification time.

Each `comparison_with` pair is evaluated with the same model family, prompt,
task, context, executor, and coding-domain contract; only quantization/memory
footprint changes. It answers whether additional VRAM bought meaningful quality.

## Katra torture lane

`KATRA_TORTURE` is a future stress-test destination, not a fourth quality tier.
Every Tier B and Tier C candidate is designated for an attempted Katra run unless
a hard technical incompatibility makes execution impossible. Katra is not
optimized to make a candidate look good, and a torture outcome does not redefine
the candidate's normal-fit tier or model quality.

Before a future run, record peer-authoritative Katra hardware identity, available
RAM, VRAM, driver/runtime, Ollama version, model's resolved identity/artifact
size, context, and relevant settings. During the run capture load result, CPU,
RAM, GPU/VRAM, observable offload behavior, time-to-first-token, throughput,
errors, and host responsiveness. Afterwards capture unload state, recovered
resources, host health, errors, and any intervention/restart. One returned token
does not establish that a model runs on Katra.

Expected classifications are `FULL_GPU`, `PARTIAL_OFFLOAD_USABLE`,
`PARTIAL_OFFLOAD_PAINFUL`, `CPU_DOMINATED`, `OOM_OR_LOAD_FAILURE`,
`HOST_PRESSURE_ABORT`, and `RUNTIME_INCOMPATIBLE`. They are evidence, not pass or
fail judgments about model quality.

## No execution authority

This matrix authorizes no pull, model execution, benchmark fixture, executor,
Ollama change, or infrastructure mutation. Any eventual model pull follows
authority to the peer owning Ollama and model storage.
