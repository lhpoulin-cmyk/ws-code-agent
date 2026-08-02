# Frozen benchmark execution

The authoritative benchmark revision is `ws-doc-writer-frozen-10/v1`. Its ten
fixtures are under `benchmarks/fixtures/`, with hashes recorded in
`benchmarks/fixture-manifest.yaml`. The runner is
`tools/benchmark_runner.py`.

Before execution, commit the benchmark implementation and ensure the worktree
is clean. Run the non-model dry run:

```text
python3 tools/benchmark_runner.py --dry-run
```

The live runner validates the XFS runtime, project `1002`, 20 GiB benchmark
quota, loopback Ollama API, exact model digests, frozen hashes, and 100% GPU
residency. It executes models sequentially at context `8192` with temperature
`0.2`, top-p `0.9`, seed `42`, streaming disabled, and thinking disabled.

Raw responses and protected model mapping go under
`/srv/ws-doc-writer/benchmarks/runs/<benchmark-id>/`. The anonymous review
bundle goes under `blinded/<benchmark-id>/`. The runner never selects a winner
and never marks generated prose accepted.
