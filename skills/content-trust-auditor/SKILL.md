---
name: content-trust-auditor
description: Audits content scannability and on-page trust signals. Checks average paragraph length against the 80-word threshold (RC26), subheading density (RC26), search presence on content-heavy pages (RC27), social proof signals such as customer counts and testimonials, inline contact information, footer legal links (privacy policy, terms of service), author bylines on article pages, and breadcrumb navigation on inner pages. Use alongside eeeat-signal-checker for complete trust and credibility coverage.
license: MIT
allowed-tools: web_fetch, web_search, run_script
---

# Content Trust Auditor

## When to use

Called by `audit-orchestrator` as sub-skill #13. May also be run standalone against any URL to check content
scannability and on-page trust signals. Use alongside `eeeat-signal-checker` for complete trust and credibility
coverage.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL with `https://` prefix |

## Procedure

Run the helper script. Unlike `crawlability-probe`, this script performs the severity judgment itself and
returns ready-to-use finding objects — no separate interpretation step is needed.

```bash
python skills/content-trust-auditor/scripts/content_trust_check.py <url>
```

The script fetches the homepage (and `/about` for breadcrumb checks) and evaluates:

| Check | Finding ID | Severity |
|-------|-----------|----------|
| Average paragraph length > 80 words | `RC26-001` | MEDIUM |
| Fewer subheadings than 1 per ~300 words on pages > 500 words | `RC26-002` | LOW (proactive) |
| > 40 links with no on-site search input | `RC27-001` | MEDIUM |
| No social proof (customer counts, testimonials, ratings) in static HTML | `RC-TRUST-001` | LOW (proactive) |
| No contact info (email/phone/contact link) in static HTML | `RC-TRUST-002` | LOW (proactive) |
| Missing privacy policy or terms-of-service footer links | `RC-TRUST-003` | LOW (proactive) |
| `<article>` content with no author byline | `RC-TRUST-004` | LOW (proactive) |
| `/about` page with no breadcrumb navigation | `RC-NAV-001` | LOW (proactive) |

Take the script's `findings[]` array as-is — each finding already has `id`, `title`, `severity`, `evidence`,
and `suggested_action` per [report-schema.md](../audit-orchestrator/references/report-schema.md).

## Output

Return a JSON object:

```json
{
  "skill": "content-trust-auditor",
  "findings": [ /* array of finding objects per report-schema.md */ ]
}
```

If no issues found, return `"findings": []`.
