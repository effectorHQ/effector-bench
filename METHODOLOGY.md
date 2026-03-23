# effector Benchmark Methodology

## Overview

Two-tier benchmark system measuring effector toolchain correctness and schema quality improvement.

## Tier A — Toolchain Accuracy (Internal, Deterministic)

**What it measures**: Does effector's toolchain (type checker, validator, composer, security scanner, compiler) produce correct results?

**Methodology**: 179 test cases across 5 categories, each with expected outcomes including adversarial edge cases that expose known toolchain limitations.

| Category | Cases | Score | What It Tests |
|---|---|---|---|
| Type Resolution | 57 | 87.7% | 6-tier type compatibility (exact, alias, subtype, wildcard, structural, incompatible) |
| Manifest Validation | 29 | 89.7% | Schema accept/reject with edge cases |
| Composition Safety | 30 | 100% | Pipeline type checking across tool chains |
| Security Detection | 43 | 81.4% | Prompt injection, data exfil, permission creep, obfuscation detection |
| Compilation | 20 | 100% | Cross-runtime output correctness (MCP, OpenAI, LangChain, JSON) |

**Overall: 89.9% (161/179 cases, 3.2ms)**

### Known Limitations (Why Not 100%)

- **Type checker**: Wildcard matching uses naive prefix check — `BarCode` matches `Code*` incorrectly. Structural subtyping ignores value types. Null/undefined treated as compatible.
- **Validator**: Does not reject unknown top-level fields. Does not check interface type names against catalog.
- **Security scanner**: Regex-based — misses leetspeak evasion, WebSocket/sendBeacon exfiltration, produces false positives on code comments.

All known gaps are annotated in corpus files with `"note": "KNOWN GAP: ..."`.

---

## Tier B — Schema Quality Comparison (Controlled Variable)

**What it measures**: Does compiling an effector.toml manifest to MCP produce a higher-quality schema than hand-written MCP JSON Schema?

**Experimental design**: Same 10 MCP tools, two representations:
- **Control**: Raw MCP JSON Schema (baseline)
- **Treatment**: effector.toml manifest compiled via `compile(def, 'mcp')`

### Metric Classes

We separate metrics into two classes to avoid conflating fair comparisons with structural advantages:

**Comparable Metrics (M1-M3)** — Both formats CAN express these:
| Metric | Baseline μ±σ | Effector μ±σ | Δ |
|---|---|---|---|
| M1: Description Specificity | 9 ± 3.6 | 34 ± 7.4 | +25 |
| M2: Parameter Constraints | 41 ± 11.5 | 37 ± 38.6 | **-4** |
| M3: Schema Info Density | 36 ± 5.3 | 80 ± 9.5 | +44 |
| **Comparable Overall** | **29 ± 5** | **50 ± 16.2** | **+21** |

**Differential Metrics (M4-M6)** — Capabilities only effector adds:
| Metric | Baseline μ±σ | Effector μ±σ | Δ |
|---|---|---|---|
| M4: Interface Type Coverage | 22 ± 5 | 75 ± 9.5 | +53 |
| M5: Permission Explicitness | 0 ± 0 | 47 ± 17.1 | +47 |
| M6: Composition Readiness | 0 ± 0 | 97 ± 6 | +97 |
| **Differential Overall** | **7 ± 1.6** | **73 ± 9.6** | **+66** |

**Combined Overall: 18 → 62 (Δ+44)**

### Regression Analysis

6 of 10 tools show **parameter constraint regression** (effector scores lower). Root cause: `compile()` generates `inputSchema.properties` only for `envRead` environment variables. Tools without `envRead` produce empty parameter schemas, losing the hand-written parameter definitions the baseline has.

This is a real compiler limitation, not a measurement artifact. The fix is to expand type catalog entries into JSON Schema properties during compilation.

### Composition Chain Verification

8/8 chains verified correct. Tests both valid compositions (subtype matching) and correctly-rejected incompatible chains:

| Chain | Expected | Result |
|---|---|---|
| code-review → slack-notify | Compatible (exact) | ✓ |
| security-scan → slack-notify | Compatible (subtype) | ✓ |
| code-review → summarize-doc | Incompatible | ✓ |
| file-search → deploy-service | Incompatible | ✓ |
| db-query → summarize-doc | Incompatible | ✓ |
| web-scraper → translate-text | Incompatible | ✓ |
| translate-text → deploy-service | Incompatible | ✓ |
| git-commit → web-scraper | Incompatible | ✓ |

Baseline tools cannot participate — no typed interfaces for static verification.

---

## References

- **BFCL** (Berkeley Function Calling Leaderboard) — AST-match evaluation for function calling accuracy. gorilla.cs.berkeley.edu/leaderboard.html
- **MCPToolBench++** — MCP tool invocation accuracy benchmark. arxiv.org/abs/2508.07575
- **MCP-AgentBench** — Real-world MCP task completion benchmark. arxiv.org/abs/2509.09734

## Reproducing

```bash
cd effector-bench

# Tier A: Toolchain accuracy
node benchmark.js --verbose

# Tier B: Schema quality comparison
node tier-b/benchmark.js --verbose
```

Both benchmarks are deterministic, require no API keys, and complete in <10ms combined.
