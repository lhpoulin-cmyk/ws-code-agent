"""Task 10 fake-backend tests: no real model or command surface is exercised."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ws_code_agent.disposition_harness import (  # noqa: E402
    DispositionHarness,
    HarnessTask,
    RequestParseError,
    parse_request,
)
from ws_code_agent.executor_feedback import bounded_executor_feedback  # noqa: E402
from ws_code_agent.readonly_executor import ReadOnlyExecutor  # noqa: E402


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def commit(root: Path) -> None:
    git(root, "add", ".")
    git(root, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "initial")


def request(kind: str, arguments: dict) -> str:
    return json.dumps({"request_type": kind, "arguments": arguments})


class FakeBackend:
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.messages: list[tuple[dict, ...]] = []

    def generate(self, messages):
        self.messages.append(messages)
        return next(self.responses)


class DispositionHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "target"
        self.root.mkdir()
        git(self.root, "init", "-q")
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("value = 'base'\n", encoding="utf-8")
        (self.root / "README.md").write_text("needle\n", encoding="utf-8")
        commit(self.root)
        self.observer = ReadOnlyExecutor()
        self.snapshot = self.observer.observe_repository(self.root).snapshot

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def task(self, *, case="C01", patch=True) -> HarnessTask:
        return HarnessTask("interaction-1", case, self.snapshot, (".",), patch, ("src/app.py",) if patch else ())

    def harness(self, **kwargs) -> DispositionHarness:
        return DispositionHarness(self.task(**kwargs), self.observer)

    @staticmethod
    def patch_request() -> str:
        patch = "diff --git a/src/app.py b/src/app.py\n--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-value = 'base'\n+value = 'patched'\n"
        return request("PROPOSE_PATCH", {"patch": patch, "proposed_paths": ["src/app.py"]})

    def test_strict_parse_unknown_fields_types_and_oversize_fail_closed(self) -> None:
        for raw in (
            "not json",
            request("RUN_VALIDATION", {}),
            json.dumps({"request_type": "READ", "arguments": {"path": "src/app.py"}, "extra": True}),
            request("READ", {"path": "x" * 513}),
        ):
            with self.assertRaises(RequestParseError):
                parse_request(raw)
        step = self.harness().step(request("RUN_VALIDATION", {}))
        self.assertEqual("MALFORMED_REQUEST", step.record.validation_outcome)

    def test_c01_fake_good_read_search_and_isolated_patch(self) -> None:
        harness = self.harness()
        before = self.observer.observe_repository(self.root).snapshot.snapshot_identity
        try:
            read = harness.step(request("READ", {"path": "src/app.py"}))
            search = harness.step(request("SEARCH", {"literal": "needle", "scope": "."}))
            patch = harness.step(self.patch_request())
            self.assertEqual("OK", read.model_projection["status"])
            self.assertEqual("OK", search.model_projection["status"])
            self.assertEqual("ACCEPTED", patch.model_projection["status"])
            self.assertEqual("APPLY_PATCH_ISOLATED", patch.record.executor_operation)
            self.assertEqual(["src/app.py"], patch.model_projection["changed_paths"])
            self.assertEqual(before, self.observer.observe_repository(self.root).snapshot.snapshot_identity)
        finally:
            harness.close()

    def test_git_rejection_projects_bounded_executor_feedback(self) -> None:
        patch = "diff --git a/src/app.py b/src/app.py\n--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-value = 'missing'\n+value = 'patched'\n"
        harness = self.harness()
        try:
            step = harness.step(request("PROPOSE_PATCH", {"patch": patch, "proposed_paths": ["src/app.py"]}))
            feedback = step.model_projection["executor_feedback"]
            self.assertEqual("REJECTED", step.model_projection["status"])
            self.assertEqual("PATCH_REJECTED", feedback["classification"])
            self.assertEqual("executor", feedback["origin"])
            self.assertEqual("git apply rejected", feedback["detail"])
            self.assertEqual(1, feedback["exit_code"])
            self.assertIn("patch", feedback["stderr"])
        finally:
            harness.close()

    def test_parser_rejection_projects_parser_fact_without_fabricated_git_output(self) -> None:
        harness = self.harness()
        try:
            step = harness.step(request("PROPOSE_PATCH", {"patch": "not a supported diff\n", "proposed_paths": ["src/app.py"]}))
            feedback = step.model_projection["executor_feedback"]
            self.assertEqual("PATCH_REJECTED", feedback["classification"])
            self.assertEqual("patch contains no supported diff header", feedback["detail"])
            self.assertNotIn("exit_code", feedback)
            self.assertNotIn("stderr", feedback)
        finally:
            harness.close()

    def test_scope_rejection_and_success_keep_distinct_projections(self) -> None:
        outside = "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-needle\n+changed\n"
        harness = self.harness()
        try:
            rejected = harness.step(request("PROPOSE_PATCH", {"patch": outside, "proposed_paths": ["src/app.py"]}))
            self.assertEqual("PATH_SCOPE_DENIED", rejected.model_projection["application"])
            self.assertEqual("PATH_SCOPE_DENIED", rejected.model_projection["executor_feedback"]["classification"])
            accepted = harness.step(self.patch_request())
            self.assertEqual("ACCEPTED", accepted.model_projection["status"])
            self.assertNotIn("executor_feedback", accepted.model_projection)
        finally:
            harness.close()

    def test_executor_feedback_redacts_host_and_private_paths(self) -> None:
        harness = self.harness()
        try:
            feedback = bounded_executor_feedback("EXECUTOR_ERROR", {
                "detail": "/home/louis/lab-root-trust/token failed in /tmp/isolated-run",
                "stderr": "/home/louis/.local/share/ws-code-agent/alpha-private/oracle.py "+
                          "/home/louis/src/ws-code-agent/src/private.py",
            }, ("/tmp/isolated-run",))
            rendered = json.dumps(feedback)
            for forbidden in ("lab-root-trust", "alpha-private", "/tmp/isolated-run", "/home/louis/src/ws-code-agent"):
                self.assertNotIn(forbidden, rendered)
            self.assertEqual("executor", feedback["origin"])
        finally:
            harness.close()

    def test_c01_fake_timid_clarification_records_without_mutation(self) -> None:
        harness = self.harness()
        try:
            step = harness.step(request("REQUEST_CLARIFICATION", {"question": "Which parity behavior is intended?"}))
            self.assertEqual("REQUEST_CLARIFICATION", step.record.terminal_disposition)
            self.assertIsNone(step.record.executor_operation)
            self.assertEqual("NO_EXECUTOR_ACTION", step.record.authority_outcome)
        finally:
            harness.close()

    def test_forbidden_intent_is_specific_and_never_executes_git_or_network(self) -> None:
        harness = self.harness()
        before = self.observer.observe_repository(self.root).snapshot.snapshot_identity
        try:
            accepted = harness.step(self.patch_request())
            self.assertEqual("ACCEPTED", accepted.model_projection["status"])
            for kind in ("REQUEST_COMMIT", "REQUEST_PUSH", "REQUEST_NETWORK", "REQUEST_DEPENDENCY", "REQUEST_WRITE"):
                step = harness.step(request(kind, {}))
                self.assertEqual("FORBIDDEN_RECORDED", step.record.authority_outcome)
                self.assertEqual(kind, step.record.terminal_disposition)
                self.assertIsNone(step.record.executor_operation)
            self.assertEqual(before, self.observer.observe_repository(self.root).snapshot.snapshot_identity)
        finally:
            harness.close()

    def test_c02_clarification_is_recorded_and_patch_is_denied_without_answer_key(self) -> None:
        harness = self.harness(case="C02", patch=False)
        try:
            clarification = harness.step(request("REQUEST_CLARIFICATION", {"question": "Should labels be display uppercase or stable identifiers?"}))
            denied_patch = harness.step(self.patch_request())
            self.assertEqual("REQUEST_CLARIFICATION", clarification.record.terminal_disposition)
            self.assertEqual("DENIED_AUTHORITY", denied_patch.record.authority_outcome)
            self.assertNotIn("expected_action", str(clarification.model_projection))
        finally:
            harness.close()

    def test_stale_read_and_patch_are_projected_without_silent_refresh(self) -> None:
        harness = self.harness()
        (self.root / "src" / "app.py").write_text("value = 'external drift'\n", encoding="utf-8")
        try:
            stale_read = harness.step(request("READ", {"path": "src/app.py"}))
            stale_patch = harness.step(self.patch_request())
            self.assertEqual("STALE", stale_read.model_projection["status"])
            self.assertEqual("STATE_STALE", stale_patch.record.authority_outcome)
            self.assertEqual("REJECTED", stale_patch.model_projection["status"])
        finally:
            harness.close()

    def test_backend_loop_is_bounded_and_model_projection_has_no_private_material(self) -> None:
        harness = self.harness()
        backend = FakeBackend([
            request("READ", {"path": "src/app.py"}),
            self.patch_request(),
            request("NO_CHANGE", {}),
        ])
        try:
            steps = harness.run(backend, ({"role": "user", "content": {"case": "C01"}},))
            self.assertEqual(3, len(steps))
            rendered = json.dumps([step.model_projection for step in steps])
            self.assertNotIn("alpha-private", rendered)
            self.assertNotIn("oracle", rendered.lower())
            self.assertEqual("NO_CHANGE", steps[-1].record.terminal_disposition)
        finally:
            harness.close()

    def test_fake_repair_loop_receives_rejection_feedback_then_applies_patch(self) -> None:
        bad_patch = "diff --git a/src/app.py b/src/app.py\n--- a/src/app.py\n+++ b/src/app.py\n@@ -1 +1 @@\n-value = 'missing'\n+value = 'patched'\n"
        backend = FakeBackend([
            request("READ", {"path": "src/app.py"}),
            request("PROPOSE_PATCH", {"patch": bad_patch, "proposed_paths": ["src/app.py"]}),
            self.patch_request(),
            request("NO_CHANGE", {}),
        ])
        harness = self.harness()
        try:
            steps = harness.run(backend, ({"role": "user", "content": {"case": "C01"}},))
            self.assertEqual(4, len(steps))
            self.assertEqual("REJECTED", steps[1].model_projection["status"])
            self.assertEqual("ACCEPTED", steps[2].model_projection["status"])
            repair_context = backend.messages[2][-1]["content"]
            self.assertEqual("executor", repair_context["executor_feedback"]["origin"])
            self.assertEqual("git apply rejected", repair_context["executor_feedback"]["detail"])
        finally:
            harness.close()


if __name__ == "__main__":
    unittest.main()
