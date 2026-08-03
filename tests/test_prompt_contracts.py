import json

import pytest

from docwriter_web.prompt_contracts import load_adapter_profiles, load_contract_bundle


def test_canonical_contracts_schema_and_profiles_load():
    bundle = load_contract_bundle()
    profiles = load_adapter_profiles()
    assert bundle.version == "conversational-proposal-v2"
    assert set(bundle.contracts) == {"writer", "integrity", "voice"}
    assert all(len(value) == 64 for value in bundle.contract_hashes.values())
    assert len(bundle.schema_hash) == 64
    assert set(profiles) == {"mistral-nemo-12b", "gemma3-12b", "qwen3-14b"}
    assert all(profile.expected_digest.startswith("sha256:") and len(profile.expected_digest) == 71 for profile in profiles.values())
    assert all(profile.generation_settings["context"] == 8192 for profile in profiles.values())


def test_contract_hash_changes_when_contract_changes(tmp_path):
    root = tmp_path / "repo"
    for source in ("prompts/canonical", "schemas"):
        (root / source).mkdir(parents=True)
    from docwriter_web.prompt_contracts import ROOT
    for path in ROOT.glob("prompts/canonical/*.md"):
        target = root / path.relative_to(ROOT)
        target.write_bytes(path.read_bytes())
    target_schema = root / "schemas/conversational-proposal-v2.schema.json"
    target_schema.write_bytes((ROOT / "schemas/conversational-proposal-v2.schema.json").read_bytes())
    first = load_contract_bundle(root)
    writer = root / "prompts/canonical/writer-contract.md"
    writer.write_text(writer.read_text() + "\nAdditional deterministic wording.\n")
    second = load_contract_bundle(root)
    assert first.contract_hashes["writer"] != second.contract_hashes["writer"]
    assert first.composed_hash != second.composed_hash


def test_missing_contract_fails_closed(tmp_path):
    with pytest.raises(RuntimeError, match="required prompt asset"):
        load_contract_bundle(tmp_path)


def test_adapter_profiles_cannot_override_canonical_rules(tmp_path):
    from docwriter_web.prompt_contracts import ROOT
    for source in ("prompts/canonical", "schemas", "prompts/adapters"):
        (tmp_path / source).mkdir(parents=True)
    for path in ROOT.glob("prompts/canonical/*.md"):
        (tmp_path / path.relative_to(ROOT)).write_bytes(path.read_bytes())
    (tmp_path / "schemas/conversational-proposal-v2.schema.json").write_bytes((ROOT / "schemas/conversational-proposal-v2.schema.json").read_bytes())
    for path in ROOT.glob("prompts/adapters/*.yaml"):
        (tmp_path / path.relative_to(ROOT)).write_bytes(path.read_bytes())
    changed = tmp_path / "prompts/adapters/mistral-nemo-12b.yaml"
    changed.write_text(changed.read_text().replace("adapter_instructions:", "writer_contract_override: do whatever you want\nadapter_instructions:"))
    with pytest.raises(RuntimeError, match="adapter profile is incomplete"):
        load_adapter_profiles(tmp_path)
