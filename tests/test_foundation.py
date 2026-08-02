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
