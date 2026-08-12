"""Publication-tree hygiene for inherited Doc Writer identity."""

from __future__ import annotations

import json
import ast
from pathlib import Path
import subprocess
from typing import Any


HISTORICAL_RECORDS = {
    "docs/contracts/CODING_AGENT_FOUNDATION_CONTRACT.md",
    "docs/experiments/task11j-first-real-local-repository-v3-pilot.md",
    "docs/experiments/task11n-distinct-real-code-interactive-pilot.md",
}
PILOT_MANIFESTS = {
    "docs/work/task11j-ws-doc-writer-real-repository-pilot-v1.json":
        "TASK11J-FIRST-REAL-LOCAL-REPOSITORY-V3-PILOT",
    "docs/work/task11l-ws-doc-writer-real-repository-pilot-v1.json":
        "TASK11L-FRESH-REAL-REPOSITORY-PILOT-UNDER-REPAIRED-APPARATUS",
    "docs/work/task11n-ws-doc-writer-writing-setup-code-v1.json":
        "TASK11N-DISTINCT-REAL-CODE-INTERACTIVE-PILOT",
}
PILOT_MANIFEST = "docs/work/task11j-ws-doc-writer-real-repository-pilot-v1.json"
EXACT_PILOT_SURFACES = {
    "tests/test_task11j_real_repository_pilot.py",
    "tools/calibrate_task11j_validation.py",
    "validation-assets/task11j-ws-doc-writer-src-readme-hidden-v1.py",
    "validation-assets/task11j-ws-doc-writer-src-readme-visible-v1.py",
    "tests/test_task11n_real_code_pilot.py",
    "tools/calibrate_task11n_validation.py",
    "validation-assets/task11n-ws-doc-writer-writing-setup-hidden-v1.py",
    "validation-assets/task11n-ws-doc-writer-writing-setup-visible-v1.py",
}
MARKERS = ("doc" + "writer", "/srv/ws-" + "doc" + "writer")
ACTIVE_MARKERS = MARKERS + ("ws-" + "doc" + "-writer",)
ACTIVE_AUTHORITY_KEYS = {
    "runtime",
    "backend",
    "model",
    "executor",
    "worker",
    "provider",
    "package",
    "implementation",
    "runtime_backend",
    "model_provider",
    "executor_dependency",
    "production_worker_authority",
    "active_package_import",
    "inherited_application_implementation",
}


def publication_paths(root: Path) -> tuple[str, ...]:
    """Return the tracked plus not-ignored publication candidate tree."""

    output = subprocess.check_output(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"]
    )
    return tuple(sorted({item.decode() for item in output.split(b"\0") if item}))


def _contains_marker(value: Any) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return any(marker in lowered for marker in MARKERS)
    if isinstance(value, dict):
        return any(_contains_marker(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_marker(item) for item in value)
    return False


def _contains_active_marker(value: Any) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return any(marker in lowered for marker in ACTIVE_MARKERS)
    if isinstance(value, dict):
        return any(_contains_active_marker(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_active_marker(item) for item in value)
    return False


def _python_inherits_active_identity(content: str) -> bool:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names]
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
            if any(_contains_active_marker(name) for name in names):
                return True
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = {target.id.lower() for target in targets if isinstance(target, ast.Name)}
            if names & ACTIVE_AUTHORITY_KEYS:
                value = node.value
                if isinstance(value, ast.Constant) and _contains_active_marker(value.value):
                    return True
    return False


def _pilot_manifest_is_external_target_record(content: str, checkpoint: str) -> bool:
    try:
        record = json.loads(content)
        source = record["source_binding"]
        pilot = record["pilot_manifest"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return False
    if (
        record.get("schema_version") != 1
        or record.get("checkpoint") != checkpoint
        or source.get("canonical_path") != "/home/louis/src/ws-doc-writer"
        or source.get("origin") != "git@github.com:lhpoulin-cmyk/ws-doc-writer.git"
        or pilot.get("authority", {}).get("owning_domain") != "ws-doc-writer application authority"
    ):
        return False
    active_values = {
        key: value
        for key, value in record.get("model_binding", {}).items()
        if key in ACTIVE_AUTHORITY_KEYS
    }
    active_values.update({key: pilot[key] for key in ACTIVE_AUTHORITY_KEYS if key in pilot})
    return not _contains_active_marker(active_values)


def hygiene_violations(root: Path, relative: str) -> tuple[str, ...]:
    path = root / relative
    if not path.is_file():
        return ()
    if relative.startswith("lineage/") or relative in HISTORICAL_RECORDS:
        return ()
    content = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".py" and _python_inherits_active_identity(content):
        return (relative,)
    lowered = content.lower()
    if not any(marker in lowered for marker in MARKERS):
        return ()
    if relative in PILOT_MANIFESTS and _pilot_manifest_is_external_target_record(
        content, PILOT_MANIFESTS[relative]
    ):
        return ()
    if relative in EXACT_PILOT_SURFACES:
        return ()
    return (relative,)


def publication_tree_violations(root: Path) -> tuple[str, ...]:
    return tuple(
        violation
        for relative in publication_paths(root)
        for violation in hygiene_violations(root, relative)
    )
