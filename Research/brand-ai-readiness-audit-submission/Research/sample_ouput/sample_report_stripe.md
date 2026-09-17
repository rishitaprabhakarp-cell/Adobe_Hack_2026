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

**Evidence:** og:title, og:description, and og:image are all absent from the homepage. OpenGraph tags are used by ChatGPT, Perplexity, and social AI surfaces to generate rich previews and brand descriptions. Without them, AI tools construct generic or inaccurate brand summaries.

**Action:** Add og:title, og:description, og:image, og:type to every page template.
> Effort: `low` · Priority: `high`
> 📈 **Research lift:** OpenGraph tags → AI tools use og:description as primary brand description source; absent = AI generates its own (often inaccurate)


---

## ▲ HIGH — 9 findings

### `CEA-001` No direct answer in first 80 words (/)

**Evidence:** First 80 words contain no direct, self-contained brand/product claim. Snippet: "Start now Contact sales...". AI engines extract the lede to populate brand descriptions in summaries.

**Action:** Open the page with a clear, self-contained statement of what the brand/product does.
> Effort: `low` · Priority: `high`
> 📈 **Research lift:** Answer-first structure → +17.3% citation rate (AuthorityTech 2026); top-of-page content = 44% of all AI citations (Surfer SEO 2026)

### `CEA-004` Statistics without source citations on /

**Evidence:** 10 uncited statistics found, only 0 have source attribution. Unsourced stats are deprioritised by citation engines — AI treats sourced claims as more authoritative and quotable.

**Action:** Add source links or parenthetical citations to every statistic.
> Effort: `low` · Priority: `high`
> 📈 **Research lift:** Sourced statistics → +40% AI citation probability (Princeton KDD 2024 GEO study)

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

**Evidence:** Brand Authority Score: 23/100 (scale: 0–100 weighted across Wikipedia, Reddit, review platforms, social profiles, Wikidata). Weak dimensions: reddit, review_platforms, social_profiles, wikidata. AI engines weight brand authority when selecting sources for brand-related queries.

**Action:** Prioritize: reddit, review_platforms — these dimensions have the most room for improvement in brand authority.
> Effort: `high` · Priority: `medium`
> 📈 **Research lift:** High brand authority → AI engines preferentially select brand as authoritative source; Wikipedia + Reddit alone account for 45% of composite score

### `RC3-001` No Organization schema detected

**Evidence:** No Organization, Corporation, or LocalBusiness @type found in JSON-LD. Without this, AI engines cannot reliably associate the site with a named brand entity — critical for Knowledge Graph inclusion.

**Action:** Add Organization JSON-LD with name, url, logo, and sameAs to every page.
> Effort: `low` · Priority: `high`
> 📈 **Research lift:** Organization schema → confirmed Knowledge Graph inclusion; Onely 5,000-site study: schema presence = +34% AI citation rate

### `RSL-001` No RSL 1.0 machine-readable license declaration

**Evidence:** /.well-known/rsl.json returns 404 and no <link rel='robots-standard-license'> tag found in HTML. Without RSL, AI crawlers cannot determine permitted reuse terms — many default to 'no training' or skip the domain entirely.

**Action:** Deploy /.well-known/rsl.json with RSL 1.0 to declare content reuse terms for AI crawlers.
> Effort: `low` · Priority: `high`
> 📈 **Research lift:** RSL 1.0 declaration → AI crawlers recognise explicit reuse permission; absence = conservative default = reduced indexing likelihood

### `RSL-003` Zero AI discovery endpoints present (0/14 checked)

**Evidence:** None of 14 standard AI discovery endpoints return HTTP 200 (checked: /.well-known/ai.txt, /ai/summary.json, /llms.txt, /brand.txt, /identity.json, and 9 others). These endpoints are the primary way AI agents discover brand facts, product descriptions, and authorised content.

**Action:** Deploy /.well-known/ai.txt and /ai/summary.json as minimum viable AI discovery.
> Effort: `low` · Priority: `high`
> 📈 **Research lift:** AI discovery endpoints → brand facts served directly to AI agents; sites with ≥3 endpoints see +28% brand mention accuracy (Profound AI, 2026)

### `RSL-007` Private/admin URLs exposed in llms.txt (5 found)

**Evidence:** 5 private or admin-area URLs found in llms.txt: https://stripe.com/payments/checkout, https://docs.stripe.com/payments/checkout. Exposing /admin, /checkout, /account paths invites AI crawlers into authenticated areas and leaks internal infrastructure details.

