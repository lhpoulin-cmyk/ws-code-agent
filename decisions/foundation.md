# Foundation decision

Status: **accepted for repository foundation; no executor, no deployment**.

`ws-code-agent` is founded as governance and evaluation architecture for a
bounded coding agent: task/intent capture, provenance, review lifecycle, and a
future frozen evaluation. It is not a coding executor and claims no coding
capability, autonomous safety, or repository-general competence.

`ws-cp` and `gpu-cp` remain peer infrastructure authorities. This repository
holds no authority over them and declares no disk, model, GPU, Ollama, or
deployment state. The prior inherited model-storage allocation belonged to
`ws-doc-writer` and has been removed from this repository.

On 2026-08-09 a skeleton reduction removed the inherited Doc Writer
implementation, prompts, writing schemas, benchmark, and phase tests from the
live tree. Witnessed evidence and reusable references were relocated under
`lineage/`. Nothing was rewritten out of Git history. What survives in the live
tree is the coding-agent contract and chosen governance only.

No coding-specific schema, capability-lease implementation, executor, or
benchmark is authorized by this decision.
