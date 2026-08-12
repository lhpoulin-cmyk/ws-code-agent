# hv-matrix VM 320 ws-code-agent comparison handoff

Status: `MIGRATION_NOT_STARTED`

Task 11O records this handoff but performs no Matrix action.

```text
next host: hv-matrix
next appliance: new VM 320
next runtime authority: gpu-compute
next application: ws-code-agent
```

A separately authorized future play should compare the frozen
`RTX_5070_TI_KATRA_WS_CODE_AGENT_BASELINE_V1` against Arc Pro B70 on Matrix.
Where available, it must preserve the same exact model artifact,
quantization, context, frozen benchmark prompts/tasks, evidence fields, and
correctness/validation accounting.

The required comparison axes are:

- cold load;
- warm latency;
- prompt evaluation;
- decode throughput;
- GPU memory residency;
- CPU offload;
- end-to-end governed task time;
- candidate correctness; and
- validation outcome.

No VM, host, GPU, service, repository, network, storage, or runtime mutation
is authorized by this handoff. Katra's cuda-compute VM, Ollama service,
NVIDIA/CUDA stack, model inventory, and Doc Writer connectivity remain in
service and unchanged.
