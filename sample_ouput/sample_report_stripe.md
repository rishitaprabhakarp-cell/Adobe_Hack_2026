# Brand AI Readiness Audit — stripe.com

> **Site:** [stripe.com](https://stripe.com)  
> **Audited:** 2026-09-12  
> **Overall GEO Score:** 40/100 — Not GEO Ready  
> **Findings:** 2 Critical · 9 High · 9 Medium · 7 Low  

---

## GEO Dimension Scores

| Dimension | Score | Status |
|-----------|------:|--------|
| Crawlability | 18 | 🔴 Critical gap |
| Content Extractability | 7 | 🔴 Critical gap |
| Entity Clarity | 88 | ✅ On track |
| Schema Integrity | 52 | ⚠️ Developing |
| Off-Page Authority | 50 | ⚠️ Developing |
| Technical Foundation | 20 | 🔴 Critical gap |

## Per-Engine GEO Scores

| Engine | Score | Threshold |
|--------|------:|-----------|
| ChatGPT | 45 | ⚠️ 70 |
| Perplexity | 37 | ⚠️ 70 |
| Google AI Overviews | 40 | ⚠️ 70 |
| Gemini | 41 | ⚠️ 70 |
| Bing Copilot | 38 | ⚠️ 70 |

## 🚀 Projected Score After Fixes

> Fixing 11 CRITICAL/HIGH findings would raise your score from 40 to 67 (+27 pts)

| Metric | Current | After Fixes |
|--------|---------|-------------|
| Overall GEO Score | 40 | **67** |
| GEO Readiness | Not GEO Ready | **Developing** |
| Score Lift | — | **+27 pts** |


## 📈 Performance Metrics

**Citability Coverage:** 38% (6/16 passages extractable) — Needs Work
**Industry Benchmark:** Below median — ~31th percentile vs. Brand AI Readiness Audit — 10-site live benchmark (2026-09-12)

| Dimension | Your Score | Benchmark Median | Delta |
|-----------|-----------|------------------|-------|
| Crawlability | 18 | 72 | **-54** |
| Content Extractability | 7 | 48 | **-41** |
| Entity Clarity | 88 | 63 | **+25** |
| Schema Integrity | 52 | 44 | **+8** |
| Off-Page Authority | 50 | 55 | **-5** |
| Technical Foundation | 20 | 68 | **-48** |


## 🔢 Score Formula

> Overall = average of per-engine scores. Each engine weights the 6 dimensions differently.

| Engine | Formula | Score |
|--------|---------|-------|
| ChatGPT | `15% × Crawlability(18) + 20% × Content Extractability(7) + 25% × Entity Clarity(88) + 20% × Schema I` | **45** |
| Perplexity | `20% × Crawlability(18) + 25% × Content Extractability(7) + 15% × Entity Clarity(88) + 15% × Schema I` | **37** |
| Google AI Overviews | `15% × Crawlability(18) + 15% × Content Extractability(7) + 15% × Entity Clarity(88) + 25% × Schema I` | **40** |
| Gemini | `15% × Crawlability(18) + 18% × Content Extractability(7) + 18% × Entity Clarity(88) + 22% × Schema I` | **41** |
| Bing Copilot | `20% × Crawlability(18) + 20% × Content Extractability(7) + 15% × Entity Clarity(88) + 15% × Schema I` | **38** |


## 🗺 Prioritised Action Roadmap

| # | Dimension | Action | Effort | Est. Lift |
|---|-----------|--------|--------|-----------|
| 1 | Content Extractability | Add at minimum: JSON-LD dateModified, HTTP Last-Modified header, and visible 'La | `low` | +15 overall |
| 2 | Content Extractability | Open the page with a clear, self-contained statement of what the brand/product d | `low` | +8 overall |
| 3 | Content Extractability | Add source links or parenthetical citations to every statistic. | `low` | +8 overall |
| 4 | Content Extractability | Add a comparison or data table (with <th> headers, ≥3 rows) to key content pages | `medium` | +8 overall |
| 5 | Content Extractability | Add a direct 40–60 word answer paragraph immediately after each major H2/H3 head | `medium` | +8 overall |
| 6 | Content Extractability | Rewrite key H2 headings as questions to improve FAQ schema eligibility and AI di | `low` | +3 overall |
| 7 | Content Extractability | Add 'Last updated: [Month Year]' visible text near the top of content pages. | `low` | +3 overall |
| 8 | Crawlability | Deploy /.well-known/rsl.json with RSL 1.0 to declare content reuse terms for AI  | `low` | +8 overall |
| 9 | Crawlability | Deploy /.well-known/ai.txt and /ai/summary.json as minimum viable AI discovery. | `low` | +8 overall |
| 10 | Crawlability | Remove /admin, /account, /checkout and similar private paths from llms.txt immed | `low` | +8 overall |


---

## ● CRITICAL — 2 findings

### `FRESH-001` No machine-readable freshness signals present — AI treats content as undated

**Evidence:** 0/5 freshness signal layers found (HTTP Last-Modified, JSON-LD dateModified, OG article:modified_time, visible 'Last updated', meta date tag). AI defaults to treating undated content as stale. Lureon: 76% of citations go to content updated within 30 days.

**Action:** Add at minimum: JSON-LD dateModified, HTTP Last-Modified header, and visible 'Last updated: [Date]' text.
> Effort: `low` · Priority: `high`
> 📈 **Research lift:** +47% citation lift for fresh, multi-layer dated content (AuthorityTech 2026)

### `OG-001` No OpenGraph tags on homepage

**Evidence:** og:title, og:description, og:image all absent from homepage.

**Action:** Add og:title, og:description, og:image, og:type to every page template.
> Effort: `low` · Priority: `high`


---

## ▲ HIGH — 9 findings

### `CEA-001` No direct answer in first 80 words (/)

**Evidence:** First 80 words: "Start now Contact sales..."

**Action:** Open the page with a clear, self-contained statement of what the brand/product does.
> Effort: `low` · Priority: `high`

### `CEA-004` Statistics without source citations on /

**Evidence:** 10 uncited stats, 0 cited. Princeton KDD 2024: sourced stats → +40% AI citation.

**Action:** Add source links or parenthetical citations to every statistic.
> Effort: `low` · Priority: `high`

### `CEA-008` No HTML tables on / — missing highest-citation format

**Evidence:** Zero <table> elements found. Bigeye Agency + TryProfound: HTML data tables → +400% citation probability vs. prose. Comparison pages with semantic tables achieve 67% citation rate — highest single format ever measured.

**Action:** Add a comparison or data table (with <th> headers, ≥3 rows) to key content pages, especially feature/pricing/comparison pages.
> Effort: `medium` · Priority: `high`
> 📈 **Research lift:** +400% citation probability with data tables (Bigeye Agency + TryProfound, 2026)

### `CEA-015` Low answer-capsule ratio (0%) on /

**Evidence:** 0/5 H2/H3 sections have a 40+ word direct answer capsule. ChatGPT citation correlation: 72.4% of cited pages have ≥50%.

**Action:** Add a direct 40–60 word answer paragraph immediately after each major H2/H3 heading.
> Effort: `medium` · Priority: `high`
> 📈 **Research lift:** 72.4% of ChatGPT-cited pages have ≥50% answer capsule ratio (Cognism, 2026)

### `EEAT-010` Low Brand Authority Score (23/100) — weak AI trust signals

**Evidence:** Brand Authority Score: 23/100. Weak dimensions: reddit, review_platforms, social_profiles, wikidata.

**Action:** Prioritize: reddit, review_platforms — these dimensions have the most room for improvement in brand authority.
> Effort: `high` · Priority: `medium`

### `RC3-001` No Organization schema detected

**Evidence:** No Organization, Corporation, or LocalBusiness @type found in JSON-LD.

**Action:** Add Organization JSON-LD with name, url, logo, and sameAs to every page.
> Effort: `low` · Priority: `high`

### `RSL-001` No RSL 1.0 machine-readable license declaration

**Evidence:** /.well-known/rsl.json returns 404 and no <link rel='robots-standard-license'> in HTML.

**Action:** Deploy /.well-known/rsl.json with RSL 1.0 to declare content reuse terms for AI crawlers.
> Effort: `low` · Priority: `high`

### `RSL-003` Zero AI discovery endpoints present (0/14 checked)

**Evidence:** None of 14 AI discovery endpoints return HTTP 200.

**Action:** Deploy /.well-known/ai.txt and /ai/summary.json as minimum viable AI discovery.
> Effort: `low` · Priority: `high`

### `RSL-007` Private/admin URLs exposed in llms.txt (5 found)

**Evidence:** Admin or private paths in llms.txt: https://stripe.com/payments/checkout, https://docs.stripe.com/payments/checkout. These expose private infrastructure to AI crawlers.

**Action:** Remove /admin, /account, /checkout and similar private paths from llms.txt immediately.
> Effort: `low` · Priority: `high`


---

## ◆ MEDIUM — 9 findings

### `CEA-003` Low question-format heading ratio (7%) on /

**Evidence:** 2/30 H2/H3s are questions. Sample: ['what&#x27;s happening', 'how leading retailers unify customer experiences and drive growth.']

**Action:** Rewrite key H2 headings as questions to improve FAQ schema eligibility and AI direct-answer targeting.
> Effort: `low` · Priority: `medium`

### `CEA-014` No visible content freshness date marker on /

**Evidence:** No visible 'As of [date]' or 'Last updated' text marker found. Visible date text is the most human-readable of the 5 freshness signal layers.

**Action:** Add 'Last updated: [Month Year]' visible text near the top of content pages.
> Effort: `low` · Priority: `medium`

### `EEAT-002` No review platform links from homepage

**Evidence:** No G2, Capterra, Trustpilot, or other review platform links detected.

**Action:** Add G2/Trustpilot badges. SE Ranking 2026: review links → 3× citation probability.
> Effort: `low` · Priority: `medium`

### `IMG-001` 30 images missing alt text

**Evidence:** Images without alt attributes: https://images.stripeassets.com/fzn2n1nzq965/115d4Vd5LVAsqFGDR1ClAv/0ceb2c44a7a7, https://images.stripeassets.com/fzn2n1nzq965/vYmk6v8n7oDAwbDpwhjV6/846f9b3e21454, https://images.stripeassets.com/fzn2n1nzq965/m9HBEK464p46FeNIhs2PV/f5054a93c8a0a...

**Action:** Add descriptive alt text to all images. Alt text is an AI-indexable content signal.
> Effort: `low` · Priority: `medium`

### `RC17-001` No RSS/Atom feed found

**Evidence:** Checked /feed, /rss.xml, /atom.xml, /feed.xml — all returned non-200.

**Action:** Create an RSS/Atom feed. Perplexity and AI news agents index feeds for freshness.
> Effort: `low` · Priority: `medium`

### `RSL-005` llms.txt fails spec validation (2 issues)

**Evidence:** File size 63KB exceeds 50KB limit; Private/admin URLs exposed in llms.txt

**Action:** Fix llms.txt spec violations: ensure H1 present, use absolute links, verify no broken URLs.
> Effort: `low` · Priority: `medium`

### `SC-001` No Speakable schema

**Evidence:** site_has_speakable=False. No SpeakableSpecification markup found.

**Action:** Add Speakable schema to product descriptions and key content sections.
> Effort: `low` · Priority: `medium`

### `TSEO-007` Multiple H1 headings (2) on homepage

**Evidence:** h1_count=2. Multiple H1s dilute topical authority signal.

**Action:** Reduce to exactly one H1 per page.
> Effort: `low` · Priority: `medium`

### `TSEO-012` Last-Modified HTTP header absent

**Evidence:** No Last-Modified header in homepage HTTP response. Perplexity uses Last-Modified as primary freshness signal.

**Action:** Configure web server to emit Last-Modified header with accurate file modification date.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** Last-Modified present → +22% Perplexity freshness score (Ahrefs AI Indexing Guide 2026)


---

## ○ LOW — 7 findings

### `CEA-006` No key-takeaway / TL;DR box on /

**Evidence:** No TL;DR, summary, or key-highlight block detected.

**Action:** Add a 'Key highlights' box near top of content pages.
> Effort: `low` · Priority: `low`

### `EEAT-009` Weak Reddit brand presence

**Evidence:** No dedicated subreddit found, fewer than 3 organic mentions in Reddit search. Reddit is a top-cited source for Perplexity and ChatGPT.

**Action:** Engage authentically in relevant Reddit communities. A brand subreddit with r/{brand} > 500 subscribers boosts trust signals.
> Effort: `high` · Priority: `low`
> 📈 **Research lift:** Reddit mentions → +19% Perplexity citation probability (Profound AI, 2026)

### `OG-005` No Twitter Card meta tags

**Evidence:** No twitter:card, twitter:title, or twitter:description found.

**Action:** Add twitter:card=summary_large_image and twitter:title/description.
> Effort: `low` · Priority: `low`

### `RSL-002` No llms-full.txt companion file

**Evidence:** /llms-full.txt returns 404.

**Action:** Create /llms-full.txt with complete product documentation for LLM ingestion.
> Effort: `high` · Priority: `low`

### `RSL-004` IndexNow not implemented

**Evidence:** No IndexNow key found in HTML or robots.txt.

**Action:** Implement IndexNow to notify Bing/Perplexity on publish.
> Effort: `low` · Priority: `low`

### `RSL-006` No machine-readable alternate content links (RSL-006)

**Evidence:** No <link rel='alternate' type='text/markdown'> or text/plain found. AutoGEO ICLR 2026: pages with machine-readable alternates have 2.1× higher RAG retrieval rate.

**Action:** Add <link rel='alternate' type='text/markdown' href='/page.md'> to key content pages.
> Effort: `low` · Priority: `low`
> 📈 **Research lift:** +2.1× RAG retrieval rate (AutoGEO ICLR 2026)

### `RSL-008` No WebMCP agentic readiness signals

**Evidence:** /.well-known/mcp.json, /.well-known/webmcp, and /.well-known/agents.json all absent. No MCP card or agent tool HTML attributes detected.

**Action:** Deploy /.well-known/mcp.json with brand MCP card for Lighthouse 13.3.0+ agentic audits.
> Effort: `low` · Priority: `low`

---

## ✅ Passing Checks

10 skill scripts completed successfully with data.

---

*Generated by Brand AI Readiness Audit v2.0 · 2026-09-12 · 72 finding IDs across 6 GEO dimensions*