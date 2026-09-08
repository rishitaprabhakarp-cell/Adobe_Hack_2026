---
name: content-extractability-auditor
description: Audits whether content on a website can be extracted and cited by AI answer engines at the passage level. Checks answer-first structure (direct answer in first 40-80 words), question-format headings, paragraph length distribution, statistic density with source citations, FAQ section quality, key-takeaway boxes, hedge-word ratio, and content front-loading. Based on Princeton KDD 2024 GEO research and Directive Consulting 2026 framework. Use when auditing AI citation readiness at the content level.
license: MIT
allowed-tools: web_fetch, run_script
---

# Content Extractability Auditor

## When to use

Called by `audit-orchestrator` as sub-skill #8. Checks passage-level content structure — the dimension most ignored by traditional SEO tools but most predictive of AI citation frequency.

**Research basis**: Aggarwal et al. (Princeton/ACM KDD 2024): statistics + source citations + quotations improve AI citation by up to **40%**. CXL (2026): 55% of AI Overview citations come from the **first 30% of page content**.

## Inputs

| Field | Required | Description |
|-------|----------|-------------|
| `url` | Yes | Normalized site URL with `https://` prefix |

## Procedure

### Step 1 — Run the content extractability script

```bash
python skills/content-extractability-auditor/scripts/content_check.py <url>
```

### Step 2 — Generate findings

#### CEA-1 — No direct answer in first 40–80 words

Check `above_fold_direct_answer`:
- Does the first 40–80 words of the main content contain a direct, self-contained statement about what the brand/page does?
- "Self-contained" means: an AI can lift the paragraph and quote it without pronoun resolution.

| Condition | Severity |
|-----------|----------|
| No direct answer in first 80 words — page starts with navigation, hero image alt text, or generic welcome | HIGH |
| Direct answer present but uses unresolved pronouns ("We make it easier", "Our platform") | MEDIUM |
| Direct answer present but > 100 words before the key claim | LOW |

Finding ID: `CEA-001`
Evidence: first 100 words of extracted static text, directness assessment.

#### CEA-2 — Question-format headings absent

Check `question_headings_count` and `total_headings_count`:
- Question-format H2/H3 headings (starting with "What", "How", "Why", "When", "Which", "Can", "Does", "Is") are 40% more likely to be cited by AI engines.

| Condition | Severity |
|-----------|----------|
| 0 question-format headings across sampled pages | HIGH |
| < 20% of H2/H3 headings are question-format | MEDIUM |

Finding ID: `CEA-002`
Evidence: total heading count, question-format heading count, sample headings.

#### CEA-3 — No statistics with source attribution

Check `statistics_with_citations` vs `statistics_without_citations`:
- Statistics cited from external sources ("According to [Source], X% of...") get 40% more AI citations.
- Statistics without source ("X% of users...") are treated as unverifiable claims.

| Condition | Severity |
|-----------|----------|
| 0 statistics of any kind on homepage | MEDIUM |
| Statistics present but 0 have inline source attribution | MEDIUM |
| < 30% of statistics have source attribution | LOW |

Finding ID: `CEA-003`
Evidence: count of statistics found, count with source citation, example patterns.

#### CEA-4 — Paragraph length violations

Check `paragraph_length_violations`:
- Passages > 150 words are harder for AI to extract as atomic citations.
- Rule: no more than 3 sentences over 30 words per 10 paragraphs (Directive Consulting 2026 threshold).

| Condition | Severity |
|-----------|----------|
| > 30% of paragraphs exceed 150 words | HIGH |
| > 20% of paragraphs exceed 100 words | MEDIUM |
| Average paragraph > 80 words | LOW |

Finding ID: `CEA-004`
Evidence: paragraph count, violation count, longest paragraph snippet.

#### CEA-5 — No FAQ section

Check `has_faq_section`:
- FAQ sections with 5+ self-contained Q&A pairs are one of the highest-ROI GEO changes.
- FAQ schema lifts citation likelihood 3.2x (Directive Consulting, 2026).

