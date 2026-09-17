# Citation Checks — Reference Guide

## Search queries to run

For a brand named `[BRAND]` with core product `[PRODUCT]`:

| Query | Purpose |
|-------|---------|
| `"[BRAND]" what does it do` | Brand awareness — do third parties describe this brand? |
| `"[BRAND]" founded` | Founding/provenance — is founding story externally corroborated? |
| `"[BRAND]" [PRODUCT]` | Product category ranking — does the brand rank for its own category? |
| `"[BRAND]" review` | Social proof — are there independent reviews/mentions? |
| `site:[DOMAIN]` | Index coverage — how many pages from the domain are indexed? |

## Evaluating search results

### Independent source classification

A source is **independent** if:
- It is NOT on the brand's own domain or any subdomain
- It is NOT a press release republished verbatim from the brand
- It is NOT a directory listing with only the brand's own submitted description
- It IS: news coverage, analyst reports, customer reviews, academic citations, Wikipedia, Crunchbase, LinkedIn company profile with third-party followers

### Source quality tiers

| Tier | Examples | Weight |
|------|----------|--------|
| High | Wikipedia, major news outlets, industry analysts, G2/Capterra/Trustpilot | 3x |
| Medium | Blog posts, mid-tier news, Crunchbase, LinkedIn company page | 2x |
| Low | Social media mentions, small directories, republished press releases | 1x |

### Counting results

- Count only the first 10 organic results (exclude paid ads, featured snippets from own site).
- A result "belongs to the brand" if the domain matches the brand's own domain or is a direct subdomain.
- A result "mentions the brand" if the brand name appears in the title or snippet.

## Severity criteria

### Citation absence

| Independent sources in top 10 | Severity |
|-------------------------------|----------|
| 0 (only brand's own domain) | HIGH |
| Brand not in top 10 at all | CRITICAL |
| 1–2 low-tier sources | MEDIUM |
| 3+ sources (any tier) | Pass |

### Product category ranking

| Brand position for `[BRAND] [PRODUCT]` | Severity |
|----------------------------------------|----------|
| Not in top 10 | HIGH |
| Position 8–10 | MEDIUM |
| Position 4–7 | LOW |
| Position 1–3 | Pass |

### Factual contradiction detection

Compare brand claims to search results:

1. **Founding year**: if brand says "founded 2019" but a credible source says 2017 or 2021 → flag MEDIUM
2. **Product type**: if brand says "AI writing tool" but search results describe it as "SEO tool" → flag HIGH
3. **Name spelling**: if brand spells itself "Acme" but external sources say "ACME Corp" consistently → flag LOW
4. **Location**: if brand says "San Francisco" but external sources say "Austin" → flag MEDIUM

### Name confusion / entity mix-up

Search for `"[BRAND]" company`:

- If the top result is a Wikipedia article about a completely different company → HIGH
- If 3+ of top 10 results are about a different entity → CRITICAL
- If 1–2 results mention a different entity but brand still ranks → MEDIUM (advisory)

## What a strong citation profile looks like

A brand with strong AI citation profile has:
1. Appears in top 3 results for `"[BRAND] what does it do"`
2. Has ≥ 1 high-tier independent source (Wikipedia, major news outlet)
3. Has ≥ 3 independent sources total in top 10
4. Brand description in search snippets matches brand's own claims exactly
5. No entity mix-up in top 10 results
6. Has Wikidata QID with `sameAs` link in Organization JSON-LD
7. Meta description is factually precise and searchable (not generic marketing copy)

## Common failure patterns

| Pattern | Root Cause | Suggested Fix |
|---------|-----------|---------------|
| Only brand.com appears in results | RC6 (zero external corroboration) | PR/content seeding on high-DA sites |
| Search results show wrong company | RC5 (entity collision) | Wikidata disambiguation page, clarifier in all JSON-LD |
| Search snippets are stale | RC21 (freshness drift) | Update dateModified in JSON-LD, republish key pages |
| Brand ranks for name but not product | RC3 (no inner-page schema) | Add Product/Service JSON-LD to category pages |
| Brand invisible for all searches | RC1+RC2+RC4 | SSR + llms.txt + unblock citation bots |
