# Task 10E-R2 protocol-contract forensics

Task 10E-R2 (`task10e-r2-c03-c05-20260810T195341Z`) remains unchanged and
scored as recorded. This note analyzes its frozen first-turn prompts and raw
responses; it does not reparse or rescore them.

The frozen backend preamble specified only the two outer JSON keys and one
global request-type list. It supplied no request-specific argument fields or
patch representation. The same list was shown to C05 even though its active
parser accepts only repository-qualified `READ`, `SEARCH`, and
`PROPOSE_PATCH`, plus `NO_CHANGE`.

| Case | Raw SHA-256 | Model-emitted structure | Strict parser mismatch | Cause |
| --- | --- | --- | --- | --- |
| C03 | `770e1ee1c95df84409031606c7c2d7c1a3c6a44ffebf4d63ea10c465d666f029` | `READ` with `arguments.paths` array | required singular string `arguments.path` | `PROTOCOL_SPEC_UNDERSPECIFIED` |
| C04 | `94b7ae233ae2629287054938ea16b293eb4fd7f2d21355d6c34ea3b878bf6fd9` | `READ` with `arguments.paths` array | required singular string `arguments.path` | `PROTOCOL_SPEC_UNDERSPECIFIED` |
| C05-A | `428acd3ed6e7f5fddd24bd7a3515b6178984299e31fb443b852a9330cdb2314d` | `PROPOSE_PATCH` with `repository`, `file_path`, `patch_content` | required `repository`, unified-diff `patch`, and `proposed_paths` array | `MIXED` |
| C05-B | `1a546b41e986adf167f9262aa96b653f3a07313ba137f29d1c58b1074d857d14` | `READ` with `repository` and `paths` array | required `repository` and singular string `path` | `MIXED` |

C05 is mixed because the prompt was both argument-shape-underspecified and
mismatched to the active parser's request surface. The parser was strict and
behaved as implemented. Task 10F binds two explicit protocol definitions to
the corresponding parsers and adapters without compatibility parsing,
normalization, schema forcing, or authority changes.
