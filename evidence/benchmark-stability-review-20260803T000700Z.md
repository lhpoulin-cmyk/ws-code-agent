# Stability benchmark review: 2026-08-03

## Lineage

- Application starting commit: 
- Primary run: 
- Stability run: 
- Incomplete subset attempt excluded:  (, 2 outputs); no outputs were mixed into scoring.
- Primary freeze manifest SHA-256: 
- Stability freeze manifest SHA-256: 

## Blind stability review

All four outputs were scored before mapping access. All integrity gates passed: factual fidelity, authority fidelity, uncertainty/status preservation, and required content present.

| Blind case | Clarity | Audience | Naturalness | Structure | Concision | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| blind-cobalt / concise-revision | 5 | 5 | 4 | 5 | 4 | 4.6 |
| blind-verdant / concise-revision | 5 | 5 | 4 | 5 | 5 | 4.8 |
| blind-cobalt / peer-conflict | 4 | 4 | 4 | 5 | 3 | 4.0 |
| blind-verdant / peer-conflict | 5 | 5 | 4 | 4 | 5 | 4.6 |

## Mapping and stability result

-  = 
-  = 
- Gemma3: 
- Mistral Nemo: 

The primary-versus-stability comparison found zero-point deltas on every paired communication dimension, no integrity regression, and no meaningful performance reversal across  and .

The locked paired communication means were Gemma3  and Mistral Nemo . Mistral Nemo is the preferred benchmark model on communication quality. Speed, token rate, and GPU behavior were not used to select it. No generated prose was marked accepted automatically.

## Frozen evidence

- Blind scorecard: 
  - SHA-256: 
- Reviewer notes: 
  - SHA-256: 
- Mapping reveal: 
  - SHA-256: 
- Primary-versus-stability comparison: 
  - SHA-256: 
- Final disposition: 
  - SHA-256: 
- New review-artifact manifest: 
  - SHA-256: 

The pre-existing modifications to  and  were preserved and are not part of this commit.
