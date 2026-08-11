# Task 10N-A Devstral completion forensics

Date: 2026-08-11

This is a forward-only forensic addendum. Task 10N remains unchanged:

```text
write: MALFORMED_REQUEST / FAIL
clarification: PASS
admission: DEVSTRAL_V2_PRODUCTION_ADMISSION_FAIL
```

No Task 10N response, hash, journal, disposition, or score was changed.

## Foundation

- Starting `ws-code-agent`: `845825181633243dd1457cd9ce2ef250a0b44290`.
- Completion-evidence `ws-code-agent` freeze:
  `4a37d9b6b8b92511f7a6d0ac16f6b4c0afe6d6af`.
- Starting `gpu-compute`: `0d8e9f6b9a4ef063e6110808b66f7bcd1e34389f`.
- Completion-evidence `gpu-compute` freeze:
  `37c449d38634061177e44baef6f78d8508a8fd08`.
- `gpu-cp` remained unchanged at
  `d9dd4bd6ad2276c3a49a04a26588037a5c44650a`.

The pre-change baseline passed 114 `ws-code-agent` tests, the complete Alpha
gate, and every `gpu-compute` unit test.

## Historical recovery

Historical invocation:
`alpha-2dde7adbd00b-WORK-t0001-500a19e7034e`.

Linked job:
`job-20260811T045422Z-911382`.

The exact historical invocation retained its response, response SHA-256, job
identity, prompt SHA-256, runtime profile, and success state. The invocation
and job trees did not contain an Ollama API envelope or completion sidecar.
`ollama.log` was empty. The bounded Ollama service journal retained server
activity but no API `done_reason` or response-envelope fields.

The journal showed one HTTP generation request, prompt processing at context
4096, `task.n_tokens = 1349`, final server `n_tokens = 1424`, and
`truncated = 0`. These are server-log observations, not cryptographically
retained API `prompt_eval_count`, `eval_count`, or `done_reason`, and are not
used to infer those values.

```text
HISTORICAL_COMPLETION_CAUSE = UNRECOVERABLE
```

## Evidence repair

`gpu-compute` now retains `OLLAMA_RESPONSE_META_V1` separately from the exact
model response. A successful controlled invocation contains:

```text
evidence/invocations/<invocation>/response.txt
evidence/invocations/<invocation>/ollama-response-meta.json
evidence/<job>/ollama-response-meta.json
```

The response remains the exact UTF-8 bytes decoded from the Ollama `response`
field and keeps its independent SHA-256 identity. The completion sidecar
retains the exact model, terminal flag/reason, prompt/evaluation counts, and
API durations. Its SHA-256 is recorded in both invocation status and linked
job metadata. The transport remains `OLLAMA_MACHINE_RESPONSE_V1`; evidence
retention alone changed.

The helper fails closed for nonterminal, malformed, empty, wrong-model, or
invalid-count envelopes. Synthetic tests cover ordinary `stop`, `length`,
`done=false`, malformed envelopes, missing response, exact response bytes,
sidecar linkage, status visibility, and idempotent replay. `ws-code-agent`
retains the contract ID, sidecar SHA, `done_reason`, `prompt_eval_count`, and
`eval_count` in trusted turn evidence. Those fields are not projected to the
model.

Published source and canonical `/srv/gpu-compute` hashes matched before the
forensic execution. Deployed synthetic envelope and idempotency tests passed.

## One-turn forensic probe

Session:
`work-task10n-a-devstral-forensic-20260811T051637Z`.

The session used the exact Devstral artifact, V2 render, Task 10N write
fixture, authority, context 4096, artifact defaults, runtime policy, and turn
limit. Exactly one logical first-turn invocation was attempted; the session
was not continued or retried.

| Field | Evidence |
| --- | --- |
| Invocation | `alpha-9f9eeab79457-WORK-t0001-511a16f5057b` |
| Job | `job-20260811T051654Z-912991` |
| Prompt SHA-256 | `c8b72147b82983660af6fdee57e452de3c1be9452452ba7591c2f276fef16afa` |
| Remote state | `FAILED_INFERENCE` |
| Machine-response error | `Ollama machine response is not terminal` |
| Response SHA-256 | `NOT_DURABLE` |
| Response byte count | `NOT_DURABLE` |
| Parser result | `NOT_RUN` |
| `done` | not boolean `true`; exact absent/false value not retained |
| `done_reason` | `UNAVAILABLE` |
| `prompt_eval_count` | `UNAVAILABLE` |
| `eval_count` | `UNAVAILABLE` |
| Runtime split | `UNAVAILABLE` for this failed job |
| Duplicate inference count | 0 |

The envelope passed the non-empty response and exact-model checks before the
terminal check failed. Because the helper deliberately does not promote a
nonterminal response as completed evidence, neither response nor sidecar was
committed. The bounded server journal again showed one request, context 4096,
`task.n_tokens = 1352`, final server `n_tokens = 1427`, and `truncated = 0`.
Those log values do not establish an API completion reason.

The probe therefore cannot distinguish ordinary model stop, generation limit,
or another completion cause. Repeating it would violate the one-probe rule.

```text
DEVSTRAL_COMPLETION_CAUSE_INCONCLUSIVE
```

The exact prerequisite for another causal attempt is an independently reviewed
failure-envelope evidence contract that durably records the terminal-field
state without treating `done=false` as successful, followed by separately
authorized fresh forensic execution. No output-budget or model-specific change
is justified by the present evidence.

No V2, prompt, sampling, context, schema, parser, authority, or Qwen execution
changed in this play.
