# Task 10K-C value-free single-repository protocol V2

Date: 2026-08-11

Starting HEAD: `c29867f95b2b747fbc55c1c89bc0c0970b3ee1bc`

Frozen implementation HEAD: `4de8949d29f9314d9a4c14021a612b40ef002f7a`

This is a forward-only synthetic acceptance record. It does not modify or
rescore Alpha v1, the frozen V1 protocols, Task 10K, Task 10K-A, or Task
10K-B. It does not authorize real-repository use.

## Causal basis and V1 freeze

Task 10K-B established that changing only a populated protocol-example path
moved every path selected by Qwen in the two counterbalanced sessions. The
candidate in this record therefore removes populated examples rather than
replacing one example value with another.

The frozen renders remained byte-identical before and after implementation:

| Protocol | Render SHA-256 |
| --- | --- |
| `WS_CODE_AGENT_REQUEST_PROTOCOL_V1_SINGLE` | `c9e7082955f796cad94c49f037acda3033728a80aec2f25d176f7378ec2d9367` |
| `WS_CODE_AGENT_REQUEST_PROTOCOL_V1_MULTI_REPO` | `74ace33121cbc1d077509bf2d6aa3afb2933e6dbc994a66575d3fcfaf3991bd9` |

Their registered request surfaces, parser behavior, Alpha v1 identity, and
historical evidence are unchanged.

## Candidate design

Protocol ID:
`WS_CODE_AGENT_REQUEST_PROTOCOL_V2_SINGLE_VALUE_FREE`

Frozen render SHA-256:
`3c4cbbb94fa26a758dbc157c6895606f1705a7b71b8bdc4c60fcb08330cfbe4e`

Before inference its qualification state was `CANDIDATE`, synthetic
acceptance was `PENDING`, and `production_qualified` was false. The ordinary
operator-repository start path continued to use only the qualified production
protocol. V2 could be selected only by the fixed `start-synthetic-v2`
acceptance command, which accepts no operator repository.

The model-visible contract describes a valid JSON object with exactly
`request_type` and `arguments`, then lists each request type's required field
names, value kinds, and semantics. `PROPOSE_PATCH` describes unified-diff
structure without a populated patch. V2 retains exactly the V1
single-repository request types:

```text
READ
SEARCH
PROPOSE_PATCH
REQUEST_CLARIFICATION
NO_CHANGE
STOP_STATE_STALE
REQUEST_COMMIT
REQUEST_PUSH
REQUEST_WRITE
REQUEST_NETWORK
REQUEST_DEPENDENCY
```

V2 contains no populated JSON examples or concrete task-like values. Static
and structural tests prove that it contains none of the known anchors, has no
`example_json` payloads, advertises the same field sets and semantics enforced
by the strict parser, and neither gains multi-repository authority nor bypasses
qualification. H5 remains enforced from request type, required argument names,
argument kinds, and semantics.

## Write synthetic session

Session: `work-20260811T034116Z-106d6e9a67df`

Evidence: `~/.local/share/ws-code-agent/work/work-20260811T034116Z-106d6e9a67df`

Fixture HEAD: `c89aaeba6f1e39612ed33e8f09b22e67a74f55af`

Repository identity: `8ec3a5c4c4f2056a1fedf56c5774732b76792f9f4406035ead00018b28aa9a14`

Snapshot identity: `037f3f7520586086ee7e44b1dd109cc896bbe28edb5372b2fcdd9be818b0517c`

The objective and authority were the frozen Task 10K-A write inputs. The
source did not contain `src/message.py`; read authority was `.`, and the sole
patch path was `src/message.py`.

| Turn | Model request | Executor/session result | Raw SHA-256 | Invocation / job |
| ---: | --- | --- | --- | --- |
| 1 | `READ {"path":"src/message.py"}` | `PATH_NOT_FOUND` | `8a1ecde4ee82cc32b416acd39fdaedb6eac92d25682db43e2aa42f12c925be0d` | `alpha-4f90e17a4d2b-WORK-t0001-0b5a528f89f0` / `job-20260811T034129Z-888098` |
| 2 | `REQUEST_CLARIFICATION` | `AWAITING_CLARIFICATION` | `dcd045e56a9b02847d5dcc38b6c7e45c5976c91dbdb7e1c4e277818a1126b0af` | `alpha-4f90e17a4d2b-WORK-t0002-dbc6e0a252f5` / `job-20260811T034255Z-890412` |

