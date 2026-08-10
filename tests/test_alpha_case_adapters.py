from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ws_code_agent.alpha_case_adapters import C05_MODEL_VISIBLE_CONTRACT, initialize_task10e, prepare_case_step, process_case_turn, verify_case
from ws_code_agent.alpha_experiment import AlphaExperimentController, ExperimentError
from ws_code_agent.katra_ollama_backend import KatraOllamaDispositionBackend, RuntimeTurnEvidence

def request(kind, arguments): return json.dumps({"request_type":kind,"arguments":arguments}, separators=(",",":"))
def patch(path, old, new): return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-{old}\n+{new}\n"

class FakeBackend:
    def __init__(self, raw): self.raw=raw; self.calls=0
    def invocation_for(self, messages, invocation_id, *, protocol): return KatraOllamaDispositionBackend.invocation_for(messages,invocation_id,protocol=protocol)
    def generate(self, messages, *, protocol, invocation, evidence_sink):
        self.calls+=1; evidence_sink.capture_response(self.raw, RuntimeTurnEvidence(hashlib.sha256(self.raw.encode()).hexdigest(),f"job-{self.calls}","d","Q4_K_M","gpu-primary-partial","GPU_PRIMARY_PARTIAL_OFFLOAD",20,80,"20%/80% CPU/GPU","","")); return self.raw

