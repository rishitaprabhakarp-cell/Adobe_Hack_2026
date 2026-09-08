---
name: engagement-analyzer
description: Checks whether content that reaches an AI agent is useful and engaging. Tests above-fold value proposition clarity, CTA presence, paragraph length for AI scannability, response time, mobile viewport, dynamic state fallback for marketplaces, and contact/about reachability. Use when auditing on-site engagement signals. Covers RC8, RC16, RC22.
license: MIT
allowed-tools: web_fetch, run_script
---

# Engagement Analyzer

## When to use

Called by `audit-orchestrator` as sub-skill #5. May also be run standalone to audit on-site engagement quality.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL with `https://` prefix |

## Procedure

### Step 1 — Run the engagement check script

```bash
python skills/engagement-analyzer/scripts/engagement_check.py <url>
```

The script checks above-fold content, CTAs, paragraph lengths, response time, and contact reachability. Capture the JSON output.

### Step 2 — Generate findings

#### RC8 — Weak engagement signals

Evaluate `above_fold` from script output:

| Condition | Severity |
|-----------|----------|
| No H1 in first 200 static words AND no clear description paragraph | HIGH |
| H1 present but no description paragraph in first 200 words | MEDIUM |
| `cta_found` is false (no action verb link/button) | MEDIUM |
| H1 present, CTA present, but above-fold word count < 50 | LOW |

Finding ID: `RC8-001`
Evidence: first 200 words of static text, H1 text (or absent), CTAs detected (or not).

**Average paragraph length check:**
- If `avg_paragraph_word_count` > 150: agents struggle to extract and summarize key facts.
  Severity: MEDIUM. Finding ID: `RC8-002`
  Evidence: avg paragraph word count, longest paragraph snippet.

#### RC8 — Response time risk

| Condition | Severity |
|-----------|----------|
| `response_time_ms` > 5000 | HIGH |
| `response_time_ms` > 3000 | MEDIUM |
| `response_time_ms` > 2000 | LOW |

Finding ID: `RC8-003`
Evidence: measured response time in ms, target threshold.

#### RC16 — Empty alt text on key images (engagement layer)

This check overlaps with structured-data-auditor's RC16 but focuses on engagement context (hero images, product images above the fold).

Check `hero_images_missing_alt` from script output:

| Condition | Severity |
|-----------|----------|
| Hero/above-fold images have empty alt attributes | MEDIUM |

Finding ID: `RC16-002`
Evidence: image src values, count of images missing alt in above-fold section.

#### RC22 — Dynamic state with no static fallback (marketplace/booking/job-board)

The script checks `dynamic_state_signals` — indicators that the page is a marketplace, booking engine, or job board that relies on dynamic data.

| Condition | Severity |
|-----------|----------|
| Site appears to be a marketplace/booking/job-board AND static HTML has < 50 words AND no static entity data | HIGH |
| Site has dynamic content but a minimal static description is present | MEDIUM |

Finding ID: `RC22-001`
Evidence: dynamic state signals detected (e.g., listing pages, search results, no static description), word count of static content.

**Advisory for RC22**: even if no defect is detected, add a LOW proactive finding if the site has dynamic content recommending static fallback content (organization name, category, description) that AI agents can use when the dynamic content is unavailable.

#### Contact / About reachability

If `contact_reachable` is false AND `about_reachable` is false:

| Condition | Severity |
|-----------|----------|
| Neither /about nor /contact are reachable from homepage links | MEDIUM |
| Contact info (email/phone) absent from entire site | LOW |

Finding ID: `RC8-004`
Evidence: links checked, HTTP status for each.

#### Mobile viewport (agent proxy signal)

If `has_meta_viewport` is false:

Finding ID: `RC8-005`, Severity: LOW
Evidence: `<meta name="viewport">` absent. Many AI crawlers and assistants score mobile-ready pages higher.

### Step 3 — Proactive suggestions

If all engagement checks pass (no defects found), add a LOW proactive finding if:
- The page has no FAQ section (cross-references RC11 — adding FAQ content improves agent summarization)
- There is no structured contact info (telephone, email in JSON-LD `ContactPoint`)

## Output

```json
{
  "skill": "engagement-analyzer",
  "findings": [ /* array of finding objects per report-schema.md */ ]
}
```
