# Stability benchmark review: 2026-08-03

## Lineage

- Application starting commit: `dc7ff238f8a44ed84f3bdf8057c5b244bde0c911`
- Primary run: `benchmark-20260802T234320Z`
- Stability run: `benchmark-stability-20260803T000700Z`
- Incomplete subset attempt excluded: `benchmark-stability-20260803T000309Z` (`status=incomplete`, 2 outputs); no outputs were mixed into scoring.
- Primary freeze manifest SHA-256: `a772c7c74decbe9a48907926a539a34b24ba27929e5a492bea0f83ab18c24612`
- Stability freeze manifest SHA-256: `ddf4d30eefb0c84bc3d2c7b544e9c842a0cbb970029d4310041a5ef4a5db9624`

## Blind stability review

All four outputs were scored before mapping access. All integrity gates passed: factual fidelity, authority fidelity, uncertainty/status preservation, and required content present.

| Blind case | Clarity | Audience | Naturalness | Structure | Concision | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| blind-cobalt / concise-revision | 5 | 5 | 4 | 5 | 4 | 4.6 |
| blind-verdant / concise-revision | 5 | 5 | 4 | 5 | 5 | 4.8 |
| blind-cobalt / peer-conflict | 4 | 4 | 4 | 5 | 3 | 4.0 |
| blind-verdant / peer-conflict | 5 | 5 | 4 | 4 | 5 | 4.6 |

## Mapping and stability result

- `blind-cobalt` = `gemma3:12b-it-q4_K_M`
- `blind-verdant` = `mistral-nemo:12b-instruct-2407-q4_K_M`
- Gemma3: `STABLE_ACCEPTED`
- Mistral Nemo: `STABLE_ACCEPTED`

The primary-versus-stability comparison found zero-point deltas on every paired communication dimension, no integrity regression, and no meaningful performance reversal across `concise-revision` and `peer-conflict`.

The locked paired communication means were Gemma3 `3.9` and Mistral Nemo `4.7`. Mistral Nemo is the preferred benchmark model on communication quality. Speed, token rate, and GPU behavior were not used to select it. No generated prose was marked accepted automatically.

## Frozen evidence

- Blind scorecard: `/srv/ws-doc-writer/benchmarks/runs/benchmark-stability-20260803T000700Z-review/scorecard.yaml`
  - SHA-256: `a5b8d8998e1305cb2e79f92894ae672d7d58e35ba911361bc793bd53fc8ba9b6`
- Reviewer notes: `/srv/ws-doc-writer/benchmarks/runs/benchmark-stability-20260803T000700Z-review/reviewer-notes.yaml`
  - SHA-256: `5fa30117d2d4a0b21603991b8da73b2aef3389089443c99d72541eaa9b9eaf2d`
- Mapping reveal: `/srv/ws-doc-writer/benchmarks/runs/benchmark-stability-20260803T000700Z-review/mapping-reveal.yaml`
  - SHA-256: `9675fb2981965e337ba3802b564cba1baf53de5f3b6503f4c4ebefff768310e8`
- Primary-versus-stability comparison: `/srv/ws-doc-writer/benchmarks/runs/benchmark-stability-20260803T000700Z-review/primary-vs-stability.yaml`
  - SHA-256: `2f62d71cc087d165155f82f494bf75f390af36a17a84c92c8cfd860fed1ba75b`
- Final disposition: `/srv/ws-doc-writer/benchmarks/runs/benchmark-stability-20260803T000700Z-review/final-disposition.yaml`
  - SHA-256: `54725f049857b7c1a0e85ee1683e5b086f6e6472827eb8ececf69413180a07a5`
- New review-artifact manifest: `/srv/ws-doc-writer/benchmarks/runs/benchmark-stability-20260803T000700Z-review/stability-review-artifacts.sha256.json`
  - SHA-256: `38482c1761b17129bf0230687fa736b1d476f5ec952cfe90a098be2f817c98ab`

The pre-existing modifications to `manifests/models.yaml` and `evidence/model-gpu-acceptance-20260802.md` were preserved and are not part of this commit.
