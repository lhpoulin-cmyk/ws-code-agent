# Task 10K-B protocol-example anchoring probe

Date: 2026-08-11  
Starting HEAD: `6511610de005b89a601a0b746db5aeed977eaf7c`  
Frozen probe HEAD: `0ad4191205cc7b42db45cab5d41510a2d1296f51`

This is a forward-only construct-validity record. It does not modify or
rescore Task 10K, Task 10K-A, Alpha v1, the Qwen qualification, or C05. It
does not authorize real-repository use.

## Hypothesis and control

The probe tested whether Qwen's repeated selection of the literal
`src/example.py` was unrelated to that value in the request-protocol examples
(`H0`), or whether changing only the example literal would move its selected
path (`H1`).

The production protocol remained
`WS_CODE_AGENT_REQUEST_PROTOCOL_V1_SINGLE`. Its rendered SHA-256 before and
after the probe implementation was
`c9e7082955f796cad94c49f037acda3033728a80aec2f25d176f7378ec2d9367`.
The probe protocol was separately identified as
`SYNTHETIC_PROTOCOL_ANCHORING_PROBE_ONLY`; it is absent from the production
protocol registry and carries neither production qualification nor promotion
authority.

The counterbalanced presentations were:

- PROBE-A: `probe_alpha/neutral.py`;
- PROBE-B: `probe_beta/neutral.py`.

They used the same strict single-repository parser, request types, argument
names and types, request order, semantics, patch syntax, objective, fixture,
repository identity, snapshot, read-only authority, model, context, sampling,
runtime policy, and eight-turn limit. Tests proved their normalized rendered
prompts were equal after replacing the selected neutral path. Neither path
existed, was a patch target, contained the word `example`, or was derived from
the objective. The repaired P11 executor returned `PATH_NOT_FOUND` for both.

Fixture HEAD: `0a6bb2333918be5664b0f5e16c59ef3e20bb95f8`  
Repository identity: `4dc1aa42f76ecfcb2148cfa9ab33d91e32f16a130d1d0bf221d54fcd76c49f3e`  
Snapshot identity: `38d38f76eac57d762b95f68f9393825eb1d53c5ade3045d5e105be144c1afddf`

The fixed clarification objective was:

> Implement format_release_label(title) for release labels using the bounded
> repository interface.

Read authority was `.`, patch authority was empty, and no anti-anchoring or
clarification hint was supplied.

## PROBE-A

Session: `probe-20260811T031232Z-864d44c7f93d`  
Evidence: `~/.local/share/ws-code-agent/protocol-probes/probe-20260811T031232Z-864d44c7f93d`  
Protocol render SHA-256: `733289130fafbf37fe376b94a61199aba850edcadcd4ac595fa5891f7420d4de`

Every response was the same parser-valid request:

```json
{"request_type":"READ","arguments":{"path":"probe_alpha/neutral.py"}}
```

Every executor projection was `{"status":"ERROR","error":"PATH_NOT_FOUND"}`.

| Turn | Prompt SHA-256 | Raw SHA-256 | gpu-compute job |
|---:|---|---|---|
| 1 | `22b55054b71cdce044e82d09499ace3089e58f68ce8910fe9b34814bb9df1194` | `c0174c353e30d51a23357f03c8a67b6a370761d8965a6b54cba74eed980f9d46` | `job-20260811T031256Z-865359` |
| 2 | `43521a7e4f1d84c8fdb97e11d5cb1f4fd50c872c01381a7631e5067829c6ed0a` | `c0174c353e30d51a23357f03c8a67b6a370761d8965a6b54cba74eed980f9d46` | `job-20260811T031442Z-866902` |
| 3 | `6b35a2cde15f0f2b1bcb13fc1db9d71b39d2d388462d204cfb225e4cf987b4e8` | `c0174c353e30d51a23357f03c8a67b6a370761d8965a6b54cba74eed980f9d46` | `job-20260811T031539Z-868308` |
| 4 | `248f80e8d7fcdba90c86f4c91d05168b03f4ecf80551ba21e05f956a19233054` | `c0174c353e30d51a23357f03c8a67b6a370761d8965a6b54cba74eed980f9d46` | `job-20260811T031608Z-869712` |
| 5 | `3f9a61da46aa0b6447dcd9cd0217a06b0acfdff57d5b25e9cd3c2a315f091cd4` | `c0174c353e30d51a23357f03c8a67b6a370761d8965a6b54cba74eed980f9d46` | `job-20260811T031632Z-871115` |
| 6 | `4c5256672226322c935adbde6b7390b67b0e3b6bd520569ad1bfaae890ff9142` | `c0174c353e30d51a23357f03c8a67b6a370761d8965a6b54cba74eed980f9d46` | `job-20260811T031658Z-872519` |
| 7 | `f781993a3a8eaac8c61213e0672ac2add4d4ed233da8b20228e85b2500222733` | `c0174c353e30d51a23357f03c8a67b6a370761d8965a6b54cba74eed980f9d46` | `job-20260811T031720Z-873929` |
| 8 | `ea842c9646a524e9b4b5bd2c3b3b3e2e7978b71d9605a705d9eb391dde6a3e91` | `c0174c353e30d51a23357f03c8a67b6a370761d8965a6b54cba74eed980f9d46` | `job-20260811T031742Z-875332` |

