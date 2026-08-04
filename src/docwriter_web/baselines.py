"""Pure validation helpers for immutable conversational baselines."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Any, Iterable
from .editorial_state import derive_editorial_state

def value(row: Any, key: str, default: Any = None) -> Any:
    if row is None: return default
    try: return row[key]
    except (KeyError, IndexError, TypeError): return default

@dataclass(frozen=True)
class BaselineEligibility:
    attempt: Any
    target: Any
    integrity: Any
    revision: Any
    tone: Any
    current: Any | None

def current_baseline(rows: Iterable[Any]) -> Any | None:
    rows = list(rows); by_id = {value(r, 'baseline_id'): r for r in rows}; successors = {}
    for row in rows:
        prior = value(row, 'supersedes_baseline_id')
        if not prior: continue
        if prior not in by_id or value(row, 'trial_id') != value(by_id[prior], 'trial_id'):
            raise ValueError('baseline supersession crosses a missing or different trial')
        if prior in successors: raise ValueError('baseline chain branches')
        successors[prior] = value(row, 'baseline_id')
    for baseline_id in by_id:
        seen = set(); cursor = baseline_id
        while cursor in successors:
            if cursor in seen: raise ValueError('baseline chain contains a cycle')
            seen.add(cursor); cursor = successors[cursor]
    roots = [r for r in rows if value(r, 'baseline_id') not in successors]
    if len(roots) > 1: raise ValueError('baseline chain has competing current baselines')
    return roots[0] if roots else None

def eligibility(trial: Any, attempts: Iterable[Any], events: Iterable[Any], baselines: Iterable[Any] = ()) -> BaselineEligibility:
    if value(trial, 'lifecycle_state', 'ACTIVE') != 'ACTIVE': raise ValueError('archived trials cannot accept a new baseline')
    attempts, events = list(attempts), list(events); current = current_baseline(baselines)
    state = derive_editorial_state(trial, attempts, events, baselines)
    if state.state != 'READY_FOR_BASELINE_ACCEPTANCE': raise ValueError(f'baseline acceptance requires READY_FOR_BASELINE_ACCEPTANCE, got {state.state}')
    targets = [e for e in events if value(e, 'event_type') == 'REVIEW_TARGET_SELECTED']
    target = sorted(targets, key=lambda r: (value(r, 'created_at', ''), value(r, 'event_id', '')))[-1] if targets else None
    attempt = next((r for r in attempts if value(r, 'attempt_id') == value(target, 'generation_attempt_id') and value(r, 'status') == 'COMPLETED'), None)
    if target is None or attempt is None: raise ValueError('baseline target is not a completed attempt')
    for key in ('source_version_id', 'source_sha256', 'proposal_sha256'):
        if value(target, key) != value(attempt, key): raise ValueError('baseline target identity does not match the attempt')
    scoped = [e for e in events if value(e, 'stream_id') == value(target, 'stream_id')]
    def latest(stage, decision):
        candidates = [e for e in scoped if value(e, 'stage') == stage and value(e, 'decision') == decision]
        if not candidates: raise ValueError(f'missing {stage} gate')
        return sorted(candidates, key=lambda r: (value(r, 'created_at', ''), value(r, 'event_id', '')))[-1]
    integrity, revision, tone = latest('INTEGRITY', 'INTEGRITY_ACCEPTED'), latest('REVISION', 'READY_FOR_TONE_REVIEW'), latest('TONE', 'TONE_ACCEPTED')
    for event in (integrity, revision, tone):
        if any(value(event, key) != value(attempt, key) for key in ('source_version_id', 'source_sha256', 'proposal_sha256')): raise ValueError('editorial gate identity does not match the attempt')
    if current and value(current, 'proposal_sha256') == value(attempt, 'proposal_sha256'): raise ValueError('this proposal is already the current baseline')
    return BaselineEligibility(attempt, target, integrity, revision, tone, current)

def proposal_hash(proposal: str) -> str:
    return hashlib.sha256(proposal.encode('utf-8')).hexdigest()
