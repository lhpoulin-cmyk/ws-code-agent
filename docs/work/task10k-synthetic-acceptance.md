# Task 10K synthetic acceptance — blocked

Date: 2026-08-11  
Harness: `b5b159a` (`feat: add supervised single-repository work lane`)

This is a forward evidence addendum. It does not alter Alpha v1 qualification
or historical model evidence.

## Write task

Session: `work-20260810T235703Z-098d4639fe2c`  
Evidence: `~/.local/share/ws-code-agent/work/work-20260810T235703Z-098d4639fe2c`

Objective: create `src/message.py` with a no-argument function returning
`"hello"`. Read authority was `.` and patch authority was exactly
`src/message.py`.

The model emitted eight parser-valid `READ` requests. Turns 1–2 and 8 selected
the neutral protocol-example path `src/example.py`; turns 3–7 selected the
not-yet-created `src/message.py`. The read executor projected
`PATH_ESCAPE_DENIED` for each nonexistent path. No patch was proposed, no
isolated mutation context was retained, and the session ended `TURN_LIMIT`.

All eight runtime turns used the exact qualified artifact and accepted
`GPU_PRIMARY_PARTIAL_OFFLOAD` 80/20 profile. Invocation IDs were unique, raw
response/runtime hashes matched, and the turn hash chain passed. The source
remained clean at HEAD `5d3344a6e8ba1a6af97473b74c09906465893706`;
`src/message.py` was absent after the session.

Result: **synthetic write acceptance not met**.

## Clarification task

Session: `work-20260811T000243Z-ec4f331237b6`  
Evidence: `~/.local/share/ws-code-agent/work/work-20260811T000243Z-ec4f331237b6`

The clean synthetic repository made the unresolved uppercase-display versus
lowercase-slug product choice explicit. Read authority was `.`, and no patch
authority was granted.

The model emitted the same parser-valid `READ {"path":"src/example.py"}` on
all eight turns. Each received `PATH_ESCAPE_DENIED`; no
`REQUEST_CLARIFICATION` occurred and the session ended `TURN_LIMIT`.

All eight runtime turns used the exact qualified artifact and accepted profile.
Invocation IDs were unique, raw response/runtime hashes matched, and the turn
hash chain passed. The source remained clean at HEAD
`3ba8b1e52b87c6286cf5ba1401cd49a65e116d15`.

Result: **synthetic clarification acceptance not met**.

## Preserved properties

- no authoritative source mutation;
- no candidate effect or automatic promotion;
- no second-repository authority;
- strict frozen protocol and parser;
- durable one-turn journaling and idempotent invocation identity;
- exact qualified model/runtime profile;
- no retry, prompt change, model tuning, schema forcing, or Alpha mutation.

## Disposition

The lane mechanics are deterministically covered by the 95-test gate, but Task
10K product acceptance is blocked by the observed live model progression. A
future play must decide whether this is addressed as an operating-envelope
restriction or as an independently justified interface/executor defect. This
record does not authorize either change and does not approve real-repository
use.
