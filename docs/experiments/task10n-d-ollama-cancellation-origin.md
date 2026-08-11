# Task 10N-D Ollama cancellation origin

Date: 2026-08-11

Task 10N, Task 10N-A, Task 10N-B, and Task 10N-C evidence and scoring
remain unchanged. This investigation used the already-retained Task 10N-C
HTTP stream and live read-only service/source evidence. No additional model
generation was required.

## Foundation

- ws-code-agent: `dc9ee920500cae0f8ab3b3f3a0d5478c242a96cc`
- gpu-compute: `10905713bd823f7b143c0ae613b6e20dc1ea42d6`
- gpu-cp: `d9dd4bd6ad2276c3a49a04a26588037a5c44650a`
- Ollama: `0.32.0`
- `/usr/bin/ollama` SHA-256:
  `e010ce570cfa04334b30867c228a45781857b2ff5071630f3f59ef7cc2513d1f`
- ELF build ID: `0e105e59ddca69a63978644d2a642122f2c14da5`
- canonical deployment: `/srv/gpu-compute`, diagnostic helper/test hashes
  equal source

ws-code-agent's 120-test Alpha gate and all current protocol, private,
lineage, invariant, and diff checks passed. All seven gpu-compute unit suites
passed. All repositories began clean and at origin parity.

## Client deadline audit

The Task 10N-C helper calls Python `urllib.request.urlopen` with a 180-second
socket timeout. It has no separate connect timeout, overall request deadline,
subprocess deadline, shell `timeout`, or systemd request unit. The fetch is not
wrapped by a timed subprocess. SSH keepalives do not impose a command deadline.

The observed API-handler durations were:

- non-streaming: `17.930120887 s`, including cold model load
- streaming: `7.751535010 s`, reusing the loaded runner

Both are far below 180 seconds. Both reads ended as HTTP EOF without a timeout,
read exception, broken pipe, connection reset, or client-cancel indication.
Task 10N-C wrote complete response bodies after EOF.

Derived from the precise GIN completion timestamp and duration, HTTP handling
began at approximately:

- non-streaming: `2026-08-11T13:34:07.933875113Z`
- streaming: `2026-08-11T13:34:39.579486990Z`

The streaming handler returned at `13:34:47.331022Z`. The client had completed
the body read before creating `http-body.bin` at `13:34:47.347733796Z`.
Client-side cancellation is excluded.

## Service and resource audit

The service is `/etc/systemd/system/ollama.service` with one drop-in. It runs
`/usr/bin/ollama serve` as `ollama:ollama`, binds loopback, and uses the mounted
model store. Its only configured environment entries are:

- `OLLAMA_MODELS=/mnt/models/library`
- `OLLAMA_HOST=127.0.0.1:11434`
- `CUDA_VISIBLE_DEVICES=0`

The following were absent, not default-inferred:

- `OLLAMA_CONTEXT_LENGTH`
- `OLLAMA_KEEP_ALIVE`
- `OLLAMA_LOAD_TIMEOUT`
- `OLLAMA_NUM_PARALLEL`
- `OLLAMA_MAX_LOADED_MODELS`
- `OLLAMA_MAX_QUEUE`
- `OLLAMA_FLASH_ATTENTION`
- `OLLAMA_KV_CACHE_TYPE`
- `OLLAMA_GPU_OVERHEAD`
- `OLLAMA_DEBUG`

The unit has `Restart=always`, `RestartSec=3s`, and 90-second service start/stop
timeouts. Those lifecycle timeouts do not bound requests. CPU, address-space,
resident-memory, and cgroup memory limits are unlimited; `cpu.max` is
unlimited. The cgroup reported no OOM or OOM kill, no swap use, and no memory
high/max events. The service remained active with no failed units. The bounded
kernel/service window contained no OOM-killer event, NVIDIA XID, CUDA error,
segfault, service restart, panic, or fatal runner error.

## Request, scheduler, and runner ownership

Ollama v0.32.0 passes the Gin HTTP request context through scheduler allocation
and into `llamaServerRunner.Completion`. The runner `/completion` request is
created with the same context. The scheduler watches that context only to
release its runner reference after the request finishes.

For the first Task 10N-C request, llama-server loaded successfully, slot 0
started task 0, and prompt evaluation completed. It remained healthy after the
request. The second request selected the same slot and runner by prompt-cache
similarity (`1.000`) and ran as task 80. `ollama ps` immediately after each
diagnostic reported the same loaded 16 GB model at 12% CPU / 88% GPU with
context 4096. The runner PID was not retained in the historical log, but runner
reuse and post-request loaded state prove it neither exited nor crashed at the
first cancellation. After the second cancellation it again remained loaded
until normal keep-alive expiration.

The scheduler did not initiate the abort. It observed request-context
completion after the API handler returned, decremented the reference count,
and left the healthy runner available. Slot 0 released cleanly with
`truncated = 0` and returned idle.

## Exact internal trigger

The installed binary contains the exact diagnostic string `prediction
aborted, token repeat limit reached`. The matching v0.32.0 source is in
`llm/llama_server.go`.

