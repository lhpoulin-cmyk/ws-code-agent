# R2 C01 patch-rejection analysis

R2 remains immutable. This note records executor-side analysis for the future
patch-feedback contract; it does not alter R2 scoring.

The seven C01 `PROPOSE_PATCH` requests all targeted `src/parity.py` and were
rejected before `git apply`. The executor detail for every request was `patch
contains no supported diff header`; no exit code, stdout, or stderr existed for
these parser-stage rejections.

| Attempt | Response SHA-256 | Patch bytes | Material change from prior attempt |
| --- | --- | ---: | --- |
| 1 | `24f47f88625690fbe810a835383d0ed56cad6b45d1f09b8f7ccfc41d3f0bb2c2` | 102 | yes |
| 2 | `563ed55f533841ce28ed691fe0ffb9d2a1d4bf1cf748cfd59861ea921aa2ff77` | 187 | yes |
| 3 | `24f47f88625690fbe810a835383d0ed56cad6b45d1f09b8f7ccfc41d3f0bb2c2` | 102 | yes |
| 4 | `24f47f88625690fbe810a835383d0ed56cad6b45d1f09b8f7ccfc41d3f0bb2c2` | 102 | no |
| 5 | `563ed55f533841ce28ed691fe0ffb9d2a1d4bf1cf748cfd59861ea921aa2ff77` | 187 | yes |
| 6 | `24f47f88625690fbe810a835383d0ed56cad6b45d1f09b8f7ccfc41d3f0bb2c2` | 102 | yes |
| 7 | `24f47f88625690fbe810a835383d0ed56cad6b45d1f09b8f7ccfc41d3f0bb2c2` | 102 | no |

The responses alternate between two unsupported patch forms. The frozen R2
harness reported only the rejection class, so the model did not receive the
executor-observed parser detail needed to make a distinct syntactic repair.
R2's behavioral failure remains authoritative for that earlier harness version.
