# Brand AI Readiness Audit — www.adobe.com

> **Site:** [www.adobe.com](https://www.adobe.com)  
> **Audited:** 2026-09-12  
> **Overall GEO Score:** 46/100 — Not GEO Ready  
> **Findings:** 1 Critical · 5 High · 12 Medium · 5 Low  

---

## GEO Dimension Scores

| Dimension | Score | Status |
|-----------|------:|--------|
| Crawlability | 31 | 🔴 Critical gap |
| Content Extractability | 31 | 🔴 Critical gap |
| Entity Clarity | 88 | ✅ On track |
| Schema Integrity | 64 | ⚠️ Developing |
| Off-Page Authority | 23 | 🔴 Critical gap |
| Technical Foundation | 27 | 🔴 Critical gap |

## Per-Engine GEO Scores

| Engine | Score | Threshold |
|--------|------:|-----------|
| ChatGPT | 50 | ⚠️ 70 |
| Perplexity | 43 | ⚠️ 70 |
| Google AI Overviews | 46 | ⚠️ 70 |
| Gemini | 47 | ⚠️ 70 |
| Bing Copilot | 42 | ⚠️ 70 |

## 🚀 Projected Score After Fixes

> Fixing 6 CRITICAL/HIGH findings would raise your score from 46 to 61 (+15 pts)

| Metric | Current | After Fixes |
|--------|---------|-------------|
| Overall GEO Score | 46 | **61** |
| GEO Readiness | Not GEO Ready | **Developing** |
| Score Lift | — | **+15 pts** |


## 📈 Performance Metrics

**Industry Benchmark:** Below median — ~40th percentile vs. Brand AI Readiness Audit — 10-site live benchmark (2026-09-12)

| Dimension | Your Score | Benchmark Median | Delta |
|-----------|-----------|------------------|-------|
| Crawlability | 31 | 72 | **-41** |
| Content Extractability | 31 | 48 | **-17** |
| Entity Clarity | 88 | 63 | **+25** |
| Schema Integrity | 64 | 44 | **+20** |
| Off-Page Authority | 23 | 55 | **-32** |
| Technical Foundation | 27 | 68 | **-41** |


## 🔢 Score Formula

> Overall = average of per-engine scores. Each engine weights the 6 dimensions differently.

| Engine | Formula | Score |
|--------|---------|-------|
| ChatGPT | `15% × Crawlability(31) + 20% × Content Extractability(31) + 25% × Entity Clarity(88) + 20% × Schema ` | **50** |
| Perplexity | `20% × Crawlability(31) + 25% × Content Extractability(31) + 15% × Entity Clarity(88) + 15% × Schema ` | **43** |
| Google AI Overviews | `15% × Crawlability(31) + 15% × Content Extractability(31) + 15% × Entity Clarity(88) + 25% × Schema ` | **46** |
| Gemini | `15% × Crawlability(31) + 18% × Content Extractability(31) + 18% × Entity Clarity(88) + 22% × Schema ` | **47** |
| Bing Copilot | `20% × Crawlability(31) + 20% × Content Extractability(31) + 15% × Entity Clarity(88) + 15% × Schema ` | **42** |


## 🗺 Prioritised Action Roadmap

| # | Dimension | Action | Effort | Est. Lift |
|---|-----------|--------|--------|-----------|
| 1 | Off-Page Authority | Add named author bylines + Person schema to blog and editorial content. | `medium` | +8 overall |
| 2 | Off-Page Authority | Prioritize:  — these dimensions have the most room for improvement in brand auth | `high` | +8 overall |
| 3 | Off-Page Authority | Add G2/Trustpilot review badges with links to footer. Even a single third-party  | `low` | +3 overall |
| 4 | Off-Page Authority | Add visible social links in footer HTML matching the sameAs JSON-LD values. | `low` | +3 overall |
| 5 | Off-Page Authority | Publish an original study or benchmark. Original research is the highest-value c | `high` | +3 overall |
| 6 | Off-Page Authority | Add a visible Privacy Policy link to the homepage footer. | `low` | +3 overall |
| 7 | Technical Foundation | Add og:title, og:description, og:image, og:type to every page template. | `low` | +15 overall |
| 8 | Technical Foundation | Add descriptive alt text to all images. Alt text is an AI-indexable content sign | `low` | +3 overall |
| 9 | Crawlability | Deploy /.well-known/rsl.json with RSL 1.0 to declare content reuse terms for AI  | `low` | +8 overall |
| 10 | Crawlability | Deploy /.well-known/ai.txt and /ai/summary.json as minimum viable AI discovery. | `low` | +8 overall |


---

## ● CRITICAL — 1 finding

### `OG-001` No OpenGraph tags on homepage

**Evidence:** og:title, og:description, and og:image are all absent from the homepage. OpenGraph tags are used by ChatGPT, Perplexity, and social AI surfaces to generate rich previews and brand descriptions. Without them, AI tools construct generic or inaccurate brand summaries.

**Action:** Add og:title, og:description, og:image, og:type to every page template.
> Effort: `low` · Priority: `high`
> 📈 **Research lift:** OpenGraph tags → AI tools use og:description as primary brand description source; absent = AI generates its own (often inaccurate)


---

## ▲ HIGH — 5 findings

### `CEA-004` Statistics without source citations on /

**Evidence:** 3 uncited statistics found, only 0 have source attribution. Unsourced stats are deprioritised by citation engines — AI treats sourced claims as more authoritative and quotable.

**Action:** Add source links or parenthetical citations to every statistic.
> Effort: `low` · Priority: `high`
> 📈 **Research lift:** Sourced statistics → +40% AI citation probability (Princeton KDD 2024 GEO study)

### `EEAT-001` No author bylines detected on homepage

**Evidence:** author_count=0, has_person_schema=False. No bylines, bio sections, or author credential markup.

**Action:** Add named author bylines + Person schema to blog and editorial content.
> Effort: `medium` · Priority: `high`

### `EEAT-010` Low Brand Authority Score (0/100) — weak AI trust signals

**Evidence:** Brand Authority Score: 0/100 (scale: 0–100 weighted across Wikipedia, Reddit, review platforms, social profiles, Wikidata). Weak dimensions: . AI engines weight brand authority when selecting sources for brand-related queries.

**Action:** Prioritize:  — these dimensions have the most room for improvement in brand authority.
> Effort: `high` · Priority: `medium`
> 📈 **Research lift:** High brand authority → AI engines preferentially select brand as authoritative source; Wikipedia + Reddit alone account for 45% of composite score

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


---

## ◆ MEDIUM — 12 findings

### `CEA-003` Low question-format heading ratio (4%) on /

**Evidence:** 4/104 H2/H3 headings are phrased as questions. Sample: ['do it all in less time.', 'do it all in less time.']. Question-format headings directly match conversational AI query patterns.

**Action:** Rewrite key H2 headings as questions to improve FAQ schema eligibility and AI direct-answer targeting.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** Question-format headings → FAQPage schema eligibility; FAQ schema pages = 2.7× more likely to appear in AI Overviews (Onely 2026)

### `CEA-005` No FAQ section on /

**Evidence:** has_faq_section=False, estimated_qa_pairs=0.

**Action:** Add FAQ section + FAQPage schema.
> Effort: `medium` · Priority: `medium`

### `CEA-014` No visible content freshness date marker on /

**Evidence:** No visible 'As of [date]', 'Last updated', or 'Published' text marker found on page. Visible date text is the most human-readable of the 5 freshness signal layers and acts as a reader trust signal alongside machine-readable metadata.

**Action:** Add 'Last updated: [Month Year]' visible text near the top of content pages.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** Visible freshness date = human-readable layer 5 of 5-layer freshness sync; Lureon: 76% of citations go to content updated within 30 days

### `CEA-015` Low answer-capsule ratio (20%) on /

**Evidence:** 1/5 H2/H3 sections have a 40+ word direct answer capsule. ChatGPT citation correlation: 72.4% of cited pages have ≥50%.

**Action:** Add a direct 40–60 word answer paragraph immediately after each major H2/H3 heading.
> Effort: `medium` · Priority: `high`
> 📈 **Research lift:** 72.4% of ChatGPT-cited pages have ≥50% answer capsule ratio (Cognism, 2026)

### `EEAT-002` No review platform links from homepage

**Evidence:** No G2, Capterra, Trustpilot, G2Crowd, or similar review platform links detected in homepage HTML. Third-party review signals are a top E-E-A-T corroboration source for AI citation engines.

**Action:** Add G2/Trustpilot review badges with links to footer. Even a single third-party review platform link signals independent validation.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** Review platform links → 3× AI citation probability (SE Ranking 2026 E-E-A-T study)

### `EEAT-003` Social profile links absent from homepage HTML

**Evidence:** No LinkedIn company, Twitter/X, or YouTube links detected in homepage HTML.

**Action:** Add visible social links in footer HTML matching the sameAs JSON-LD values.
> Effort: `low` · Priority: `medium`

### `EEAT-004` No original research or proprietary data signals

**Evidence:** No 'our study', 'we surveyed', 'n=X respondents' signals found.

**Action:** Publish an original study or benchmark. Original research is the highest-value citation magnet.
> Effort: `high` · Priority: `medium`

### `EEAT-005` No privacy policy link detectable on homepage

**Evidence:** Privacy policy link pattern not found in homepage HTML.

**Action:** Add a visible Privacy Policy link to the homepage footer.
> Effort: `low` · Priority: `medium`

### `IMG-001` 6 images missing alt text

**Evidence:** 6 images have no alt attribute. Examples: ./media_15d0c67d468c6ab860bd67d3af2d0998c15f45bbc.webp?width=750&#x26;format=web, ./media_180a8327664c8013005414b32d539cb95ce16ef7a.webp?width=750&#x26;format=web, ./media_13dac5079e7f5c35eb785e3e282b020d3859f4c5a.webp?width=750&#x26;format=web.... Alt text is the only machine-readable content signal for images; absent = invisible to AI crawlers.

**Action:** Add descriptive alt text to all images. Alt text is an AI-indexable content signal.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** Alt text present → images indexed as content by AI crawlers; each image = additional citation surface

### `RC17-001` No RSS/Atom feed found

**Evidence:** Checked /feed, /rss.xml, /atom.xml, /feed.xml — all returned non-200. Perplexity, Bing Copilot, and AI news agents actively consume RSS/Atom feeds to discover and rank fresh content.

**Action:** Create an RSS/Atom feed. Perplexity and AI news agents index feeds for freshness.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** RSS feeds indexed by Perplexity/Bing AI for freshness signals — absence = stale content perception

### `SC-001` No Speakable schema

**Evidence:** site_has_speakable=False. No SpeakableSpecification markup found. Speakable markup tells Google and voice assistants exactly which passages to read aloud or surface in AI Overview snippets.

**Action:** Add Speakable schema to product descriptions and key content sections.
> Effort: `low` · Priority: `medium`
> 📈 **Research lift:** Speakable markup → eligible for Google AI Overviews voice-snippet selection (Google Search Central, 2026)

### `SC-002` No FAQPage schema

**Evidence:** site_has_faqpage=False.

**Action:** Add FAQPage + Question + Answer schema to key landing pages.
> Effort: `medium` · Priority: `medium`


---

## ○ LOW — 5 findings

### `CEA-006` No key-takeaway / TL;DR box on /

**Evidence:** No TL;DR, key highlights, or summary box detected. These compact blocks are prime AI extraction targets — they concentrate citable facts in a scannable format AI engines prefer for quick answers.

**Action:** Add a 'Key highlights' box near top of content pages.
> Effort: `low` · Priority: `low`
> 📈 **Research lift:** Summary/TL;DR boxes → high AI extraction rate; compact fact-dense blocks preferred by ChatGPT and Perplexity for answer generation

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

---

## ✅ Passing Checks

10 skill scripts completed successfully with data.

---

*Generated by Brand AI Readiness Audit v2.0 · 2026-09-12 · 72 finding IDs across 6 GEO dimensions*