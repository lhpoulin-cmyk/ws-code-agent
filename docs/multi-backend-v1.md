# Multi-backend / multi-model v1

`tools/benchmark_runner.py` and `benchmarks/fixture-manifest.yaml` remain the
historical frozen v1 benchmark. New multi-backend runs use
`tools/benchmark_runner_v2.py`; it invokes v1's fixture verifier before it
creates any output.

Backends are logical Ollama targets. Runtime endpoint configuration is owned by
the appliance and loaded from `WS_DOC_WRITER_BACKENDS_FILE` (normally
`/etc/ws-doc-writer/backends.yaml`). The repository contains only
`config/backends.example.yaml` and `schemas/backends.yaml`; neither contains a
credential, private key, token, or infrastructure command. With no runtime
file, the application retains one enabled local loopback backend at
`127.0.0.1:11434`.

Each v2 record includes backend ID, tag, reconciled digest, controlled settings,
prompt/output hashes, Ollama API timings, and `/api/ps` processor residency.
Generated prose remains `REVIEW_REQUIRED`; this change adds explicit choice and
does not select a winner or introduce automatic routing.
