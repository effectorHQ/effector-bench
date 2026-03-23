# Benchmark Methodology

Detailed methodology for the two-tier effector benchmark suite.

---

## Tier A — Toolchain Accuracy

### What It Measures

Does effector's toolchain (type checker, validator, compositor, security scanner, compiler) produce correct results on adversarial inputs?

### Experimental Setup

- **179 test cases** across 5 categories
- Each case has an `expected` outcome (pass/fail/compatible/incompatible)
- Adversarial cases deliberately target known toolchain limitations
- All gaps annotated with `"note": "KNOWN GAP: ..."` in corpus files
- **Deterministic**: no randomness, no API calls, no LLM

### Categories

| Category | Cases | Score | Measures |
|---|---|---|---|
| Type Resolution | 57 | 87.7% | 6-tier type compatibility engine |
| Manifest Validation | 29 | 89.7% | Schema validation accept/reject correctness |
| Composition Safety | 30 | 100% | Pipeline type checking across tool chains |
| Security Detection | 43 | 81.4% | 5 security rules: injection, exfil, creep, obfuscation, mismatch |
| Compilation | 20 | 100% | Cross-runtime output: MCP, OpenAI Agents, LangChain, JSON |
| **Overall** | **179** | **89.9%** | **161 passed, 18 known gaps, 2.9ms** |

### Type Resolution Breakdown (57 cases)

| Tier | Cases | Description |
|---|---|---|
| Exact match | 10 | `CodeDiff` = `CodeDiff` |
| Alias match | 10 | `Diff` → `CodeDiff` (catalog alias) |
| Subtype match | 7 | `SecurityReport` ⊂ `ReviewReport` (+ reverse-subtype failures) |
| Wildcard match | 9 | `Code*` matches `CodeDiff`, `CodeSnippet` (+ 3 false positive tests) |
| Structural match | 8 | Field overlap checking (+ 3 value-type blindness tests) |
| Null safety | 3 | Null/undefined compatibility gaps |
| Mixed type | 2 | Cross-tier edge cases |
| Incompatible | 8 | Correctly rejected incompatible pairs |

### Security Detection Breakdown (43 cases)

| Rule | Positives | Negatives | False Negatives | False Positives |
|---|---|---|---|---|
| Prompt injection | 5 | 4 | 4 (leetspeak, spacing) | — |
| Data exfiltration | 4 | 2 | 3 (WebSocket, sendBeacon, pixel) | — |
| Permission creep | 4 | 3 | — | 3 (code comments) |
| Obfuscation | 3 | 2 | — | — |
| Permission-interface mismatch | 3 | 3 | — | — |

Security F1 score: **0.84**

### Known Limitations

| Component | Gap | Impact |
|---|---|---|
| Type checker | Wildcard uses naive substring match | `BarCode` matches `Code*` (false positive) |
| Type checker | Structural subtyping ignores value types | `{name: String}` ≈ `{name: Integer}` |
| Type checker | Null/undefined treated as compatible | Silent type holes |
| Validator | No unknown-field rejection | Typos like `interafce` pass silently |
| Validator | No interface type checking against catalog | Invalid types accepted |
| Security | Regex-based detection | Misses leetspeak, WebSocket exfil |
| Security | No context-aware analysis | False positives on code comments |

---

## Tier B — Schema Quality Comparison

### What It Measures

Does compiling an `effector.toml` manifest to MCP produce a higher-quality schema than hand-written baseline MCP JSON Schema?

### Experimental Design

**Controlled variable experiment:**
- **Control**: 10 raw MCP JSON Schema tool descriptions (baseline)
- **Treatment**: Same 10 tools with effector.toml manifests compiled via `compile(def, 'mcp')`
- **N = 10 tools x 5 dimensions = 50 measurements per condition**

### Tool Corpus

10 tools spanning 8 categories, chosen for diversity:

| Tool | Category | Interface (effector) |
|---|---|---|
| file-search | filesystem | FilePath → JSON |
| code-review | code-analysis | CodeDiff → ReviewReport |
| slack-notify | communication | ReviewReport → SlackMessage |
| web-scraper | web | URL → StructuredData |
| db-query | database | String → DataTable |
| git-commit | version-control | PatchSet → CommitRef |
| security-scan | security | CodeSnippet → SecurityReport |
| deploy-service | infrastructure | PatchSet → DeploymentStatus |
| translate-text | nlp | TextDocument → TranslatedText |
| summarize-doc | nlp | TextDocument → Summary |

### Evaluation Dimensions

Each dimension is grounded in findings from established academic benchmarks. We separate **Comparable** dimensions (both formats can express) from **Differential** dimensions (only effector can express) to avoid conflating fair comparisons with structural advantages.

#### D1: Function Selection Signal (Comparable)

- **Grounded in**: BFCL (Gorilla Project, UC Berkeley)
- **Finding**: Ambiguous tool descriptions cause 10-30% function misselection in LLMs
- **Measures**: Description disambiguation quality — word count, domain terms, action verbs, output specification

#### D2: Parameter Extraction Signal (Comparable)

- **Grounded in**: BFCL + API-Bank (Li et al., ACL 2023)
- **Finding**: Underspecified parameter types cause 15-25% extraction errors
- **Measures**: Required field declarations, type annotations beyond `string`, enum usage, parameter descriptions

#### D3: Multi-Step Composition Safety (Differential)

- **Grounded in**: τ-bench (Yao et al., 2024) + MCP-Bench
- **Finding**: Type errors cascade across multi-turn tool sequences; composition fails at boundaries
- **Measures**: Typed I/O interface coverage, static composability verification, context declarations
- **Note**: Structurally near-zero for baseline (MCP spec has no typed interface model)

