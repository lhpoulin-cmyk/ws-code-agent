from pathlib import Path
import yaml

ROOT = Path(__file__).parents[1]


def test_exact_candidates():
    data = yaml.safe_load((ROOT / "manifests/models.yaml").read_text())
    assert [x["tag"] for x in data["candidates"]] == [
        "qwen3:14b-q4_K_M",
        "gemma3:12b-it-q4_K_M",
        "mistral-nemo:12b-instruct-2407-q4_K_M",
    ]


def test_benchmark_cases_have_safety_fields():
    data = yaml.safe_load((ROOT / "benchmarks/cases.yaml").read_text())
    assert len(data["cases"]) == 10
    for case in data["cases"]:
        for field in ("required_facts", "forbidden_inventions", "authority_boundaries", "exact_terminology"):
            assert case[field]


def test_acceptance_requires_validation_and_operator():
    lifecycle = (ROOT / "docs/lifecycle.md").read_text()
    assert "validation evidence" in lifecycle
    assert "operator acceptance" in lifecycle


def test_peer_boundary_and_no_forbidden_identities():
    text = "\n".join(
        p.read_text()
        for p in ROOT.rglob("*")
        if p.is_file()
        and ".git" not in p.parts
        and "tests" not in p.parts
        and p.suffix in {".md", ".yaml", ".py"}
    )
    assert "ws-cp" in text and "gpu-cp" in text
    assert "domain disagreement" in text.lower()
    assert "hv-matriarch" not in text
    assert "cpu-cp" not in text
    assert "Intel" in text and "Arc Vulkan" in text
    assert "conflict" in text


def test_no_live_acceptance_claim():
    text = (ROOT / "README.md").read_text() + (ROOT / "manifests/models.yaml").read_text()
    assert "No model has been pulled" in text
    assert "proposed-not-pulled" in text


def test_storage_and_soak_contract():
    storage = yaml.safe_load((ROOT / "manifests/storage-requirement.yaml").read_text())
    assert storage["allocation"]["size_gb"] == 128
    assert storage["allocation"]["source"] == "unpartitioned-gap-only"
    assert storage["allocation"]["remaining_gap"] == "unassigned"
    assert "nvme0n1p6-free-space" in storage["exclusions"]
    assert storage["filesystem"]["type"] == "xfs"
    assert storage["filesystem"]["project_quotas"] == "required"
    assert storage["quota_policy"]["automatic_growth"] is False
    quota_total = sum(v["quota_gib"] for v in storage["directories"].values() if "quota_gib" in v)
    assert quota_total == 112
    assert quota_total < storage["allocation"]["size_gb"]
    soak = yaml.safe_load((ROOT / "benchmarks/daily-soak-record.template.yaml").read_text())
    assert soak["day"] == "required-1-through-14"
    encryption = (ROOT / "docs/evidence-encryption.md").read_text()
    assert "SOPS" in encryption and "age" in encryption
    reproducibility = yaml.safe_load((ROOT / "schemas/reproducibility.yaml").read_text())
    assert reproducibility["rules"]["model_blobs"]
    encrypted = (ROOT / "docs/encrypted-storage.md").read_text()
    assert "LUKS2" in encrypted and "ws-doc-writer" in encrypted
    assert "shared passphrase" in encrypted
    assert "must never fall back" in encrypted
    assert "allocation-pattern" in encrypted
