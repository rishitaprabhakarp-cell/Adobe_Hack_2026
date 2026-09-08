---
name: opengraph-meta-auditor
description: Audits OpenGraph tags, Twitter Card meta, canonical URLs, meta descriptions, and AI-specific meta signals (nosnippet, max-snippet) across sampled pages. OpenGraph tags are used by AI engines as fallback metadata when JSON-LD is absent or incomplete. Checks og:title, og:description, og:image, og:type, og:site_name, twitter:card completeness, and whether meta description is AI-quotable. Use when auditing metadata completeness for AI citation readiness.
license: MIT
allowed-tools: web_fetch, run_script
---

# OpenGraph & Meta Auditor

## When to use

Called by `audit-orchestrator` as sub-skill #11. Checks meta-layer signals. AI engines fall back to OG tags when JSON-LD is absent — a weak or missing og:description means the AI has nothing to quote from for the brand's page preview.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL with `https://` prefix |

## Procedure

### Step 1 — Run the OpenGraph audit script

```bash
python skills/opengraph-meta-auditor/scripts/og_audit.py <url>
```

### Step 2 — Generate findings

#### OG-1 — Missing or weak og:description

Check `og_description` from script:

| Condition | Severity |
|-----------|----------|
| `og:description` absent | HIGH |
| `og:description` present but < 50 chars | HIGH |
| `og:description` matches `<meta name="description">` exactly (duplicate, not optimized) | LOW |
| `og:description` > 300 chars (gets truncated by AI engines) | MEDIUM |

Finding ID: `OG-001`
Evidence: og:description value (or absent), char count.

**Note**: A strong `og:description` should be 120–160 chars, contain the brand name + core value prop, and be written as a quotable fact (not marketing copy).

#### OG-2 — Missing og:image

Check `og_image`:

| Condition | Severity |
|-----------|----------|
| `og:image` absent | MEDIUM |
| `og:image` present but returns 404 | HIGH |
| `og:image` is not absolute URL (relative URL breaks off-site AI rendering) | MEDIUM |
| No `og:image:alt` (alt text for AI accessibility) | LOW |

Finding ID: `OG-002`
Evidence: og:image URL, HTTP status of image, alt text present/absent.

#### OG-3 — Missing or wrong og:type

Check `og_type`:

| Condition | Severity |
|-----------|----------|
| `og:type` absent | LOW |
| Article pages use `og:type = website` instead of `article` | MEDIUM |
| Product pages use `og:type = website` instead of `product` | MEDIUM |

Finding ID: `OG-003`
Evidence: og:type value, expected type for page content.

#### OG-4 — Twitter Card incomplete

Check `twitter_card`:

| Condition | Severity |
|-----------|----------|
| `twitter:card` absent | LOW |
| `twitter:card` present but `twitter:description` absent | LOW |
| `twitter:image` absent | LOW |

Finding ID: `OG-004`
Evidence: twitter card tags found/absent.

#### OG-5 — Meta description quality

Check `meta_description`:

| Condition | Severity |
|-----------|----------|
| Meta description absent on any sampled page | HIGH |
| Meta description < 50 chars | HIGH |
| Meta description is generic ("Welcome to Example.com") | HIGH |
| Duplicate meta description across pages | MEDIUM |
| Meta description > 160 chars (truncated in AI snippets) | LOW |

Finding ID: `OG-005`
Evidence: meta description value per page, char count, uniqueness check.

#### OG-6 — Meta author absent on article pages

Check `meta_author`:

| Condition | Severity |
|-----------|----------|
| Blog/article pages have no `<meta name="author">` or author byline | MEDIUM |

Finding ID: `OG-006`
Evidence: pages checked, author meta found/absent.

#### OG-7 — og:site_name inconsistency

Check `og_site_name` against brand name from entity-corroboration-checker:

| Condition | Severity |
|-----------|----------|
| `og:site_name` absent | LOW |
| `og:site_name` differs from Organization JSON-LD `name` | MEDIUM |

Finding ID: `OG-007`
Evidence: og:site_name value, Organization JSON-LD name value.

#### OG-8 — Markdown alternate route (emerging AI standard)

Check for `<link rel="alternate" type="text/markdown" href="...">`:
- A small but growing number of AI agents (especially those trained on GitHub data) prefer Markdown versions of pages. Advertising a Markdown alternate is an emerging signal.

| Condition | Severity |
|-----------|----------|
| No Markdown alternate link (informational only) | LOW |

Finding ID: `OG-008`
Evidence: link tags found. Mark `proactive: true`.

## Output

```json
{
  "skill": "opengraph-meta-auditor",
  "findings": []
}
```
