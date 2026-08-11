# Task 10K-A missing-path semantics acceptance addendum

Date: 2026-08-11  
Starting HEAD: `f352912f480d8da84df76f6efdbcc795c5a4ba87`  
Frozen repair HEAD: `b2a57c4b2b506923a821c102f9dfddd285c5eaf9`

This is a forward evidence addendum. It does not modify the two original Task
10K sessions, Alpha evidence, protocol, parser, or qualification.

## Executor defect and repair

The prior read resolver used strict final-target resolution. Ordinary absence
inside the repository and an actual containment escape therefore both produced
`PATH_ESCAPE_DENIED`. The repair walks repository-relative path components,
verifies every existing symlink target remains inside the canonical repository,
and classifies the first ordinary missing component separately.

- bounded missing READ target: `PATH_NOT_FOUND`;
- bounded missing SEARCH scope: `SEARCH_SCOPE_NOT_FOUND`;
- existing non-file READ target: `NOT_A_REGULAR_FILE`;
- existing non-directory SEARCH scope: `SEARCH_SCOPE_NOT_DIRECTORY`;
- absolute path, traversal, `.git`, escaping parent/final symlink, or dangling
  symlink: `PATH_ESCAPE_DENIED`.

Invariant P11 records this distinction. The frozen repair passed 98 tests and
the full Alpha, H5/H6, qualification, private-material, lineage, invariant, and
diff gates before either live session began.

## Fresh write session

Session: `work-20260811T003519Z-c880816d82b4`  
Evidence: `~/.local/share/ws-code-agent/work/work-20260811T003519Z-c880816d82b4`

The objective, authority, qualified artifact, protocol, context, sampling,
runtime policy, and eight-turn limit match the original write acceptance. The
source began clean at `94df9b57a77a087b47a471847e455a512cd7255b` with
`src/message.py` absent.

The request sequence was:

1. `READ src/example.py` -> `PATH_NOT_FOUND`;
2. `READ src/message.py` -> `PATH_NOT_FOUND`;
3. `READ src/message.py` -> `PATH_NOT_FOUND`;
4. `READ src/message.py` -> `PATH_NOT_FOUND`;
5. `READ src/message.py` -> `PATH_NOT_FOUND`;
6. `READ src/message.py` -> `PATH_NOT_FOUND`;
7. `READ src/message.py` -> `PATH_NOT_FOUND`;
8. `READ src/message.py` -> `PATH_NOT_FOUND`.

No patch was proposed. The session ended `TURN_LIMIT` with no candidate,
changed paths, isolated effect, review packet, operator disposition, or
promotion. The source remained clean and unchanged at its starting HEAD, and
`src/message.py` remained absent.

All eight turns used distinct invocation IDs and gpu-compute jobs. Every local
raw hash matched the journal and gpu-compute response hash; every runtime record
passed `GPU_PRIMARY_PARTIAL_OFFLOAD` at 80% GPU / 20% CPU; the turn hash chain
passed. Turn 1 was recovered through its persisted invocation intent without a
duplicate invocation or model inference.

Result: **synthetic write acceptance not met**.

## Fresh clarification session

Session: `work-20260811T003944Z-98433b647c4f`  
Evidence: `~/.local/share/ws-code-agent/work/work-20260811T003944Z-98433b647c4f`

The objective, ambiguity-bearing fixture, read authority `.`, empty patch
authority, qualified artifact, protocol, context, sampling, runtime policy, and
eight-turn limit match the original clarification acceptance. The source began
clean at `d75be1f48a487dce4e602a17d8db8cccde3ae45d`.

All eight requests were `READ src/example.py`; each returned
`PATH_NOT_FOUND`. The model emitted no `REQUEST_CLARIFICATION`, and the session
ended `TURN_LIMIT`. No candidate, isolated effect, operator disposition, or
promotion existed. The source remained clean and unchanged.

All eight turns used distinct invocation IDs and gpu-compute jobs. Every local
raw hash matched the journal and gpu-compute response hash; every runtime record
passed the accepted 80/20 profile; the turn hash chain passed.

Result: **synthetic clarification acceptance not met**.

## Protocol-example observation and disposition

`src/example.py` is a literal neutral protocol example. It was selected once
in the write session and on all eight clarification turns:

```text
example_path_reads:
  write: 1
  clarification: 8
```

This play changes no protocol text or example. Accurate absence semantics are
now proven, but the repeated literal example path remains observable and both
acceptances failed. The bounded disposition is:

`PROTOCOL_EXAMPLE_ANCHORING_SUSPECTED`

Task 10K remains blocked. No real-repository lane is approved by this addendum.
