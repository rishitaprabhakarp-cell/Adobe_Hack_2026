# Testing Guide — Brand AI Readiness Audit Marketplace

## Overview

This guide covers:
1. [Test site selection strategy](#1-test-site-selection-strategy)
2. [Manual testing walkthrough](#2-manual-testing-walkthrough)
3. [Automated test runner script](#3-automated-test-runner)
4. [Per-skill test cases with expected outputs](#4-per-skill-test-cases)
5. [Grading your audit results](#5-grading-audit-results)
6. [Common failure modes and debugging](#6-debugging)

---

## 1. Test Site Selection Strategy

To properly test this marketplace, you need sites across a spectrum of AI readiness. Use these 5 categories:

### Category A — "AI-Invisible" sites (expect CRITICAL/HIGH findings)

Sites that will trigger the most findings — good for verifying detection logic:

| Site | Why useful |
|------|-----------|
| `https://www.reddit.com` | Complex JS app; GPTBot was blocked until 2025; now partially allowed |
| Any small local business site | Typically no JSON-LD, no llms.txt, often JS-rendered |
| `https://www.craigslist.org` | Intentionally bare HTML, no schema, no llms.txt |
| A Wix/Squarespace-built site | Often has thin schema, may have SPA-style rendering |

### Category B — "Partially Optimized" sites (expect MED findings)

Sites with some GEO work done but gaps:

| Site | Why useful |
|------|-----------|
| `https://linear.app` | Good schema, has llms.txt; test for completeness |
| `https://vercel.com` | Strong technical SEO; test entity/E-E-A-T layer |
| `https://supabase.com` | Developer docs; test for speakable, FAQ schema |
| `https://tailwindcss.com` | Excellent content structure; test for entity sameAs |

### Category C — "AI-Optimized" sites (expect mostly LOW/proactive findings)

Benchmark sites that should score high:

| Site | Why useful |
|------|-----------|
| `https://openai.com` | Best-in-class GEO implementation; high baseline |
| `https://anthropic.com` | Good entity signals, llms.txt; good benchmark |
| `https://stripe.com` | Excellent structured data, docs, E-E-A-T |
| `https://www.nytimes.com` | High E-E-A-T, news schema; test freshness checks |

### Category D — "Edge case" sites (test robustness)

| Site | Why useful |
|------|-----------|
| `https://example.com` | Minimal HTML; should return near-zero findings without errors |
| `https://httpstat.us/404` | Test error handling for unreachable sites |
| A paywalled site | Test RC13 (paywall without isAccessibleForFree schema) |
| A multilingual site | Test RC15, hreflang checks |

### Category E — Your own test site (recommended)

Create a simple 3-page test site you control:
- One page with perfect GEO implementation
- One page with deliberately broken robots.txt
- One SPA-style page with minimal static content

Use GitHub Pages (free): `https://<username>.github.io/<repo>` — easily modifiable.

---

## 2. Manual Testing Walkthrough

### Prerequisites

```bash
# Clone and set up
cd /Users/pawankumar/Adobe_Hack_2026
pip install requests

# Verify Python 3.9+
python3 --version
```

### Step-by-step manual test for a single URL

#### Test 1: Crawlability Probe

```bash
python3 skills/crawlability-probe/scripts/crawlability_check.py https://linear.app 2>/dev/null | python3 -m json.tool
```

**What to verify**:
- `robots_txt.bots` — all 27 bots should be listed
- `llms_txt.starts_with_hash` — should be `true` for a site with valid llms.txt
- `llms_txt.word_count` — should be > 50 for a meaningful file
- `sitemap` — should have `status: 200` and `lastmod_count > 0`
- `feeds` — at least one feed should return 200

**Expected output shape**:
```json
{
  "site": "linear.app",
  "robots_txt": { "status": 200, "bots": { "GPTBot": { "fully_blocked": false }, ... } },
  "llms_txt": { "status": 200, "starts_with_hash": true, "word_count": 120 },
  "sitemap": [{ "status": 200, "lastmod_count": 45 }],
  "feeds": [{ "status": 404 }, ...],
  "ai_endpoints": [{ "path": "/.well-known/ai.txt", "status": 404 }]
}
```

#### Test 2: Render Gap Detector

```bash
python3 skills/render-gap-detector/scripts/render_check.py https://stripe.com 2>/dev/null | python3 -m json.tool
```

**What to verify**:
- `pages[0].classification` — should be `raw_html_works` for a well-built site
- `pages[0].word_count` — should be ≥ 100 for non-SPA pages
- `pages[0].has_h1` — should be `true`
- `pages[0].spa_shell_detected` — should be `false` for SSR sites
- Test a known SPA (e.g., `https://app.some-spa.com`) — should return `browser_only`

**Red flags to look for**:
```json
{
  "classification": "browser_only",
  "word_count": 3,
  "spa_shell_markers": ["<div id=\"root\">"],
  "js_framework_signals": [{"signal": "__NEXT_DATA__", "framework": "Next.js"}]
}
```
→ This means RC1 CRITICAL finding should be emitted.

#### Test 3: Structured Data Auditor

```bash
python3 skills/structured-data-auditor/scripts/schema_audit.py https://www.nytimes.com 2>/dev/null | python3 -m json.tool | head -80
```

**What to verify**:
- `pages[0].schema_types` — should include `Article`, `NewsArticle`, `Organization`
- `pages[0].schema_richness` — field counts should be > 5 for rich schema
- `pages[0].freshness_dates` — `dateModified` should be recent
- `pages[0].images_missing_alt` — ideally empty or few

#### Test 4: Entity Corroboration Checker

```bash
python3 skills/entity-corroboration-checker/scripts/entity_check.py https://stripe.com 2>/dev/null | python3 -m json.tool
```

**What to verify**:
- `brand_name` — correctly extracted as "Stripe"
- `wikidata.found` — should be `true` (Stripe has a Wikidata entry)
- `same_as_links` — should include wikidata/linkedin links
- `entity_collision_risk.high_risk` — should be `false` for unique brand names

#### Test 5: Content Extractability Auditor

```bash
python3 skills/content-extractability-auditor/scripts/content_check.py https://openai.com 2>/dev/null | python3 -m json.tool
```

**What to verify**:
- `above_fold.has_direct_claim` — should be `true`
- `above_fold.has_unresolved_pronouns` — ideally `false`
- `headings.question_format_count` — should be > 0
- `statistics.total_statistics` — well-optimized sites have stats with citations

#### Test 6: Technical SEO Probe

```bash
python3 skills/technical-seo-probe/scripts/technical_check.py https://vercel.com 2>/dev/null | python3 -m json.tool
```

**What to verify**:
- `https_redirect.redirects_to_https` — should be `true`
- `meta_robots.has_noindex` — should be `false`
- `meta_robots.has_nosnippet` — should be `false`
- `heading_hierarchy.multiple_h1` — should be `false`
- `redirect_chain.hop_count` — should be ≤ 2
- `broken_links.broken_count` — should be 0

#### Test 7: OpenGraph Meta Auditor

```bash
python3 skills/opengraph-meta-auditor/scripts/og_audit.py https://github.com 2>/dev/null | python3 -m json.tool | head -60
```

**What to verify**:
- `og_description` — should be non-empty, 50-160 chars
- `og_image_validation.valid` — should be `true` (image returns 200)
- `meta_description_quality.optimal_length` — should be `true`
- `duplicate_meta_descriptions` — should be `false`

#### Test 8: RSL Licensing Checker

```bash
python3 skills/rsl-licensing-checker/scripts/rsl_check.py https://anthropic.com 2>/dev/null | python3 -m json.tool
```

**What to verify**:
- `llms_txt_deep_validation.has_h1` — should be `true`
- `llms_txt_deep_validation.passes_spec` — should be `true` for well-formed files
- `ai_discovery_endpoint_count` — how many of the 7 endpoints exist?
- `rsl_declaration.has_rsl` — most sites will return `false` (new standard)

---

## 3. Automated Test Runner

Use this script to run all helper scripts against a URL and collect results:

```bash
#!/bin/bash
# run_audit.sh — Run all skill scripts against a URL
# Usage: bash run_audit.sh https://example.com

URL="${1:-https://example.com}"
TIMESTAMP=$(date -u +"%Y%m%dT%H%M%SZ")
OUTPUT_DIR="audit_results/${TIMESTAMP}"
mkdir -p "$OUTPUT_DIR"

echo "=== Brand AI Readiness Audit ==="
echo "Target: $URL"
echo "Output: $OUTPUT_DIR"
echo "================================"

SCRIPTS=(
  "crawlability-probe/scripts/crawlability_check.py"
  "render-gap-detector/scripts/render_check.py"
  "structured-data-auditor/scripts/schema_audit.py"
  "entity-corroboration-checker/scripts/entity_check.py"
  "engagement-analyzer/scripts/engagement_check.py"
  "content-extractability-auditor/scripts/content_check.py"
  "eeeat-signal-checker/scripts/eeeat_check.py"
  "technical-seo-probe/scripts/technical_check.py"
  "opengraph-meta-auditor/scripts/og_audit.py"
  "rsl-licensing-checker/scripts/rsl_check.py"
)

TOTAL=0
ERRORS=0

for script in "${SCRIPTS[@]}"; do
  skill_name=$(dirname "$script" | cut -d'/' -f1)
  output_file="$OUTPUT_DIR/${skill_name}.json"

  echo -n "Running $skill_name... "

  if python3 "skills/$script" "$URL" 2>/dev/null > "$output_file"; then
    # Validate it's valid JSON
    if python3 -m json.tool "$output_file" > /dev/null 2>&1; then
      echo "OK ✓"
      TOTAL=$((TOTAL + 1))
    else
      echo "INVALID JSON ✗"
      ERRORS=$((ERRORS + 1))
    fi
  else
    echo "SCRIPT ERROR ✗"
    ERRORS=$((ERRORS + 1))
  fi
done

echo ""
echo "Results: $TOTAL/$((TOTAL + ERRORS)) scripts succeeded"
echo "Output directory: $OUTPUT_DIR"
echo ""
echo "To view a result:"
echo "  cat $OUTPUT_DIR/crawlability-probe.json | python3 -m json.tool | head -50"
```

Save as `run_audit.sh` and run:
```bash
chmod +x run_audit.sh
./run_audit.sh https://linear.app
```

---

## 4. Per-Skill Test Cases

### Expected findings for known-bad sites

#### Site: Any plain HTML site with no schema (e.g., craigslist.org)

| Skill | Expected Findings |
|-------|------------------|
| `crawlability-probe` | RC2-001 (no llms.txt) HIGH, RC14-001 (no AI endpoints) LOW, RC19-001 (sitemap absent) HIGH |
| `render-gap-detector` | No findings (full HTML) |
| `structured-data-auditor` | RC3-001 (no inner-page JSON-LD) HIGH, RC10-001 (no speakable) MED |
| `entity-corroboration-checker` | RC5-001 (no sameAs) MED |
| `content-extractability-auditor` | CEA-002 (no question headings) HIGH, CEA-003 (no stats) MED |
| `technical-seo-probe` | TSEO-002 (no canonical) LOW |

#### Site: A JS-only SPA (no SSR)

| Skill | Expected Findings |
|-------|------------------|
| `render-gap-detector` | RC1-001 CRITICAL (browser_only, < 20 words, SPA shell detected) |
| `structured-data-auditor` | RC3-001 HIGH (no JSON-LD extractable from raw HTML) |
| `technical-seo-probe` | TSEO-005 (no H1 in raw HTML) HIGH |

#### Site: Well-optimized SaaS (e.g., stripe.com)

| Skill | Expected Findings (mostly LOW or proactive) |
|-------|--------------------------------------|
| `crawlability-probe` | RC17-001 LOW (no RSS feed) |
| `render-gap-detector` | No findings |
| `entity-corroboration-checker` | RC6-001 LOW (Wikidata found but sameAs not in JSON-LD) |
| `rsl-licensing-checker` | RSL-001 LOW proactive (no RSL 1.0) |

### Validation checklist for each skill

Run this checklist after each script execution:

```
[ ] Script exits with code 0
[ ] Output is valid JSON (python3 -m json.tool validates it)
[ ] `site` field matches the domain
[ ] `probed_at` is a valid ISO-8601 timestamp
[ ] No Python tracebacks in stderr
[ ] No hardcoded test data (results vary per URL)
[ ] At least 1 key data field is populated (not all nulls)
```

---

## 5. Grading Audit Results

### How to manually grade an audit

1. **Run all scripts** against a test site using `run_audit.sh`
2. **For each script output**, compare the raw data to the SKILL.md thresholds
3. **Map each threshold breach** to its finding ID and severity
4. **Construct the findings array** manually for 2-3 sites
5. **Check for false positives**: each finding should have concrete evidence — not assumptions

### Quality scoring rubric (for self-assessment)

| Criterion | How to check | Pass threshold |
|-----------|-------------|----------------|
| Detection accuracy | Run against a known-bad site; compare findings to manually observed issues | ≥ 80% of actual problems detected |
| False positive rate | Run against a known-good site; count spurious HIGH/CRITICAL findings | ≤ 1 false HIGH per audit |
| Evidence quality | Each finding's `evidence` field should contain specific data, not generic statements | 100% of findings have specific URL/count/value |
| Suggested action quality | Each `suggested_action` should name a specific fix, not "improve your SEO" | 100% specific |
| Runtime | Full audit should complete in < 5 minutes on a standard connection | < 300 seconds |

### GEO score sanity checks

After running `geo-score-aggregator`:
- A site with CRITICAL findings should score < 50%
- A well-known tech brand (Stripe, Linear, Vercel) should score 60–80%
- A site with a perfect llms.txt + Organization JSON-LD + no JS rendering should score ≥ 75%
- `geo_ready: false` should be the output for any site with ≥ 2 HIGH findings

---

## 6. Debugging

### Script exits with no output

```bash
# Run with stderr visible (remove 2>/dev/null)
python3 skills/crawlability-probe/scripts/crawlability_check.py https://example.com
```

Common causes:
- Missing `requests` library → `pip install requests`
- URL without scheme → pass `https://example.com` not `example.com`
- Site behind Cloudflare → try a different test URL

### JSON parse error

```bash
python3 skills/render-gap-detector/scripts/render_check.py https://example.com | python3 -m json.tool
```

If you see `json.decoder.JSONDecodeError`, the script wrote non-JSON to stdout (likely a Python traceback mixed in). Run without `2>/dev/null` to see the full error.

### Timeout errors

All scripts have `TIMEOUT = 12` seconds per request. For slow sites:
- Edit the `TIMEOUT` constant in the script
- Or use a faster test URL (e.g., `https://example.com` is instant)

### All findings are LOW severity on a known-bad site

This usually means the script is working correctly but the SKILL.md's threshold logic hasn't been applied yet (the script provides raw data; the agent applies the thresholds). When testing scripts standalone, manually compare `script_output.key` values against the SKILL.md threshold tables.

### Entity check returns wrong brand name

The brand extraction priority is: Organization JSON-LD → og:site_name → `<title>` first segment → domain. For sites with complex titles (e.g., "Buy Shoes | BigBrand.com"), the title extraction may return "Buy Shoes". In this case, pass `brand_name` directly to the orchestrator.

### Wikidata lookup returns "partial_match" for a well-known brand

Wikidata search is fuzzy. If `wikidata.found = false` but `wikidata.partial_match` contains the correct entity, the brand has a Wikidata entry but the label doesn't exactly match what's on the site. This is itself a finding (name inconsistency between site and Wikidata).

---

## 7. Reference: All Finding IDs

| ID prefix | Skill | Description |
|-----------|-------|-------------|
| RC1-RC23 | Various (original 7 skills) | Original root causes |
| CEA-001 to 008 | content-extractability-auditor | Passage-level content |
| EEAT-001 to 006 | eeeat-signal-checker | E-E-A-T signals |
| TSEO-001 to 009 | technical-seo-probe | Technical SEO |
| OG-001 to 008 | opengraph-meta-auditor | OpenGraph/meta |
| RSL-001 to 005 | rsl-licensing-checker | RSL/AI standards |
| CITE-001 to 004 | llm-citation-tester | LLM citation |
| ORCH-ERR-* | audit-orchestrator | Sub-skill error |

---

## 8. Recommended Test Run Sequence

```bash
# 1. Quickest sanity check (< 30 seconds)
python3 skills/crawlability-probe/scripts/crawlability_check.py https://example.com 2>/dev/null | python3 -m json.tool | head -20

# 2. Full script battery against a well-known site
./run_audit.sh https://stripe.com

# 3. Test a known-bad site (no schema, no llms.txt)
./run_audit.sh https://craigslist.org

# 4. Test edge case — unreachable site
./run_audit.sh https://httpstat.us/503

# 5. Compare two sites side-by-side
diff <(./run_audit.sh https://stripe.com 2>/dev/null) <(./run_audit.sh https://example.com 2>/dev/null)
```

### Expected timeline for a full audit

| Phase | Sub-skills | Estimated time |
|-------|-----------|----------------|
| Scripts (parallel) | All 10 Python scripts | 20–60 seconds |
| Agent web_search | llm-citation-tester + eeeat off-page | 30–60 seconds |
| Agent judgment | Applying thresholds, writing findings | 60–120 seconds |
| geo-score-aggregator | Scoring + roadmap | 10–20 seconds |
| **Total** | | **~2–4 minutes** |

---

*Last updated: September 2026. Based on research from Princeton KDD 2024, Directive Consulting 2026, Onely 2026, and open-source projects: geo-optimizer-skill (Auriti-Labs), ultimate-seo-geo (mykpono), geo-audit-skill (zilisrikle), ai-seo-auditor (ngstcf).*
