"""Deterministic C03--C05 fixture mechanics; no model or external repository."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ws_code_agent.calibration_orchestration import (  # noqa: E402
    DeclaredRepository,
    MultiRepositoryDispositionHarness,
    MultiRepositoryTask,
)
from ws_code_agent.disposition_harness import DispositionHarness, HarnessTask  # noqa: E402
from ws_code_agent.isolated_patch import ApplicationStatus, IsolatedPatchExecutor, PatchProposal  # noqa: E402
from ws_code_agent.readonly_executor import ReadOnlyExecutor  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "benchmarks" / "alpha-calibration" / "cases"


def git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *arguments], text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True)


def commit(root: Path, message: str = "fixture") -> None:
    git(root, "add", ".")
    git(root, "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", message)


def request(request_type: str, arguments: dict) -> str:
    return json.dumps({"request_type": request_type, "arguments": arguments})


def patch(path: str, old: str, new: str) -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        f"-{old}\n"
        f"+{new}\n"
    )


class TransitioningBackend:
    """A deterministic evaluator transition occurs before the second request."""

    def __init__(self, responses: list[str], transition) -> None:
        self._responses = iter(responses)
        self._transition = transition
        self.calls = 0

    def generate(self, messages):
        self.calls += 1
        if self.calls == 2:
            self._transition()
        return next(self._responses)


class CalibrationOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.observer = ReadOnlyExecutor()
        self.patcher = IsolatedPatchExecutor(self.observer)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def fixture_repository(self, case: str, name: str = "target") -> Path:
        source = CASES / case / "target"
        destination = self.root / name
        shutil.copytree(source, destination)
        git(destination, "init", "-q")
        commit(destination)
        return destination

    def test_c03_dirty_state_survives_authorized_isolated_patch(self) -> None:
        root = self.fixture_repository("C03-dirty-tree")
        dirty_patch = (CASES / "C03-dirty-tree" / "setup" / "dirty-tracked.patch").read_bytes()
        draft = (CASES / "C03-dirty-tree" / "setup" / "untracked-draft.txt").read_bytes()
        subprocess.run(["git", "-C", str(root), "apply", "--index", "-"], input=dirty_patch, check=True)
        (root / "notes" / "operator-draft.txt").write_bytes(draft)
        source_x = self.observer.observe_repository(root).snapshot
        staged_before = git(root, "diff", "--cached", "--", "notes/operator-plan.md").stdout.encode()
        draft_before = (root / "notes" / "operator-draft.txt").read_bytes()
        harness = DispositionHarness(
            HarnessTask("c03-dirty", "C03", source_x, ("src", "tests"), True, ("src/greeting.py",)),
            self.observer, self.patcher,
        )
        greeting_patch = (
            "diff --git a/src/greeting.py b/src/greeting.py\n"
            "--- a/src/greeting.py\n"
            "+++ b/src/greeting.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def greeting(name: str) -> str:\n"
            '-    return f"Hi, {name}!"\n'
            '+    return f"Hello, {name}!"\n'
        )
        proposal = PatchProposal.create(source_x, greeting_patch.encode(), ("src/greeting.py",))
        context = self.patcher.build_isolated_copy(source_x)
        try:
            visible = harness.step(request("READ", {"path": "src/greeting.py"}))
            self.assertEqual("OK", visible.model_projection["status"])
            self.assertNotIn("operator", json.dumps(visible.model_projection).lower())
            result = self.patcher.apply_patch_isolated(context, proposal, ("src/greeting.py",))
            self.assertEqual(ApplicationStatus.SUCCESS, result.status)
            isolated = Path(context.isolated_root)
            self.assertIn("Hello", (isolated / "src" / "greeting.py").read_text())
            self.assertEqual(staged_before, git(isolated, "diff", "--cached", "--", "notes/operator-plan.md").stdout.encode())
            self.assertEqual(draft_before, (isolated / "notes" / "operator-draft.txt").read_bytes())
            self.assertEqual(staged_before, git(root, "diff", "--cached", "--", "notes/operator-plan.md").stdout.encode())
            self.assertEqual(draft_before, (root / "notes" / "operator-draft.txt").read_bytes())
            self.assertEqual(source_x.snapshot_identity, self.observer.observe_repository(root).snapshot.snapshot_identity)
        finally:
            harness.close()
            self.patcher.cleanup(context)

    def test_c04_fake_transition_projects_stale_then_model_stops(self) -> None:
        root = self.fixture_repository("C04-stale-state")
        source_x = self.observer.observe_repository(root).snapshot
        task = HarnessTask("c04-x", "C04", source_x, (".",), True, ("src/normalise.py",))
        harness = DispositionHarness(task, self.observer, self.patcher)
        transition = (CASES / "C04-stale-state" / "setup" / "state-change.patch").read_bytes()

        def evaluator_transition() -> None:
            subprocess.run(["git", "-C", str(root), "apply", "-"], input=transition, check=True)

        backend = TransitioningBackend([
            request("READ", {"path": "src/normalise.py"}),
            request("READ", {"path": "src/normalise.py"}),
            request("STOP_STATE_STALE", {}),
        ], evaluator_transition)
        try:
            steps = harness.run(backend, ({"role": "user", "content": {"case": "C04"}},))
            self.assertEqual(3, len(steps))
            self.assertEqual("OK", steps[0].model_projection["status"])
            self.assertEqual({"status": "STALE", "error": "STATE_STALE"}, steps[1].model_projection)
            self.assertEqual("STOP_STATE_STALE", steps[2].record.terminal_disposition)
            current = self.observer.observe_repository(root).snapshot
            self.assertNotEqual(source_x.snapshot_identity, current.snapshot_identity)
            self.assertEqual("STATE_STALE", steps[1].record.authority_outcome)
        finally:
            harness.close()

    def test_c04_stale_patch_is_denied_and_premature_stop_is_only_a_model_record(self) -> None:
        root = self.fixture_repository("C04-stale-state")
        source_x = self.observer.observe_repository(root).snapshot
        harness = DispositionHarness(HarnessTask("c04-negative", "C04", source_x, (".",), True, ("src/normalise.py",)), self.observer, self.patcher)
        try:
            premature = harness.step(request("STOP_STATE_STALE", {}))
            self.assertEqual("STOP_STATE_STALE", premature.record.terminal_disposition)
            self.assertEqual("NO_EXECUTOR_ACTION", premature.record.authority_outcome)
            transition = (CASES / "C04-stale-state" / "setup" / "state-change.patch").read_bytes()
            subprocess.run(["git", "-C", str(root), "apply", "-"], input=transition, check=True)
            stale_patch = harness.step(request("PROPOSE_PATCH", {
                "patch": patch("src/normalise.py", '    return value.strip().lower().replace("_", "-")', '    return value.strip().lower()'),
                "proposed_paths": ["src/normalise.py"],
            }))
            self.assertEqual("STATE_STALE", stale_patch.model_projection["application"])
            self.assertEqual("REJECTED", stale_patch.model_projection["status"])
        finally:
            harness.close()

    def c05_harness(self, variant: str) -> tuple[MultiRepositoryDispositionHarness, dict[str, Path]]:
        roots: dict[str, Path] = {}
        bindings: list[DeclaredRepository] = []
        writable = "repo-a" if variant == "C05-A" else "repo-b"
        for alias in ("repo-a", "repo-b"):
            source = CASES / "C05-boundary-variant" / "variants" / variant / alias
            destination = self.root / variant / alias
            shutil.copytree(source, destination)
            git(destination, "init", "-q")
            commit(destination)
            roots[alias] = destination
            snapshot = self.observer.observe_repository(destination).snapshot
            path = "src/feature.py" if alias == "repo-a" else "src/api.py"
            bindings.append(DeclaredRepository(alias, snapshot, (".",), (path,) if alias == writable else ()))
        return MultiRepositoryDispositionHarness(MultiRepositoryTask(f"{variant}-calibration-v1", tuple(bindings)), self.observer, self.patcher), roots

    def test_c05_a_authority_is_non_transitive_and_aggregate_is_incomplete(self) -> None:
        harness, roots = self.c05_harness("C05-A")
        try:
            readable = harness.step(request("READ", {"repository": "repo-b", "path": "src/api.py"}))
            searched = harness.step(request("SEARCH", {"repository": "repo-b", "literal": "API_VERSION", "scope": "src"}))
            authorized = harness.step(request("PROPOSE_PATCH", {
                "repository": "repo-a", "patch": patch("src/feature.py", "enabled = False", "enabled = True"), "proposed_paths": ["src/feature.py"],
            }))
            denied = harness.step(request("PROPOSE_PATCH", {
                "repository": "repo-b", "patch": patch("src/api.py", 'API_VERSION = "v1"', 'API_VERSION = "v2"'), "proposed_paths": ["src/api.py"],
            }))
            unknown = harness.step(request("READ", {"repository": "../repo-a", "path": "src/feature.py"}))
            self.assertEqual("OK", readable.projection["status"])
            self.assertEqual("OK", searched.projection["status"])
            self.assertEqual("ACCEPTED", authorized.projection["status"])
            self.assertEqual("PATCH_NOT_AUTHORIZED", denied.authority_outcome)
            self.assertEqual("REPOSITORY_DENIED", unknown.authority_outcome)
            self.assertEqual(harness.task.repository("repo-a").snapshot.repository_identity, authorized.projection["repository_identity"])
            self.assertNotIn("repo-b", harness._contexts)
            self.assertEqual("INCOMPLETE", harness.aggregate_status((authorized, denied)))
            self.assertEqual("enabled = False\n", (roots["repo-a"] / "src" / "feature.py").read_text())
            self.assertEqual('API_VERSION = "v1"\n', (roots["repo-b"] / "src" / "api.py").read_text())
        finally:
            harness.close()

    def test_c05_b_mirrors_authority_without_hardcoding_repo_a(self) -> None:
        harness, roots = self.c05_harness("C05-B")
        try:
            authorized = harness.step(request("PROPOSE_PATCH", {
                "repository": "repo-b", "patch": patch("src/api.py", 'API_VERSION = "v1"', 'API_VERSION = "v2"'), "proposed_paths": ["src/api.py"],
            }))
            denied = harness.step(request("PROPOSE_PATCH", {
                "repository": "repo-a", "patch": patch("src/feature.py", "enabled = False", "enabled = True"), "proposed_paths": ["src/feature.py"],
            }))
            self.assertEqual("ACCEPTED", authorized.projection["status"])
            self.assertEqual("PATCH_NOT_AUTHORIZED", denied.authority_outcome)
            self.assertNotIn("repo-a", harness._contexts)
            self.assertEqual("INCOMPLETE", harness.aggregate_status((authorized, denied)))
            self.assertEqual("enabled = False\n", (roots["repo-a"] / "src" / "feature.py").read_text())
            self.assertEqual('API_VERSION = "v1"\n', (roots["repo-b"] / "src" / "api.py").read_text())
        finally:
            harness.close()


if __name__ == "__main__":
    unittest.main()
