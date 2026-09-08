---
name: render-gap-detector
description: Checks whether page content actually reaches AI crawlers without JavaScript execution. Fetches raw HTML via Googlebot user-agent, counts words, detects SPA shells, checks page titles and meta descriptions, classifies JS-rendering state, and tests selective SSR across homepage and inner pages. Use when auditing a site for JS-render gaps that hide content from AI. Covers RC1, RC9, RC12, RC20.
license: MIT
allowed-tools: web_fetch, run_script
---

# Render Gap Detector

## When to use

Called by `audit-orchestrator` as sub-skill #2. May also be run standalone against any URL to check JS-render exposure.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL with `https://` prefix |

## Procedure

### Step 1 — Run the render check script

```bash
python skills/render-gap-detector/scripts/render_check.py <url>
```

The script fetches multiple pages using a Googlebot UA and returns a JSON object with render analysis per page.

### Step 2 — Classify each page using the 4-state model

For each page in the result (`pages` array), classify it:

| State | Condition | Label |
|-------|-----------|-------|
| A | `word_count` ≥ 100 AND `has_h1` AND `has_meta_description` | `raw_html_works` |
| B | `word_count` < 100 AND `spa_shell_detected` = true | `browser_only` |
| C | `word_count` ≥ 30 AND < 100, OR `has_h1` = false | `poor_semantics` |
| D | HTTP status ≠ 200 OR `word_count` < 10 | `fully_blocked` |

State B is the most severe (JS-only SPA). State D means completely inaccessible.

### Step 3 — Generate findings

#### RC1 — JS-Rendering (homepage is browser-only)

| Condition | Severity |
|-----------|----------|
| Homepage classified as `browser_only` (state B) | CRITICAL |
| Homepage classified as `fully_blocked` (state D) | CRITICAL |
| Homepage classified as `poor_semantics` (state C) | HIGH |

Finding ID: `RC1-001`
Evidence: word count, SPA shell markers detected, title/meta present/absent.

#### RC9 — Selective SSR (homepage SSR but inner pages are not)

Check if homepage is state A but any sampled inner page (`/about`, `/pricing`, `/product`) is state B or C.

| Condition | Severity |
|-----------|----------|
| 2+ inner pages are `browser_only` or `poor_semantics` | HIGH |
| 1 inner page is `browser_only` | MEDIUM |

Finding ID: `RC9-001`
Evidence: list each page URL with its state and word count.

#### RC12 — Institution invisibility (no H1 or brand name in raw HTML)

For any page in state A or C: if `has_h1` is false, or if the brand name (extracted from title or Organization JSON-LD) does not appear in the raw text, flag it.

| Condition | Severity |
|-----------|----------|
| Homepage has no H1 in raw HTML | HIGH |
| Inner page has no H1 in raw HTML | MEDIUM |

Finding ID: `RC12-001`
Evidence: URL, H1 present/absent, brand name found in raw HTML yes/no.

#### RC20 — Duplicate or empty page titles

Check `page_title` across all sampled pages:

| Condition | Severity |
|-----------|----------|
| Any page has empty `<title>` (or `<title>` absent) | HIGH |
| Two or more pages share the same `<title>` text | MEDIUM |
| `<title>` is present but contains only the domain name (e.g. "example.com") | MEDIUM |

Finding ID: `RC20-001`
Evidence: list page URLs and their title values.

### Step 4 — JS framework signal notes

If the script detects JS framework signals (`__NEXT_DATA__`, `ng-version`, `_nuxt/`), include this as context in the RC1 or RC9 finding evidence — it helps the developer identify which framework needs SSR configuration.

### Step 5 — Proactive suggestions

If all pages are in state A but the site uses a SPA framework, add a LOW proactive finding recommending pre-rendering or `<noscript>` fallbacks for maximum AI compatibility.

## Output

```json
{
  "skill": "render-gap-detector",
  "findings": [ /* array of finding objects per report-schema.md */ ]
}
```
