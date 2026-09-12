---
name: landing-clarity-auditor
description: Audits the first-5-second landing experience for AI-referred visitors. Checks H1 presence and conciseness (RC24), navigation item count against Miller's Law max of 7 (RC25), above-fold CTA density (RC28), and AI-referrer handling signals such as utm_source detection, document.referrer logic, or a dedicated /from/ai page (RC30). Use after crawlability-probe and before report generation to surface engagement-layer gaps.
license: MIT
allowed-tools: web_fetch, web_search, run_script
---

# Landing Clarity Auditor

## When to use

Called by `audit-orchestrator` as sub-skill #12. Run after crawlability confirms the site is reachable. Targets
the engagement dimension — specifically why AI-referred visitors bounce within the first 5 seconds.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL with `https://` prefix |

## Procedure

Run the helper script. It performs the severity judgment itself and returns ready-to-use finding objects —
no separate interpretation step is needed.

```bash
python skills/landing-clarity-auditor/scripts/landing_clarity_check.py <url>
```

The script fetches the homepage and evaluates:

| Check | Finding ID | Severity |
|-------|-----------|----------|
| No `<h1>` on homepage | `RC24-001` | HIGH |
| H1 present but > 15 words (not a clear elevator pitch) | `RC24-002` | MEDIUM |
| No above-fold summary (no first paragraph, meta description, or og:description) | `RC24-003` | MEDIUM |
| Meta description present but < 50 chars | `RC24-004` | LOW (proactive) |
| Navigation items > 7 (Miller's Law) | `RC25-001` | MEDIUM |
| More than 3 CTA elements (buttons + action links) in first viewport | `RC28-001` | MEDIUM |
| No AI-referrer handling signal (`utm_source`, `document.referrer`, `/from/ai` page, etc.) | `RC30-001` | LOW (proactive) |

Take the script's `findings[]` array as-is — each finding already has `id`, `title`, `severity`, `evidence`,
and `suggested_action` per [report-schema.md](../audit-orchestrator/references/report-schema.md).

## Output

Return a JSON object:

```json
{
  "skill": "landing-clarity-auditor",
  "findings": [ /* array of finding objects per report-schema.md */ ]
}
```

If no issues found, return `"findings": []`.
