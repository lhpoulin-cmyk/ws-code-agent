# Task 10N-B Devstral failure-envelope evidence

Date: 2026-08-11

Task 10N historical scoring is unchanged: write `FAIL`, clarification `PASS`,
and production admission `FAIL`. Task 10N-A remains the authoritative
inconclusive forensic record for its own evidence contract. This addendum does
not rescore either experiment.

## Frozen repair

- ws-code-agent: `52d4047ed121b4aea39b43834de45e86a6e40de5`
- gpu-compute: `f7660283c6e1aedbc47884b25921e73ed56c9242`
- gpu-cp: `d9dd4bd6ad2276c3a49a04a26588037a5c44650a` (unchanged)
- gpu-compute deployment: canonical `/srv/gpu-compute`, with the deployed
  helper, runner, status helper, and focused tests byte-identical to source

`OLLAMA_MACHINE_RESPONSE_V1` generation transport is unchanged. The new
evaluator-only `OLLAMA_RESPONSE_META_V2` contract records field presence and
value before terminality enforcement. Only a valid terminal envelope creates
`response.txt`. An explicit nonterminal envelope instead retains exact
non-empty bytes as `partial-response.txt`, binds its hash and the completion
sidecar hash to the invocation/job, and fails closed. No completion evidence is
model-visible.

E10 removes the controller's former Qwen intent label. Durable inference intent
now records the backend-owned model tag, manifest digest, quantization,
runtime-profile ID, and execution policy. Recovery re-derives those fields from
the selected backend and fails with `DURABLE_MODEL_BINDING_MISMATCH` before a
remote call if they differ.

## One-shot forensic generation

Exactly one first-turn generation used the unchanged Task 10N write contract.
The session was not advanced to turn 2 and is not an admission retry.

- session: `work-task10n-b-devstral-forensic-20260811T131549Z`
- fixture: `task10k-c-write/synthetic-v1`
- protocol: `WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE`
- model: `devstral-small-2:24b-instruct-2512-q4_K_M`
- manifest digest: `24277f07f62db8f9cb68e9dfc679ea1818a7fbac47a50eff0a701d3f645b63c8`
- quantization: `Q4_K_M`
- runtime profile: `devstral-small-2-24b-katra-partial`
- invocation: `alpha-3048873af9bf-WORK-t0001-15d32d1387aa`
- job: `job-20260811T131614Z-920492`
- prompt SHA-256: `9633a2f25e796cde6a6c11e6c3a319271de34ab5963ef12ca2db47d7d18a8395`
- completion metadata SHA-256: `f7ce27f6446fe18262080683e224dbc8a8db69686be2462c0709430808724b97`
- partial response SHA-256: `d0c8350bab1b0373a6b4fe928e90ef270349219487a519bc1507833f810e1a96`
- partial response bytes: `163`
- envelope body SHA-256: `1a73a5c704a59ed77cb1e0e2c9b18aa56e15402b574fd23366f2cf667a41057f`
- envelope body bytes: `299`
- `done` present: `true`
- `done`: `false`
- `done_reason` present: `false`
- `done_reason`: absent
- `prompt_eval_count` present: `false`
- `eval_count` present: `false`
- runtime: `GPU_PRIMARY_PARTIAL_OFFLOAD`, 88% GPU / 12% CPU
- remote state: `FAILED_OLLAMA_NONTERMINAL_RESPONSE`
- successful response artifact: absent
- parser result: `NOT_RUN_NONTERMINAL_RESPONSE`
- candidate/effect: absent; synthetic source repository unchanged

The retained partial bytes begin a `PROPOSE_PATCH` envelope and terminate inside
the unified-diff string. They are evaluator-only failure evidence and were not
fed to the parser as a completed inference.

## Classification

`DEVSTRAL_OLLAMA_NONTERMINAL_RESPONSE`

The evidence establishes explicit `done=false`; it does not establish an
ordinary model stop or a generation-length termination. The bounded next step
is:

`NEXT: INVESTIGATE OLLAMA NONTERMINAL MACHINE-RESPONSE BEHAVIOR`

