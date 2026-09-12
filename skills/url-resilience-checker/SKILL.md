---
name: url-resilience-checker
description: Tests URL integrity for AI-cited pages. Detects catch-all redirects where non-existent URLs silently serve homepage content (RC29) — the critical failure mode when AI assistants cite expired pages and users land with no context. Also checks redirect chain depth on key pages, samples dead URLs in llms.txt and sitemap.xml, and verifies whether a dedicated AI-referrer landing page exists at /from/ai (RC30). Use after crawlability-probe.
license: MIT
allowed-tools: web_fetch, web_search, run_script
---

# URL Resilience Checker

## When to use

Called by `audit-orchestrator` as sub-skill #14. Run after `crawlability-probe` to verify that URLs cited by AI
assistants resolve correctly and don't silently redirect to the homepage, breaking the AI handoff experience.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL with `https://` prefix |

## Procedure

Run the helper script. It performs the severity judgment itself and returns ready-to-use finding objects —
no separate interpretation step is needed.

```bash
python skills/url-resilience-checker/scripts/url_resilience_check.py <url>
```

The script probes the site and evaluates:

| Check | Finding ID | Severity |
|-------|-----------|----------|
| A random non-existent URL returns HTTP 200 or redirects to the homepage (catch-all) | `RC29-001` | HIGH |
| Homepage/`/about`/`/pricing` redirect chain > 2 hops | `RC29-002` | MEDIUM |
| Dead URLs found when sampling links listed in `llms.txt` | `RC29-003` | HIGH |
| Dead URLs found when sampling links listed in `sitemap.xml` | `RC29-004` | MEDIUM |
| No dedicated AI-referrer landing page at `/from/ai`, `/ai-landing`, or `/ai` | `RC30-002` | LOW (proactive) |

Take the script's `findings[]` array as-is — each finding already has `id`, `title`, `severity`, `evidence`,
and `suggested_action` per [report-schema.md](../audit-orchestrator/references/report-schema.md).

## Output

Return a JSON object:

```json
{
  "skill": "url-resilience-checker",
  "findings": [ /* array of finding objects per report-schema.md */ ]
}
```

If no issues found, return `"findings": []`.
