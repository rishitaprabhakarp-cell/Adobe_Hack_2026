---
name: audit-orchestrator
description: Entrypoint for the Brand AI Readiness Audit marketplace. Takes a website URL, sequentially invokes all 15 sub-skills covering AI discoverability (crawlability-probe, render-gap-detector, structured-data-auditor, entity-corroboration-checker, llm-citation-tester, content-extractability-auditor, eeeat-signal-checker, technical-seo-probe, opengraph-meta-auditor, rsl-licensing-checker) and on-site engagement (engagement-analyzer, landing-clarity-auditor, content-trust-auditor, url-resilience-checker), scores GEO readiness via geo-score-aggregator, merges all findings, deduplicates, and emits a single structured JSON audit report. Use when a user wants to audit a website for AI discoverability or on-site engagement problems.
license: MIT
---

# Brand AI Readiness Audit — Orchestrator

## When to use

Use when given a website URL and asked to audit it for AI discoverability issues, citation gaps, structured data problems, engagement failures, or any combination thereof. This is the single entrypoint for the entire marketplace.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Full URL or bare domain to audit (e.g. `https://example.com` or `example.com`) |

Normalize the URL: if no scheme is provided, prepend `https://`. Strip trailing slashes. Extract the bare `site` hostname for the report.

## Procedure

Work through these steps in order. Do NOT skip a step even if a prior step found critical issues — each sub-skill covers a distinct concern.

### Step 1 — Normalize input

```
site_url  = normalize(input)          # ensure https:// prefix
site_host = extract_hostname(site_url) # e.g. "example.com"
audited_at = current ISO-8601 UTC timestamp
```

### Step 2 — Run sub-skills in sequence

Invoke each sub-skill below, passing `site_url`. Collect the `findings` array each returns. If a sub-skill errors or times out, log a LOW-severity finding `{id: "ORCH-ERR-<skill>", title: "Sub-skill <name> did not complete", ...}` and continue.

| Order | Sub-skill | Coverage |
|-------|-----------|----------|
| 1 | `crawlability-probe` | RC2, RC4, RC7, RC14, RC17, RC19, RC23 — 27-bot check |
| 2 | `render-gap-detector` | RC1, RC9, RC12, RC20 — JS render gaps |
| 3 | `structured-data-auditor` | RC3, RC10, RC11, RC13, RC15, RC16, RC18, RC21 — JSON-LD quality |
| 4 | `entity-corroboration-checker` | RC5, RC6 — Wikidata/sameAs/entity collision |
| 5 | `llm-citation-tester` | CITE-001 to 004 — LLM perspective via web_search |
| 6 | `content-extractability-auditor` | CEA-001 to 008 — passage-level structure (Princeton KDD 2024) |
| 7 | `eeeat-signal-checker` | EEAT-001 to 006 — E-E-A-T, review platforms, Reddit |
| 8 | `technical-seo-probe` | TSEO-001 to 009 — canonical, nosnippet, HTTPS, redirects |
| 9 | `opengraph-meta-auditor` | OG-001 to 008 — OpenGraph, Twitter Card, meta quality |
| 10 | `rsl-licensing-checker` | RSL-001 to 005 — RSL 1.0, llms-full.txt, deep llms.txt |
| 11 | `engagement-analyzer` | RC8, RC16, RC22 — CTA, above-fold, response time |
| 12 | `landing-clarity-auditor` | RC24, RC25, RC28, RC30 — first-5-second landing clarity, nav overload, CTA density, AI-referrer handling |
| 13 | `content-trust-auditor` | RC26, RC27, RC-TRUST, RC-NAV — scannability, search, social proof, trust signals |
| 14 | `url-resilience-checker` | RC29, RC30 — catch-all redirects, dead llms.txt/sitemap URLs, AI-referrer landing page |
| 15 | `geo-score-aggregator` | Scoring layer — produces GEO readiness % and per-engine scores |

Sub-skills 12–14 emit their `findings[]` directly (each finding already includes `id`, `title`, `severity`, `evidence`, `suggested_action`) — pass them straight into the merge step without re-deriving severity.

### Step 3 — Merge and deduplicate findings

1. Concatenate all `findings` arrays from sub-skills at order 1–14 above (`geo-score-aggregator` at order 15 consumes the merged findings rather than producing its own).
2. Deduplicate: if two findings share the same `id`, keep the one with the higher severity (CRITICAL > HIGH > MEDIUM > LOW). If same severity, keep the one with more evidence text.
3. Sort: CRITICAL → HIGH → MEDIUM → LOW, then alphabetically by `id` within each group.

### Step 4 — Count severity buckets

```
total_findings = len(findings)
critical = count(findings where severity == "CRITICAL")
high     = count(findings where severity == "HIGH")
medium   = count(findings where severity == "MEDIUM")
low      = count(findings where severity == "LOW")
```

### Step 5 — Run geo-score-aggregator

After merging findings, pass the full findings array to `geo-score-aggregator`. It will:
- Map findings to 6 GEO dimensions
- Score each dimension (0–100)
- Calculate per-engine scores (ChatGPT, Perplexity, Google AI Overviews, Gemini, Bing Copilot)
- Produce an overall GEO readiness percentage (threshold: 70% = GEO Ready)
- Generate a prioritized action roadmap

Add the returned `geo_score` object as a top-level key in the final report.

### Step 6 — Emit report

Before emitting, lowercase every finding's `severity` value (`critical`/`high`/`medium`/`low`) to match the
published report schema exactly — sub-skills and the severity tables above use uppercase internally for
readability, but the final JSON must use lowercase. `suggested_action.priority` is already lowercase from
every sub-skill; leave it as-is.

Output the final JSON report using the schema in [references/report-schema.md](references/report-schema.md).

Print the report as a fenced JSON code block so the caller can parse it directly.

### Step 7 — Human-readable summary (required)

After the JSON block, append:
1. **GEO Readiness**: `Overall: XX% — [GEO Ready / Developing / Not GEO Ready]`
2. **Per-engine breakdown**: one line per engine with score
3. **Top 3 findings** (highest severity) with their suggested actions
4. **Highest-ROI next action**: the single fix most likely to improve the overall GEO score

## Output

```json
{
  "site": "example.com",
  "audited_at": "2026-09-08T00:00:00Z",
  "summary": {
    "total_findings": 0,
    "critical": 0,
    "high": 0,
    "medium": 0,
    "low": 0
  },
  "findings": []
}
```

See [references/report-schema.md](references/report-schema.md) for full field definitions and severity criteria.

## Guardrails

- Read-only: no skill in this marketplace ever modifies a live site.
- Respect `robots.txt`: do not fetch pages that are disallowed for the crawling user-agent being tested.
- No authenticated actions, no destructive operations.
- Target runtime: < 5 minutes total for a typical website.
