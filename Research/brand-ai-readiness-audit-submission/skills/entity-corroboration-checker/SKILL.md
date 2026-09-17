---
name: entity-corroboration-checker
description: Checks whether AI systems can uniquely identify and trust the brand. Extracts the brand name, checks for entity collision risk, looks up Wikidata QID, verifies sameAs links in Organization JSON-LD, checks external corroboration, and validates name consistency across pages. Use when auditing brand entity disambiguation and external knowledge graph presence. Covers RC5, RC6.
license: MIT
allowed-tools: web_fetch, web_search, run_script
---

# Entity Corroboration Checker

## When to use

Called by `audit-orchestrator` as sub-skill #4. May also be run standalone to check brand entity clarity.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL with `https://` prefix |

## Procedure

### Step 1 — Run the entity check script

```bash
python skills/entity-corroboration-checker/scripts/entity_check.py <url>
```

The script extracts the brand name and fetches Wikidata data. Capture the JSON output.

### Step 2 — Agent-level checks (require web_search)

After the script runs, use `web_search` for:

1. **External corroboration search**: `"<brand_name>" founded`
   - Count how many unique non-brand domains appear in the top 10 results
   - < 2 independent sources = zero corroboration (RC6)

2. **Entity collision risk**: `"<brand_name>" company`
   - Do results show multiple distinct companies sharing the name? Flag collision risk (RC5)

3. **Product category search**: `"<brand_name>" <core_product>`
   - Does the brand appear in results for its own product category?
   - If not, flag as citation gap (informs RC5/RC6)

### Step 3 — Generate findings

#### RC5 — Entity disambiguation risk

Use `entity_collision_risk` from script output combined with web search results.

| Condition | Severity |
|-----------|----------|
| Brand name is a common English word (dict word, color, animal, etc.) AND no Wikidata QID | HIGH |
| Multiple companies share the exact brand name (from web search) AND no `sameAs` in JSON-LD | HIGH |
| Brand name shares 80%+ similarity with a well-known brand (risk of confusion) | MEDIUM |
| Brand name is unique but Organization JSON-LD is missing `sameAs` links | MEDIUM |
| `sameAs` present but links to only 1 external source | LOW |

Finding ID: `RC5-001`
Evidence: brand name extracted, Wikidata QID found (or not), collision results from web search, `sameAs` links present.

#### RC6 — Zero or weak external corroboration

Combine `wikidata` result from script + web search results.

| Condition | Severity |
|-----------|----------|
| No Wikidata entity found AND < 2 independent domains mention the brand | CRITICAL |
| No Wikidata entity found but 2–4 independent domains mention the brand | HIGH |
| Wikidata entity found but no `sameAs` link to it in Organization JSON-LD | MEDIUM |
| Wikidata entity found, `sameAs` link present, but no Wikipedia article | LOW |
| Name inconsistency: brand name on homepage ≠ about page ≠ footer | MEDIUM |

Finding ID: `RC6-001`
Evidence: Wikidata QID (if found), independent domain count, `sameAs` values present, name variants found.

### Step 4 — Name consistency check

Use `name_variants` from script output. If more than one distinct name is found across the homepage, about page, and footer:

Finding ID: `RC6-002`, Severity: MEDIUM
Evidence: list each variant and where it was found.

### Step 5 — Proactive suggestions

If entity is well-established (Wikidata QID present, multiple corroborating domains) but Organization JSON-LD lacks `sameAs` links to Wikidata/Wikipedia, add a LOW proactive finding recommending adding these links.

## Output

```json
{
  "skill": "entity-corroboration-checker",
  "findings": [ /* array of finding objects per report-schema.md */ ]
}
```
