# Phase 1 discovery — ws-doc-writer

Status: **observed; packet rendering blocked**. No live mutation occurred.

## Application and service observations

- Host: `ws-matriarch`.
- Ollama package: `0.12.11-4.fc44.x86_64`.
- Service: active, user/group `ollama:ollama`.
- API: `127.0.0.1:11434`.
- Active executable: `/opt/ollama-intel/bin/ollama`.
- Active environment selects Intel Vulkan and model path
  `/var/lib/ai-models/ollama`; this is the stale path to be migrated later.
- Existing models are present at that old path; no approved benchmark model
  was pulled by this task.

## Storage and vault observations

- Target device: Crucial `CT2000T710SSD8`, serial `2532525E0E43`, WWN
  `eui.000000000000000100a07525525e0e43`, firmware `PBCR5103`.
- GPT disk size: `3907029168` sectors, 512-byte sectors.
- Free gap: sectors `739276800–1038319615`, between p3 and p5.
- Approved partition geometry: sectors `739276800–989276799` inclusive,
  exactly 250,000,000 sectors / 128,000,000,000 bytes.
- Remaining gap: sectors `989276800–1038319615`, 49,042,816 sectors,
  25,109,921,792 bytes; remains unassigned.
- p6 starts at `1040416768` and is excluded.
- Approved vault mounts are `FOUNDATION-2` and `LAB_ROOT_TRUST`; both are
  currently mounted read-only.

## Monitoring and evidence

Observed host services include Beszel Agent, `ntfy-lore`, and `smartd`.
Prometheus/Grafana were not observed. `evidencectl`, SOPS, and age are
installed. Vault public metadata confirms SOPS/age continuity-kit conventions;
no private key material was read.

## Blockers

The vaults are read-only and cannot receive recovery copies. ROCm CLI tools
`rocminfo` and `rocm-smi` are not installed. Exact LUKS/boot-cache runtime
behavior remains unproven. These facts block packet rendering and all
subsequent phases.