class AdapterTests(unittest.TestCase):
    def controller(self, root): return initialize_task10e(root,{"experiment_id":"family","experiment_harness_sha":"test","case_order":["C03","C04","C05-A","C05-B"]})
    def step(self, controller, case, raw):
        current=controller._case(case); prepare_case_step(controller,current)
        return controller.step(case,FakeBackend(raw),lambda state,response:process_case_turn(controller,state,response))

    def test_c03_restart_preserves_dirty_state_feedback_and_accepted_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.controller(Path(tmp)); before=c._case("C03")
            self.step(c,"C03",request("READ",{"path":"src/greeting.py"})); c=AlphaExperimentController(c.root)
            rejected=self.step(c,"C03",request("PROPOSE_PATCH",{"patch":"not a diff","proposed_paths":["src/greeting.py"]})); self.assertEqual("REJECTED",rejected["projection"]["status"])
            c=AlphaExperimentController(c.root); greeting_patch='diff --git a/src/greeting.py b/src/greeting.py\n--- a/src/greeting.py\n+++ b/src/greeting.py\n@@ -1,2 +1,2 @@\n def greeting(name: str) -> str:\n-    return f"Hi, {name}!"\n+    return f"Hello, {name}!"\n'; good=request("PROPOSE_PATCH",{"patch":greeting_patch,"proposed_paths":["src/greeting.py"]})
            accepted=self.step(c,"C03",good); self.assertEqual("ACCEPTED",accepted["projection"]["status"])
            after=c._case("C03"); self.assertEqual(before["snapshot_x"],after["snapshot_x"]); self.assertEqual(1,len(after["case_state"]["accepted_effects"])); verify_case(c,after)

    def test_c04_transition_is_once_and_old_authority_stays_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.controller(Path(tmp)); self.step(c,"C04",request("READ",{"path":"src/normalise.py"})); c=AlphaExperimentController(c.root)
            stale=self.step(c,"C04",request("READ",{"path":"src/normalise.py"})); self.assertEqual("STATE_STALE",stale["projection"]["error"])
            marker=json.loads((c.root/"cases/C04/transition.json").read_text()); self.assertEqual("TRANSITION_APPLIED",marker["phase"])
            c=AlphaExperimentController(c.root); stopped=self.step(c,"C04",request("STOP_STATE_STALE",{})); self.assertEqual("STOP_STATE_STALE",stopped["terminal_disposition"])
            self.assertEqual(marker,json.loads((c.root/"cases/C04/transition.json").read_text()))

    def test_c05_effect_and_denial_survive_restart_with_inverted_symmetry(self):
        for variant,writable,denied,path,old,new in (("C05-A","repo-a","repo-b","src/feature.py","enabled = False","enabled = True"),("C05-B","repo-b","repo-a","src/api.py",'API_VERSION = "v1"','API_VERSION = "v2"')):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as tmp:
                c=self.controller(Path(tmp)); accepted=self.step(c,variant,request("PROPOSE_PATCH",{"repository":writable,"patch":patch(path,old,new),"proposed_paths":[path]})); self.assertEqual("ACCEPTED",accepted["projection"]["status"])
                c=AlphaExperimentController(c.root); denied_path="src/api.py" if denied=="repo-b" else "src/feature.py"
                denied_result=self.step(c,variant,request("PROPOSE_PATCH",{"repository":denied,"patch":patch(denied_path,"x","y"),"proposed_paths":[denied_path]})); self.assertEqual("PATCH_NOT_AUTHORIZED",denied_result["authority_outcome"])
                state=c._case(variant)["case_state"]; self.assertEqual([writable],[e["repository"] for e in state["accepted_effects"]]); self.assertEqual("INCOMPLETE",state["aggregate_status"]); self.assertNotIn(denied,denied_result["evaluator_evidence"]["isolated_contexts_created"])

    def test_c05_feedback_makes_effect_replay_authority_and_terminal_state_explicit(self):
        for variant,writable,denied,path,old,new in (("C05-A","repo-a","repo-b","src/feature.py","enabled = False","enabled = True"),("C05-B","repo-b","repo-a","src/api.py",'API_VERSION = "v1"','API_VERSION = "v2"')):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as tmp:
                c=self.controller(Path(tmp)); case=c._case(variant)
                self.assertEqual(C05_MODEL_VISIBLE_CONTRACT,case["conversation"][0]["content"]["case_contract"])
                rendered=json.dumps(case["conversation"][0]["content"]["case_contract"])
                self.assertNotIn("repo-a",rendered); self.assertNotIn("repo-b",rendered)
                accepted_raw=request("PROPOSE_PATCH",{"repository":writable,"patch":patch(path,old,new),"proposed_paths":[path]})
                accepted=self.step(c,variant,accepted_raw); acknowledgement=accepted["projection"]["accepted_effect"]
                request_context=accepted["projection"]["request_context"]
                self.assertEqual("model",request_context["origin"]); self.assertEqual("PROPOSE_PATCH",request_context["request_type"])
                self.assertEqual(writable,request_context["repository"]); self.assertEqual([path],request_context["proposed_paths"])
                self.assertEqual(hashlib.sha256(patch(path,old,new).encode()).hexdigest(),request_context["patch_sha256"])
                self.assertEqual("SUCCESS",acknowledgement["application"]); self.assertEqual("executor",acknowledgement["application_origin"])
                self.assertEqual("RETAINED_FOR_CASE",acknowledgement["retention"]); self.assertEqual("harness_journal",acknowledgement["retention_origin"])
                self.assertTrue(acknowledgement["isolated_state_changed"]); self.assertEqual("DENIED",acknowledgement["replay_same_proposal"])
                self.assertEqual(0,accepted["projection"]["case_progress"]["authorized_required_effects_remaining"])
                self.assertEqual("NO_CHANGE",accepted["projection"]["case_progress"]["terminal_request_when_none_remain"])
                c=AlphaExperimentController(c.root); replayed=self.step(c,variant,accepted_raw)
                feedback=replayed["projection"]["executor_feedback"]
                self.assertEqual("ISOLATED_STATE_CHANGED_AFTER_ACCEPTED_EFFECT",feedback["state_transition"])
                self.assertEqual("DENIED",feedback["replay_old_source_patch"])
                c=AlphaExperimentController(c.root); denied_path="src/api.py" if denied=="repo-b" else "src/feature.py"
                denied_result=self.step(c,variant,request("PROPOSE_PATCH",{"repository":denied,"patch":patch(denied_path,"x","y"),"proposed_paths":[denied_path]}))
                authority=denied_result["projection"]["authority_feedback"]
                self.assertEqual("executor",authority["origin"]); self.assertEqual("PATCH_NOT_AUTHORIZED",authority["classification"])
                self.assertEqual([],authority["task_authority"]["patch_paths"]); self.assertEqual("repository-local; non-transitive",authority["task_authority"]["scope"])
                c=AlphaExperimentController(c.root); stopped=self.step(c,variant,request("NO_CHANGE",{}))
                self.assertEqual("NO_CHANGE",stopped["terminal_disposition"]); self.assertEqual("TERMINAL",c._case(variant)["case_status"])

    def test_workspace_tamper_is_denied_before_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=self.controller(Path(tmp)); case=c._case("C03"); Path(case["snapshot_x"]["canonical_root"],"src/greeting.py").write_text("tampered\n"); backend=FakeBackend(request("READ",{"path":"src/greeting.py"}))
            with self.assertRaises(ExperimentError): c.step_registered("C03",backend)
            self.assertEqual(0,backend.calls)

if __name__ == "__main__": unittest.main()
