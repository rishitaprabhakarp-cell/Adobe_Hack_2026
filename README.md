# Brand AI Readiness Audit

A **13-skill** Agent Skill Marketplace that audits any website for AI discoverability and on-site engagement issues across **6 GEO dimensions**, producing evidence-backed findings, a prioritized fix roadmap, and a **per-engine GEO readiness score** (ChatGPT, Perplexity, Google AI Overviews, Gemini, Bing Copilot) — in HTML, Markdown, PDF, and JSON formats.

**Research basis**: Princeton/ACM KDD 2024 foundational GEO study · Directive Consulting 2026 70%-threshold framework · Onely 2026 5,000-site schema study · AutoGEO ICLR 2026 · Cognism 2026 (72.4% ChatGPT-cited pages have answer capsules) · seoprocheck/ai-crawler-audit · kai-cmo-harness/llm-cliche-detector · Wikidata P856 entity corroboration

---

## Table of Contents

1. [Requirements](#requirements)
2. [Setup — Virtual Environment](#setup--virtual-environment)
3. [Running an Audit](#running-an-audit)
4. [Report Formats](#report-formats)
5. [Project Structure](#project-structure)
6. [Skills Reference](#skills-reference)
7. [Output Schema](#output-schema)
8. [Root Cause Coverage](#root-cause-coverage)
9. [Guardrails](#guardrails)

---

## Requirements

| Dependency | Version | Notes |
|------------|---------|-------|
| Python | 3.9 + | 3.11+ recommended |
| pip | any | comes with Python |
| Git | any | for cloning |
| Google Chrome | any | for PDF generation (optional) |

No system packages, databases, or API keys are required for the core audit.

---

## Setup — Virtual Environment

### 1. Clone the repository

```bash
git clone https://github.com/<your-org>/Adobe_Hack_2026.git
cd Adobe_Hack_2026
```

### 2. Create and activate the virtual environment

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (cmd):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

You should see `(venv)` prefixed in your terminal prompt.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `requests` — HTTP calls to probe sites
- `beautifulsoup4` + `lxml` — HTML parsing
- `weasyprint` — PDF generation (requires system fonts; see [PDF note](#pdf-generation) below)

### 4. Verify the installation

```bash
python -c "import requests, bs4, weasyprint; print('All dependencies OK')"
```

Expected output:
```
All dependencies OK
```

### Deactivating the environment

```bash
deactivate
```

---

## Running an Audit

### Option A — Full audit + reports (recommended)

```bash
# Make the runner executable (first time only)
chmod +x run_audit_live.sh

# Basic run — produces HTML + Markdown reports by default
bash run_audit_live.sh https://example.com

# With all formats and branding
bash run_audit_live.sh https://example.com \
  --format html,md,pdf,json \
  --brand-name "Example Corp" \
  --brand-color "#0066CC"
```

**What this does, step by step:**
1. Launches all 10 Python skill scripts **in parallel** against the target URL
2. Waits for all to finish and prints a live summary table
3. Saves raw JSON outputs to `/tmp/audit_results/<domain>/<timestamp>/`
4. Calls `generate_report.py` to merge findings, compute GEO scores, and render reports
5. Prints the path to each generated report file

**CLI flags for `run_audit_live.sh`:**

| Flag | Default | Description |
|------|---------|-------------|
| `--format` | `html,md` | Comma-separated: `html`, `md`, `pdf`, `json` |
| `--brand-name` | *(domain)* | Brand name shown in report title |
| `--brand-color` | `#0066CC` | Accent color for HTML/PDF (hex) |
| `--no-report` | off | Skip report generation; keep raw JSON only |

### Option B — Report from an existing audit directory

If you've already run the scripts and just want to regenerate reports:

```bash
python generate_report.py /tmp/audit_results/example.com/20260909T120000Z/ \
  --format html,md,pdf,json \
  --brand-name "Example Corp" \
  --brand-color "#0066CC"
```

**CLI flags for `generate_report.py`:**

| Flag | Default | Description |
|------|---------|-------------|
| `audit_dir` | *(required)* | Directory containing the 10 `*.json` skill outputs |
| `--format` | `html,md` | `html`, `md`, `pdf`, `json` (comma-separated) |
| `--output-dir` | `<audit_dir>/reports/` | Where to write report files |
| `--brand-name` | *(inferred from domain)* | Brand name |
| `--brand-color` | `#0066CC` | Accent hex color |
| `--site` | *(from skill outputs)* | Override displayed site URL |

### Option C — Run a single skill script

Each skill has a standalone Python script you can run directly:

```bash
# Activate the venv first
source venv/bin/activate

# Run any individual script
python skills/crawlability-probe/scripts/crawlability_check.py https://example.com
python skills/content-extractability-auditor/scripts/content_check.py https://example.com
python skills/eeeat-signal-checker/scripts/eeeat_check.py https://example.com
python skills/opengraph-meta-auditor/scripts/og_audit.py https://example.com
python skills/rsl-licensing-checker/scripts/rsl_check.py https://example.com
python skills/structured-data-auditor/scripts/schema_audit.py https://example.com
python skills/technical-seo-probe/scripts/technical_check.py https://example.com
python skills/render-gap-detector/scripts/render_check.py https://example.com
python skills/engagement-analyzer/scripts/engagement_check.py https://example.com
python skills/entity-corroboration-checker/scripts/entity_check.py https://example.com

# Pretty-print the output
python skills/crawlability-probe/scripts/crawlability_check.py https://example.com \
  | python -m json.tool | less
```

### Option D — Agent-driven (Cursor / Claude)

```
Use the audit-orchestrator skill on https://example.com
```

The `audit-orchestrator` SKILL.md calls all 12 sub-skills in sequence, merges their findings, and passes them to `geo-score-aggregator` for scoring. No scripts needed — the agent uses its own fetch/search tools.

---

## Report Formats

| Format | File | Best for | Size (typical) |
|--------|------|----------|----------------|
| **HTML** | `ai-readiness-audit-<domain>.html` | Sharing via email/Slack — opens in any browser with inline SVG charts, no dependencies | ~28 KB |
| **Markdown** | `ai-readiness-audit-<domain>.md` | GitHub wiki, Notion, Confluence, PR comments | ~7 KB |
| **PDF** | `ai-readiness-audit-<domain>.pdf` | Client deliverables, print-ready (5 pages) | ~450 KB |
| **JSON** | `ai-readiness-audit-<domain>.json` | CI pipelines, Jira/Linear auto-issue creation, audit diffing | ~10 KB |

### Sample reports (adobe.com live run)

The `sample_ouput/` directory contains real audit outputs from a live run against `www.adobe.com`:

```
sample_ouput/
├── sample_report_adobe.html   ← open in browser
├── sample_report_adobe.pdf    ← 5-page PDF
├── sample_report_adobe.md     ← Markdown
└── sample_report_adobe.json   ← enriched JSON
```

```bash
# Open the HTML report in your default browser
open sample_ouput/sample_report_adobe.html          # macOS
xdg-open sample_ouput/sample_report_adobe.html      # Linux
start sample_ouput/sample_report_adobe.html         # Windows
```

### PDF generation

PDF rendering uses **Google Chrome headless** (best quality, no extra system deps):

```bash
# Chrome is used automatically if found at the standard path:
/Applications/Google Chrome.app/Contents/MacOS/Google Chrome  # macOS
/usr/bin/google-chrome                                          # Linux
```

If Chrome is not available, `weasyprint` is tried next. If neither works, the HTML file is kept and a `.pdf.txt` file is written with manual instructions (File → Print → Save as PDF from any browser).

---

## Project Structure

```
Adobe_Hack_2026/
├── .gitignore
├── README.md                                ← this file
├── TESTING.md                               ← detailed testing guide
├── requirements.txt                         ← pip dependencies
├── marketplace.json                         ← skill manifest (13 skills, 1 entrypoint)
│
├── run_audit_live.sh                        ← main runner: audits + generates reports
├── run_audit.sh                             ← legacy runner (raw JSON only)
├── generate_report.py                       ← report generator: HTML / MD / PDF / JSON
│
├── sample_ouput/                            ← live audit results from www.adobe.com
│   ├── sample_report_adobe.html
│   ├── sample_report_adobe.pdf
│   ├── sample_report_adobe.md
│   └── sample_report_adobe.json
│
└── skills/
    ├── audit-orchestrator/                  ← ENTRYPOINT (orchestrates all 12 sub-skills)
    │   ├── SKILL.md
    │   └── references/report-schema.md
    │
    ├── crawlability-probe/                  ← 27-bot check, llms.txt, CDN/WAF, sitemap
    │   ├── SKILL.md
    │   └── scripts/crawlability_check.py
    ├── render-gap-detector/                 ← JS render gaps, SPA shells, Googlebot UA
    │   ├── SKILL.md
    │   └── scripts/render_check.py
    ├── structured-data-auditor/             ← JSON-LD richness, schema types, freshness
    │   ├── SKILL.md
    │   └── scripts/schema_audit.py
    ├── entity-corroboration-checker/        ← Wikidata P856, sameAs, entity collision
    │   ├── SKILL.md
    │   └── scripts/entity_check.py
    ├── engagement-analyzer/                 ← CTA, above-fold, response time
    │   ├── SKILL.md
    │   └── scripts/engagement_check.py
    ├── llm-citation-tester/                 ← LLM-perspective citation visibility
    │   ├── SKILL.md
    │   └── references/citation-checks.md
    ├── content-extractability-auditor/      ← answer capsules, AI-cliché, passage structure
    │   ├── SKILL.md
    │   └── scripts/content_check.py
    ├── eeeat-signal-checker/                ← E-E-A-T, review platforms, Wikidata P856
    │   ├── SKILL.md
    │   └── scripts/eeeat_check.py
    ├── technical-seo-probe/                 ← HTTPS, nosnippet, redirects, canonicals
    │   ├── SKILL.md
    │   └── scripts/technical_check.py
    ├── opengraph-meta-auditor/              ← OG tags, Twitter Card, meta quality
    │   ├── SKILL.md
    │   └── scripts/og_audit.py
    ├── rsl-licensing-checker/               ← RSL 1.0, llms-full.txt, ADF 2026 endpoints
    │   ├── SKILL.md
    │   └── scripts/rsl_check.py
    └── geo-score-aggregator/                ← dimension scoring, per-engine GEO scores
        └── SKILL.md
```

---

## Skills Reference

### Skill execution flow

```
run_audit_live.sh
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
  generate_report.py
    ├─ merge + deduplicate findings
    ├─ compute 6 dimension scores (D1–D6)
    ├─ compute 5 per-engine GEO scores
    └─ render → HTML + MD + PDF + JSON
```

### Skill summary

| # | Skill | Finding IDs | Key checks |
|---|-------|-------------|------------|
| 1 | `crawlability-probe` | RC2, RC4, RC7, RC14, RC17, RC19, RC23, CDN-WAF-001/002 | 27-bot check, llms.txt, CDN/WAF bypass, OAI-SearchBot policy |
| 2 | `render-gap-detector` | RC1, RC9, RC12, RC20 | Googlebot UA fetch, SPA shell detection, JS word delta |
| 3 | `structured-data-auditor` | RC3, RC10, RC11, RC13, RC15, RC16, RC18, RC21 | JSON-LD richness, FAQPage, Speakable, freshness dates |
| 4 | `entity-corroboration-checker` | RC5, RC6 | Wikidata QID, sameAs links, brand name collision |
| 5 | `engagement-analyzer` | RC8, RC16, RC22 | CTA above fold, response time, dynamic state |
| 6 | `llm-citation-tester` | CITE-001–004 | web_search visibility (agent-only, no script) |
| 7 | `content-extractability-auditor` | CEA-001–010 | Answer capsules, AI-cliché slop, sourced stats, FAQ |
| 8 | `eeeat-signal-checker` | EEAT-001–007 | Author bylines, review platforms, Wikidata P856 via SPARQL |
| 9 | `technical-seo-probe` | TSEO-001–009 | HTTPS, noindex/nosnippet, canonicals, H1 hierarchy |
| 10 | `opengraph-meta-auditor` | OG-001–008 | og:title/image/description, Twitter Card, meta description |
| 11 | `rsl-licensing-checker` | RSL-001–005 | RSL 1.0, 14 ADF endpoints, llms-full.txt, IndexNow |
| 12 | `geo-score-aggregator` | GEO scoring | 6 dimension scores, 5 per-engine scores, action roadmap |
| — | `audit-orchestrator` | (entrypoint) | Orchestrates all above, merges, deduplicates, scores |

---

## Output Schema

Every generated JSON report has this structure:

```json
{
  "site": "example.com",
  "audited_at": "2026-09-08T19:10:43Z",
  "overall_score": 48,
  "geo_readiness": "Not GEO Ready",
  "summary": {
    "total_findings": 21,
    "critical": 1,
    "high": 4,
    "medium": 12,
    "low": 4,
    "passing_checks": 10
  },
  "dimension_scores": [
    { "id": "D1", "name": "Crawlability",           "score": 33 },
    { "id": "D2", "name": "Content Extractability", "score": 31 },
    { "id": "D3", "name": "Entity Clarity",         "score": 88 },
    { "id": "D4", "name": "Schema Integrity",       "score": 64 },
    { "id": "D5", "name": "Off-Page Authority",     "score": 32 },
    { "id": "D6", "name": "Technical Foundation",   "score": 27 }
  ],
  "engine_scores": {
    "ChatGPT": 52,
    "Perplexity": 45,
    "Google AI Overviews": 48,
    "Gemini": 48,
    "Bing Copilot": 45
  },
  "findings": [
    {
      "id": "OG-001",
      "title": "No OpenGraph tags on homepage",
      "severity": "CRITICAL",
      "evidence": "og:title, og:description, og:image all absent from homepage.",
      "suggested_action": {
        "summary": "Add og:title, og:description, og:image, og:type to every page template.",
        "priority": "high",
        "effort": "low"
      }
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

Full finding schema in `skills/audit-orchestrator/references/report-schema.md`.

---

## Root Cause Coverage

| Root Cause | Skill |
|---|---|
| RC1: JS-Rendering | `render-gap-detector` |
| RC2: Missing llms.txt | `crawlability-probe` |
| RC3: No inner-page JSON-LD | `structured-data-auditor` |
| RC4: AI crawler misconfiguration | `crawlability-probe` |
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
| CEA-001–010: Passage-level content, answer capsules, AI-cliché slop | `content-extractability-auditor` |
| EEAT-001–007: E-E-A-T signals + Wikidata P856 | `eeeat-signal-checker` |
| TSEO-001–009: Technical SEO | `technical-seo-probe` |
| OG-001–008: OpenGraph / meta | `opengraph-meta-auditor` |
| RSL-001–005: RSL 1.0, 14 ADF endpoints | `rsl-licensing-checker` |
| GEO Score: 6-dimension + 5 per-engine scoring | `geo-score-aggregator` |

---

## Guardrails

- **Read-only**: no skill ever modifies a live site.
- **robots.txt respected**: the audit reads public HTTP responses only; it does not scrape disallowed content.
- **No authenticated actions**: no login, form submission, or destructive operations.
- **Rate-limited**: each script makes ≤ 15 HTTP requests per site, with a 12-second timeout per request.
- **No API keys required**: all checks use open HTTP probes or agent-native tools.
- **Runtime**: ~90 seconds for a typical site (10 scripts in parallel + report generation).
