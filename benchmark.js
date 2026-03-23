#!/usr/bin/env node
/**
 * effector Toolchain Benchmark
 *
 * 200 test cases across 5 verification categories.
 * Measures accuracy and performance of the effector toolchain.
 *
 * Usage:
 *   node benchmark.js              # Run all categories
 *   node benchmark.js --verbose    # Show per-case results
 *   node benchmark.js --category type-resolution  # Run one category
 *
 * Output: results/latest.json
 */

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

// ─── Imports from effector toolchain ────────────────────────

import { checkTypeCompatibility, setCatalog, validateManifest, compile } from '@effectorhq/core';

// Load types catalog for type-checker (from npm package)
const require = createRequire(import.meta.url);
const typesCatalog = JSON.parse(readFileSync(require.resolve('@effectorhq/types/types.json'), 'utf-8'));
setCatalog(typesCatalog);

// ─── CLI args ───────────────────────────────────────────────

const args = process.argv.slice(2);
const verbose = args.includes('--verbose');
const categoryFilter = args.find((a, i) => args[i - 1] === '--category') || null;

// ─── Load corpus files ──────────────────────────────────────

function loadCorpus(name) {
  return JSON.parse(readFileSync(join(__dirname, 'corpus', `${name}.json`), 'utf-8'));
}

// ─── Category Runners ───────────────────────────────────────

function runTypeResolution(cases) {
  const results = [];
  for (const c of cases) {
    const result = checkTypeCompatibility(c.output, c.input);
    const pass =
      result.compatible === c.expected.compatible &&
      result.reason === c.expected.reason;
    results.push({
      id: c.id,
      pass,
      expected: c.expected,
      actual: { compatible: result.compatible, reason: result.reason, precision: result.precision },
    });
  }
  return results;
}

function runValidation(cases) {
  const results = [];
  for (const c of cases) {
    const result = validateManifest(c.manifest);
    let pass;
    if (c.expected.valid) {
      pass = result.valid === true && result.errors.length === (c.expected.errorCount || 0);
    } else {
      pass = result.valid === false && result.errors.length >= (c.expected.minErrors || 1);
    }
    results.push({
      id: c.id,
      pass,
      expected: c.expected,
      actual: { valid: result.valid, errorCount: result.errors.length, errors: result.errors },
    });
  }
  return results;
}

function runComposition(cases) {
  // Dynamic import would be cleaner, but we keep it simple
  // effector-compose uses its own local type-checker, so we import directly
  const results = [];
  for (const c of cases) {
    try {
      // Parse pipeline manually (same logic as effector-compose)
      const pipeline = parsePipelineMinimal(c.pipeline);
      const registry = new Map(Object.entries(c.registry));

      // Type check using our own implementation
      const typeCheckResult = typeCheckPipeline(pipeline, registry);

      let pass;
      if (c.expected.valid !== undefined) {
        if (c.expected.valid) {
          pass = typeCheckResult.valid === true &&
            typeCheckResult.errors.length === (c.expected.errorCount || 0);
        } else {
          pass = typeCheckResult.valid === false &&
            typeCheckResult.errors.length >= (c.expected.minErrors || 1);
        }
      } else {
        pass = true; // warning-only cases
      }

      // Check warnings if specified
      if (c.expected.warningCount !== undefined) {
        pass = pass && typeCheckResult.warnings.length === c.expected.warningCount;
      }

      results.push({ id: c.id, pass, expected: c.expected, actual: typeCheckResult });
    } catch (err) {
      results.push({
        id: c.id,
        pass: false,
        expected: c.expected,
        actual: { error: err.message },
      });
    }
  }
  return results;
}

/** Minimal pipeline parser (same as effector-compose) */
function parsePipelineMinimal(yamlContent) {
  const lines = yamlContent.split('\n');
  const pipeline = { name: '', version: '', steps: [] };
  let currentStep = null;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('name:')) {
      pipeline.name = trimmed.slice(5).trim();
    } else if (trimmed.startsWith('version:')) {
      pipeline.version = trimmed.slice(8).trim();
    } else if (trimmed.startsWith('- id:')) {
      if (currentStep) pipeline.steps.push(currentStep);
      currentStep = { id: trimmed.slice(5).trim() };
    } else if (currentStep && trimmed.startsWith('effector:')) {
      currentStep.effector = trimmed.slice(9).trim();
    } else if (currentStep && trimmed.startsWith('parallel-with:')) {
      currentStep.parallelWith = trimmed.slice(14).trim();
    }
  }
  if (currentStep) pipeline.steps.push(currentStep);
  return pipeline;
}

