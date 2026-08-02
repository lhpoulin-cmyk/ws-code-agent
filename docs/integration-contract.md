# Coordinated infrastructure integration

`ws-doc-writer` declares requirements; it does not mutate the workstation or
GPU.

```text
ws-doc-writer → application benchmark, prompts, and acceptance requirements
ws-cp         → workstation and Ollama service packet
gpu-cp        → RX 9070 XT identity and acceleration acceptance
```

Existing peer packet references:

- `ws-cp/implementation/ws-doc-writer-foundation.packet.md`
- `gpu-cp/implementation/ws-doc-writer-accelerator-gate.md`

Those packets remain blocked and are not executed here. The discovered Intel
Arc Vulkan Ollama override conflicts with the intended AMD ROCm path. This
application must not repair it. Any conflict between peer requirements stops
and returns to the operator with evidence.

Required infrastructure acceptance includes loopback-only API exposure,
approved model storage, device permissions, exact pinned versions, and
`ollama ps` reporting `100% GPU` for every initial candidate at the common 8K
context.

## Model-storage requirement

The application declares one storage requirement for `ws-cp` to implement and
validate:

```text
Crucial Gen5 NVMe
└── 128 GB dedicated permanently to ws-doc-writer
    ├── carved only from the unpartitioned gap
    └── remaining gap stays unassigned
```

This is an intended requirement, not observed partition state or execution
authority. The exact device identity, partition plan, filesystem, mount path,
free-space proof, and rollback/recovery procedure remain unresolved. Any
partition mutation belongs in a separately reviewed `ws-cp` packet.