For every llama-server fragment, Ollama compares
`strings.TrimSpace(lsResp.Content)` with the prior fragment. Once the repeat
counter is greater than 30, it aborts before forwarding the triggering
fragment. Critically, that branch returns `ctx.Err()`. In this case the request
context was healthy, so `ctx.Err()` was `nil`.

That nil return caused the GenerateHandler completion goroutine to close its
response channel without an error or `Done` callback. Both the non-streaming
aggregator and streaming writer therefore returned HTTP 200 with the last
ordinary response still carrying `done=false`. Handler return then canceled
the shared request context; that downstream cancellation caused llama-server's
later `cancel task` and slot release logs. The log word `cancel` is therefore a
consequence, not the initiating layer.

This is the precise ordering implied by the source and observed timestamps:

1. Ollama's internal repeat guard returns nil.
2. The response channel closes without a terminal event.
3. The API handler returns HTTP 200 and the client receives EOF.
4. Request-context teardown cancels the runner HTTP request.
5. llama-server logs `cancel task` and releases the slot.

## Token boundary and stop analysis

- prompt tokens: `1352`
- runner stop position: `n_tokens = 1427`
- generated position difference: `75`
- context: `4096`
- request `num_predict`: absent
- Ollama default `NumPredict`: `-1`
- v0.32.0 open-ended runner bound: `10 * 4096 = 40960`
- batch and micro-batch: `512`; neither is the 75-token boundary
- runner truncation: `0`
- configured model parameter: temperature `0.15` only
- configured stop strings: none

The retained stream contains 73 forwarded fragments. Events 43 through 73 are
31 consecutive one-byte `"0"` fragments. The next repeated fragment crosses
the `>30` repeat threshold before it can be forwarded, explaining both the
stable stop point and missing terminal event.

The exact tokenizer metadata records:

- BOS token ID: `1`
- EOS token ID: `2`
- padding token ID: `11`
- unique `"0"` token ID: `1048`, token type `1` (ordinary)

The final 16 retained fragments are all `"0"`, hence all map to ordinary token
1048. They are not EOS, EOG, or a template stop. No valid stop condition was
lost. This is not a stop-token handling defect.

## Chronology: Task 10N-C streaming diagnostic

1. `13:34:39.579486990Z` — API request begins (derived from the precise handler
   completion and duration).
2. `13:34:39.880169Z` — existing runner/slot 0 selected; task 80 starts.
3. `13:34:39.890242Z` — prompt cache/evaluation and sampler initialization
   complete at 1,352 prompt tokens.
4. Before `13:34:47.331022Z` — fragment 73, the 31st forwarded consecutive
   `"0"`, is produced. Per-fragment wall timestamps were not retained by the
   Task 10N-C buffered helper.
5. Before `13:34:47.331022Z` — the next repeated `"0"` trips Ollama's internal
   repeat guard; `ctx.Err()` returns nil, closing the response channel.
6. `13:34:47.331022Z` — Gin records HTTP 200 handler completion after
   `7.751535010 s`.
7. By `13:34:47.347733796Z` — the client observes EOF and begins persisting the
   complete 9,438-byte body.
8. `13:34:47.431771Z` — llama-server receives downstream `cancel task` for
   task 80.
9. `13:34:47.544019Z` — slot 0 releases at `n_tokens=1427`, `truncated=0`, and
   becomes idle.

No debug reproduction was run because the retained fragment sequence, exact
source branch, installed-binary string, and chronology identify the initiating
layer without another generation.

## Published-source comparison

The official Ollama v0.32.0 tag resolves to
`f1a0ffd6219b5ef82aee77254f895b383efb5486`. Its
[`llm/llama_server.go`](https://github.com/ollama/ollama/blob/v0.32.0/llm/llama_server.go#L1640-L1652)
contains the repeat guard and nil `ctx.Err()` return described above.

The current published main source inspected at
`96fb6d2fa9944bb76e2c5c3f73086a12457b301b` retains the same relevant branch;
no post-v0.32.0 fix was found in this path. Existing upstream reports also
describe repeated ordinary output followed by this guard and a nonterminal
`done=false` response in both streaming and non-streaming modes
([Ollama issue #8517](https://github.com/ollama/ollama/issues/8517)). No Ollama
upgrade or alternate binary was tested.

## Classification

`OLLAMA_INTERNAL_GENERATION_CANCELLATION_CONFIRMED`

`ROOT_TRIGGER = TOKEN_REPEAT_GUARD_RETURNED_NIL_WITHOUT_TERMINAL_EVENT`

The model entered a repeated ordinary-token sequence. Ollama's internal
llama-server completion wrapper deliberately aborted it, but returned nil and
failed to emit either a terminal response or an error. API and runner
cancellation followed that internal decision.

`NEXT: ISOLATE OLLAMA GENERATION-ENGINE DEFECT`

No admission retry, model tuning, Ollama upgrade, generation-setting change,
V2/fixture change, Qwen inference, operational repair, or authority broadening
occurred.