| Condition | Severity |
|-----------|----------|
| No FAQ section detected on any sampled page | MEDIUM |
| FAQ section detected but < 5 Q&A pairs | LOW |

Finding ID: `CEA-005`
Evidence: FAQ detection result, Q&A pair count if found.

#### CEA-6 — No Key Takeaways / TL;DR box

Check `has_key_takeaways`:
- Summary boxes (Key Takeaways, TL;DR, Quick Summary) are extracted verbatim by AI engines.
- Their presence at the top of content creates a "quotable anchor" for AI citation.

| Condition | Severity |
|-----------|----------|
| No key-takeaway or TL;DR box on any sampled page | LOW |

Finding ID: `CEA-006`
Evidence: search patterns checked, result.

#### CEA-7 — High hedge-word ratio

Check `hedge_word_ratio`:
- Definitive language correlates with higher AI citation. Hedge words ("might", "could", "possibly", "we think", "perhaps") signal uncertain content that AI deprioritizes.
- Target: < 15% hedge words per passage.

| Condition | Severity |
|-----------|----------|
| Hedge word ratio > 25% of sentences contain hedge words | HIGH |
| Hedge word ratio 15–25% | MEDIUM |

Finding ID: `CEA-007`
Evidence: sample sentences with hedge words, ratio.

#### CEA-8 — Content freshness markers absent

Check `has_explicit_date_marker`:
- Explicit date markers ("As of September 2026", "Last updated: Q3 2026") tell AI engines the information is current without relying only on schema dateModified.

| Condition | Severity |
|-----------|----------|
| No visible date marker on pages claiming current information | MEDIUM |
| dateModified in schema exists but no visible date on page | LOW |

Finding ID: `CEA-008`
Evidence: schema dates found, visible date markers found.

#### CEA-9 — No answer capsules (highest single predictor of ChatGPT citation)

Check `answer_capsules.capsule_ratio`:
- An **answer capsule** is a ≥ 40-word direct answer immediately following an H2/H3 heading, with no preamble
  ("let me explain", "great question", "in this guide…").
- Research (Cognism, 2026): **72.4% of ChatGPT-cited pages** have at least one answer capsule per section.
- ChatGPT Search's RAG retriever scores page sections individually; a dense answer capsule is the
  single strongest trigger for that section to be selected.

| Condition | Severity |
|-----------|----------|
| 0 answer capsules found across all H2/H3 sections analyzed | HIGH |
| `capsule_ratio` < 0.33 (< 1 in 3 sections has a capsule) | MEDIUM |
| `capsule_ratio` ≥ 0.5 | PASS |

Finding ID: `CEA-009`
Evidence: `sections_analyzed`, `answer_capsules_found`, `capsule_ratio`, `examples` (first capsule openings).

#### CEA-10 — High AI-cliché density (content slop signal)

Check `ai_cliches.cliche_count`:
- AI citation engines increasingly deprioritize pages whose language patterns match known AI-generated
  "slop" phrases ("delve into", "in today's fast-paced world", "seamlessly integrate", etc.).
- Pages with high cliché density signal low substance and low first-person experience — both are
  negative E-E-A-T signals. Research: kai-cmo-harness/llm-cliche-detector, 2026.

| Condition | Severity |
|-----------|----------|
| `cliche_count` ≥ 6 Tier-1 clichés detected | HIGH |
| `cliche_count` 3–5 | MEDIUM |
| `cliche_count` 1–2 | LOW (informational) |

Finding ID: `CEA-010`
Evidence: `cliche_count`, `examples` list (up to 5 matching phrases).
Suggested action: Rewrite flagged passages with first-person experience, concrete data, and specific claims.

### Step 3 — Proactive suggestions

Even if no defects found:
- If page has lists/tables but no numbered steps for procedural content → recommend HowTo schema
- If content covers a topic authoritatively but has no pull-quotes or highlighted statistics → recommend adding quotable passages formatted for AI extraction
- If answer capsules are present but `capsule_ratio` < 0.75, add capsules to remaining sections for maximum ChatGPT citation surface

## Output

```json
{
  "skill": "content-extractability-auditor",
  "findings": []
}
```
