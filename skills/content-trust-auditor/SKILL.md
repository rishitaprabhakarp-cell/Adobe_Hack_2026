---
name: content-trust-auditor
description: Audits content scannability and on-page trust signals. Checks average paragraph length against the 80-word threshold (RC26), subheading density (RC26), search presence on content-heavy pages (RC27), social proof signals such as customer counts and testimonials, inline contact information, footer legal links (privacy policy, terms of service), author bylines on article pages, and breadcrumb navigation on inner pages. Use alongside eeeat-signal-checker for complete trust and credibility coverage.
license: MIT
allowed-tools: web_fetch, web_search, run_script
---

# Content Trust Auditor

## When to use

Run on any site to check readability, scannability, and trust markers that AI assistants use to evaluate page credibility and authority.

## Output

Returns `findings[]` (RC26, RC27, RC-TRUST, RC-NAV IDs) and `checks{}` with raw signal counts.
