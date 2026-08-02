# Frozen benchmark implementation decision

Status: **prepared / operator review required**

`ws-doc-writer` owns the ten case definitions, synthetic source-material
fixtures, blinding semantics, scoring rubric, provenance, and application
acceptance. `ws-cp` owns the runtime benchmark directories and quota. `gpu-cp`
owns accelerator acceptance.

The implementation freezes revision `ws-doc-writer-frozen-10/v1`, validates
content hashes before execution, runs the exact 30-output matrix sequentially,
and separates protected raw evidence from anonymous review outputs. Numeric
scores do not select a winner. Generated prose remains `REVIEW_REQUIRED` until
operator disposition.
