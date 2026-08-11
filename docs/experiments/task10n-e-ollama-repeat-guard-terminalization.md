# Task 10N-E Ollama repeat-guard terminalization

Date: 2026-08-11

Task 10N, Task 10N-A, Task 10N-B, Task 10N-C, and Task 10N-D evidence
and scoring remain unchanged. This task confirms the already-published bounded
Ollama reporting repair at runtime. It does not reopen Devstral admission,
advance a supervised session, change the V2 protocol, or treat generated
content as a coding request.

## Published foundation

- ws-code-agent starting point:
  `d044ab059e5d02a28c113071a4adfb91bafbc0af`
- gpu-compute implementation:
  `0752c5d11b94df48ed01d78807e1012a53d1f92c`
- gpu-cp acceptance:
  `36851481e841048d7318060fe2a8e2a2c4b7f5b4`
- runtime deviation:
  `OLLAMA_V0_32_0_REPEAT_LIMIT_TERMINALIZATION_V1`

gpu-cp acceptance binds that exact implementation to Ollama
`0.32.0+helix.repeatlimit.1`, binary SHA-256
`b53a386d6e2f8e17a360eb3d08bfc17e3e475d03918d07ace386c359324ef143`,
and build ID `ffd1f9f6c8ffd69fdca1316e7c032447479fe139`.

## Deployment and request identity

The live Katra runtime reported the accepted version, binary hash, and build
ID. All 13 paths changed by the published gpu-compute implementation were
byte-identical in canonical `/srv/gpu-compute`. The live Devstral manifest was:

`24277f07f62db8f9cb68e9dfc679ea1818a7fbac47a50eff0a701d3f645b63c8`

The retained first-turn prompt reconstructed to 3,051 bytes and SHA-256:

`9633a2f25e796cde6a6c11e6c3a319271de34ab5963ef12ca2db47d7d18a8395`

The one forensic confirmation retained:

- invocation:
  `alpha-task10n-e-repeat-forensic-t0001-0752c5d`
- job: `job-20260811T144913Z-941667`
- bounded interval:
  `2026-08-11T14:49:13.529212216Z` through
  `2026-08-11T14:49:50.491278047Z`
- model: `devstral-small-2:24b-instruct-2512-q4_K_M`
- quantization: `Q4_K_M`
- runtime profile: `devstral-small-2-24b-katra-partial`
- execution policy: `GPU_PRIMARY_PARTIAL_OFFLOAD`
- context: `4096`
- temperature: `0.15`
- all other generation settings: unchanged artifact/Ollama defaults

This was the only post-patch forensic Devstral generation. Recovery inspection
found the completed invocation and did not run it again.

## Runtime result

Bounded debug evidence contains exactly one initiating guard line:

```text
prediction aborted, token repeat limit reached
```

The Generate API returned HTTP 200 after `36.405205907 s`. The machine-response
envelope was valid and recorded:

```text
done = true
done_reason = repeat_limit
classification = MODEL_REPEAT_LIMIT
```

Completion evidence:

- contract: `OLLAMA_RESPONSE_META_V2`
- completion metadata SHA-256:
  `ef4c4cc994f958ce566bedc81088681fe496e66848b024f95bc5878f95e0c35a`
- envelope body SHA-256:
  `304c5e4b505a28c97941a1e1aee3fdaf78433da3b2180fc45212ca154995e610`
- envelope body bytes: `7892`
- response present: `true`
- partial-response SHA-256:
  `d0c8350bab1b0373a6b4fe928e90ef270349219487a519bc1507833f810e1a96`
- partial-response bytes: `163`
- prompt/evaluation counts: absent from the repeat-limit terminal callback
- total duration: `36,385,014,648 ns`
- runtime: 12% CPU / 88% GPU on the NVIDIA GeForce RTX 5070 Ti

The controlled invocation state is `FAILED_MODEL_REPEAT_LIMIT`.
`partial-response.txt` is retained as evaluator-only evidence;
`response.txt` is absent. No parser, candidate effect, patch execution,
supervised-session advancement, second turn, or retry occurred.

## Restoration and gates

The temporary `OLLAMA_DEBUG=1` drop-in was removed. The restored service
environment contains only `OLLAMA_MODELS`, `OLLAMA_HOST`, and
`CUDA_VISIBLE_DEVICES`. Ollama is active, `/api/version` reports the accepted
patched version, systemd reports no failed units, and the GPU remained healthy.

All eight gpu-compute unit gates passed. The first ws-code-agent gate attempt
inside the managed sandbox ran all 120 tests but reported four real-systemd
tests as containment unavailable. The unchanged gate then ran through the
approved host containment path: all 120 tests passed, the separate two-test
private-material check passed, lineage verification passed, the invariant
register passed, and `git diff --check` passed.

## Disposition

The live repaired runtime truthfully terminalized the same repeated-token
guard previously shown to close nonterminally. The model degeneration remains
a failed model outcome, not a successful coding response or infrastructure
failure.

`TASK 10N-E COMPLETE — OLLAMA REPEAT-GUARD TERMINALIZATION REPAIRED AND GOVERNED`

No challenger was started, no Devstral admission was rerun, and no Qwen
inference occurred.
