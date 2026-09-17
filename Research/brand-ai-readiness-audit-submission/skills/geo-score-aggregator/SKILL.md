---
name: geo-score-aggregator
description: Produces a scored GEO (Generative Engine Optimization) readiness report across 6 dimensions with per-engine scores for ChatGPT, Perplexity, Google AI Overviews, Gemini, and Bing Copilot. Aggregates findings from all other skills, weights them by AI engine preferences, calculates dimension scores (0-100), and produces a compliance percentage against Directive Consulting's 70% GEO readiness threshold. Use at the end of a full audit to produce the final scored summary and prioritized action roadmap.
license: MIT
allowed-tools: web_fetch, web_search
---

# GEO Score Aggregator

## When to use

Called by `audit-orchestrator` as the final sub-skill (#13), after all other skills have run. Takes the merged `findings` array and produces a scored readiness report with per-engine breakdowns and a prioritized action roadmap.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL |
| `all_findings` | Yes | Merged findings array from all prior skills |

## Procedure

### Step 1 — Map findings to GEO dimensions

Map each finding to one of 6 dimensions based on its ID prefix:

| Dimension | Covers | Finding ID prefixes |
|-----------|--------|---------------------|
| D1: Crawlability | Bot access, robots.txt, llms.txt, sitemap, CDN/WAF silencing | RC2, RC4, RC7, RC14, RC17, RC19, RC23, CDN-WAF-001, CDN-WAF-002, RSL-001 to 005, TSEO-001 |
| D2: Content Extractability | Passage structure, FAQs, statistics, headings, answer capsules, AI cliché slop | CEA-001 to 010, RC8, RC11 |
| D3: Entity Clarity | Brand disambiguation, sameAs, name consistency, Wikidata P856 | RC5, RC6, CITE-003, CITE-004, EEAT-001, EEAT-007 |
| D4: Schema Integrity | JSON-LD richness, schema types, correctness | RC3, RC10, RC11, RC13, RC15, RC18, RC21, OG-007 |
| D5: Off-Page Authority | External corroboration, E-E-A-T, review platforms | RC6, CITE-001, CITE-002, EEAT-002 to 006 |
| D6: Technical Foundation | Render, meta, OG, technical SEO | RC1, RC9, RC12, RC20, TSEO-002 to 009, OG-001 to 008 |

**Note**: `CDN-WAF-001` and `CDN-WAF-002` are auto-promoted to CRITICAL weight in the D1 score —
a CDN block makes all other GEO work irrelevant until resolved.
`CEA-009` (answer capsules) carries double MEDIUM weight in the ChatGPT per-engine score
(72.4% correlation with citations is the strongest single predictor in the dataset).

### Step 2 — Score each dimension (0–100)

For each dimension:
1. Count total possible checks (based on all check IDs in that dimension).
2. Count checks that PASSED (no finding, or only LOW-severity findings).
3. Score = (passing_checks / total_checks) × 100

Severity penalty weights:
- CRITICAL finding: counts as 0 for all checks in its category
- HIGH finding: −2 checks worth of score
- MEDIUM finding: −1 check worth of score
- LOW finding: −0.5 (proactive suggestions don't count against score)

### Step 3 — Calculate per-engine scores

Different AI engines weight dimensions differently. Apply these weights:

| Engine | D1 Crawl | D2 Content | D3 Entity | D4 Schema | D5 Authority | D6 Technical |
|--------|----------|------------|-----------|-----------|--------------|--------------|
| ChatGPT | 15% | 20% | 25% | 20% | 15% | 5% |
| Perplexity | 20% | 25% | 15% | 15% | 20% | 5% |
| Google AI Overviews | 15% | 15% | 15% | 25% | 15% | 15% |
| Gemini | 15% | 18% | 18% | 22% | 15% | 12% |
| Bing Copilot | 20% | 20% | 15% | 15% | 20% | 10% |

Per-engine score = weighted sum of dimension scores.

**Engine preferences explained**:
- **ChatGPT**: entity links and Wikipedia-style sameAs are highest weight
- **Perplexity**: freshness (D2/D5) and depth are weighted highest
- **Google AI Overviews**: schema (D4) and technical (D6) are highest
- **Gemini**: follows Google's lead, slightly more entity-sensitive
- **Bing Copilot**: uses Bing's index + Claude weighting

### Step 4 — Calculate overall GEO readiness score

Overall = average of the 5 per-engine scores.

GEO readiness threshold (Directive Consulting 2026):
- ≥ 70%: **GEO Ready** — meaningful citation probability
- 50–69%: **Developing** — structural barriers present
- < 50%: **Not GEO Ready** — fundamental gaps must be closed first

### Step 5 — Produce prioritized action roadmap

From all findings:
1. Group by dimension.
2. Within each dimension, sort: CRITICAL → HIGH → MEDIUM → LOW.
3. For each group, identify the single highest-impact action (the CRITICAL or first HIGH finding).
4. Output a table: | Priority | Dimension | Action | Effort | Expected Score Lift |

Effort estimates:
- Adding llms.txt: LOW effort
- Adding JSON-LD schema: MEDIUM effort
- Fixing JS rendering (SSR): HIGH effort
- Adding author bylines: LOW effort
- Building review platform profiles: MEDIUM effort

Expected score lift: use the severity → score delta from Step 2 to estimate points gained.

### Step 6 — Emit the GEO Score block

Append this block to the main audit report as an additional top-level key `"geo_score"`:

```json
{
  "geo_score": {
    "overall": 62,
    "threshold": 70,
    "geo_ready": false,
    "dimension_scores": {
      "d1_crawlability": 80,
      "d2_content_extractability": 45,
      "d3_entity_clarity": 55,
      "d4_schema_integrity": 60,
      "d5_off_page_authority": 30,
      "d6_technical_foundation": 85
    },
    "per_engine_scores": {
      "chatgpt": 58,
      "perplexity": 52,
      "google_ai_overviews": 66,
      "gemini": 64,
      "bing_copilot": 57
    },
    "action_roadmap": [
      {
        "priority": 1,
        "dimension": "D5: Off-Page Authority",
        "action": "Register on G2, Capterra, and Trustpilot",
        "effort": "low",
        "estimated_score_lift": "+8 overall, +12 on Perplexity"
      }
    ]
  }
}
```

## Output

This skill adds a `geo_score` block to the existing report. It does not add to `findings[]` — it is a summary layer.

```json
{
  "skill": "geo-score-aggregator",
  "geo_score": { ... }
}
```