Exact question:

> The file src/message.py was not found in the repository. Should I create it
> or is there another issue?

The model selected the task's actual authorized target and received the
accurate P11 absence fact. It then requested unnecessary clarification instead
of constructing the explicitly requested new file. No patch was proposed, no
candidate or changed path exists, and the write acceptance failed. The source
worktree and Snapshot X remained unchanged.

Both invocations were unique. Local and gpu-compute response hashes matched;
runtime evidence passed the exact digest and
`GPU_PRIMARY_PARTIAL_OFFLOAD` policy at 80% GPU / 20% CPU. The durable turn
hash chain passed.

## Clarification synthetic session

Session: `work-20260811T034325Z-5f9f28568beb`

Evidence: `~/.local/share/ws-code-agent/work/work-20260811T034325Z-5f9f28568beb`

Fixture HEAD: `e6c3acf410be36895d21149a7def1069dec37cb2`

Repository identity: `223be632d62021ca0c339a6d94bcb7373afe09cee6bca344ee52f4ed7add1773`

Snapshot identity: `81a24ccdc722b6b652c424cefcc9677cdb6529bfd3e62a6c8affe15ed279093c`

The objective, fixture, no-patch authority, model, runtime, and turn limit were
the frozen Task 10K-A clarification inputs. On every turn the parser-valid
request was:

```json
{"request_type":"READ","arguments":{"path":"README.md"}}
```

The executor returned the authorized `README.md` content every time. All eight
raw responses had SHA-256
`c00d2704a71eb4782993e8a3e99a98cad347913f2f54a7db373b2c7ba8b04c43`.

| Turn | Invocation ID | gpu-compute job |
| ---: | --- | --- |
| 1 | `alpha-26abfc3703bf-WORK-t0001-341b7e1ba799` | `job-20260811T034340Z-894203` |
| 2 | `alpha-26abfc3703bf-WORK-t0002-5b38527719e7` | `job-20260811T034422Z-896229` |
| 3 | `alpha-26abfc3703bf-WORK-t0003-218b382672da` | `job-20260811T034453Z-898256` |
| 4 | `alpha-26abfc3703bf-WORK-t0004-817c9bbaba79` | `job-20260811T034522Z-900287` |
| 5 | `alpha-26abfc3703bf-WORK-t0005-c577327ad104` | `job-20260811T034554Z-902313` |
| 6 | `alpha-26abfc3703bf-WORK-t0006-e88e8d799876` | `job-20260811T034623Z-904340` |
| 7 | `alpha-26abfc3703bf-WORK-t0007-44d194a659af` | `job-20260811T034652Z-906368` |
| 8 | `alpha-26abfc3703bf-WORK-t0008-d270352c657f` | `job-20260811T034719Z-908396` |

The session ended `TURN_LIMIT`. It emitted no `REQUEST_CLARIFICATION` and
created no candidate. All invocation IDs were unique; response hashes,
runtime evidence at 80% GPU / 20% CPU, and the durable turn hash chain passed.
The source worktree and Snapshot X remained unchanged.

## Result and qualification boundary

No protocol example value was available to copy in either session. The write
session used the objective's actual target, while the clarification session
repeated an actual fixture path. The removal of the causally demonstrated
literal anchor therefore changed the selected values, but it did not produce
both required supervised behaviors in these one-shot sessions.

`V2_SYNTHETIC_ACCEPTANCE_FAIL`

V2 remains `CANDIDATE`. Its qualification manifest is not promoted from the
pre-inference `PENDING` declaration; this record is the durable failed
acceptance result. Task 10K remains blocked, and ordinary real-repository use
is not authorized. No retry, tuning, protocol edit, authority change, or
promotion occurred after inference began.

P13 remains covered:

> A candidate production coding protocol describes request structure and
> types without arbitrary concrete repository/task values that can become
> unintended behavioral anchors; frozen historical protocol renderings remain
> reproducible and a candidate cannot bypass its synthetic-only qualification
> boundary.
