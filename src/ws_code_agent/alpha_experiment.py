"""Restart-safe, one-turn Alpha experiment journaling.

This is deliberately a controller, not an autonomous agent: a caller supplies
the already-frozen case processor and invokes :meth:`step` once per model turn.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable, Mapping, Protocol

from .katra_ollama_backend import InferenceInvocation, KatraOllamaDispositionBackend, ResponseEvidenceSink, RuntimeTurnEvidence
from .request_protocol import ProtocolSpec, protocol_by_id


class ExperimentError(RuntimeError):
    pass


class TurnBackend(Protocol):
    def generate(self, messages: tuple[dict[str, Any], ...], *, protocol: ProtocolSpec, invocation: InferenceInvocation, evidence_sink: ResponseEvidenceSink) -> str: ...
    def invocation_for(self, messages: tuple[dict[str, Any], ...], invocation_id: str, *, protocol: ProtocolSpec) -> InferenceInvocation: ...


Processor = Callable[[dict[str, Any], str], Mapping[str, Any]]


def _json(value: Any) -> Any:
    if is_dataclass(value):
        return _json(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): _json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(item) for item in value]
    return value.value if hasattr(value, "value") else value


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    encoded = (json.dumps(_json(value), sort_keys=True, indent=2) + "\n").encode()
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class _Sink:
    def __init__(self, controller: "AlphaExperimentController", case: dict[str, Any], turn: int) -> None:
        self.controller, self.case, self.turn = controller, case, turn

    def capture_response(self, raw_response: str, evidence: RuntimeTurnEvidence) -> None:
        directory = self.controller._turn_dir(self.case["case_id"], self.turn)
        raw = raw_response.encode("utf-8")
        _atomic_bytes(directory / "raw-response.txt", raw)
        payload = {"phase": "RAW_RESPONSE_DURABLE", "turn": self.turn,
                   "raw_sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw),
                   "runtime": _json(evidence)}
        _atomic_json(directory / "state.json", payload)
        self.case["pending_turn"] = payload
        self.controller._write_case(self.case)


class AlphaExperimentController:
    """File-backed family state. Each call to ``step`` performs <= one inference."""

    def __init__(self, family_root: Path) -> None:
        self.root = family_root

    @classmethod
    def start(cls, store: Path, manifest: Mapping[str, Any], cases: tuple[Mapping[str, Any], ...]) -> "AlphaExperimentController":
        family = store / str(manifest["experiment_id"])
        if family.exists(): raise ExperimentError("experiment identity already exists")
        family.mkdir(mode=0o700, parents=True)
        _atomic_json(family / "family-manifest.json", dict(manifest))
        _atomic_json(family / "family-state.json", {"status": "ACTIVE", "case_order": [c["case_id"] for c in cases]})
        controller = cls(family)
        for source in cases:
            case = dict(source)
            case.update({"turn_committed": 0, "case_status": "READY", "terminal_disposition": None, "pending_turn": None, "previous_turn_digest": None})
            controller._write_case(case)
        return controller

    def status(self) -> dict[str, Any]:
        family = _load(self.root / "family-state.json")
        cases = [_load(path) for path in sorted((self.root / "cases").glob("*/case.json"))]
        summaries=[]
        for c in cases:
            summary={k: c.get(k) for k in ("case_id", "turn_committed", "case_status", "terminal_disposition", "pending_turn")}
            try:
                from .alpha_case_adapters import case_status
                summary.update(case_status(self, c))
            except (ImportError, KeyError):
                pass
            summaries.append(summary)
        active=next((c["case_id"] for c in cases if c["case_status"] in {"READY", "ACTIVE", "EVALUATING"}), None)
        return {"family_status": family["status"], "current_or_next_case": active, "cases": summaries}

    def step_registered(self, case_id: str, backend: TurnBackend) -> dict[str, Any]:
        from .alpha_case_adapters import (REGISTERED_CASE_IDS, TASK10E_CASE_ORDER, TASK10G_R3_CASE_ORDER,
                                          advance_case_evaluation, prepare_case_step, process_case_turn, verify_case)
        family_state = _load(self.root / "family-state.json")
        case_order = tuple(family_state["case_order"])
        if case_order not in {TASK10E_CASE_ORDER, TASK10G_R3_CASE_ORDER}:
            raise ExperimentError("family case order is not registered")
        if case_id not in REGISTERED_CASE_IDS or case_id not in case_order:
            raise ExperimentError("case is not registered in this family")
        cases={item["case_id"]: item for item in (_load(path) for path in (self.root / "cases").glob("*/case.json"))}
        preceding=case_order[:case_order.index(case_id)]
        if any(cases[item]["case_status"] not in {"TERMINAL", "TURN_LIMIT"} for item in preceding):
            raise ExperimentError("preceding case is not complete")
        verify_case(self, cases[case_id])
        if cases[case_id]["case_status"] == "EVALUATING":
            return dict(advance_case_evaluation(self, cases[case_id]))
        prepare_case_step(self, cases[case_id])
        result=self.step(case_id, backend, lambda case, raw: process_case_turn(self, case, raw))
        case=self._case(case_id)
        if case["turn_committed"] >= case["turn_limit"] and case["case_status"] == "ACTIVE":
            case["case_status"]="TURN_LIMIT"; case["terminal_disposition"]="TURN_LIMIT"; self._write_case(case)
        if case_id == case_order[-1] and case["case_status"] in {"TERMINAL", "TURN_LIMIT"}:
            _atomic_json(self.root / "family-state.json", {"status": "COMPLETE", "case_order": list(case_order)})
        return result

    def step(self, case_id: str, backend: TurnBackend, processor: Processor) -> dict[str, Any]:
        case = self._case(case_id)
        pending = case.get("pending_turn")
        if pending:
            if pending["phase"] == "INFERENCE_INTENT_DURABLE":
                return self._invoke_intent(case, backend, processor)
            return self._recover(case, processor)
        if case["case_status"] not in {"READY", "ACTIVE"}: raise ExperimentError("case may not advance")
        if case["turn_committed"] >= case["turn_limit"]: raise ExperimentError("turn limit reached")
        turn = case["turn_committed"] + 1
        try:
            protocol=protocol_by_id(case["protocol_id"])
        except (KeyError, ValueError) as error:
            raise ExperimentError("case request protocol is not registered") from error
        case["case_status"] = "ACTIVE"
        case["pending_turn"] = {"phase": "TURN_STARTED", "turn": turn}
        self._write_case(case)
        family=_load(self.root / "family-manifest.json")
        material=f"{self.root.name}\0{case_id}\0{case['interaction_id']}\0{turn}\0{family['experiment_harness_sha']}"
        suffix=hashlib.sha256(material.encode()).hexdigest()
        invocation_id=f"alpha-{hashlib.sha256(self.root.name.encode()).hexdigest()[:12]}-{case_id}-t{turn:04d}-{suffix[:12]}"
        invocation=backend.invocation_for(tuple(case["conversation"]), invocation_id, protocol=protocol)
        case["pending_turn"]={"phase":"INFERENCE_INTENT_DURABLE","turn":turn,"invocation_id":invocation.invocation_id,"prompt_sha256":invocation.prompt_sha256,"protocol_id":protocol.protocol_id,"model":"qwen3-coder:30b","execution_policy":"gpu-primary-partial","remote_response":f"evidence/invocations/{invocation.invocation_id}/response.txt"}
        self._write_case(case)
        return self._invoke_intent(case, backend, processor)

    def _invoke_intent(self, case: dict[str, Any], backend: TurnBackend, processor: Processor) -> dict[str, Any]:
        pending=case["pending_turn"]; turn=pending["turn"]
        try:
            protocol=protocol_by_id(pending["protocol_id"])
        except (KeyError, ValueError) as error:
            raise ExperimentError("durable inference protocol is not registered") from error
        if case.get("protocol_id") != protocol.protocol_id:
            raise ExperimentError("durable inference protocol mismatch")
        invocation=InferenceInvocation(pending["invocation_id"],pending["prompt_sha256"])
        sink = _Sink(self, case, turn)
        # Any backend cleanup happens only after ``capture_response`` returns.
        try:
            backend.generate(tuple(case["conversation"]), protocol=protocol, invocation=invocation, evidence_sink=sink)
        except Exception as error:
            raise
        return self._recover(self._case(case["case_id"]), processor)

    def _recover(self, case: dict[str, Any], processor: Processor) -> dict[str, Any]:
        pending = case.get("pending_turn")
        if not pending: raise ExperimentError("no recoverable turn")
        phase = pending["phase"]
        directory = self._turn_dir(case["case_id"], pending["turn"])
        if phase == "RAW_RESPONSE_DURABLE":
            # Processing starts only after this durable marker. A later crash in
            # processing is intentionally ambiguous and invalidates the case.
            pending["phase"] = "HARNESS_PROCESSING"; self._write_case(case)
            raw = (directory / "raw-response.txt").read_text(encoding="utf-8")
            try:
                result = dict(processor(case, raw))
            except Exception as error:
                case["case_status"] = "INVALIDATED"; case["pending_turn"] = {"phase": "AMBIGUOUS_EXECUTOR_OPERATION", "turn": pending["turn"], "error": type(error).__name__}; self._write_case(case); raise
            _atomic_json(directory / "harness-result.json", result)
            pending = {"phase": "HARNESS_RESULT_DURABLE", "turn": pending["turn"], "raw_sha256": pending["raw_sha256"], "result_sha256": hashlib.sha256((directory / "harness-result.json").read_bytes()).hexdigest()}
            case["pending_turn"] = pending; self._write_case(case)
        elif phase == "HARNESS_PROCESSING":
            case["case_status"] = "INVALIDATED"; case["pending_turn"] = {"phase": "AMBIGUOUS_EXECUTOR_OPERATION", "turn": pending["turn"]}; self._write_case(case); raise ExperimentError("ambiguous executor operation")
        elif phase != "HARNESS_RESULT_DURABLE":
            raise ExperimentError(f"turn cannot recover from {phase}")
        result = _load(directory / "harness-result.json")
        digest = hashlib.sha256(json.dumps({"previous": case["previous_turn_digest"], "raw": pending["raw_sha256"], "result": pending["result_sha256"], "turn": pending["turn"]}, sort_keys=True).encode()).hexdigest()
        _atomic_json(directory / "committed.json", {"phase": "TURN_COMMITTED", "turn": pending["turn"], "previous_turn_digest": case["previous_turn_digest"], "turn_digest": digest})
        case["turn_committed"] = pending["turn"]; case["previous_turn_digest"] = digest; case["pending_turn"] = None
        case["conversation"].append({"role": "tool", "content": result["projection"]})
        if result.get("terminal_disposition"):
            case["terminal_disposition"] = result["terminal_disposition"]
            case["case_status"] = result.get("case_status", "TERMINAL")
        self._write_case(case)
        return result

    def _case(self, case_id: str) -> dict[str, Any]: return _load(self.root / "cases" / case_id / "case.json")
    def _write_case(self, case: Mapping[str, Any]) -> None: _atomic_json(self.root / "cases" / str(case["case_id"]) / "case.json", case)
    def _turn_dir(self, case_id: str, turn: int) -> Path: return self.root / "cases" / case_id / "turns" / f"{turn:04d}"
