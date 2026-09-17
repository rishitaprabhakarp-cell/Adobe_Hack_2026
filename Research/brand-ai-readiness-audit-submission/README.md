# Brand AI Readiness Audit

A **13-skill** Agent Skill Marketplace that audits any website for AI discoverability and on-site engagement issues across **6 GEO dimensions**, producing evidence-backed findings, a prioritized fix roadmap, and a **per-engine GEO readiness score** (ChatGPT, Perplexity, Google AI Overviews, Gemini, Bing Copilot) — in HTML, Markdown, and JSON formats.

**Research basis**: Princeton/ACM KDD 2024 foundational GEO study · Directive Consulting 2026 70%-threshold framework · Onely 2026 5,000-site schema study · AutoGEO ICLR 2026 · Cognism 2026 (72.4% ChatGPT-cited pages have answer capsules) · AuthorityTech 2026 (+47% citation lift for fresh multi-layer dates) · Bigeye/TryProfound (+400% citation probability with `<th>`-headed tables)

---

## Table of Contents

1. [Marketplace Layout](#marketplace-layout)
2. [Skills Reference](#skills-reference)
3. [How the Entrypoint Works](#how-the-entrypoint-works)
4. [Output Schema](#output-schema)
5. [Root Cause Coverage](#root-cause-coverage)
6. [Guardrails](#guardrails)
7. [Running Locally (Extra/)](#running-locally-extra)

---

## Marketplace Layout

```
brand-ai-readiness-audit/       ← marketplace root (what you submitted)
├── marketplace.json            ← manifest: 13 skills, 1 entrypoint marked
├── README.md                   ← this file
│
├── skills/
│   ├── audit-orchestrator/     ← ENTRYPOINT — orchestrates all 12 sub-skills,
│   │   ├── SKILL.md              merges findings, emits the final report
│   │   └── references/
│   │       └── report-schema.md
│   │
│   ├── crawlability-probe/     ← 27-bot check, llms.txt, CDN/WAF, sitemap, crawl-delay
│   │   ├── SKILL.md
│   │   └── scripts/crawlability_check.py
│   │
│   ├── content-extractability-auditor/  ← passage scorer, named entity density,
│   │   ├── SKILL.md                       semantic tables, top-third citable density,
│   │   └── scripts/content_check.py       commercial independence, quotability
│   │
│   ├── technical-seo-probe/    ← HTTPS, noindex, canonicals, freshness 5-layer sync,
│   │   ├── SKILL.md              Last-Modified, anchor text, content chunk size
│   │   └── scripts/technical_check.py
│   │
│   ├── eeeat-signal-checker/   ← E-E-A-T, Wikipedia quality, Reddit presence,
│   │   ├── SKILL.md              Brand Authority Score (0–100)
│   │   └── scripts/eeeat_check.py
│   │
│   ├── structured-data-auditor/  ← JSON-LD richness, FAQPage, Speakable, schema types
│   │   ├── SKILL.md
│   │   └── scripts/schema_audit.py
│   │
│   ├── opengraph-meta-auditor/   ← og:title/image/description, Twitter Card
│   │   ├── SKILL.md
│   │   └── scripts/og_audit.py
│   │
│   ├── render-gap-detector/      ← JS render gaps, SPA shells, Googlebot UA delta
│   │   ├── SKILL.md
│   │   └── scripts/render_check.py
│   │
│   ├── entity-corroboration-checker/  ← Wikidata QID, sameAs links, brand collision
│   │   ├── SKILL.md
│   │   └── scripts/entity_check.py
│   │
│   ├── engagement-analyzer/      ← CTA above fold, response time, dynamic state
│   │   ├── SKILL.md
│   │   └── scripts/engagement_check.py
│   │
│   ├── rsl-licensing-checker/    ← RSL 1.0, 14 ADF endpoints, llms-full.txt,
│   │   ├── SKILL.md                WebMCP readiness, alternate text links
│   │   └── scripts/rsl_check.py
│   │
│   ├── llm-citation-tester/      ← LLM-perspective citation visibility (agent-only)
│   │   ├── SKILL.md
│   │   └── references/citation-checks.md
│   │
│   └── geo-score-aggregator/     ← 6-dimension + 5 per-engine GEO scoring
│       └── SKILL.md
│
└── Extra/                        ← supporting material (not part of the spec)
    ├── generate_report.py        ← report renderer: HTML / MD / JSON
    ├── benchmark_runner.py       ← 10-site benchmark suite
    ├── run_audit_live.sh         ← shell runner (parallel scripts + report)
    ├── run_audit.sh              ← legacy raw-JSON-only runner
    ├── requirements.txt          ← pip dependencies
    ├── EVAL.md                   ← benchmark methodology + competitor comparison
    ├── TESTING.md                ← per-skill test cases + grading rubric
    ├── benchmark_results/        ← live audit data for 10 benchmark sites
    └── sample_ouput/             ← sample HTML / JSON / MD reports
```

---

## Skills Reference

### Skill summary

| # | Skill | Finding IDs | Key checks |
|---|-------|-------------|------------|
| 1 | `audit-orchestrator` | *(entrypoint)* | Orchestrates all 12 sub-skills, merges + deduplicates findings, emits final report |
| 2 | `crawlability-probe` | RC2, RC4, RC7, RC14, RC17, RC19, RC23, CDN-WAF-001/002, RC4-002 | 27-bot check, llms.txt, CDN/WAF bypass, OAI-SearchBot policy, crawl-delay |
| 3 | `render-gap-detector` | RC1, RC9, RC12, RC20 | Googlebot UA fetch, SPA shell detection, JS word delta |
| 4 | `structured-data-auditor` | RC3, RC10, RC11, RC13, RC15, RC16, RC18, RC21 | JSON-LD richness, FAQPage, Speakable, freshness dates |
| 5 | `entity-corroboration-checker` | RC5, RC6 | Wikidata QID, sameAs links, brand name collision |
| 6 | `engagement-analyzer` | RC8, RC16, RC22 | CTA above fold, response time, dynamic state |
| 7 | `llm-citation-tester` | CITE-001–004 | web_search visibility (agent-only, no script) |
| 8 | `content-extractability-auditor` | CEA-001–016 | 6-signal passage scorer, named entity density, semantic tables, top-third citable density, commercial independence, quotability, passage density, structured content ratio |
| 9 | `eeeat-signal-checker` | EEAT-001–010 | Author bylines, review platforms, Wikipedia quality, Reddit presence, Brand Authority Score |
| 10 | `technical-seo-probe` | TSEO-001–013, FRESH-001 | HTTPS, noindex/nosnippet, canonicals, H1 hierarchy, 5-layer freshness sync, Last-Modified, generic anchors, content chunk size |
| 11 | `opengraph-meta-auditor` | OG-001–008 | og:title/image/description, Twitter Card, meta description |
| 12 | `rsl-licensing-checker` | RSL-001–008 | RSL 1.0, 14 ADF endpoints, llms-full.txt, WebMCP readiness, alternate text links, private URL detection |
| 13 | `geo-score-aggregator` | *(scoring)* | 6 dimension scores (D1–D6), 5 per-engine scores, citability coverage %, vertical benchmark, score formula transparency |

**90 finding IDs across 6 GEO dimensions · v2.1**

### Skill execution flow (when run via scripts)

```
run_audit_live.sh  (in Extra/)
  │
  ├─ [parallel] crawlability_check.py   → crawlability.json
  ├─ [parallel] render_check.py         → render.json
  ├─ [parallel] schema_audit.py         → schema.json
  ├─ [parallel] entity_check.py         → entity.json
  ├─ [parallel] content_check.py        → content.json
  ├─ [parallel] eeeat_check.py          → eeeat.json
  ├─ [parallel] engagement_check.py     → engagement.json
  ├─ [parallel] rsl_check.py            → rsl.json
  ├─ [parallel] og_audit.py             → opengraph.json
  └─ [parallel] technical_check.py      → technical.json
        │
        ▼
  generate_report.py  (in Extra/)
    ├─ merge + deduplicate findings
    ├─ compute 6 dimension scores (D1–D6)
    ├─ compute 5 per-engine GEO scores
    ├─ compute citability coverage %
    ├─ compare vs. 10-site vertical benchmark
    └─ render → HTML + MD + JSON
```

---

## How the Entrypoint Works

The **`audit-orchestrator`** (`skills/audit-orchestrator/SKILL.md`) is the designated entrypoint.

**When an agent invokes it with a URL, it:**

1. **Dispatches** all 12 sub-skills in parallel — each probes a different dimension of AI readiness.
2. **Merges findings** from all sub-skills into a single deduplicated list, each with `id`, `severity`, `evidence`, and `suggested_action`.
3. **Scores** via `geo-score-aggregator`: 6 GEO dimension scores + 5 per-engine scores (ChatGPT, Perplexity, Google AI Overviews, Gemini, Bing Copilot).
4. **Enriches** each finding with:
   - `research_lift` — quantified citation improvement from peer-reviewed GEO research
   - `platform_fix_code` — auto-detected platform (Next.js / WordPress / Shopify / generic) with copy-paste fix snippets
5. **Emits** the final structured report (see schema below).

**Agent-mode invocation (no scripts needed):**
```
Use the audit-orchestrator skill on https://example.com
```

---

## Output Schema

Every report (JSON format) has this structure — a superset of the contest minimum:

```json
{
  "site": "example.com",
  "audited_at": "2026-09-13T06:52:00Z",
  "overall_score": 40,
  "geo_readiness": "Not GEO Ready",
  "platform_detected": "generic",
  "summary": {
    "total_findings": 27,
    "critical": 2,
    "high": 9,
    "medium": 9,
    "low": 7,
    "passing_checks": 12
  },
  "dimension_scores": [
    { "id": "D1", "name": "Crawlability",            "score": 18 },
    { "id": "D2", "name": "Content Extractability",  "score": 7  },
    { "id": "D3", "name": "Entity Clarity",          "score": 88 },
    { "id": "D4", "name": "Schema Integrity",        "score": 52 },
    { "id": "D5", "name": "Off-Page Authority",      "score": 50 },
    { "id": "D6", "name": "Technical Foundation",    "score": 20 }
  ],
  "engine_scores": {
    "ChatGPT": 45,
    "Perplexity": 37,
    "Google AI Overviews": 40,
    "Gemini": 41,
    "Bing Copilot": 38
  },
  "citability_coverage": {
    "pct": 38,
    "interpretation": "Needs Work",
    "citeable_passages": 6,
    "total_passages": 16
  },
  "vertical_benchmark": {
    "benchmark_median": 52,
    "overall_position": "Below median",
    "estimated_percentile": 31
  },
  "projected_score": {
    "projected_overall": 67,
    "score_lift": 27,
    "fixes_required": 11
  },
  "findings": [
    {
      "id": "FRESH-001",
      "title": "No machine-readable freshness signals present",
      "severity": "CRITICAL",
      "evidence": "0/5 freshness signal layers found (HTTP Last-Modified, JSON-LD dateModified, OG article:modified_time, visible Last updated, meta date tag).",
      "suggested_action": {
        "summary": "Add JSON-LD dateModified, HTTP Last-Modified header, and visible Last updated text.",
        "priority": "high",
        "effort": "low"
      },
      "research_lift": "+47% citation lift for fresh, multi-layer dated content (AuthorityTech 2026)",
      "platform_fix_code": "// Next.js: add to getServerSideProps..."
    }
  ]
}
```

GEO readiness thresholds (Directive Consulting 2026):

| Score | Label | Meaning |
|-------|-------|---------|
| ≥ 70 | **GEO Ready** | Meaningful citation probability across all major AI engines |
| 50–69 | **Developing** | Structural barriers present; targeted fixes needed |
| < 50 | **Not GEO Ready** | Fundamental gaps must be closed before GEO optimization matters |

Full finding schema: `skills/audit-orchestrator/references/report-schema.md`

---

## Root Cause Coverage

| Root Cause | Skill |
|---|---|
| RC1: JS-Rendering | `render-gap-detector` |
| RC2: Missing llms.txt | `crawlability-probe` |
| RC3: No inner-page JSON-LD | `structured-data-auditor` |
| RC4: AI crawler misconfiguration | `crawlability-probe` |
| RC4-002: Excessive crawl-delay for citation bots | `crawlability-probe` |
| RC5: Entity disambiguation | `entity-corroboration-checker` |
| RC6: Zero external corroboration | `entity-corroboration-checker` |
| RC7: Phantom/broken llms.txt | `crawlability-probe` |
| RC8: Engagement signals | `engagement-analyzer` |
| RC9: Selective SSR | `render-gap-detector` |
| RC10: No speakable schema | `structured-data-auditor` |
| RC11: Missing FAQPage/HowTo | `structured-data-auditor` |
| RC12: Institution invisibility | `render-gap-detector` |
| RC13: Paywall without schema | `structured-data-auditor` |
| RC14: No AI discovery endpoints | `crawlability-probe` |
| RC15: Language signal gaps | `structured-data-auditor` |
| RC16: Empty alt on key images | `structured-data-auditor` + `engagement-analyzer` |
| RC17: No RSS/Atom feed | `crawlability-probe` |
| RC18: Video without transcript | `structured-data-auditor` |
| RC19: Sitemap absent | `crawlability-probe` |
| RC20: Duplicate/empty page titles | `render-gap-detector` |
| RC21: Freshness metadata drift | `structured-data-auditor` |
| RC22: Dynamic state no fallback | `engagement-analyzer` |
| RC23: robots.txt policy vs content gap | `crawlability-probe` |
| CDN-WAF-001: CDN/WAF silently blocks citation bots | `crawlability-probe` |
| CDN-WAF-002: GPTBot vs OAI-SearchBot policy mismatch | `crawlability-probe` |
| CEA-001–016: Passage-level content, answer capsules, named entity density, semantic tables, commercial independence, quotability | `content-extractability-auditor` |
| EEAT-001–010: E-E-A-T signals, Wikipedia quality, Reddit presence, Brand Authority Score | `eeeat-signal-checker` |
| TSEO-001–013: Technical SEO, generic anchors, content chunk size, lang/hreflang | `technical-seo-probe` |
| FRESH-001: 5-layer freshness signal sync | `technical-seo-probe` |
| OG-001–008: OpenGraph / meta | `opengraph-meta-auditor` |
| RSL-001–008: RSL 1.0, 14 ADF endpoints, WebMCP readiness, alternate text links | `rsl-licensing-checker` |

---

## Guardrails

- **Read-only**: no skill ever modifies a live site.
- **robots.txt respected**: the audit reads public HTTP responses only; it does not scrape disallowed content.
- **No authenticated actions**: no login, form submission, or destructive operations.
- **Rate-limited**: each script makes ≤ 15 HTTP requests per site, with a 12-second timeout per request.
- **No API keys required**: all checks use open HTTP probes or agent-native tools.
- **Runtime**: ~90 seconds for a typical site (10 scripts in parallel + report generation).

---

## Running Locally (Extra/)

The `Extra/` folder contains tooling for running the audit via scripts locally. These files are **not** part of the marketplace spec — they are helpers for development, testing, and demo purposes.

### Requirements

| Dependency | Version | Notes |
|------------|---------|-------|
| Python | 3.9 + | 3.11+ recommended |
| pip | any | comes with Python |

No API keys required.

### Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate.bat     # Windows cmd

# 2. Install dependencies
pip install -r Extra/requirements.txt
```

### Run a full audit

```bash
# Runs all 10 skill scripts in parallel, then generates HTML + MD + JSON reports
bash Extra/run_audit_live.sh https://example.com

# With explicit formats
bash Extra/run_audit_live.sh https://example.com --format html,md,json
```

### Run a single skill script

```bash
source venv/bin/activate
python skills/crawlability-probe/scripts/crawlability_check.py https://example.com
python skills/content-extractability-auditor/scripts/content_check.py https://example.com
python skills/technical-seo-probe/scripts/technical_check.py https://example.com
python skills/eeeat-signal-checker/scripts/eeeat_check.py https://example.com
python skills/rsl-licensing-checker/scripts/rsl_check.py https://example.com
# ... etc.
```

### Generate a report from existing skill outputs

```bash
python Extra/generate_report.py /path/to/audit/dir/ --format html,md,json
```

### Sample reports

Pre-generated sample reports are in `Extra/sample_ouput/`:

```
Extra/sample_ouput/
├── sample_report_adobe.html    ← open in browser
├── sample_report_adobe.json
├── sample_report_adobe.md
├── sample_report_stripe.html
├── sample_report_stripe.json
└── sample_report_stripe.md
```

### Benchmark results

Live audit data for 10 benchmark sites is in `Extra/benchmark_results/`:

| Tier | Sites | Score Range |
|------|-------|-------------|
| 🟢 GEO Ready | `openai.com`, `anthropic.com` | 65–90 |
| 🟡 Developing | `stripe.com`, `vercel.com`, `linear.app`, `hubspot.com`, `shopify.com`, `supabase.com` | 45–65 |
| 🔴 Not GEO Ready | `adobe.com`, `craigslist.org` | 10–50 |

See `Extra/EVAL.md` for the full evaluation framework and competitor comparison.
