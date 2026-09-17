---
name: structured-data-auditor
description: Checks the quality and completeness of JSON-LD schema markup across a website. Samples homepage and inner pages, scores schema richness, detects missing high-value schema types (FAQPage, HowTo, speakable, VideoObject), checks freshness signals, paywall declarations, language signals, and empty alt text on images. Use when auditing structured data quality for AI discoverability. Covers RC3, RC10, RC11, RC13, RC15, RC16, RC18, RC21.
license: MIT
allowed-tools: web_fetch, run_script
---

# Structured Data Auditor

## When to use

Called by `audit-orchestrator` as sub-skill #3. May also be run standalone to audit schema.org JSON-LD quality.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL with `https://` prefix |

## Procedure

### Step 1 — Run the schema audit script

```bash
python skills/structured-data-auditor/scripts/schema_audit.py <url>
```

The script samples the homepage + up to 3 inner pages and extracts all JSON-LD blocks. Capture the output JSON.

### Step 2 — Score schema richness per page

For each JSON-LD block in `pages[*].jsonld_blocks`:
- Count the number of first-level fields (excluding `@context`, `@type`)
- `< 3 fields` = generic (penalized)
- `3–4 fields` = adequate
- `5+ fields` = rich (cited ~61.7% more frequently in AI assistant responses)

#### RC3 — No inner-page JSON-LD

| Condition | Severity |
|-----------|----------|
| Inner pages (non-homepage) have zero JSON-LD blocks | HIGH |
| Inner pages have JSON-LD but all blocks have < 3 fields | MEDIUM |

Finding ID: `RC3-001`
Evidence: list each inner page URL and its JSON-LD block count + field counts.

### Step 3 — Check for missing high-value schema types

Check `site_schema_types` (all @type values seen across all pages) against required types.

#### RC10 — No speakable schema

| Condition | Severity |
|-----------|----------|
| `speakable` property absent from all pages | MEDIUM |

Finding ID: `RC10-001`
Evidence: list all @types found; confirm `speakable` absent.

#### RC11 — Missing FAQPage / HowTo

| Condition | Severity |
|-----------|----------|
| Site appears to have FAQ or How-to content (based on page titles/headings) but no `FAQPage` or `HowTo` schema | MEDIUM |
| Site has no `FAQPage` or `HowTo` schema at all, and content type is unclear | LOW |

Finding ID: `RC11-001`
Evidence: page URLs checked, FAQ/HowTo-like headings found (if any), schema types actually present.

### Step 4 — Freshness signals

Check `freshness` fields across all JSON-LD blocks:

#### RC21 — Freshness metadata drift

| Condition | Severity |
|-----------|----------|
| Article/BlogPosting pages have no `datePublished` or `dateModified` | HIGH |
| `dateModified` is > 180 days old on pages claiming fresh content | MEDIUM |
| `dateReviewed` absent on Review/Product pages | LOW |

Finding ID: `RC21-001`
Evidence: page URL, @type, dates found (or absent), age in days.

### Step 5 — Paywall signal

#### RC13 — Paywall without isAccessibleForFree schema

If any page returns a paywall indicator (HTTP 402, or body contains "subscribe", "paywall", "premium", "members only") AND `isAccessibleForFree` is absent from JSON-LD:

| Condition | Severity |
|-----------|----------|
| Gated content detected, `isAccessibleForFree: false` absent | HIGH |
| Gated content detected, `isAccessibleForFree` present but value is incorrect | MEDIUM |

Finding ID: `RC13-001`
Evidence: page URL, paywall indicator found, isAccessibleForFree value if present.

### Step 6 — Language signals

#### RC15 — Language signal gaps

Check:
- `<html lang="...">` attribute present?
- `hreflang` tags present for multi-language sites?
- `inLanguage` in Organization or WebPage JSON-LD?

| Condition | Severity |
|-----------|----------|
| `<html lang="">` is empty or absent | MEDIUM |
| Site has content in multiple languages but no `hreflang` | MEDIUM |
| `inLanguage` absent from all JSON-LD | LOW |

Finding ID: `RC15-001`
Evidence: `lang` attribute value found (or absent), `hreflang` count, `inLanguage` values found.

### Step 7 — Video without transcript

#### RC18 — VideoObject without transcript

| Condition | Severity |
|-----------|----------|
| `VideoObject` schema present but `transcript` property absent | MEDIUM |
| `VideoObject` schema present but `description` < 50 chars | LOW |

Finding ID: `RC18-001`
Evidence: page URL, VideoObject @type found, transcript/description presence.

### Step 8 — Empty alt text on key images

#### RC16 — Empty alt on key images

Check `images_missing_alt` from script output:

| Condition | Severity |
|-----------|----------|
| Homepage has > 0 `<img>` tags with empty `alt=""` or no `alt` | MEDIUM |
| Inner pages have > 2 `<img>` with empty alt | LOW |

Finding ID: `RC16-001`
Evidence: page URL, count of images missing alt, example src values.

### Step 9 — Proactive suggestions

If schema is present and rich, but missing `sameAs` links in Organization JSON-LD (Wikidata, Wikipedia, LinkedIn), add a LOW proactive finding linking to entity-corroboration-checker concerns.

## Output

```json
{
  "skill": "structured-data-auditor",
  "findings": [ /* array of finding objects per report-schema.md */ ]
}
```
