---
name: llm-citation-tester
description: Tests what an LLM actually knows and cites about a brand using web_search. Searches for brand name in context of its purpose and founding, checks product category ranking, extracts key facts from the homepage, compares search results to brand's own claims, and flags citation absence or factual contradictions. Use when auditing brand citation quality from the LLM's own perspective. Validates all RC1-RC23 from the LLM's viewpoint.
license: MIT
allowed-tools: web_search, web_fetch
---

# LLM Citation Tester

## When to use

Called by `audit-orchestrator` as sub-skill #6. This is the only skill that tests what the LLM itself actually knows about the brand — no helper script needed. Uses the agent's own `web_search` tool exclusively.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL with `https://` prefix |
| `brand_name` | No | Brand name (auto-extracted if not provided using the site's homepage title / Organization JSON-LD) |

## Procedure

Work through these steps in order. All checks use `web_search`.

### Step 1 — Establish brand name

If `brand_name` is not provided:
- Fetch `<url>` and extract the brand name from: Organization JSON-LD `name` > `og:site_name` > `<title>` first segment.
- Record the brand name and the extraction source.

Also extract 3–5 key facts from the homepage:
- Founding year (look for "founded in", "since", "est.")
- Core product or service description (first paragraph or H1 + subheading)
- Headquarters / location (if stated)
- Number of customers / team size (if stated)
- Key differentiator claim (if stated)

Record these as `brand_claims`.

### Step 2 — Brand awareness search

Run: `web_search("[brand_name] what does it do")`

Evaluate results:
- Does the brand appear in any of the top 5 results?
- Which domains are citing the brand (brand's own domain vs. independent sources)?
- Is the description in search results consistent with `brand_claims`?

Run: `web_search("[brand_name] founded")`

Evaluate:
- Does the brand appear in any of the top 5 results?
- Is the founding year consistent with `brand_claims`?

See [references/citation-checks.md](references/citation-checks.md) for detailed evaluation criteria.

### Step 3 — Product category ranking

Run: `web_search("[brand_name] [core_product_keyword]")`
where `core_product_keyword` is the main product/service category extracted from the homepage (e.g., "project management software", "AI writing tool", "cloud accounting").

Evaluate:
- Does the brand appear in the top 10 results for its own product category?
- Are competitors outranking the brand for its own name + product?

### Step 4 — Citation accuracy check

Compare search result snippets against `brand_claims`:

| Check | What to look for |
|-------|-----------------|
| Founding year | Does any source contradict the year on the brand's own site? |
| Product description | Do search results describe the same product the site claims? |
| Location/HQ | Do sources agree on the location? |
| Brand name variants | Do sources use a different spelling or capitalization? |

Flag contradictions between sources and brand's own claims as citation accuracy issues.

### Step 5 — Generate findings

For findings, consult [references/citation-checks.md](references/citation-checks.md) for severity criteria.

#### Citation absence (validates RC1, RC2, RC4, RC6, RC9)

| Condition | Severity |
|-----------|----------|
| Brand does not appear in top 10 results for `"[brand_name] what does it do"` | CRITICAL |
| Brand appears in results only from its own domain (zero independent sources) | HIGH |
| Brand appears in 1–2 independent sources | MEDIUM |
| Brand appears in results but description is vague or incorrect | MEDIUM |

Finding ID: `CITE-001`
Evidence: search query used, number of independent sources found, sample snippet from results.

#### Product category invisibility (validates RC1, RC3, RC9)

| Condition | Severity |
|-----------|----------|
| Brand does not appear in top 10 results for its own product category | HIGH |
| Brand appears but below position 7 | MEDIUM |

Finding ID: `CITE-002`
Evidence: search query, brand position in results, competitors that outrank it.

#### Citation accuracy — factual contradictions (validates RC5, RC6, RC21)

| Condition | Severity |
|-----------|----------|
| A key fact (founding year, product type, location) is contradicted by ≥ 1 independent source | HIGH |
| Founding year or name is inconsistent across sources | MEDIUM |
| Description in search snippets is outdated (based on dateModified gap from RC21) | LOW |

Finding ID: `CITE-003`
Evidence: brand's claim vs. contradicting source (URL + snippet).

#### Name confusion / entity mix-up (validates RC5)

If search results for `"[brand_name]"` prominently show a different company:

| Condition | Severity |
|-----------|----------|
| Top result is a different company with the same name | HIGH |
| 3+ of top 10 results refer to a different entity with the same name | CRITICAL |

Finding ID: `CITE-004`
Evidence: search query, conflicting entity name/description, position in results.

### Step 6 — Proactive suggestions

Even if all citation checks pass:
- If the brand has no Wikipedia article, add LOW proactive finding recommending creating a notable Wikipedia entry or contributing to Wikidata.
- If search result snippets use the site's `<meta description>` verbatim but it's weak/vague, recommend improving the meta description for better LLM citation quality.

## Output

```json
{
  "skill": "llm-citation-tester",
  "findings": [ /* array of finding objects per report-schema.md */ ]
}
```