**Action:** Remove /admin, /account, /checkout and similar private paths from llms.txt immediately.
> Effort: `low` · Priority: `high`
> 📈 **Research lift:** Clean llms.txt = AI crawlers only index intended public content; private URL exposure = security risk + crawler misdirection


---

## ◆ MEDIUM — 9 findings

### `CEA-003` Low question-format heading ratio (7%) on /

**Evidence:** 2/30 H2/H3 headings are phrased as questions. Sample: ['what&#x27;s happening', 'how leading retailers unify customer experiences and drive growth.']. Question-format headings directly match conversational AI query patterns.

**Action:** Rewrite key H2 headings as questions to improve FAQ schema eligibility and AI direct-answer targeting.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** Question-format headings → FAQPage schema eligibility; FAQ schema pages = 2.7× more likely to appear in AI Overviews (Onely 2026)

### `CEA-014` No visible content freshness date marker on /

**Evidence:** No visible 'As of [date]', 'Last updated', or 'Published' text marker found on page. Visible date text is the most human-readable of the 5 freshness signal layers and acts as a reader trust signal alongside machine-readable metadata.

**Action:** Add 'Last updated: [Month Year]' visible text near the top of content pages.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** Visible freshness date = human-readable layer 5 of 5-layer freshness sync; Lureon: 76% of citations go to content updated within 30 days

### `EEAT-002` No review platform links from homepage

**Evidence:** No G2, Capterra, Trustpilot, G2Crowd, or similar review platform links detected in homepage HTML. Third-party review signals are a top E-E-A-T corroboration source for AI citation engines.

**Action:** Add G2/Trustpilot review badges with links to footer. Even a single third-party review platform link signals independent validation.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** Review platform links → 3× AI citation probability (SE Ranking 2026 E-E-A-T study)

### `IMG-001` 30 images missing alt text

**Evidence:** 30 images have no alt attribute. Examples: https://images.stripeassets.com/fzn2n1nzq965/115d4Vd5LVAsqFGDR1ClAv/0ceb2c44a7a7, https://images.stripeassets.com/fzn2n1nzq965/vYmk6v8n7oDAwbDpwhjV6/846f9b3e21454, https://images.stripeassets.com/fzn2n1nzq965/m9HBEK464p46FeNIhs2PV/f5054a93c8a0a.... Alt text is the only machine-readable content signal for images; absent = invisible to AI crawlers.

**Action:** Add descriptive alt text to all images. Alt text is an AI-indexable content signal.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** Alt text present → images indexed as content by AI crawlers; each image = additional citation surface

### `RC17-001` No RSS/Atom feed found

**Evidence:** Checked /feed, /rss.xml, /atom.xml, /feed.xml — all returned non-200. Perplexity, Bing Copilot, and AI news agents actively consume RSS/Atom feeds to discover and rank fresh content.

**Action:** Create an RSS/Atom feed. Perplexity and AI news agents index feeds for freshness.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** RSS feeds indexed by Perplexity/Bing AI for freshness signals — absence = stale content perception

### `RSL-005` llms.txt fails spec validation (2 issues)

**Evidence:** llms.txt spec violations (2 issues): File size 63KB exceeds 50KB limit; Private/admin URLs exposed in llms.txt. Malformed llms.txt causes AI parsers to reject or partially parse the file, reducing the brand information available to AI agents.

**Action:** Fix llms.txt spec violations: ensure H1 present, use absolute links, verify no broken URLs.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** Spec-compliant llms.txt = fully parsed by AI agents; non-compliant = partial or no ingestion

### `SC-001` No Speakable schema

**Evidence:** site_has_speakable=False. No SpeakableSpecification markup found. Speakable markup tells Google and voice assistants exactly which passages to read aloud or surface in AI Overview snippets.

**Action:** Add Speakable schema to product descriptions and key content sections.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** Speakable markup → eligible for Google AI Overviews voice-snippet selection (Google Search Central, 2026)

### `TSEO-007` Multiple H1 headings (2) on homepage

**Evidence:** h1_count=2. Multiple H1s dilute topical authority signal — AI crawlers use the H1 to identify the primary topic of a page; multiple H1s send conflicting signals about what the page is about.

**Action:** Reduce to exactly one H1 per page.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** Single H1 = unambiguous primary topic signal for AI crawlers; multiple H1s = topic dilution, lower topical authority score

### `TSEO-012` Last-Modified HTTP header absent