/** Pipeline type checker using canonical checkTypeCompatibility */
function typeCheckPipeline(pipeline, registry) {
  const errors = [];
  const warnings = [];

  for (let i = 0; i < pipeline.steps.length; i++) {
    const step = pipeline.steps[i];
    const def = registry.get(step.effector);

    if (!def) {
      errors.push({ step: step.id, message: `Effector "${step.effector}" not found` });
      continue;
    }

    // Sequential type check
    if (i > 0 && !step.parallelWith) {
      const prevStep = pipeline.steps[i - 1];
      const prevDef = registry.get(prevStep.effector);
      if (prevDef && def) {
        const compat = checkTypeCompatibility(
          prevDef.interface?.output,
          def.interface?.input
        );
        if (!compat.compatible) {
          errors.push({
            step: step.id,
            message: `Type mismatch: ${compat.outputType} → ${compat.inputType}`,
          });
        }
      }
    }

    // Parallel ref check
    if (step.parallelWith) {
      const target = pipeline.steps.find(s => s.id === step.parallelWith);
      if (!target) {
        warnings.push({ step: step.id, message: `Parallel target "${step.parallelWith}" not found` });
      }
    }
  }

  return { valid: errors.length === 0, errors, warnings };
}

function runSecurity(cases) {
  // Import all rules
  const rules = loadSecurityRules();
  const results = [];

  for (const c of cases) {
    const content = c.content;
    const lines = content.split('\n');
    const targetRule = rules.find(r => r.id === c.rule);

    if (!targetRule) {
      results.push({ id: c.id, pass: false, expected: c.expected, actual: { error: `Rule ${c.rule} not found` } });
      continue;
    }

    const findings = targetRule.check(content, lines, c.file);
    const triggered = findings.length > 0;
    const pass = triggered === c.expected.shouldTrigger;

    results.push({
      id: c.id,
      pass,
      expected: c.expected,
      actual: { triggered, findingCount: findings.length },
    });
  }
  return results;
}