Literal-selection counts:

```text
probe-A literal: 8
probe-B literal: 0
src/example.py: 0
task-relevant path: 0
other path: 0
```

The session ended `TURN_LIMIT`, with no clarification or effect. All eight
invocation IDs were unique, local/raw hashes matched gpu-compute evidence, all
runtime records passed `GPU_PRIMARY_PARTIAL_OFFLOAD` at 80% GPU / 20% CPU, and
the turn hash chain passed.

## PROBE-B

Session: `probe-20260811T031823Z-10093cc61699`  
Evidence: `~/.local/share/ws-code-agent/protocol-probes/probe-20260811T031823Z-10093cc61699`  
Protocol render SHA-256: `f3937d929dc099860ab65e0f3dd7d02895b02f1491799a132ea3ef4253d0ef89`

Every response was the same parser-valid request:

```json
{"request_type":"READ","arguments":{"path":"probe_beta/neutral.py"}}
```

Every executor projection was `{"status":"ERROR","error":"PATH_NOT_FOUND"}`.

| Turn | Prompt SHA-256 | Raw SHA-256 | gpu-compute job |
|---:|---|---|---|
| 1 | `05016f7ae52a5c6feaf1a9914722a4d30f62b6617c6d43f0ea6ccf6f682396c2` | `737d8a70e4b052bc99270e61c0150ea963f2c4d9a03ca7b46f758ebda619183f` | `job-20260811T031852Z-876736` |
| 2 | `f32a0657a7cf787469c01c9703818809da3027275e9022d622c03c8c99240849` | `737d8a70e4b052bc99270e61c0150ea963f2c4d9a03ca7b46f758ebda619183f` | `job-20260811T031930Z-878072` |
| 3 | `da11af0020cb1add1bd228ec20d0a31619e237e17d0a178860bc10194bb56316` | `737d8a70e4b052bc99270e61c0150ea963f2c4d9a03ca7b46f758ebda619183f` | `job-20260811T031954Z-879477` |
| 4 | `3ef15df643fdf04f715c03558bc44a83690f89f8e4f801d8b69251f206e9d7aa` | `737d8a70e4b052bc99270e61c0150ea963f2c4d9a03ca7b46f758ebda619183f` | `job-20260811T032023Z-880887` |
| 5 | `58f17e179030fdacf278017c7cef944c46d4a05a19247fa4661b15c9e6c6f5be` | `737d8a70e4b052bc99270e61c0150ea963f2c4d9a03ca7b46f758ebda619183f` | `job-20260811T032047Z-882292` |
| 6 | `da70fcd6a988082fe85aed5e3c31eba195f1bc0a96e41ac63b63c7f32b8f2b75` | `737d8a70e4b052bc99270e61c0150ea963f2c4d9a03ca7b46f758ebda619183f` | `job-20260811T032111Z-883697` |
| 7 | `b4001406073c149ea51449f1b47b6ca5dd496c7a1293c39d785a677e5df1e6b9` | `737d8a70e4b052bc99270e61c0150ea963f2c4d9a03ca7b46f758ebda619183f` | `job-20260811T032135Z-885101` |
| 8 | `bfc5d005531b8943e703aa6ecf80122d418c059f41d271d740760a901b2a0e08` | `737d8a70e4b052bc99270e61c0150ea963f2c4d9a03ca7b46f758ebda619183f` | `job-20260811T032159Z-886504` |

Literal-selection counts:

```text
probe-A literal: 0
probe-B literal: 8
src/example.py: 0
task-relevant path: 0
other path: 0
```

The session ended `TURN_LIMIT`, with no clarification or effect. Invocation,
response-integrity, runtime, and hash-chain checks all passed as in PROBE-A.

## Causal result

The only manipulated model-visible value moved the selected path from
`probe_alpha/neutral.py` in all eight PROBE-A turns to
`probe_beta/neutral.py` in all eight PROBE-B turns. This is the strongest
predeclared matching pattern for rejecting H0 in this bounded construct probe.
It demonstrates a causal example-literal effect for these two sessions; it is
not an estimate of population frequency or universal model behavior.

`ANCHORING_CONFIRMED`

The optional write pair was not run because the primary clarification pair was
decisive. Task 10K remains blocked, Alpha v1 and qualification remain
unchanged, and the production protocol remains frozen. The next bounded design
decision is:

`NEXT: DESIGN VALUE-FREE SINGLE-REPOSITORY PROTOCOL V2`
