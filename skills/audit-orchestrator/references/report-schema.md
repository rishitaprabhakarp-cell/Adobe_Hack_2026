# Audit Report Schema

## Top-level fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `site` | string | Yes | Bare hostname audited, e.g. `example.com` |
| `audited_at` | string | Yes | ISO-8601 UTC timestamp of audit start |
| `summary` | object | Yes | Severity bucket counts (see below) |
| `findings` | array | Yes | Ordered list of finding objects (CRITICAL first) |

## summary object

| Field | Type | Description |
|-------|------|-------------|
| `total_findings` | integer | Total number of unique findings |
| `critical` | integer | Count of CRITICAL findings |
| `high` | integer | Count of HIGH findings |
| `medium` | integer | Count of MEDIUM findings |
| `low` | integer | Count of LOW findings |

## finding object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique finding ID. Format: `<RC-code>-<NNN>`, e.g. `RC1-001`. Use `ORCH-ERR-<skill>` for orchestrator-level errors. |
| `title` | string | Yes | Short, human-readable title of the finding (≤ 80 chars) |
| `severity` | string | Yes | One of (lowercase, exact): `critical`, `high`, `medium`, `low`. Sub-skills and internal severity tables reason in uppercase for readability — lowercase only when writing the final `severity` value into this report. |
| `evidence` | string | Yes | Concrete evidence observed (URL, count, snippet, word count, etc.) |
| `suggested_action` | object | Yes | Recommended fix (see below) |

## suggested_action object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `summary` | string | Yes | What to change and how. Be specific and mechanism-sound. |
| `priority` | string | Yes | One of: `high`, `medium`, `low` |
| `effort` | string | No | Estimated implementation effort: `low`, `medium`, `high` |
| `proactive` | boolean | No | `true` if this is a proactive improvement (no defect detected), `false` if fixing a detected problem |

## Severity criteria

| Severity | Meaning |
|----------|---------|
| `CRITICAL` | AI crawlers cannot access or parse any meaningful content. Brand is effectively invisible to AI assistants. Immediate action required. |
| `HIGH` | Significant content or signal loss. Brand is likely under-cited or misrepresented. Fix within sprint. |
| `MEDIUM` | Partial signal loss or missing best-practice signals. Brand may be cited inaccurately or incompletely. Fix in next release. |
| `LOW` | Minor gap or proactive improvement opportunity. Brand discoverability is acceptable but could be strengthened. |

## Example report

```json
{
  "site": "acme.com",
  "audited_at": "2026-09-08T10:00:00Z",
  "summary": {
    "total_findings": 4,
    "critical": 1,
    "high": 1,
    "medium": 1,
    "low": 1
  },
  "findings": [
    {
      "id": "RC1-001",
      "title": "Homepage is fully JS-rendered — content invisible to AI crawlers",
      "severity": "critical",
      "evidence": "Fetching homepage with Googlebot UA returned 12 words and <div id='root'></div> SPA shell. No H1 or meta description found in raw HTML.",
      "suggested_action": {
        "summary": "Implement server-side rendering (SSR) or static generation for the homepage. At minimum, ensure the H1, meta description, and Organization JSON-LD are present in the initial HTML response before any JavaScript executes.",
        "priority": "high",
        "effort": "high",
        "proactive": false
      }
    },
    {
      "id": "RC2-001",
      "title": "llms.txt absent — AI citation bots have no structured content manifest",
      "severity": "high",
      "evidence": "GET https://acme.com/llms.txt returned HTTP 404.",
      "suggested_action": {
        "summary": "Create /llms.txt following the llms.txt spec (https://llmstxt.org). Include a # heading, a brief description, and links to key pages (about, product, docs). Serve as text/plain.",
        "priority": "high",
        "effort": "low",
        "proactive": false
      }
    },
    {
      "id": "RC3-001",
      "title": "No JSON-LD structured data on product pages",
      "severity": "medium",
      "evidence": "Sampled 3 product pages (/product/a, /product/b, /product/c). 0/3 contain any schema.org JSON-LD blocks.",
      "suggested_action": {
        "summary": "Add Product and Offer JSON-LD to every product page. Include at minimum: @type, name, description, url, brand, and offers. Rich schema increases citation frequency by ~61% in AI assistant responses.",
        "priority": "medium",
        "effort": "medium",
        "proactive": false
      }
    },
    {
      "id": "RC10-001",
      "title": "speakable schema absent — audio AI assistants cannot identify quotable passages",
      "severity": "low",
      "evidence": "No speakable property found in any JSON-LD block across homepage and sampled pages.",
      "suggested_action": {
        "summary": "Add speakable JSON-LD to key landing pages, marking the H1 and the first paragraph as speakable. This improves citations in voice and audio AI surfaces.",
        "priority": "low",
        "effort": "low",
        "proactive": true
      }
    }
  ]
}
```
