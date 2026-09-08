---
name: crawlability-probe
description: Checks whether AI crawlers can reach and discover a website. Tests robots.txt bot policies, llms.txt presence and validity, sitemap freshness, RSS/Atom feeds, AI discovery endpoints, and whether robots.txt policies are actually enforced. Use when auditing a site's AI crawler accessibility. Covers RC2, RC4, RC7, RC14, RC17, RC19, RC23.
license: MIT
allowed-tools: web_fetch, web_search, run_script
---

# Crawlability Probe

## When to use

Called by `audit-orchestrator` as sub-skill #1. May also be run standalone against any URL to check AI crawler accessibility.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL with `https://` prefix |

## Procedure

Run the helper script first, then apply agent-level judgment on the results.

### Step 1 — Run the crawlability script

```bash
python skills/crawlability-probe/scripts/crawlability_check.py <url>
```

The script outputs a JSON object with raw probe results. Capture it.

### Step 2 — Interpret results and generate findings

For each check below, evaluate the script output and emit a finding if the condition is met.

#### RC2 — Missing or phantom llms.txt

| Condition | Severity |
|-----------|----------|
| `llms_txt.status` is 404 / connection error | HIGH |
| `llms_txt.status` is 200 but `content_type` is not `text/plain` | MEDIUM |
| `llms_txt.status` is 200, correct content type, but file does not start with `#` | MEDIUM |
| `llms_txt.status` is 301/302 to a different domain | MEDIUM |
| `llms_txt.word_count` < 10 (skeleton/placeholder) | LOW |

Finding ID: `RC2-001`
Evidence: include HTTP status, content-type header, first 100 chars of body.

#### RC4 — AI crawler misconfiguration in robots.txt

Check `robots_txt.bots` for all 27 AI user-agents across 3 tiers (sourced from geo-optimizer-skill research, 2026):

**Tier 1 — Citation/Retrieval bots** (blocking these prevents AI citation):
`GPTBot`, `ChatGPT-User`, `OAI-SearchBot`, `ClaudeBot`, `Claude-Web`, `anthropic-ai`, `PerplexityBot`, `Perplexity-User`, `Gemini-Web`, `Google-Extended`, `BingBot-AI`, `YouBot`

**Tier 2 — Training bots** (blocking these is acceptable for most sites):
`CCBot`, `Applebot-Extended`, `Amazonbot`, `DuckAssistBot`, `FacebookBot`, `cohere-ai`, `AI2Bot`

**Tier 3 — Emerging/niche bots** (low impact currently):
`Bytespider`, `PetalBot`, `SemrushBot`, `AhrefsBot`, `DataForSeoBot`, `MJ12bot`, `ia_archiver`

Distinguish between:
- **Tier 1 (Citation bots)**: blocking ANY of these prevents AI citation — CRITICAL/HIGH severity.
- **Tier 2 (Training bots)**: acceptable to block; sites often do this for copyright reasons.
- **Tier 3**: informational only.

| Condition | Severity |
|-----------|----------|
| ≥ 2 citation bots fully blocked (`Disallow: /`) | CRITICAL |
| 1 citation bot fully blocked | HIGH |
| Citation bot partially blocked (specific high-value paths) | MEDIUM |
| No explicit allow/disallow for any AI bot (no entry at all) | LOW |

Finding ID: `RC4-001`
Evidence: list each affected bot and its `Disallow` rules.

#### RC7 — Phantom or broken llms.txt

If `llms_txt.status` is 200 but the file:
- redirects more than once before resolving
- has `content_type` that is HTML (not text/plain)
- contains `<html` in the first 200 bytes

Severity: MEDIUM. Finding ID: `RC7-001`
Evidence: redirect chain, content-type, first 200 bytes of body.

#### RC14 — No AI discovery endpoints

Check `ai_endpoints` results:
- `/.well-known/ai.txt` — 200 OK?
- `/ai/summary.json` — 200 OK?

| Condition | Severity |
|-----------|----------|
| Both endpoints return 404 | LOW |
| One endpoint returns 404 | LOW (info only) |

Finding ID: `RC14-001`
Evidence: HTTP status for each endpoint.

#### RC17 — No RSS/Atom feed

Check `feeds` results for `/feed`, `/rss.xml`, `/atom.xml`, `/feed.xml`.

| Condition | Severity |
|-----------|----------|
| No feed endpoint returns 200 | MEDIUM |
| Feed found but `content_type` is not `application/rss+xml` / `application/atom+xml` / `text/xml` | LOW |

