"""Fixed Task 10A systemd validation containment; never a command interface."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import TYPE_CHECKING

from .isolated_patch import IsolatedContext

if TYPE_CHECKING:
    from .validation import ValidationDescriptor


WRAPPER = Path("/usr/local/libexec/ws-code-agent-contained-validation")
ORACLE_SOURCE = Path("/home/louis/.local/share/ws-code-agent/alpha-private/C01-oracle.py")
ORACLE_STAGE_ROOT = Path("/run/user/1000/ws-code-agent-validation-oracle")


class ContainmentUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ContainedExecution:
    exit_code: int
    stdout: bytes
    stderr: bytes
    evidence: dict[str, str]


class SystemdContainedValidationRunner:
    """Run only the fixed C01 descriptors through the ws-cp sandbox wrapper."""

    def __init__(self, wrapper: Path = WRAPPER, oracle_source: Path = ORACLE_SOURCE) -> None:
        self._wrapper = wrapper
        self._oracle_source = oracle_source

    def run(self, context: IsolatedContext, descriptor: "ValidationDescriptor") -> ContainedExecution:
        if not self._wrapper.is_file() or not os.access(self._wrapper, os.X_OK):
            raise ContainmentUnavailable("fixed systemd validation wrapper unavailable")
        root = Path(context.isolated_root).resolve()
        if not str(root).startswith("/tmp/ws-code-agent-isolated-"):
            raise ContainmentUnavailable("isolated root is outside the contained-validation boundary")
        command = ["sudo", "-n", str(self._wrapper), "--descriptor", descriptor.descriptor_id,
                   "--root", str(root), "--timeout-seconds", str(descriptor.timeout_seconds)]
        stage: Path | None = None
        oracle_digest = ""
        if descriptor.descriptor_id == "C01-visible":
            expected = ("-B", "-m", "unittest", "discover", "-s", "tests")
            if descriptor.arguments != expected:
                raise ContainmentUnavailable("C01 visible descriptor does not match the fixed contained command")
        elif descriptor.descriptor_id == "C01-oracle":
            if descriptor.arguments != ("-B", str(self._oracle_source)) or not self._oracle_source.is_file():
                raise ContainmentUnavailable("C01 oracle descriptor does not match the fixed staged oracle")
            ORACLE_STAGE_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix="run-", dir=ORACLE_STAGE_ROOT))
            oracle = stage / "oracle.py"
            oracle_digest = hashlib.sha256(self._oracle_source.read_bytes()).hexdigest()
            shutil.copyfile(self._oracle_source, oracle)
            if hashlib.sha256(oracle.read_bytes()).hexdigest() != oracle_digest:
                raise ContainmentUnavailable("staged oracle digest mismatch")
            if tuple(path.name for path in stage.iterdir()) != ("oracle.py",):
                raise ContainmentUnavailable("oracle stage is not single-artifact")
            os.chmod(oracle, 0o444)
            os.chmod(stage, 0o555)
            command.extend(("--oracle-dir", str(stage)))
        else:
            raise ContainmentUnavailable("descriptor is not approved for contained Task 10A validation")
        try:
            process = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     timeout=descriptor.timeout_seconds + 5, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ContainmentUnavailable(f"contained validation could not complete: {type(error).__name__}") from error
        finally:
            if stage is not None:
                os.chmod(stage, 0o700)
                shutil.rmtree(stage, ignore_errors=True)
        evidence = self._evidence(process.stderr)
        required = {"CONTAINMENT_MECHANISM", "CONTAINMENT_PROFILE", "CONTAINMENT_UNIT", "CONTAINMENT_UID_GID", "CONTAINMENT_NETWORK", "CONTAINMENT_RESULT"}
        if descriptor.descriptor_id == "C01-oracle":
            evidence["CONTAINMENT_ORACLE_PROJECTION"] = "single-artifact-directory"
            evidence["CONTAINMENT_ORACLE_SHA256"] = oracle_digest
        if not required <= set(evidence):
            raise ContainmentUnavailable("contained validation returned incomplete containment evidence")
        return ContainedExecution(process.returncode, process.stdout, process.stderr, evidence)

    @staticmethod
    def _evidence(stderr: bytes) -> dict[str, str]:
        result: dict[str, str] = {}
        for line in stderr.decode("utf-8", errors="replace").splitlines():
            if line.startswith("CONTAINMENT_") and "=" in line:
                key, value = line.split("=", 1)
                result[key] = value
        return result
