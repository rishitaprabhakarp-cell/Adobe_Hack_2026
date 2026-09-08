---
name: eeeat-signal-checker
description: Checks Experience, Expertise, Authoritativeness, and Trustworthiness (E-E-A-T) signals that AI engines use to validate source credibility before citation. Checks author bylines and credentials, Person schema, LinkedIN/Scholar presence, trust badges, review platform profiles, original research indicators, and editorial standards disclosure. Use when auditing a site's authority signals for AI citation eligibility.
license: MIT
allowed-tools: web_fetch, web_search, run_script
---

# E-E-A-T Signal Checker

## When to use

Called by `audit-orchestrator` as sub-skill #9. Checks authority and trustworthiness signals — the dimension that determines whether AI engines treat the brand as a citable source vs. an unverified claim.

**Research basis**: SE Ranking (2025): sites with active Trustpilot/G2/Capterra profiles have **3× higher citation probability**. Backlinko/Semrush (Jan 2026): Reddit and LinkedIn are top-2 cited domains across ChatGPT, Perplexity, and Google AI Mode.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL with `https://` prefix |

## Procedure

### Step 1 — Run the E-E-A-T script

```bash
python skills/eeeat-signal-checker/scripts/eeeat_check.py <url>
```

### Step 2 — Agent web_search checks

Run these searches to verify off-page E-E-A-T signals:

1. `site:reddit.com "[brand_name]"` — Does the brand have organic Reddit thread presence?
2. `site:linkedin.com/company "[brand_name]"` — Does LinkedIn company page exist?
3. `site:g2.com OR site:capterra.com OR site:trustpilot.com "[brand_name]"` — Review platform presence?
4. `"[brand_name]" site:news.google.com` — Press coverage in Google News?

### Step 3 — Generate findings

#### EEAT-1 — No author bylines or Person schema

Check `author_byline_count`, `has_person_schema`, `author_credentials`:

| Condition | Severity |
|-----------|----------|
| Blog/article pages have no author bylines | HIGH |
| Author bylines present but no Person schema | MEDIUM |
| Person schema present but no `sameAs` to LinkedIn/Scholar | LOW |

Finding ID: `EEAT-001`
Evidence: pages sampled, byline found (yes/no), Person schema found (yes/no).

#### EEAT-2 — No review platform presence

Based on web_search for G2/Capterra/Trustpilot:

| Condition | Severity |
|-----------|----------|
| Brand not found on any major review platform (G2, Capterra, Trustpilot, Yelp, ProductHunt) | HIGH |
| Brand found on 1 platform only | MEDIUM |
| Found on 2+ platforms but profiles appear thin (< 10 reviews) | LOW |

Finding ID: `EEAT-002`
Evidence: platforms checked, presence result, review count if detectable.

#### EEAT-3 — No Reddit/community presence

Based on `site:reddit.com "[brand_name]"` search:

| Condition | Severity |
|-----------|----------|
| 0 Reddit threads organically mention the brand | HIGH |
| Brand appears in Reddit but only in self-promotional posts | MEDIUM |

Finding ID: `EEAT-003`
Evidence: search result count, nature of mentions.

#### EEAT-4 — No original research or proprietary data

Check `original_research_signals` from script:

| Condition | Severity |
|-----------|----------|
| Site has no blog/resources section | MEDIUM |
| Blog exists but no posts contain statistics, studies, or original data | MEDIUM |

Finding ID: `EEAT-004`
Evidence: pages checked, original data indicators found.

#### EEAT-5 — No trust indicators on homepage

Check `trust_signals` from script (SSL, security badges, privacy policy link, terms link):

| Condition | Severity |
|-----------|----------|
| No privacy policy link detectable on homepage | MEDIUM |
| No terms of service or legal page linked | LOW |
| HTTPS not enforced (HTTP redirect missing) | HIGH |

Finding ID: `EEAT-005`
Evidence: trust signals found/absent.

#### EEAT-6 — LinkedIn company page absent

Based on `site:linkedin.com/company "[brand_name]"`:

| Condition | Severity |
|-----------|----------|
| No LinkedIn company page found | MEDIUM |
| LinkedIn page found but not linked in Organization sameAs JSON-LD | LOW |

Finding ID: `EEAT-006`
Evidence: LinkedIn URL found (or not), sameAs link present (or not).

#### EEAT-7 — No Wikidata entity with P856 (official website) pointing to this domain

Check `wikidata_p856` from script (SPARQL query to `query.wikidata.org`):

**Why this matters**: Wikidata P856 is the most authoritative machine-readable signal that an entity
"officially is" a given domain. AI systems (especially Google Gemini and Perplexity) use Wikidata
as a ground truth for entity disambiguation. A brand without a Wikidata entity with P856 set has:
- No definitive QID — AI models may conflate the brand with similarly-named entities
- No `sameAs` anchor for JSON-LD Organization schema to resolve against
- Lower confidence score in Knowledge Graph corroboration

| Condition | Severity |
|-----------|----------|
| `wikidata_entity_found` is false — no Wikidata entity for this domain | HIGH |
| Wikidata entity found but QID not used in `sameAs` JSON-LD on homepage | MEDIUM |
| Wikidata entity found and correctly referenced in `sameAs` | PASS |

Finding ID: `EEAT-007`
Evidence: SPARQL query result, `entities` array, `sameAs` values from homepage JSON-LD.
Suggested action: Create a Wikidata entry with P856 set to the canonical domain; add the Wikidata QID URL to `sameAs` in Organization JSON-LD.

### Step 4 — Proactive suggestions

If E-E-A-T is generally strong:
- Recommend publishing an original study or benchmark (even a small one) — original research is the highest-value citation magnet for AI engines.
- Recommend maintaining a YouTube explainer channel (YouTube is ~16% of top Perplexity citations).
- If Wikidata entity exists but is sparse, add P112 (founded by), P571 (inception), P856 (official website), P154 (logo image), P18 (image).

## Output

```json
{
  "skill": "eeeat-signal-checker",
  "findings": []
}
```