Finding ID: `RC17-001`
Evidence: HTTP status for each tested feed URL.

#### RC19 — Sitemap absent or stale

Check `sitemap` results:
- Is sitemap declared in robots.txt (`Sitemap:` directive)?
- Does the sitemap URL return 200?
- Does it contain `<lastmod>` dates?
- Are > 50% of lastmod dates within the last 90 days (for sites with fresh content)?

| Condition | Severity |
|-----------|----------|
| No `Sitemap:` in robots.txt AND no sitemap at `/sitemap.xml` | HIGH |
| Sitemap present but all `<lastmod>` dates are > 180 days old | MEDIUM |
| Sitemap present but no `<lastmod>` dates at all | LOW |

Finding ID: `RC19-001`
Evidence: sitemap URL, HTTP status, lastmod date range.

#### CDN-WAF-001 — CDN/WAF silently blocks citation bots (independent of robots.txt)

Check `bot_enforcement[*].cdn_waf_blocked` and `bot_enforcement[*].content_ratio_vs_browser`:

The most common silent citation killer: Cloudflare's "Block AI Bots" toggle, AWS WAF bot rules, or
similar CDN-layer blocks operate *at the edge* before robots.txt is ever consulted. A site may have
perfectly open robots.txt yet be invisible to every AI citation engine.

| Condition | Severity |
|-----------|----------|
| Any citation bot gets HTTP 403/429/503 or Cloudflare "Just a moment" page | CRITICAL |
| Citation bot returns < 30% of words compared to browser baseline | HIGH |
| Citation bot gets 200 OK but CDN challenge page body (no actual content) | HIGH |

Finding ID: `CDN-WAF-001`
Evidence: bot UA, actual HTTP status, CDN indicator phrases found in body, content_ratio_vs_browser.
Suggested action: Disable "Block AI Bots" in Cloudflare or equivalent WAF rule for Tier 1 citation bots.

#### CDN-WAF-002 — GPTBot blocked but OAI-SearchBot allowed (or vice versa — policy mismatch)

Check `oai_searchbot_policy`:

**Critical distinction (seoprocheck/ai-crawler-audit research, 2026):**
- `GPTBot` = OpenAI's training data crawl — acceptable to block
- `OAI-SearchBot` = ChatGPT Search RAG index crawler — blocking = invisible to ChatGPT citations
- `ChatGPT-User` = user-triggered browsing in ChatGPT — blocking = ChatGPT can't browse to your site

Many sites block `GPTBot` for copyright reasons but intend to allow citations — they do NOT realize
`OAI-SearchBot` is a completely separate bot. This creates a false sense of "I allow OpenAI access."

| Condition | Severity |
|-----------|----------|
| `GPTBot` blocked AND `OAI-SearchBot` also blocked | CRITICAL (invisible to ChatGPT Search) |
| `OAI-SearchBot` blocked, `GPTBot` allowed | HIGH (training crawl allowed, citation blocked — unusual but harmful) |
| `GPTBot` blocked, `OAI-SearchBot` allowed, `ChatGPT-User` blocked | MEDIUM (direct browse blocked) |

Finding ID: `CDN-WAF-002`
Evidence: `oai_searchbot_policy` object with individual bot flags and `policy_note`.

#### RC23 — robots.txt policy vs actual content gap

The script tests whether a citation bot blocked by robots.txt still receives full HTML content
(server does not enforce the disallow). Also checks CDN/WAF-level enforcement via UA simulation
and content ratio comparison against browser baseline.

| Condition | Severity |
|-----------|----------|
| A citation bot is `Disallow: /` in robots.txt but the server still returns full HTML when that bot UA is used | HIGH |
| A citation bot is partially disallowed but the server returns full HTML on those paths | MEDIUM |
| Citation bot gets < 30% of browser word count (JS-dependent; bots can't render) | HIGH |

Finding ID: `RC23-001`
Evidence: user-agent used, path tested, robots.txt rule, HTTP status and word count of actual response.

### Step 3 — Proactive suggestions

Even if no defects are found, add a LOW/proactive finding if:
- `llms_txt` exists but has no links to inner pages (add more links)
- `robots.txt` has no explicit AI bot section at all (add explicit `Allow: /` for citation bots)

## Output

Return a JSON object:

```json
{
  "skill": "crawlability-probe",
  "findings": [ /* array of finding objects per report-schema.md */ ]
}
```

If no issues found, return `"findings": []`.
