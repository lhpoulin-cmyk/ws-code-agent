"""Task 11C deterministic structured text-replacement candidate tests."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ws_code_agent.disposition_harness import parse_request  # noqa: E402
from ws_code_agent.readonly_executor import ReadOnlyExecutor  # noqa: E402
from ws_code_agent.request_protocol import STRUCTURED_EDIT_PROTOCOL  # noqa: E402
from ws_code_agent.response_normalization import normalize_single_markdown_json_fence  # noqa: E402
from ws_code_agent.structured_edit import (  # noqa: E402
    StructuredTextReplacement,
    StructuredTextReplacementExecutor,
    TextReplacementStatus,
)
from ws_code_agent.supervised_validation import HIDDEN_SOURCE, VISIBLE_SOURCE  # noqa: E402


SOURCE = 'def message():\n    return "hi"\n'
RESULT = 'def message():\n    return "hello"\n'


def git(root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return process.stdout.decode("utf-8", errors="strict").strip()


def make_repo(root: Path, source: bytes = SOURCE.encode()) -> None:
    root.mkdir()
    git(root, "init", "-q")
    (root / "src").mkdir()
    (root / "src/message.py").write_bytes(source)
    git(root, "add", ".")
    git(
        root,
        "-c", "user.name=Task11C",
        "-c", "user.email=task11c@example.invalid",
        "commit", "-qm", "fixture",
    )


class StructuredEditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repository"
        make_repo(self.root)
        self.observer = ReadOnlyExecutor()
        self.snapshot = self.observer.observe_repository(self.root).snapshot
        self.executor = StructuredTextReplacementExecutor(self.observer)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def proposal(
        self,
        *,
        path: str = "src/message.py",
        old: str = '    return "hi"\n',
        new: str = '    return "hello"\n',
        snapshot=None,
    ) -> StructuredTextReplacement:
        return StructuredTextReplacement.create(
            snapshot or self.snapshot,
            raw_request_sha256="a" * 64,
            path=path,
            old_text=old,
            new_text=new,
        )

    def apply(self, proposal=None, allowed=("src/message.py",)):
        context = self.executor.build_isolated_copy(self.snapshot)
        result = self.executor.apply_text_replacement_isolated(
            context, proposal or self.proposal(), allowed
        )
        return context, result

    def test_exact_replacement_isolated_with_evaluator_owned_canonical_diff(self) -> None:
        source_identity = self.snapshot.snapshot_identity
        proposal = self.proposal()
        context, result = self.apply(proposal)
        try:
            self.assertEqual(TextReplacementStatus.STRUCTURED_EDIT_ACCEPTED, result.status)
            self.assertEqual(1, result.exact_match_count)
            self.assertEqual(("src/message.py",), result.actual_changed_paths)
            self.assertEqual(RESULT, (Path(context.isolated_root) / "src/message.py").read_text())
            self.assertEqual(SOURCE, (self.root / "src/message.py").read_text())
            self.assertEqual(source_identity, self.observer.observe_repository(self.root).snapshot.snapshot_identity)
            self.assertEqual("evaluator", result.fact.observed_result["canonical_diff_origin"])
            self.assertEqual(result.canonical_diff_sha256, hashlib.sha256(result.canonical_diff).hexdigest())
            self.assertEqual(
                b'diff --git a/src/message.py b/src/message.py\n',
                result.canonical_diff.splitlines(keepends=True)[0],
            )
            check = subprocess.run(
                ["git", "-C", str(self.root), "apply", "--check", "-"],
                input=result.canonical_diff,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, check.returncode, check.stderr)
            self.assertEqual(proposal.path, "src/message.py")
            self.assertEqual(proposal.old_text, '    return "hi"\n')
            self.assertEqual(proposal.new_text, '    return "hello"\n')
        finally:
            self.executor.cleanup(context)

    def test_same_request_and_snapshot_have_deterministic_bytes_and_identity(self) -> None:
        proposal = self.proposal()
        context_one, first = self.apply(proposal)
        context_two, second = self.apply(proposal)
        try:
            self.assertEqual(first.canonical_diff, second.canonical_diff)
            self.assertEqual(first.canonical_diff_sha256, second.canonical_diff_sha256)
            self.assertEqual(first.candidate_identity, second.candidate_identity)
            self.assertEqual(first.after_file_sha256, second.after_file_sha256)
            self.assertEqual(
                (Path(context_one.isolated_root) / "src/message.py").read_bytes(),
                (Path(context_two.isolated_root) / "src/message.py").read_bytes(),
            )
        finally:
            self.executor.cleanup(context_one)
            self.executor.cleanup(context_two)

    def test_canonical_diff_handles_source_without_terminal_newline(self) -> None:
        (self.root / "src/message.py").write_text('value = "hi"', encoding="utf-8")
        git(self.root, "add", "src/message.py")
        git(
            self.root,
            "-c", "user.name=Task11C",
            "-c", "user.email=task11c@example.invalid",
            "commit", "-qm", "no newline fixture",
        )
        self.snapshot = self.observer.observe_repository(self.root).snapshot
        context, result = self.apply(self.proposal(old='value = "hi"', new='value = "hello"'))
        try:
            self.assertEqual(TextReplacementStatus.STRUCTURED_EDIT_ACCEPTED, result.status)
            self.assertIn(b"\\ No newline at end of file", result.canonical_diff)
            check = subprocess.run(
                ["git", "-C", str(self.root), "apply", "--check", "-"],
                input=result.canonical_diff,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, check.returncode, check.stderr)
        finally:
            self.executor.cleanup(context)

    def test_zero_multiple_no_effect_and_empty_old_text_fail_closed(self) -> None:
        cases = (
            (self.proposal(old="not present"), TextReplacementStatus.TEXT_MATCH_ZERO),
            (self.proposal(old="e", new="x"), TextReplacementStatus.TEXT_MATCH_MULTIPLE),
            (self.proposal(old="hi", new="hi"), TextReplacementStatus.TEXT_REPLACEMENT_NO_EFFECT),
        )
        for proposal, expected in cases:
            with self.subTest(expected=expected):
                context, result = self.apply(proposal)
                try:
                    self.assertEqual(expected, result.status)
                    self.assertEqual(SOURCE, (Path(context.isolated_root) / "src/message.py").read_text())
                finally:
                    self.executor.cleanup(context)
        with self.assertRaisesRegex(ValueError, "non-empty"):
            self.proposal(old="")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            StructuredTextReplacement.create(
                self.snapshot,
                raw_request_sha256="not-a-digest",
                path="src/message.py",
                old_text="hi",
                new_text="hello",
            )
        self.assertEqual(
            2,
            StructuredTextReplacementExecutor._exact_occurrence_count("aaa", "aa"),
        )

    def test_deletion_is_only_an_exact_replacement_not_file_deletion(self) -> None:
        context, result = self.apply(self.proposal(old='    return "hi"\n', new=""))
        try:
            self.assertEqual(TextReplacementStatus.STRUCTURED_EDIT_ACCEPTED, result.status)
            self.assertTrue((Path(context.isolated_root) / "src/message.py").is_file())
            self.assertEqual("def message():\n", (Path(context.isolated_root) / "src/message.py").read_text())
        finally:
            self.executor.cleanup(context)

    def test_authority_absolute_traversal_git_and_symlink_escape_are_denied(self) -> None:
        paths = (
            "README.md",
            "/tmp/message.py",
            "../message.py",
            ".git/config",
            "src//message.py",
            "src/./message.py",
        )
        for path in paths:
            with self.subTest(path=path):
                context, result = self.apply(self.proposal(path=path), (path,))
                try:
                    self.assertEqual(TextReplacementStatus.DENIED_AUTHORITY, result.status)
                finally:
                    self.executor.cleanup(context)

        outside = Path(self.temporary.name) / "outside.py"
        outside.write_text(SOURCE)
        (self.root / "src/link.py").symlink_to(outside)
        git(self.root, "add", "src/link.py")
        git(
            self.root,
            "-c", "user.name=Task11C",
            "-c", "user.email=task11c@example.invalid",
            "commit", "-qm", "symlink",
        )
        self.snapshot = self.observer.observe_repository(self.root).snapshot
        context, result = self.apply(self.proposal(path="src/link.py"), ("src/link.py",))
        try:
            self.assertEqual(TextReplacementStatus.DENIED_AUTHORITY, result.status)
            self.assertEqual(SOURCE, outside.read_text())
        finally:
            self.executor.cleanup(context)

    def test_non_utf8_and_nul_text_are_unsupported(self) -> None:
        for source in (b"\xff\xfe\n", b"hello\0world\n"):
            with self.subTest(source=source):
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary) / "repository"
                    make_repo(root, source)
                    snapshot = self.observer.observe_repository(root).snapshot
                    executor = StructuredTextReplacementExecutor(self.observer)
                    context = executor.build_isolated_copy(snapshot)
                    proposal = StructuredTextReplacement.create(
                        snapshot,
                        raw_request_sha256="b" * 64,
                        path="src/message.py",
                        old_text="hello",
                        new_text="goodbye",
                    )
                    try:
                        result = executor.apply_text_replacement_isolated(
                            context, proposal, ("src/message.py",)
                        )
                        self.assertEqual(TextReplacementStatus.TEXT_ENCODING_UNSUPPORTED, result.status)
                    finally:
                        executor.cleanup(context)
        context, result = self.apply(self.proposal(new="hello\0world"))
        try:
            self.assertEqual(TextReplacementStatus.TEXT_ENCODING_UNSUPPORTED, result.status)
            self.assertEqual(SOURCE, (Path(context.isolated_root) / "src/message.py").read_text())
        finally:
            self.executor.cleanup(context)

    def test_stale_source_and_foreign_repository_binding_are_distinct(self) -> None:
        context = self.executor.build_isolated_copy(self.snapshot)
        proposal = self.proposal()
        (self.root / "src/message.py").write_text(SOURCE + "# stale\n")
        try:
            result = self.executor.apply_text_replacement_isolated(
                context, proposal, ("src/message.py",)
            )
            self.assertEqual(TextReplacementStatus.STATE_STALE, result.status)
        finally:
            self.executor.cleanup(context)

        # Binding failure is evaluated before the now-stale source check.
        context = self.executor.build_isolated_copy(
            self.observer.observe_repository(self.root).snapshot
        )
        foreign = replace(proposal, target_repository_identity="foreign")
        try:
            result = self.executor.apply_text_replacement_isolated(
                context, foreign, ("src/message.py",)
            )
            self.assertEqual(TextReplacementStatus.REPOSITORY_MISMATCH, result.status)
        finally:
            self.executor.cleanup(context)

    def test_invalid_code_is_candidate_transport_success_but_validation_failure(self) -> None:
        context, result = self.apply(self.proposal(new='    return "hello" +\n'))
        try:
            self.assertEqual(TextReplacementStatus.STRUCTURED_EDIT_ACCEPTED, result.status)
            for validator in (VISIBLE_SOURCE, HIDDEN_SOURCE):
                process = subprocess.run(
                    [sys.executable, "-B", str(validator)],
                    cwd=context.isolated_root,
                    env={"PATH": os.defpath, "LC_ALL": "C", "PYTHONDONTWRITEBYTECODE": "1"},
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertNotEqual(0, process.returncode)
        finally:
            self.executor.cleanup(context)

    def test_normalization_and_parser_preserve_all_model_selected_values(self) -> None:
        arguments = {
            "path": "src/message.py",
            "old_text": '    return "hi"\n',
            "new_text": '    return "hello"\n',
        }
        payload = json.dumps(
            {"request_type": "PROPOSE_TEXT_REPLACEMENT", "arguments": arguments},
            separators=(",", ":"),
        ).encode()
        normalized = normalize_single_markdown_json_fence(b"```json\n" + payload + b"\n```\n")
        parsed = parse_request(
            normalized.normalized_parser_input.decode(), protocol=STRUCTURED_EDIT_PROTOCOL
        )
        self.assertEqual(arguments, parsed.arguments)
        proposal = StructuredTextReplacement.create(
            self.snapshot,
            raw_request_sha256=normalized.raw_sha256,
            **parsed.arguments,
        )
        self.assertEqual(hashlib.sha256(arguments["path"].encode()).hexdigest(), proposal.path_sha256)
        self.assertEqual(hashlib.sha256(arguments["old_text"].encode()).hexdigest(), proposal.old_text_sha256)
        self.assertEqual(hashlib.sha256(arguments["new_text"].encode()).hexdigest(), proposal.new_text_sha256)


if __name__ == "__main__":
    unittest.main()
