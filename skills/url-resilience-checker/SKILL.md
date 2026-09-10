---
name: url-resilience-checker
description: Tests URL integrity for AI-cited pages. Detects catch-all redirects where non-existent URLs silently serve homepage content (RC29) — the critical failure mode when AI assistants cite expired pages and users land with no context. Also checks redirect chain depth on key pages, samples dead URLs in llms.txt and sitemap.xml, and verifies whether a dedicated AI-referrer landing page exists at /from/ai (RC30). Use after crawlability-probe.
license: MIT
allowed-tools: web_fetch, web_search, run_script
---

# URL Resilience Checker

## When to use

Run to verify that URLs cited by AI assistants resolve correctly and don't silently redirect to the homepage, breaking the AI handoff experience.

## Output

Returns `findings[]` (RC29, RC30 IDs) and `checks{}` with redirect and URL health data.
