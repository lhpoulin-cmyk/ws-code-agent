# Task 10N-C Ollama nonterminal forensics

Date: 2026-08-11

Task 10N historical scoring is unchanged: write `FAIL`, clarification `PASS`,
and production admission `FAIL`. Task 10N-A remains
`DEVSTRAL_COMPLETION_CAUSE_INCONCLUSIVE`; Task 10N-B remains
`DEVSTRAL_OLLAMA_NONTERMINAL_RESPONSE`. This investigation did not run an
admission session or feed diagnostic output to the coding parser/controller.

## Frozen foundation

- ws-code-agent diagnostic foundation:
  `a9dfc296d30d39696b37d61495defb49af683375`
- gpu-compute starting foundation:
  `f7660283c6e1aedbc47884b25921e73ed56c9242`
- gpu-compute diagnostic implementation:
  `10905713bd823f7b143c0ae613b6e20dc1ea42d6`
- gpu-cp: `d9dd4bd6ad2276c3a49a04a26588037a5c44650a`
  (unchanged)
- canonical deployment: `/srv/gpu-compute`
- live Ollama: `0.32.0`, served by `/usr/bin/ollama`
- model:
  `devstral-small-2:24b-instruct-2512-q4_K_M`
- manifest:
  `24277f07f62db8f9cb68e9dfc679ea1818a7fbac47a50eff0a701d3f645b63c8`
- quantization: `Q4_K_M`
- runtime profile: `devstral-small-2-24b-katra-partial`

Before diagnostics, ws-code-agent passed its 120-test Alpha gate and all
protocol, private-material, lineage, invariant, and diff checks. gpu-compute's
unit suites passed, and the deployed machine-response sources were
byte-identical to the repository.

## Documented premise

