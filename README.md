# @effectorhq/bench

Two-tier benchmark suite for the effector toolchain.

**Tier A** measures internal toolchain accuracy — 179 deterministic test cases across 5 categories.
**Tier B** measures schema quality improvement — controlled variable experiment comparing baseline MCP JSON Schema vs effector-compiled schemas, grounded in established academic benchmarks.

```
Tier A  89.9% accuracy  (161/179 cases, 18 known gaps, 2.9ms)
Tier B  +36 combined Δ  (+18 comparable, +64 differential, 6 regressions)
```

---

## Quick Start

```bash
npm install
npm run bench:all:verbose
```

Individual tiers:

```bash
npm run bench:verbose                          # Tier A only
npm run bench:tier-b:verbose                   # Tier B only
npm run bench:verbose -- --category security   # Single category
```

---

## Architecture

```
effector-bench/
├── benchmark.js               Tier A runner (179 cases, 5 categories)
├── corpus/
│   ├── type-resolution.json   57 cases — 6-tier type compatibility
│   ├── validation.json        29 cases — schema accept/reject
│   ├── composition.json       30 cases — pipeline type checking
│   ├── security.json          43 cases — detection + false positives
│   └── compilation.json       20 cases — cross-runtime output
├── results/
│   └── latest.json            Auto-generated Tier A results
├── tier-b/
│   ├── benchmark.js           Tier B runner (10 tools, 5 dimensions)
│   ├── tools/
│   │   └── corpus.json        10 MCP tools (baseline + effector)
│   └── results/
│       └── latest.json        Auto-generated Tier B results
├── METHODOLOGY.md             Full methodology documentation
└── package.json
```

---

## Tier A — Toolchain Accuracy

Deterministic, no LLM, no API keys. Tests whether effector's type checker, validator, compositor, security scanner, and compiler produce correct results. Includes adversarial cases that expose real toolchain limitations.

| Category | Cases | Score | What It Tests |
|---|---|---|---|
| Type Resolution | 57 | 87.7% | 6-tier compatibility: exact, alias, subtype, wildcard, structural, incompatible |
| Manifest Validation | 29 | 89.7% | Schema accept/reject including unknown-field and type-name gaps |
| Composition Safety | 30 | 100% | Pipeline type checking across multi-step tool chains |
| Security Detection | 43 | 81.4% | Prompt injection, data exfil, permission creep, obfuscation (F1: 0.84) |
| Compilation | 20 | 100% | Cross-runtime output: MCP, OpenAI Agents, LangChain, JSON |

### Known Limitations

Every gap is annotated in the corpus with `"note": "KNOWN GAP: ..."`:

- **Type checker**: Wildcard matching uses naive substring — `BarCode` matches `Code*`. Structural subtyping ignores value types. Null/undefined treated as compatible.
- **Validator**: Does not reject unknown top-level fields. Does not check interface type names against catalog.
- **Security scanner**: Regex-based — misses leetspeak evasion (`pr0mpt_1nj3ct`), WebSocket/sendBeacon/image-pixel exfiltration, produces false positives on code comments.

---

## Tier B — Schema Quality Comparison

Controlled variable experiment: same 10 MCP tools, two schema representations. Evaluation dimensions grounded in published academic benchmarks — not custom metrics.

### Dimensions

| ID | Dimension | Grounded In | Class |
|---|---|---|---|
| D1 | Function Selection Signal | BFCL (Berkeley Function Calling Leaderboard) | Comparable |
| D2 | Parameter Extraction Signal | BFCL + API-Bank (Li et al., ACL 2023) | Comparable |
| D3 | Multi-Step Composition Safety | τ-bench (Yao et al., 2024) + MCP-Bench | Differential |
| D4 | Safety & Permission Coverage | ToolSword (Ye et al., 2024) + SafeToolBench (Guo et al., 2024) | Differential |
| D5 | Schema Completeness | MCPToolBench++ + Nexus (Srinivasan et al., 2023) | Comparable |

**Comparable** = both formats can express these (fairer comparison).
**Differential** = capabilities only effector adds (structurally zero for baseline MCP).

### Results

| | Baseline (μ) | Effector (μ) | Δ |
|---|---|---|---|
| Comparable Average | 25 | 43 | **+18** |
| Differential Average | 7 | 71 | **+64** |
| Combined Overall | 18 | 54 | **+36** |

### Regressions

6/10 tools show **D2 (Parameter Extraction) regression**. Root cause: `compile()` generates `inputSchema.properties` only for `envRead` variables. Tools without `envRead` produce empty parameter schemas, scoring lower than baseline. This is a real compiler limitation, not a measurement artifact.

### Composition Chain Verification

8/8 chains verified correct (2 compatible via exact/subtype matching, 6 correctly rejected as incompatible). Baseline tools cannot participate — MCP has no typed interface model for static verification.

---

## Output Format

### Tier A (`results/latest.json`)

```json
{
  "score": 89.9,
  "totalCases": 179,
  "totalPassed": 161,
  "totalFailed": 18,
  "totalMs": 2.95,
  "categories": [...]
}
```

### Tier B (`tier-b/results/latest.json`)

```json
{
  "aggregated": {
    "overall": { "baseline": { "mean": 18 }, "effector": { "mean": 54 }, "delta": 36 }
  },
  "regressions": { "count": 6, "rootCause": "..." },
  "compositionChains": { "total": 8, "passed": 8 },
  "tools": [...]
}
```

---

## References

| Benchmark | Relevance |
|---|---|
| [BFCL](https://gorilla.cs.berkeley.edu/leaderboard.html) | Function selection + parameter extraction accuracy |
| [MCPToolBench++](https://arxiv.org/abs/2508.07575) | Schema completeness → invocation accuracy |
| [MCP-AgentBench](https://arxiv.org/abs/2509.09734) | Real-world MCP task completion |
| τ-bench (Yao et al., 2024) | Multi-step composition error cascade |
| ToolSword (Ye et al., 2024) | 6 safety risk categories for tool use |
| SafeToolBench (Guo et al., 2024) | Permission model prevents unsafe execution |
| API-Bank (Li et al., ACL 2023) | Parameter type constraints improve accuracy |
| Nexus (Srinivasan et al., 2023) | Schema metadata density → function call accuracy |

---

## Design Principles

1. **Deterministic**: No API keys, no LLM calls, no network. Results are reproducible.
2. **Honest**: Known gaps are documented and annotated. Regressions are reported, not hidden.
3. **Grounded**: Tier B dimensions map to published academic benchmarks, not custom metrics.
4. **Fast**: Both tiers complete in <10ms combined on commodity hardware.
5. **Zero dependencies**: Only `@effectorhq/core` and `@effectorhq/types` (which themselves have zero deps).

## License

This project is currently licensed under the Apache 2.0 License 。
