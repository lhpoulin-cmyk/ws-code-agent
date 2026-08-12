from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from tools.task11b_patch_forensics import (  # noqa: E402
    INCORRECT_HUNK_COUNTS,
    INVALID_CONTEXT,
    MISSING_FILE_HEADER,
    NO_SUPPORTED_DIFF_HEADER,
    TRUNCATED_PATCH,
    WRONG_TARGET_PATH,
    canonical_unified_diff,
    inspect_patch,
)


NEW_FILE_RESULT = b'def message():\n    return "hello"\n'
EXISTING_SOURCE = b'def message():\n    return "hi"\n'
EXISTING_RESULT = b'def message():\n    return "hello"\n'


def git(root: Path, *arguments: str, input_bytes: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class PatchForensicsTests(unittest.TestCase):
    def test_new_file_wrong_count_is_serialization_not_semantic_loss(self):
        patch = (
            b"diff --git a/src/message.py b/src/message.py\n"
            b"new file mode 100644\n"
            b"--- /dev/null\n"
            b"+++ b/src/message.py\n"
            b"@@ -0,0 +1,3 @@\n"
            b"+def message():\n"
            b'+    return "hello"\n'
        )
        evidence = inspect_patch(patch, ("src/message.py",))
        self.assertEqual((INCORRECT_HUNK_COUNTS,), evidence.findings)
        self.assertEqual(("def message():", '    return "hello"'), evidence.hunks[0].added_lines)
        self.assertEqual(("src/message.py",), evidence.target_paths)

    def test_existing_file_failures_separate_envelope_context_counts_and_newline(self):
        headerless = (
            b"@@ -1,2 +1,2 @@\n"
            b"def message():\n"
            b'-    return "hi"\n'
            b'+    return "hello"'
        )
        evidence = inspect_patch(headerless, ("src/message.py",))
        self.assertEqual(
            {
                NO_SUPPORTED_DIFF_HEADER,
                MISSING_FILE_HEADER,
                INVALID_CONTEXT,
                INCORRECT_HUNK_COUNTS,
                TRUNCATED_PATCH,
            },
            set(evidence.findings),
        )
        enveloped = (
            b"diff --git a/src/message.py b/src/message.py\n"
            b"--- a/src/message.py\n"
            b"+++ b/src/message.py\n"
            + headerless
        )
        evidence = inspect_patch(enveloped, ("src/message.py",))
        self.assertEqual(
            {INVALID_CONTEXT, INCORRECT_HUNK_COUNTS, TRUNCATED_PATCH},
            set(evidence.findings),
        )
        self.assertEqual(('    return "hi"',), evidence.hunks[0].removed_lines)
        self.assertEqual(('    return "hello"',), evidence.hunks[0].added_lines)
        self.assertEqual(("def message():",), evidence.hunks[0].invalid_lines)

    def test_terminal_newline_distinguishes_32b_rejected_and_accepted_shapes(self):
        rejected = (
            b"diff --git a/src/message.py b/src/message.py\n"
            b"new file mode 100644\n"
            b"index 0000000..e69de29\n"
            b"--- /dev/null\n"
            b"+++ b/src/message.py\n"
            b"@@ -0,0 +1 @@\n"
            b'+def message(): return "hello"'
        )
        accepted = (
            b"diff --git a/src/message.py b/src/message.py\n"
            b"new file mode 100644\n"
            b"--- /dev/null\n"
            b"+++ b/src/message.py\n"
            b"@@ -0,0 +1 @@\n"
            b'+def message(): return "hello"\n'
        )
        self.assertEqual((TRUNCATED_PATCH,), inspect_patch(rejected, ("src/message.py",)).findings)
        self.assertEqual((), inspect_patch(accepted, ("src/message.py",)).findings)
        self.assertEqual(
            inspect_patch(rejected, ("src/message.py",)).hunks[0].added_lines,
            inspect_patch(accepted, ("src/message.py",)).hunks[0].added_lines,
        )

    def test_canonical_controls_are_deterministic_and_git_apply_compatible(self):
        controls = (
            (None, NEW_FILE_RESULT),
            (EXISTING_SOURCE, EXISTING_RESULT),
        )
        for before, after in controls:
            first = canonical_unified_diff("src/message.py", before, after)
            second = canonical_unified_diff("src/message.py", before, after)
            self.assertEqual(first, second)
            self.assertEqual((), inspect_patch(first, ("src/message.py",)).findings)
            with tempfile.TemporaryDirectory(prefix="task11b-forensic-control-") as temporary:
                repository = Path(temporary)
                (repository / "src").mkdir()
                git(repository, "init", "-q")
                if before is not None:
                    (repository / "src/message.py").write_bytes(before)
                else:
                    (repository / "README.md").write_text("fixture\n", encoding="utf-8")
                git(repository, "add", ".")
                git(
                    repository,
                    "-c", "user.name=Task11B",
                    "-c", "user.email=task11b@example.invalid",
                    "commit", "-qm", "forensic control",
                )
                result = git(repository, "apply", "--index", "--whitespace=nowarn", "-", input_bytes=first)
                self.assertEqual(0, result.returncode, result.stderr.decode())
                self.assertEqual(after, (repository / "src/message.py").read_bytes())
                self.assertEqual("src/message.py\n", git(repository, "diff", "--cached", "--name-only").stdout.decode())

    def test_forensics_never_rewrites_authority_or_wrong_target(self):
        patch = canonical_unified_diff("src/other.py", None, NEW_FILE_RESULT)
        evidence = inspect_patch(patch, ("src/message.py",))
        self.assertIn(WRONG_TARGET_PATH, evidence.findings)
        self.assertEqual(("src/other.py",), evidence.target_paths)
        for production_module in (
            "src/ws_code_agent/disposition_harness.py",
            "src/ws_code_agent/isolated_patch.py",
            "src/ws_code_agent/supervised_work.py",
        ):
            self.assertNotIn("patch_forensics", Path(production_module).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