**Evidence:** No Last-Modified header in homepage HTTP response. Perplexity uses Last-Modified as primary freshness signal.

**Action:** Configure web server to emit Last-Modified header with accurate file modification date.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** Last-Modified present → +22% Perplexity freshness score (Ahrefs AI Indexing Guide 2026)


---

## ○ LOW — 7 findings

### `CEA-006` No key-takeaway / TL;DR box on /

**Evidence:** No TL;DR, key highlights, or summary box detected. These compact blocks are prime AI extraction targets — they concentrate citable facts in a scannable format AI engines prefer for quick answers.

**Action:** Add a 'Key highlights' box near top of content pages.
> Effort: `low` · Priority: `low`
> 📈 **Research lift:** Summary/TL;DR boxes → high AI extraction rate; compact fact-dense blocks preferred by ChatGPT and Perplexity for answer generation

### `EEAT-009` Weak Reddit brand presence

**Evidence:** No dedicated subreddit found, fewer than 3 organic mentions in Reddit search. Reddit is a top-cited source for Perplexity and ChatGPT.

**Action:** Engage authentically in relevant Reddit communities. A brand subreddit with r/{brand} > 500 subscribers boosts trust signals.
> Effort: `high` · Priority: `low`
> 📈 **Research lift:** Reddit mentions → +19% Perplexity citation probability (Profound AI, 2026)

### `OG-005` No Twitter Card meta tags

**Evidence:** No twitter:card, twitter:title, or twitter:description tags found. Twitter Cards are consumed by Grok/xAI and social AI surfaces to generate previews; their absence reduces brand surface area on AI-powered social platforms.

**Action:** Add twitter:card=summary_large_image and twitter:title/description.
> Effort: `low` · Priority: `low`
> 📈 **Research lift:** Twitter Cards consumed by Grok/xAI for brand context; adds brand discovery surface on X AI features

### `RSL-002` No llms-full.txt companion file

**Evidence:** /llms-full.txt returns 404. The llms-full.txt companion file provides the complete, unabridged version of all content — ideal for LLMs that need full context rather than the summary llms.txt. Its absence limits the depth of brand knowledge LLMs can ingest in a single fetch.

**Action:** Create /llms-full.txt with complete product documentation, pricing, and brand narrative for LLM ingestion.
> Effort: `high` · Priority: `low`
> 📈 **Research lift:** llms-full.txt enables LLMs to ingest comprehensive brand documentation in one request — deeper context = more accurate brand representation

### `RSL-004` IndexNow not implemented

**Evidence:** No IndexNow key found in HTML meta tags or robots.txt. IndexNow is the real-time publish-notification protocol used by Bing, Perplexity, and Yandex — without it, new content may take days to be discovered.

**Action:** Implement IndexNow to notify Bing/Perplexity immediately on content publish or update.
> Effort: `low` · Priority: `low`
> 📈 **Research lift:** IndexNow → content indexed by Bing/Perplexity within minutes of publish vs. days without it (Microsoft Bing Webmaster, 2025)

### `RSL-006` No machine-readable alternate content links (RSL-006)

**Evidence:** No <link rel='alternate' type='text/markdown'> or text/plain found. AutoGEO ICLR 2026: pages with machine-readable alternates have 2.1× higher RAG retrieval rate.

**Action:** Add <link rel='alternate' type='text/markdown' href='/page.md'> to key content pages.
> Effort: `low` · Priority: `low`
> 📈 **Research lift:** +2.1× RAG retrieval rate (AutoGEO ICLR 2026)

### `RSL-008` No WebMCP agentic readiness signals

**Evidence:** /.well-known/mcp.json, /.well-known/webmcp, and /.well-known/agents.json all absent. No MCP card or agent tool HTML attributes detected. WebMCP readiness determines whether AI agents (Claude, GPT-4 with Plugins, Lighthouse) can discover and use the site's capabilities programmatically.

**Action:** Deploy /.well-known/mcp.json with brand MCP card for Lighthouse 13.3.0+ agentic audits.
> Effort: `low` · Priority: `low`
> 📈 **Research lift:** WebMCP readiness → AI agents can discover and invoke brand capabilities; future-proofing for agentic web (Anthropic MCP spec, 2025)

---

## ✅ Passing Checks

10 skill scripts completed successfully with data.

---

*Generated by Brand AI Readiness Audit v2.0 · 2026-09-12 · 72 finding IDs across 6 GEO dimensions*