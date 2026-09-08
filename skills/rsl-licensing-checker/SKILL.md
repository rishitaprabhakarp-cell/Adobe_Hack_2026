---
name: rsl-licensing-checker
description: Checks for RSL 1.0 (Robots Standard License) machine-readable AI content licensing declarations, ai.txt well-known endpoints, llms-full.txt companion files, and IndexNow ping support. These are the newest (December 2025+) AI discoverability standards. RSL 1.0 lets sites declare which AI training and citation uses are permitted. Use when auditing a site's compliance with emerging AI content licensing standards.
license: MIT
allowed-tools: web_fetch, run_script
---

# RSL Licensing & AI Standards Checker

## When to use

Called by `audit-orchestrator` as sub-skill #12. Checks the newest AI web standards (2025–2026). These are LOW severity by default (standards are new) but HIGH strategic value for forward-looking brands.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL with `https://` prefix |

## Procedure

### Step 1 — Run the RSL/standards script

```bash
python skills/rsl-licensing-checker/scripts/rsl_check.py <url>
```

### Step 2 — Generate findings

#### RSL-1 — RSL 1.0 declaration absent

RSL (Robots Standard License) 1.0 (December 2025) is a machine-readable content licensing standard. Sites declare it via:
- `<link rel="robots-standard-license" href="/rsl.json">` in `<head>`
- Or at `/.well-known/rsl.json`

Check `rsl_declaration`:

| Condition | Severity |
|-----------|----------|
| No RSL declaration and no robots.txt AI bot section | MEDIUM |
| No RSL declaration but robots.txt has explicit AI bot rules | LOW |

Finding ID: `RSL-001`
Evidence: RSL link tag found (yes/no), `/.well-known/rsl.json` status.
Mark `proactive: true` — this is an emerging standard, not a current defect.

Suggested action: Add `/.well-known/rsl.json` with `{"license":"CC-BY-4.0","ai_training":"allowed","ai_citation":"allowed","ai_retrieval":"allowed"}` as a starting point. Adjust AI training permission to match policy.

#### RSL-2 — llms-full.txt companion file absent

`llms-full.txt` is a companion to `llms.txt` — it contains the full text of key pages for AI consumers that want richer context without crawling each page individually.

Check `llms_full_txt`:

| Condition | Severity |
|-----------|----------|
| `llms.txt` present but no `llms-full.txt` | LOW |
| Neither `llms.txt` nor `llms-full.txt` present | (covered by crawlability-probe) |

Finding ID: `RSL-002`
Evidence: `llms-full.txt` HTTP status.
Mark `proactive: true`.

#### RSL-3 — AI discovery endpoints absent (standard + ADF 2026)

The script checks **14 endpoints** across 3 tiers:

**Tier 1 — Core well-known paths** (highest AI agent adoption):
- `/.well-known/ai.txt` — AI identity + usage declaration
- `/.well-known/ai.json` — machine-readable version
- `/.well-known/rsl.json` — RSL license declaration

**Tier 2 — AI API surface** (GEO Optimizer "AI Discovery" signals):
- `/ai/summary.json` — structured site summary
- `/ai/faq.json` — structured FAQ for AI agents
- `/ai/service.json` — structured service/product description
- `/ai/manifest.json` — AI manifest

**Tier 3 — ADF 2026 extensions** (Autonomous Discovery Format, emerging standard):
- `/brand.txt` — brand identity in plain text for LLM ingestion
- `/identity.json` — machine-readable brand identity card
- `/faq-ai.txt` — plain text FAQ optimized for AI extraction
- `/ai.json` — unified AI context file
- `/.well-known/brand.json` — well-known brand card
- `/.well-known/llms-context.txt` — extended LLM context beyond llms.txt

| Condition | Severity |
|-----------|----------|
| No Tier 1 endpoints present | HIGH |
| Tier 1 present but no Tier 2 or 3 endpoints | MEDIUM |
| Only `/.well-known/ai.txt` exists, all others absent | LOW |

Finding ID: `RSL-003`
Evidence: HTTP status for each endpoint, grouped by tier. Note `ai_discovery_endpoint_count` total.
Suggested action: Start with `/.well-known/ai.txt` and `/ai/summary.json`, then add `/brand.txt` (simplest ADF implementation).

#### RSL-4 — IndexNow not implemented

IndexNow is a ping protocol that notifies Bing, Yandex, and partnered AI engines instantly when content changes. Perplexity (freshness-sensitive) benefits from IndexNow-pinging sites.

Check `indexnow_key`:
- Present at `/<api-key>.txt` or referenced in `robots.txt`

| Condition | Severity |
|-----------|----------|
| IndexNow not implemented | LOW |

Finding ID: `RSL-004`
Evidence: IndexNow key file check result.
Mark `proactive: true`.

#### RSL-5 — llms.txt deep validation

Deep-validate the structure of an existing `llms.txt` against the full spec:

| Check | Severity if failing |
|-------|-------------------|
| H1 present (required) | HIGH |
| H1 contains a URL (invalid — should be project name only) | MEDIUM |
| Blockquote summary present (recommended) | LOW |
| All H2 sections contain only list items with markdown links | MEDIUM |
| Any linked URL returns 404 | HIGH |
| All URLs in file are absolute (relative URLs break off-site consumers) | MEDIUM |
| File size > 50KB (AI consumers truncate aggressively) | MEDIUM |
| `## Optional` section used for secondary links | LOW (advisory) |
| llms.txt URLs are a superset of sitemap URLs (no "secret" pages) | LOW |

Finding ID: `RSL-005`
Evidence: spec compliance check results per rule.

## Output

```json
{
  "skill": "rsl-licensing-checker",
  "findings": []
}
```
