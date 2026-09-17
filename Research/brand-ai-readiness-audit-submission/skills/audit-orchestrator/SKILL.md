---
name: audit-orchestrator
description: Entrypoint for the Brand AI Readiness Audit marketplace. Takes a website URL, sequentially invokes all 6 sub-skills (crawlability-probe, render-gap-detector, structured-data-auditor, entity-corroboration-checker, engagement-analyzer, llm-citation-tester), merges their findings, deduplicates, scores severity, and emits a single structured JSON audit report. Use when a user wants to audit a website for AI discoverability or on-site engagement problems.
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
| 1 | `crawlability-probe` | RC2, RC4-001/002, RC7, RC14, RC17, RC19, RC23, CDN-WAF-001/002 — 27-bot check + Crawl-delay |
| 2 | `render-gap-detector` | RC1, RC9, RC12, RC20 — JS render gaps |
| 3 | `structured-data-auditor` | RC3, RC10, RC11, RC13, RC15, RC16, RC18, RC21 — JSON-LD quality |
| 4 | `entity-corroboration-checker` | RC5, RC6 — Wikidata/sameAs/entity collision |
| 5 | `engagement-analyzer` | RC8, RC16, RC22 — CTA, above-fold, response time |
| 6 | `llm-citation-tester` | CITE-001 to 004 — LLM perspective via web_search |
| 7 | `content-extractability-auditor` | CEA-001 to 013 + CEA-007 to 010 — passage extractability (6-signal scorer), quotability, lede quality, structured content ratio, **named entity density** (Wellows 4.8×), **semantic HTML tables** (Bigeye +400%), **top-third citable density** (SIGI 8.5/10), **commercial independence signal** (SIGI 9.0/10) |
| 8 | `eeeat-signal-checker` | EEAT-001 to 010 — E-E-A-T, Wikipedia quality class, Reddit API, weighted Brand Authority Score (0–100) |
| 9 | `technical-seo-probe` | TSEO-001 to 013 — canonical, nosnippet, HTTPS, redirects, lang/hreflang mismatch, generic anchors, stale Last-Modified, RAG chunk size |
| 10 | `opengraph-meta-auditor` | OG-001 to 008 — OpenGraph, Twitter Card, meta quality |
| 11 | `rsl-licensing-checker` | RSL-001 to 008 — RSL 1.0, llms-full.txt, deep llms.txt, private URLs, WebMCP readiness (4 levels), markdown alternates |
| 12 | `geo-score-aggregator` | Scoring layer — produces GEO readiness %, per-engine scores, Citability Coverage %, vertical benchmark, score formula transparency, platform-specific fix code (Next.js/WordPress/Shopify/generic) |
| 13 | `technical-seo-probe` extension | FRESH-001 — 5-layer freshness signal consistency (HTTP Last-Modified + JSON-LD dateModified + OG modified_time + visible text + meta tag; Lureon 76%, AuthorityTech +47%) |

### Step 3 — Merge and deduplicate findings

1. Concatenate all `findings` arrays from the 6 sub-skills.
2. Deduplicate: if two findings share the same `id`, keep the one with the higher severity (CRITICAL > HIGH > MEDIUM > LOW). If same severity, keep the one with more evidence text.
3. Sort: CRITICAL → HIGH → MEDIUM → LOW, then alphabetically by `id` within each group.
4. Enrich each finding with `platform_fix_code` if available (platform auto-detected from response headers/HTML: nextjs / wordpress / shopify / generic).
5. Attach `research_lift` citations to eligible findings (e.g. "+33% AI citation rate").

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
- Compute **Citability Coverage %** (% of content passages scoring >70% extractable)
- Compute **vertical benchmark** vs. 10-site live benchmark median (52/100)
- Compute **projected score** after fixing all CRITICAL+HIGH findings
- Expose **score formula** per engine for full transparency
- Detect site **platform** (Next.js / WordPress / Shopify / generic) for fix code generation

Add the returned `geo_score` object as a top-level key in the final report.

### Step 6 — Emit report

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
