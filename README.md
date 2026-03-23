# effector-bench

Benchmark suite for the effector toolchain — **200 test cases** across 5 verification categories.

This repo is designed to run **deterministically** (no API keys) and produces JSON results under `results/`.

## What it measures

### Tier A — Toolchain Accuracy (Deterministic)
- Type resolution compatibility
- Effector manifest validation
- Pipeline composition safety
- Security detection
- Cross-runtime compilation correctness

See [`METHODOLOGY.md`](./METHODOLOGY.md) for the full breakdown.

### Tier B — Schema Quality Comparison
Measures whether compiling `effector.toml` → `mcp` produces a higher-quality schema than baseline hand-written JSON Schema.

## Quick start

```bash
cd effector-bench
npm install
npm run bench:verbose
```

Run one category:

```bash
npm run bench:verbose -- --category type-resolution
```

## Output

- `results/latest.json` — last run summary

## License

MIT