The [Ollama Generate API documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
describes streaming as a sequence of partial objects followed by a final
object, and non-streaming generation as a single response object. This premise
was recorded without treating the documentation as evidence of what the live
server actually returned.

## Exact Task 10N-B request proof

The Task 10N-B first-turn prompt was reconstructed from its durable supervised
session and verified byte-for-byte:

- prompt SHA-256:
  `9633a2f25e796cde6a6c11e6c3a319271de34ab5963ef12ca2db47d7d18a8395`
- prompt bytes: `3051`
- endpoint: `http://127.0.0.1:11434/api/generate`
- `model`: present with the exact Devstral tag
- `prompt`: present
- `stream`: present with value `false`
- `options`: absent
- `format`: absent
- `raw`: absent
- `keep_alive`: absent

The canonical `OLLAMA_MACHINE_RESPONSE_V1` helper constructs precisely those
fields. No default was inferred for an absent field. The diagnostic helper
used the same prompt bytes, model, and absent generation fields.

## HTTP evidence extension

gpu-compute added evaluator-only `OLLAMA_HTTP_FORENSICS_V1`. It records exact
request field presence, prompt identity, request-body identity, HTTP status and
selected header presence, complete response-body bytes, ordered event bytes,
and concatenated response bytes. It is fixed to loopback `/api/generate`, the
selected Devstral artifact/profile, and the two Task 10N-C diagnostic modes.
It has no coding-parser, executor, candidate, or promotion path.

The deployed helper and focused test matched source:

- `bin/ollama-http-forensics` SHA-256:
  `29b39d7bb9e7920817981d8e95392920e2d7a411051e4686a989fc243758ca14`
- `tests/unit/ollama-http-forensics.py` SHA-256:
  `c1df9f026e7098a1146a53f74237f612579f627aa9ac642f696a12c40d41771c`

## Diagnostic A: non-streaming

Evidence identity:
`task10n-c-nonstream-20260811T133326Z`.

- request body SHA-256:
  `9594973d15b732ff45b6f296fc9ac116c3a248bf31adc602be477f0842e9f565`
- request body bytes: `3238`
- HTTP status: `200`
- Content-Type: `application/json; charset=utf-8`
- Content-Length: present, `300`
- Transfer-Encoding: absent
- Connection: present, `close`
- read outcome: HTTP EOF without read error
- complete body SHA-256:
  `f83089e12e7e6f0f49ad2e9102e30767ca0ba6ef5a01b350b900c713005f3d6b`
- complete body bytes: `300`
- parsed envelope: valid JSON object
- `done`: present, `false`
- `done_reason`: absent
- `error`: absent
- `prompt_eval_count`: absent
- `eval_count`: absent
- response SHA-256:
  `d0c8350bab1b0373a6b4fe928e90ef270349219487a519bc1507833f810e1a96`
- response bytes: `163`
- runtime policy: `GPU_PRIMARY_PARTIAL_OFFLOAD`, 88% GPU / 12% CPU

The 163 response bytes are byte-identical to Task 10N-B's retained partial
response.

## Diagnostic B: streaming

Evidence identity: `task10n-c-stream-20260811T133326Z`.

The only intentional request change was `stream: false` to `stream: true`.

- request body SHA-256:
  `b4bcef530a403cd76ea816730cefdc944af92c0bbe9690ae2307b9355e1fd97b`
- request body bytes: `3237`
- HTTP status: `200`
- Content-Type: `application/x-ndjson`
- Content-Length: absent
- Transfer-Encoding: present, `chunked`
- Connection: present, `close`
- read outcome: HTTP EOF without read error
- complete body SHA-256:
  `94ea19cc3942db6ce7eec57355fd35f2e0659f66030b21b69cffab30081bd01b`
- complete body bytes: `9438`
- events: `73`
- intermediate `done=false` events: `73`
- terminal `done=true` events: `0`
- events with `done_reason`: `0`
- events with `error`: `0`
- events with prompt/eval counts: `0`
- concatenated response SHA-256:
  `d0c8350bab1b0373a6b4fe928e90ef270349219487a519bc1507833f810e1a96`
- concatenated response bytes: `163`
- offline parser result: `MALFORMED_REQUEST` (`response must be one JSON object`)
- runtime policy: `GPU_PRIMARY_PARTIAL_OFFLOAD`, 88% GPU / 12% CPU

The ordered stream reconstructs exactly the same incomplete response returned
by Diagnostic A and retained by Task 10N-B. Streaming did not reveal any later
model text or terminal event.

## Server/runtime evidence

For each diagnostic, Ollama returned HTTP 200 and then logged cancellation and
slot release at the same generation position:

- non-streaming: `n_tokens = 1427`, `truncated = 0`
- streaming: `n_tokens = 1427`, `truncated = 0`

The server log reported a 1,352-token prompt, so both paths ended after the
same 75 generated-token position. There was no explicit API error, Ollama
warning/error, CUDA error, OOM, NVIDIA XID, killed process, failed service, or
wedged server. Ollama remained active and the model remained loaded under its
accepted 88% GPU / 12% CPU profile.

The direct evidence establishes that the stream reached HTTP EOF without a
terminal event. The log evidence further supports the bounded inference that
both handlers stopped/canceled the same runner task rather than the
non-streaming handler merely losing later aggregation events. It does not yet
identify why Ollama/runner stopped that task.

No optional neutral control was run because A/B produced consistent,
non-contradictory transport evidence.

## Classification

`DEVSTRAL_GENERATION_NEVER_TERMINATES_NORMALLY`

The identical non-stream request reproduced `done=false`; the streaming
request then reached EOF after 73 nonterminal events without `done=true`,
`done_reason`, or an explicit API error. This rules out the narrowly proposed
non-stream aggregation-only explanation for this prompt/server/artifact while
leaving the lower-level Ollama/Devstral generation-stop cause unresolved.

`NEXT: INVESTIGATE DEVSTRAL/OLLAMA GENERATION FAILURE`

No admission retry, model tuning, output-budget change, V2/fixture change,
schema forcing, Ollama upgrade, Qwen inference, coding effect, or authority
change occurred.
