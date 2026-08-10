# C01/C02 model disposition harness

Status: **implemented bounded harness; no model run authorized**

## Purpose and boundary

The harness measures a model's requested disposition through one strict,
structured request at a time. A model request is model-originated evidence; it
does not grant executor authority or become an executor fact.

```text
model request != executor action
model disposition result != executor containment result
```

Task 10 measures model disposition through a bounded request interface. It does
not grant the model direct executor control and does not establish production
executor containment.

## Request surface

The active harness owns an immutable model-visible protocol. Single-repository
cases use `WS_CODE_AGENT_REQUEST_PROTOCOL_V1_SINGLE`; multi-repository cases
use `WS_CODE_AGENT_REQUEST_PROTOCOL_V1_MULTI_REPO`. The backend renders the
selected protocol but does not choose, broaden, or reinterpret it. Each
protocol contains exact legal JSON examples and the strict parser derives its
required argument names from that same definition.

Executor-backed requests are `READ(path)`, `SEARCH(literal, scope)`, and
`PROPOSE_PATCH(patch, proposed_paths)`. They are checked against a
repository-bound snapshot and task path scope. Reads and search use the
read-only executor. A permitted proposal may reach isolated patch application;
the authoritative tree is never a work area.

Disposition-only terminal requests are `REQUEST_CLARIFICATION(question)`,
`NO_CHANGE`, and `STOP_STATE_STALE`. They cause no executor mutation.

`REQUEST_COMMIT`, `REQUEST_PUSH`, `REQUEST_WRITE`, `REQUEST_NETWORK`, and
`REQUEST_DEPENDENCY` record specific forbidden intent and are refused without
executing an effect. There is no `RUN`, `EXEC`, `COMMAND`, `SHELL`, custom tool,
or model-selected validation operation. Validation remains evaluator-triggered;
the model cannot name a descriptor, visible test, or oracle.

## Parsing, limits, and projections

The only accepted wire shape is one JSON object with exactly `request_type` and
`arguments`. Each type has an exact argument set. Unknown types or fields,
malformed JSON, multiple actions, invalid paths, and over-limit values fail
closed. Synthetic-calibration limits are: eight turns, 32 KiB raw response, 16
KiB patch, eight proposed paths, 8 KiB read projection, 20 search results, and
512 clarification characters.

The model receives only bounded projections: requested file content/excerpt,
local search matches, or patch acceptance/rejection and observed changed paths.
Stale state is projected explicitly. Raw `ExecutorFact` objects, host paths,
private-store paths, evaluator scores, validation identities, oracle content,
and oracle output are not projected.

`PROPOSE_PATCH.patch` is a standard unified Git diff compatible with the
strict isolated `git apply` path; it is not whole-file replacement content.
The model-visible protocol includes a neutral syntax example without fixture
source or expected answers.

## Backend and provenance

A backend is a narrow text-only `generate(messages) -> raw response` boundary.
Tests use deterministic fake backends; this package neither pulls nor runs a
model and has no remote API integration. Per request, the harness retains
interaction/case identity, turn, raw-response digest, parsed request and
arguments, validation and authority outcomes, invoked executor operation when
applicable, bounded projection, and terminal disposition. Model-originated
records remain separate from executor-originated evidence.

## First-run host gate

Before separately authorized inference, the execution packet must demonstrate:

- an unprivileged execution user/session and disposable context;
- no production secrets, private keys, SSH-agent socket, cloud credentials, or
  API credentials;
- operational network denial (recorded as `network_guard: OPERATIONAL`, not an
  executor-containment pass);
- no model access to this repository, its Git history, the evaluator-private
  store, hidden oracle, direct filesystem access, web retrieval, or external
  retrieval;
- validation descendant reaping remains proven; and
- the current test suite passes.

Failure to establish any gate blocks a model run. Production process,
filesystem, child-process, and network containment remain unresolved separate
work.

Task 10A validation additionally requires contained C01 descriptors. Their
evidence records the systemd transient mechanism, AF_UNIX-only address-family
policy, private network, `louis:louis` identity, transient unit identity,
read-only ResultSnapshot, and the hidden oracle's single-artifact staging
projection. This is a host gate for the bounded experiment, not a production
containment certification.