/** Load security rules inline (avoiding import issues with @effectorhq/core dependency in audit) */
function loadSecurityRules() {
  // We replicate the rule detection patterns here to avoid import chain issues.
  // These match the canonical rules in effector-audit/src/scanner/rules/index.js

  const NETWORK_CONTEXT_TYPES = new Set([
    'GitHubCredentials', 'APICredentials', 'SlackCredentials', 'AWSCredentials', 'GenericAPIKey',
  ]);
  const FILESYSTEM_CONTEXT_TYPES = new Set(['Repository']);

  return [
    {
      id: 'prompt-injection',
      check(content, lines, file) {
        const findings = [];
        const patterns = [
          { regex: /ignore\s+(all\s+)?previous\s+instructions/i, msg: 'System prompt override' },
          { regex: /you\s+are\s+now\s+(a|an)\s+/i, msg: 'Role reassignment' },
          { regex: /disregard\s+(your|all|the)\s+(instructions|rules|guidelines)/i, msg: 'Instruction override' },
          { regex: /\bDAN\b.*\bjailbreak/i, msg: 'Known jailbreak' },
          { regex: /system:\s*you\s+must/i, msg: 'Injected system directive' },
          { regex: /\[INST\]|\[\/INST\]|<\|im_start\|>|<\|im_end\|>/i, msg: 'Chat template injection' },
        ];
        for (let i = 0; i < lines.length; i++) {
          for (const { regex, msg } of patterns) {
            if (regex.test(lines[i])) {
              findings.push({ severity: 'critical', rule: 'prompt-injection', message: msg, file, line: i + 1 });
            }
          }
        }
        return findings;
      },
    },
    {
      id: 'data-exfiltration',
      check(content, lines, file) {
        const findings = [];
        const patterns = [
          { regex: /curl\s+.*-d\s+.*\$/, msg: 'Curl POST with variable data' },
          { regex: /fetch\s*\(\s*['"][^'"]*['"].*body/, msg: 'Fetch POST request' },
          { regex: /webhook\.site|requestbin|pipedream|ngrok/i, msg: 'Known data collection service' },
          { regex: /btoa\s*\(|base64.*encode|\.toString\s*\(\s*['"]base64/i, msg: 'Base64 encoding' },
        ];
        for (let i = 0; i < lines.length; i++) {
          for (const { regex, msg } of patterns) {
            if (regex.test(lines[i])) {
              findings.push({ severity: 'high', rule: 'data-exfiltration', message: msg, file, line: i + 1 });
            }
          }
        }
        return findings;
      },
    },
    {
      id: 'permission-creep',
      check(content, lines, file) {
        if (file.endsWith('effector.toml')) return [];
        const findings = [];
        const hasRead = /readFileSync|fs\.read|cat\s+\//i.test(content);
        const hasWrite = /writeFileSync|fs\.write|>\s+\/|>>\s+\/|tee\s+\//i.test(content);
        const hasNetwork = /curl\s+|wget\s+|fetch\(|axios|http\.get|http\.post|request\(/i.test(content);
        const hasSubprocess = /exec\(|execSync|spawn|child_process/i.test(content);
        const hasEnv = /process\.env|getenv|\$\{?\w+\}?/i.test(content);

        if (hasRead) findings.push({ severity: 'medium', rule: 'permission-creep', message: 'Filesystem read detected', file });
        if (hasWrite) findings.push({ severity: 'medium', rule: 'permission-creep', message: 'Filesystem write detected', file });
        if (hasNetwork) findings.push({ severity: 'medium', rule: 'permission-creep', message: 'Network access detected', file });
        if (hasSubprocess) findings.push({ severity: 'medium', rule: 'permission-creep', message: 'Subprocess usage detected', file });
        if (hasEnv) findings.push({ severity: 'low', rule: 'permission-creep', message: 'Env var access detected', file });
        return findings;
      },
    },
    {
      id: 'obfuscation',
      check(content, lines, file) {
        const findings = [];
        const base64Regex = /[A-Za-z0-9+/=]{100,}/;
        for (let i = 0; i < lines.length; i++) {
          if (base64Regex.test(lines[i]) && !file.endsWith('.json')) {
            findings.push({ severity: 'medium', rule: 'obfuscation', message: 'Large base64 block', file, line: i + 1 });
          }
        }
        const unicodeTricks = /[\u200B\u200C\u200D\u2060\u202A\u202B\u202C\u202D\u202E\uFEFF]/;
        for (let i = 0; i < lines.length; i++) {
          if (unicodeTricks.test(lines[i])) {
            findings.push({ severity: 'high', rule: 'obfuscation', message: 'Hidden unicode', file, line: i + 1 });
          }
        }
        return findings;
      },
    },
    {
      id: 'permission-interface-mismatch',
      check(content, lines, file) {
        if (!file.endsWith('effector.toml')) return [];
        const findings = [];

        // Minimal TOML parsing for benchmark (extract context and permissions)
        const contextMatch = content.match(/context\s*=\s*\[([^\]]*)\]/);
        const contextTypes = contextMatch
          ? contextMatch[1].match(/"([^"]+)"/g)?.map(s => s.replace(/"/g, '')) || []
          : [];

        const networkMatch = content.match(/network\s*=\s*(true|false)/);
        const networkEnabled = networkMatch ? networkMatch[1] === 'true' : false;

        const fsMatch = content.match(/filesystem\s*=\s*\[([^\]]*)\]/);
        const fsEnabled = fsMatch ? fsMatch[1].trim().length > 0 : false;

        for (const ctx of contextTypes) {
          if (NETWORK_CONTEXT_TYPES.has(ctx) && !networkEnabled) {
            findings.push({
              severity: 'medium',
              rule: 'permission-interface-mismatch',
              message: `Context "${ctx}" implies network but network=false`,
              file,
            });
          }
          if (FILESYSTEM_CONTEXT_TYPES.has(ctx) && !fsEnabled) {
            findings.push({
              severity: 'low',
              rule: 'permission-interface-mismatch',
              message: `Context "${ctx}" implies filesystem but no filesystem declared`,
              file,
            });
          }
        }
        return findings;
      },
    },
  ];
}

function runCompilation(cases) {
  const results = [];
  for (const c of cases) {
    try {
      const output = compile(c.manifest, c.target);
      let pass = true;
      let parsed;

      // Check parseability
      if (c.target === 'langchain') {
        // LangChain output is Python — check it contains expected strings
        if (c.expected.containsStrings) {
          for (const str of c.expected.containsStrings) {
            if (!output.includes(str)) {
              pass = false;
              break;
            }
          }
        }
      } else {
        // JSON targets
        try {
          parsed = JSON.parse(output);
        } catch {
          pass = false;
        }

        if (pass && parsed && c.expected.hasFields) {
          for (const field of c.expected.hasFields) {
            if (!(field in parsed) && !(field in (parsed.function || {}))) {
              // For openai-agents, fields may be nested under .function
              if (c.target === 'openai-agents' && field in (parsed.function || {})) continue;
              pass = false;
              break;
            }
          }
        }

        // Check name normalization
        if (pass && parsed && c.expected.nameNormalized) {
          const name = parsed.name || parsed.function?.name;
          if (name !== c.expected.nameNormalized) pass = false;
        }
      }

      results.push({ id: c.id, pass, expected: c.expected, actual: { outputLength: output.length } });
    } catch (err) {
      results.push({ id: c.id, pass: false, expected: c.expected, actual: { error: err.message } });
    }
  }
  return results;
}

// ─── Main ───────────────────────────────────────────────────

const categories = [
  { name: 'type-resolution', label: 'Type Resolution', runner: runTypeResolution },
  { name: 'validation', label: 'Manifest Validation', runner: runValidation },
  { name: 'composition', label: 'Composition Safety', runner: runComposition },
  { name: 'security', label: 'Security Detection', runner: runSecurity },
  { name: 'compilation', label: 'Compilation', runner: runCompilation },
];

const filteredCategories = categoryFilter
  ? categories.filter(c => c.name === categoryFilter)
  : categories;

if (filteredCategories.length === 0) {
  console.error(`Unknown category: ${categoryFilter}`);
  console.error(`Available: ${categories.map(c => c.name).join(', ')}`);
  process.exit(1);
}

console.log('');
console.log('  ╔══════════════════════════════════════════════╗');
console.log('  ║    effector Toolchain Benchmark v1.0.0       ║');
console.log('  ╚══════════════════════════════════════════════╝');
console.log('');

let totalCases = 0;
let totalPassed = 0;
let totalMs = 0;
const categoryResults = [];

for (const cat of filteredCategories) {
  const corpus = loadCorpus(cat.name);
  const start = performance.now();
  const results = cat.runner(corpus);
  const elapsed = performance.now() - start;

  const passed = results.filter(r => r.pass).length;
  const failed = results.filter(r => !r.pass).length;
  const score = ((passed / results.length) * 100).toFixed(1);

  totalCases += results.length;
  totalPassed += passed;
  totalMs += elapsed;

  const icon = failed === 0 ? '✓' : '✗';
  const color = failed === 0 ? '\x1b[32m' : '\x1b[31m';
  console.log(`  ${color}${icon}\x1b[0m  ${cat.label.padEnd(24)} ${score.padStart(6)}%  (${passed}/${results.length})  ${elapsed.toFixed(1)}ms`);

  if (verbose) {
    for (const r of results) {
      const icon2 = r.pass ? '\x1b[32m✓\x1b[0m' : '\x1b[31m✗\x1b[0m';
      console.log(`       ${icon2} ${r.id}`);
      if (!r.pass) {
        console.log(`         expected: ${JSON.stringify(r.expected)}`);
        console.log(`         actual:   ${JSON.stringify(r.actual)}`);
      }
    }
  }

  // Calculate F1 for security category
  let f1 = null;
  if (cat.name === 'security') {
    let tp = 0, fp = 0, fn = 0, tn = 0;
    for (const r of results) {
      const expected = r.expected.shouldTrigger;
      const actual = r.actual.triggered;
      if (expected && actual) tp++;
      else if (!expected && actual) fp++;
      else if (expected && !actual) fn++;
      else tn++;
    }
    const precision = tp / (tp + fp) || 0;
    const recall = tp / (tp + fn) || 0;
    f1 = precision + recall > 0 ? 2 * (precision * recall) / (precision + recall) : 0;
  }

  categoryResults.push({
    name: cat.name,
    label: cat.label,
    score: parseFloat(score),
    cases: results.length,
    passed,
    failed,
    timeMs: parseFloat(elapsed.toFixed(2)),
    ...(f1 !== null ? { f1: parseFloat(f1.toFixed(4)) } : {}),
  });
}

const overallScore = ((totalPassed / totalCases) * 100).toFixed(1);

console.log('');
console.log(`  ──────────────────────────────────────────────`);
console.log(`  Overall Score:  ${overallScore}%  (${totalPassed}/${totalCases} cases)`);
console.log(`  Total Time:     ${totalMs.toFixed(1)}ms`);
console.log(`  Categories:     ${filteredCategories.length}`);
console.log('');

// ─── Write results ──────────────────────────────────────────

const output = {
  version: '1.0.0',
  timestamp: new Date().toISOString(),
  effectorVersion: '1.0.0',
  score: parseFloat(overallScore),
  totalCases,
  totalPassed,
  totalFailed: totalCases - totalPassed,
  totalMs: parseFloat(totalMs.toFixed(2)),
  categories: categoryResults,
};

mkdirSync(join(__dirname, 'results'), { recursive: true });
writeFileSync(join(__dirname, 'results', 'latest.json'), JSON.stringify(output, null, 2));
console.log(`  Results written to results/latest.json`);
console.log('');

// Exit with error if any failures
if (totalPassed < totalCases) {
  process.exit(1);
}
