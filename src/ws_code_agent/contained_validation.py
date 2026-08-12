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
ORACLE_STAGE_ROOT = Path("/run/ws-code-agent-validation/oracle-staging")
VALIDATOR_STAGE_ROOT = Path("/run/ws-code-agent-validation/validator-staging")
ASSET_ROOT = Path(__file__).resolve().parents[2] / "validation-assets"
TASK10K_VISIBLE_ID = "task10k-c-write-visible-v1"
TASK10K_HIDDEN_ID = "task10k-c-write-hidden-v1"
TASK10K_VISIBLE_SOURCE = ASSET_ROOT / f"{TASK10K_VISIBLE_ID}.py"
TASK10K_HIDDEN_SOURCE = ASSET_ROOT / f"{TASK10K_HIDDEN_ID}.py"
TASK11J_VISIBLE_ID = "task11j-ws-doc-writer-src-readme-visible-v1"
TASK11J_HIDDEN_ID = "task11j-ws-doc-writer-src-readme-hidden-v1"
TASK11J_VISIBLE_SOURCE = ASSET_ROOT / f"{TASK11J_VISIBLE_ID}.py"
TASK11J_HIDDEN_SOURCE = ASSET_ROOT / f"{TASK11J_HIDDEN_ID}.py"
TASK11M_VISIBLE_ID = "task11m-gpu-compute-current-state-visible-v1"
TASK11M_HIDDEN_ID = "task11m-gpu-compute-current-state-hidden-v1"
TASK11M_VISIBLE_SOURCE = ASSET_ROOT / f"{TASK11M_VISIBLE_ID}.py"
TASK11M_HIDDEN_SOURCE = ASSET_ROOT / f"{TASK11M_HIDDEN_ID}.py"
TASK11N_VISIBLE_ID = "task11n-ws-doc-writer-writing-setup-visible-v1"
TASK11N_HIDDEN_ID = "task11n-ws-doc-writer-writing-setup-hidden-v1"
TASK11N_VISIBLE_SOURCE = ASSET_ROOT / f"{TASK11N_VISIBLE_ID}.py"
TASK11N_HIDDEN_SOURCE = ASSET_ROOT / f"{TASK11N_HIDDEN_ID}.py"
STAGED_DESCRIPTORS = {
    TASK10K_VISIBLE_ID: (TASK10K_VISIBLE_SOURCE, "validator"),
    TASK10K_HIDDEN_ID: (TASK10K_HIDDEN_SOURCE, "oracle"),
    TASK11J_VISIBLE_ID: (TASK11J_VISIBLE_SOURCE, "validator"),
    TASK11J_HIDDEN_ID: (TASK11J_HIDDEN_SOURCE, "oracle"),
    TASK11M_VISIBLE_ID: (TASK11M_VISIBLE_SOURCE, "validator"),
    TASK11M_HIDDEN_ID: (TASK11M_HIDDEN_SOURCE, "oracle"),
    TASK11N_VISIBLE_ID: (TASK11N_VISIBLE_SOURCE, "validator"),
    TASK11N_HIDDEN_ID: (TASK11N_HIDDEN_SOURCE, "oracle"),
}


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
        staged_digest = ""
        staged_kind = ""
        try:
            if descriptor.descriptor_id == "C01-visible":
                expected = ("-B", "-m", "unittest", "discover", "-s", "tests")
                if descriptor.arguments != expected:
                    raise ContainmentUnavailable("C01 visible descriptor does not match the fixed contained command")
            elif descriptor.descriptor_id == "C01-oracle":
                if descriptor.arguments != ("-B", str(self._oracle_source)) or not self._oracle_source.is_file():
                    raise ContainmentUnavailable("C01 oracle descriptor does not match the fixed staged oracle")
                if not ORACLE_STAGE_ROOT.is_dir():
                    raise ContainmentUnavailable("ws-cp oracle staging root unavailable")
                stage = Path(tempfile.mkdtemp(prefix="run-", dir=ORACLE_STAGE_ROOT))
                oracle = stage / "oracle.py"
                staged_digest = hashlib.sha256(self._oracle_source.read_bytes()).hexdigest()
                shutil.copyfile(self._oracle_source, oracle)
                if hashlib.sha256(oracle.read_bytes()).hexdigest() != staged_digest:
                    raise ContainmentUnavailable("staged oracle digest mismatch")
                if tuple(path.name for path in stage.iterdir()) != ("oracle.py",):
                    raise ContainmentUnavailable("oracle stage is not single-artifact")
                os.chmod(oracle, 0o444)
                os.chmod(stage, 0o555)
                command.extend(("--oracle-dir", str(stage)))
                staged_kind = "oracle"
            elif descriptor.descriptor_id in STAGED_DESCRIPTORS:
                source, staged_kind = STAGED_DESCRIPTORS[descriptor.descriptor_id]
                expected = ("-B", str(source))
                if descriptor.arguments != expected or not source.is_file() or source.is_symlink():
                    raise ContainmentUnavailable("descriptor does not match its fixed staged validator")
                stage_root = VALIDATOR_STAGE_ROOT if staged_kind == "validator" else ORACLE_STAGE_ROOT
                if not stage_root.is_dir():
                    raise ContainmentUnavailable("validation staging root unavailable")
                stage = Path(tempfile.mkdtemp(prefix="run-", dir=stage_root))
                name = "validator.py" if staged_kind == "validator" else "oracle.py"
                staged = stage / name
                staged_digest = hashlib.sha256(source.read_bytes()).hexdigest()
                shutil.copyfile(source, staged)
                if hashlib.sha256(staged.read_bytes()).hexdigest() != staged_digest:
                    raise ContainmentUnavailable("staged validator digest mismatch")
                if tuple(path.name for path in stage.iterdir()) != (name,):
                    raise ContainmentUnavailable("validation stage is not single-artifact")
                os.chmod(staged, 0o444)
                os.chmod(stage, 0o555)
                option = "--validator-dir" if staged_kind == "validator" else "--oracle-dir"
                command.extend((option, str(stage)))
            else:
                raise ContainmentUnavailable("descriptor is not approved for contained validation")
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
            evidence["CONTAINMENT_ORACLE_SHA256"] = staged_digest
        elif staged_kind == "oracle":
            evidence["CONTAINMENT_ORACLE_SHA256"] = staged_digest
        elif staged_kind == "validator":
            evidence["CONTAINMENT_VALIDATOR_SHA256"] = staged_digest
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
