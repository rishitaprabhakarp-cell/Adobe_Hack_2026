# Brand AI Readiness Audit — Adobe

> **Site:** [www.adobe.com](https://www.adobe.com)  
> **Audited:** 2026-09-08  
> **Overall GEO Score:** 48/100 — Not GEO Ready  
> **Findings:** 1 Critical · 4 High · 12 Medium · 4 Low  

---

## GEO Dimension Scores

| Dimension | Score | Status |
|-----------|------:|--------|
| Crawlability | 33 | 🔴 Critical gap |
| Content Extractability | 31 | 🔴 Critical gap |
| Entity Clarity | 88 | ✅ On track |
| Schema Integrity | 64 | ⚠️ Developing |
| Off-Page Authority | 32 | 🔴 Critical gap |
| Technical Foundation | 27 | 🔴 Critical gap |

## Per-Engine GEO Scores

| Engine | Score | Threshold |
|--------|------:|-----------|
| ChatGPT | 52 | ⚠️ 70 |
| Perplexity | 45 | ⚠️ 70 |
| Google AI Overviews | 48 | ⚠️ 70 |
| Gemini | 48 | ⚠️ 70 |
| Bing Copilot | 45 | ⚠️ 70 |

---

## ● CRITICAL — 1 finding

### `OG-001` No OpenGraph tags on homepage

**Evidence:** og:title, og:description, og:image all absent from homepage.

**Action:** Add og:title, og:description, og:image, og:type to every page template.
> Effort: `low` · Priority: `high`


---

## ▲ HIGH — 4 findings

### `CEA-004` Statistics without source citations on /

**Evidence:** 3 uncited stats, 0 cited. Princeton KDD 2024: sourced stats → +40% AI citation.

**Action:** Add source links or parenthetical citations to every statistic.
> Effort: `low` · Priority: `high`

### `EEAT-001` No author bylines detected on homepage

**Evidence:** author_count=0, has_person_schema=False. No bylines, bio sections, or author credential markup.

**Action:** Add named author bylines + Person schema to blog and editorial content.
> Effort: `medium` · Priority: `high`

### `RSL-001` No RSL 1.0 machine-readable license declaration

**Evidence:** /.well-known/rsl.json returns 404 and no <link rel='robots-standard-license'> in HTML.

**Action:** Deploy /.well-known/rsl.json with RSL 1.0 to declare content reuse terms for AI crawlers.
> Effort: `low` · Priority: `high`

### `RSL-003` Zero AI discovery endpoints present (0/14 checked)

**Evidence:** None of 14 AI discovery endpoints return HTTP 200.

**Action:** Deploy /.well-known/ai.txt and /ai/summary.json as minimum viable AI discovery.
> Effort: `low` · Priority: `high`


---

## ◆ MEDIUM — 12 findings

### `CEA-003` Low question-format heading ratio (4%) on /

**Evidence:** 4/104 H2/H3s are questions. Sample: ['do it all in less time.', 'do it all in less time.']

**Action:** Rewrite key H2 headings as questions to improve FAQ schema eligibility and AI direct-answer targeting.
> Effort: `low` · Priority: `medium`

### `CEA-005` No FAQ section on /

**Evidence:** has_faq_section=False, estimated_qa_pairs=0.

**Action:** Add FAQ section + FAQPage schema.
> Effort: `medium` · Priority: `medium`

### `CEA-008` No content freshness date marker on /

**Evidence:** No visible 'As of [date]' or 'Last updated' text marker found.

**Action:** Add 'Last updated: [Month Year]' visible text. Freshness is top Perplexity ranking signal.
> Effort: `low` · Priority: `medium`

### `CEA-009` Low answer-capsule ratio (20%) on /

**Evidence:** 1/5 H2/H3 sections have a 40+ word direct answer capsule. ChatGPT citation correlation: 72.4% of cited pages have ≥50%.

**Action:** Add a direct 40–60 word answer paragraph immediately after each major H2/H3 heading.
> Effort: `medium` · Priority: `high`

### `EEAT-002` No review platform links from homepage

**Evidence:** No G2, Capterra, Trustpilot, or other review platform links detected.

**Action:** Add G2/Trustpilot badges. SE Ranking 2026: review links → 3× citation probability.
> Effort: `low` · Priority: `medium`

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

**Evidence:** Images without alt attributes: ./media_15d0c67d468c6ab860bd67d3af2d0998c15f45bbc.webp?width=750&#x26;format=web, ./media_180a8327664c8013005414b32d539cb95ce16ef7a.webp?width=750&#x26;format=web, ./media_13dac5079e7f5c35eb785e3e282b020d3859f4c5a.webp?width=750&#x26;format=web...

**Action:** Add descriptive alt text to all images. Alt text is an AI-indexable content signal.
> Effort: `low` · Priority: `medium`

### `RC17-001` No RSS/Atom feed found

**Evidence:** Checked /feed, /rss.xml, /atom.xml, /feed.xml — all returned non-200.

**Action:** Create an RSS/Atom feed. Perplexity and AI news agents index feeds for freshness.
> Effort: `low` · Priority: `medium`

### `SC-001` No Speakable schema

**Evidence:** site_has_speakable=False. No SpeakableSpecification markup found.

**Action:** Add Speakable schema to product descriptions and key content sections.
> Effort: `low` · Priority: `medium`

### `SC-002` No FAQPage schema

**Evidence:** site_has_faqpage=False.

**Action:** Add FAQPage + Question + Answer schema to key landing pages.
> Effort: `medium` · Priority: `medium`


---

## ○ LOW — 4 findings

### `CEA-006` No key-takeaway / TL;DR box on /

**Evidence:** No TL;DR, summary, or key-highlight block detected.

**Action:** Add a 'Key highlights' box near top of content pages.
> Effort: `low` · Priority: `low`

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

---

## ✅ Passing Checks

10 skill scripts completed successfully with data.

---

*Generated by Brand AI Readiness Audit v2.0 · 2026-09-08 · 72 finding IDs across 6 GEO dimensions*