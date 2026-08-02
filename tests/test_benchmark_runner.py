from pathlib import Path
import sys

import yaml

sys.path.insert(0, str(Path(__file__).parents[1]))

from tools.benchmark_runner import CASE_IDS, MODELS, RUNNER_VERSION, SETTINGS, planned_pairs

ROOT = Path(__file__).parents[1]


def test_exactly_ten_frozen_fixtures_and_ids():
    manifest = yaml.safe_load((ROOT / "benchmarks/fixture-manifest.yaml").read_text())
    assert [x["case_id"] for x in manifest["fixtures"]] == CASE_IDS
    assert len(manifest["fixtures"]) == 10
    for item in manifest["fixtures"]:
        fixture = yaml.safe_load((ROOT / item["path"]).read_text())
        assert fixture["case_id"] == item["case_id"]
        assert fixture["source_repository"]
        assert fixture["source_commit"]
        assert fixture["payload"]
        assert fixture["required_facts"]
        assert fixture["forbidden_inventions"]


def test_runner_contract_and_hashes():
    manifest = yaml.safe_load((ROOT / "benchmarks/fixture-manifest.yaml").read_text())
    assert manifest["runner_version"] == RUNNER_VERSION
    assert len(manifest["runner_sha256"]) == 64
    assert len(manifest["cases_manifest_sha256"]) == 64
    assert all(len(value) == 64 for value in manifest["contract_hashes"].values())


def test_exact_models_and_common_settings():
    assert [model for model, _, _ in MODELS] == [
        "qwen3:14b-q4_K_M", "gemma3:12b-it-q4_K_M", "mistral-nemo:12b-instruct-2407-q4_K_M"
    ]
    assert SETTINGS == {"num_ctx": 8192, "temperature": 0.2, "top_p": 0.9, "seed": 42}


def test_execution_is_sequential_and_complete():
    pairs = planned_pairs()
    assert len(pairs) == 30
    assert pairs[:10] == [(MODELS[0][0], case_id) for case_id in CASE_IDS]
    assert pairs[10:20] == [(MODELS[1][0], case_id) for case_id in CASE_IDS]
    assert pairs[20:] == [(MODELS[2][0], case_id) for case_id in CASE_IDS]


def test_thinking_and_blinding_contract():
    assert "think" not in SETTINGS
    blind_ids = [blind for _, _, blind in MODELS]
    model_names = [model for model, _, _ in MODELS]
    assert all(blind not in model_names for blind in blind_ids)
    assert len(set(blind_ids)) == 3