#### D4: Safety & Permission Coverage (Differential)

- **Grounded in**: ToolSword (Ye et al., 2024) + SafeToolBench (Guo et al., 2024)
- **Finding**: Tools without permission models enable 6 attack categories (harmful queries, risky args, etc.)
- **Measures**: Explicit permission declarations (network, filesystem, subprocess, envRead)
- **Note**: Structurally zero for baseline (MCP spec has no permission model)

#### D5: Schema Completeness (Comparable)

- **Grounded in**: MCPToolBench++ + Nexus (Srinivasan et al., 2023)
- **Finding**: Schema completeness correlates with invocation accuracy
- **Measures**: Total structured information bits — fields, types, constraints, metadata, interface info

### Results

#### Comparable Dimensions (fair head-to-head)

| Dimension | Baseline (μ ± σ) | Effector (μ ± σ) | Δ |
|---|---|---|---|
| D1 Function Selection | 10 ± 3.6 | 38 ± 7.4 | **+28** |
| D2 Parameter Extraction | 37 ± 12.6 | 23 ± 24.3 | **-14** |
| D5 Schema Completeness | 29 ± 4.4 | 66 ± 13.5 | **+37** |
| **Comparable Average** | **25 ± 5.8** | **43 ± 11.7** | **+18** |

#### Differential Dimensions (capabilities effector adds)

| Dimension | Baseline (μ ± σ) | Effector (μ ± σ) | Δ |
|---|---|---|---|
| D3 Composition Safety | 13 ± 2.9 | 88 ± 5.1 | **+75** |
| D4 Safety & Permissions | 0 ± 0 | 53 ± 18.6 | **+53** |
| **Differential Average** | **7 ± 1.7** | **71 ± 11.4** | **+64** |

#### Combined

| | Baseline | Effector | Δ |
|---|---|---|---|
| **Combined Overall** | **18 ± 3.5** | **54 ± 9.0** | **+36** |

### Regression Analysis

**6/10 tools** show D2 (Parameter Extraction) regression:

| Tool | Baseline | Effector | Δ |
|---|---|---|---|
| file-search | 56 | 3 | -53 |
| code-review | 25 | 3 | -22 |
| web-scraper | 25 | 3 | -22 |
| git-commit | 55 | 3 | -52 |
| security-scan | 25 | 3 | -22 |
| summarize-doc | 55 | 3 | -52 |

**Root cause**: `compile()` generates `inputSchema.properties` only for `envRead` environment variables. Interface types are stored in `_interface` metadata but not expanded to JSON Schema parameter definitions. Tools without `envRead` produce nearly-empty parameter schemas.

**Impact**: D2 score drops from μ=37 (baseline) to μ=23 (effector). High variance (σ=24.3) reflects the bimodal distribution — tools with envRead score well, tools without score near zero.

**Recommendation**: Expand the compiler to derive parameter schemas from type catalog entries. This would eliminate the regression and add an estimated +20-30 to the comparable average.

### Composition Chain Verification

8 chains tested, 8/8 correct:

| Chain | Expected | Actual | Mechanism |
|---|---|---|---|
| code-review → slack-notify | Compatible | Compatible | ReviewReport exact-match |
| security-scan → slack-notify | Compatible | Compatible | SecurityReport ⊂ ReviewReport (subtype) |
| code-review → summarize-doc | Incompatible | Incompatible | ReviewReport ≠ TextDocument |
| file-search → deploy-service | Incompatible | Incompatible | JSON ≠ PatchSet |
| db-query → summarize-doc | Incompatible | Incompatible | DataTable ≠ TextDocument |
| web-scraper → translate-text | Incompatible | Incompatible | StructuredData ≠ TextDocument |
| translate-text → deploy-service | Incompatible | Incompatible | TranslatedText ≠ PatchSet |
| git-commit → web-scraper | Incompatible | Incompatible | CommitRef ≠ URL |

Baseline tools score 0/8 — MCP spec has no typed interface model for static composition verification.

---

## Reproducing

```bash
cd effector-bench
npm install

# Run both tiers
npm run bench:all:verbose

# Or individually
npm run bench:verbose                          # Tier A
npm run bench:tier-b:verbose                   # Tier B
npm run bench:verbose -- --category security   # Single Tier A category
```

Both tiers are deterministic, require no API keys, and complete in <10ms combined.

---

## References

1. **BFCL** — Berkeley Function Calling Leaderboard. Gorilla Project, UC Berkeley. gorilla.cs.berkeley.edu/leaderboard.html
2. **API-Bank** — Li et al., "API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs." ACL 2023.
3. **τ-bench** — Yao et al., "τ-bench: A Benchmark for Tool-Agent-User Interaction." 2024.
4. **MCP-Bench** — github.com/modelcontextprotocol/mcp-bench
5. **ToolSword** — Ye et al., "ToolSword: Unveiling Safety Issues of LLMs in Tool Learning." 2024.
6. **SafeToolBench** — Guo et al., "SafeToolBench: Evaluating Safety of Tool-Augmented LLMs." 2024.
7. **MCPToolBench++** — arxiv.org/abs/2508.07575
8. **MCP-AgentBench** — arxiv.org/abs/2509.09734
9. **Nexus** — Srinivasan et al., "NexusRaven: Function Calling Benchmark." 2023.
10. **ToolBench** — Qin et al., "ToolBench: Tool Learning Benchmark." 2023.
11. **Seal-Tools** — Self-Instruct Tool Learning Evaluation. 2024.
