---
name: technical-seo-probe
description: Checks technical SEO foundations that AI crawlers depend on. Tests canonical tags, redirect chains, noindex/nosnippet directives, HTTPS enforcement, Core Web Vitals proxy (response time, page size), broken links, hreflang for multilingual sites, and heading hierarchy (H1-H6 nesting). These are prerequisites for AI indexability — a technically broken site cannot be cited regardless of content quality.
license: MIT
allowed-tools: web_fetch, run_script
---

# Technical SEO Probe

## When to use

Called by `audit-orchestrator` as sub-skill #10. Checks technical foundations. A site failing these checks cannot be cited by AI engines regardless of content or schema quality.

**Key insight**: Google's guidance (May 2026) states that AI features rely on the same ranking and quality systems as organic search — pages must be indexable and snippet-eligible before any GEO optimization matters.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL with `https://` prefix |

## Procedure

### Step 1 — Run the technical SEO script

```bash
python skills/technical-seo-probe/scripts/technical_check.py <url>
```

### Step 2 — Generate findings

#### TSEO-1 — HTTP not redirecting to HTTPS

Check `https_enforced`:

| Condition | Severity |
|-----------|----------|
| `http://` version of the site does NOT redirect to `https://` | HIGH |
| Redirects to HTTPS but uses 302 (temporary) instead of 301 | LOW |

Finding ID: `TSEO-001`
Evidence: HTTP URL tested, redirect status code and destination.

#### TSEO-2 — nosnippet / max-snippet:0 blocking AI citations

Check `meta_robots_tags` for `nosnippet`, `max-snippet:0`, or `noindex` on key pages:

| Condition | Severity |
|-----------|----------|
| Homepage has `noindex` | CRITICAL |
| Key pages have `nosnippet` (blocks AI Overview snippets) | HIGH |
| `max-snippet:0` on content pages | HIGH |
| `noindex` on inner pages that should be crawlable | MEDIUM |

Finding ID: `TSEO-002`
Evidence: meta robots content, X-Robots-Tag response header values.

#### TSEO-3 — Redirect chains

Check `redirect_chains`:
- Chains longer than 2 hops waste crawl budget and can cause citation bots to abandon the page.

| Condition | Severity |
|-----------|----------|
| Any URL has a redirect chain of 3+ hops | HIGH |
| 302 (temporary) redirect used for permanent moves | MEDIUM |
| Redirect loop detected | CRITICAL |

Finding ID: `TSEO-003`
Evidence: chain URL sequence, hop count, status codes.

#### TSEO-4 — Canonical tag issues

Check `canonical_issues`:

| Condition | Severity |
|-----------|----------|
| Page has no `<link rel="canonical">` | LOW |
| Canonical points to a different domain (cross-domain canonical) | MEDIUM |
| Multiple conflicting canonical tags | HIGH |
| Canonical URL returns 404 or redirect | HIGH |

Finding ID: `TSEO-004`
Evidence: canonical URL found, target URL, any conflict detected.

#### TSEO-5 — Heading hierarchy violations

Check `heading_hierarchy_violations`:
- H1-H6 must be nested correctly; skipped levels confuse AI extraction.
- Single H1 per page is required.

| Condition | Severity |
|-----------|----------|
| Multiple H1 tags on a page | MEDIUM |
| Heading levels skipped (H1 → H3, no H2) | MEDIUM |
| No H1 on any sampled page | HIGH |

Finding ID: `TSEO-005`
Evidence: heading tree for each sampled page.

#### TSEO-6 — Page response time

Check `response_time_ms` from the script (measures TTFB):

| Condition | Severity |
|-----------|----------|
| TTFB > 5000ms | HIGH |
| TTFB > 3000ms | MEDIUM |
| TTFB > 2000ms | LOW |

Finding ID: `TSEO-006`
Evidence: measured time in ms, URL tested.

#### TSEO-7 — hreflang issues (multilingual sites)

Check `hreflang_issues`:

| Condition | Severity |
|-----------|----------|
| Site serves content in multiple languages but no hreflang tags | HIGH |
| hreflang tags present but missing `x-default` | MEDIUM |
| Non-reciprocal hreflang (page A links to B, B doesn't link back to A) | MEDIUM |

Finding ID: `TSEO-007`
Evidence: languages detected, hreflang tags found, reciprocity check result.

#### TSEO-8 — Page size (HTML payload)

Check `html_size_bytes`:
- Oversized HTML (> 200KB) slows AI crawler parsing.

| Condition | Severity |
|-----------|----------|
| HTML payload > 500KB | MEDIUM |
| HTML payload > 200KB | LOW |

Finding ID: `TSEO-008`
Evidence: page URL, HTML size in KB.

#### TSEO-9 — Broken internal links

Check `broken_links`:

| Condition | Severity |
|-----------|----------|
| Any 4xx broken links found on homepage | HIGH |
| Soft-404 pages (200 status but "not found" body content) | MEDIUM |

Finding ID: `TSEO-009`
Evidence: broken URL, status code found.

## Output

```json
{
  "skill": "technical-seo-probe",
  "findings": []
}
```
