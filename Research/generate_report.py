#!/usr/bin/env python3
"""
generate_report.py — Brand AI Readiness Audit · Multi-Format Report Generator
==============================================================================
Usage:
    python generate_report.py <audit_output_dir> [options]

Reads the 10 JSON outputs produced by run_audit_live.sh from <audit_output_dir>,
merges them into a unified report, then renders it in the requested formats.

Options:
    --format html,md,pdf,json   Comma-separated formats (default: html,md)
    --output-dir <path>         Where to write reports (default: <audit_output_dir>/reports)
    --brand-name <str>          Brand name in report title (default: inferred from domain)
    --brand-color <hex>         Accent color for HTML/PDF (default: #0066CC)
    --site <url>                Override site URL displayed in report
    --help

Formats:
    html    Self-contained single HTML file with inline SVG charts, no dependencies.
            Best for sharing via email or Slack.
    md      GitHub-flavored Markdown. Pastes into Notion/Confluence/GitHub wikis.
    pdf     Professional single-page PDF via weasyprint (pip install weasyprint).
            Falls back to a "print this HTML" instruction if weasyprint is missing.
    json    Unified enriched JSON merging all 10 skill outputs + GEO scores.
"""

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ══════════════════════════════════════════════════════════════════════════════
# 1. MERGER — reads 10 JSON files, produces a unified AuditReport dict
# ══════════════════════════════════════════════════════════════════════════════

SKILL_FILES = {
    "crawlability": "crawlability.json",
    "render":       "render.json",
    "schema":       "schema.json",
    "entity":       "entity.json",
    "content":      "content.json",
    "eeeat":        "eeeat.json",
    "engagement":   "engagement.json",
    "rsl":          "rsl.json",
    "opengraph":    "opengraph.json",
    "technical":    "technical.json",
}

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def load_skill_outputs(audit_dir: Path) -> dict[str, Any]:
    """Load all available skill JSON outputs from the audit directory."""
    outputs = {}
    for skill, filename in SKILL_FILES.items():
        path = audit_dir / filename
        if path.exists():
            try:
                with open(path) as f:
                    outputs[skill] = json.load(f)
            except json.JSONDecodeError as e:
                print(f"  ⚠  {skill}: invalid JSON — {e}", file=sys.stderr)
        else:
            print(f"  ⚠  {skill}: file not found ({path})", file=sys.stderr)
    return outputs


# ── Dimension definitions ────────────────────────────────────────────────────

DIMENSIONS = [
    {"id": "D1", "name": "Crawlability",           "weight_key": "crawl",   "finding_prefixes": ["RC2","RC4","RC7","RC14","RC17","RC19","RC23","CDN-WAF","RSL"]},
    {"id": "D2", "name": "Content Extractability", "weight_key": "content", "finding_prefixes": ["CEA","RC8","RC11","FRESH"]},
    {"id": "D3", "name": "Entity Clarity",         "weight_key": "entity",  "finding_prefixes": ["RC5","RC6","EEAT-007","CITE-003","CITE-004"]},
    {"id": "D4", "name": "Schema Integrity",       "weight_key": "schema",  "finding_prefixes": ["RC3","RC10","RC11","RC13","RC15","RC18","RC21","OG-007","SC-"]},
    {"id": "D5", "name": "Off-Page Authority",     "weight_key": "authority","finding_prefixes": ["EEAT","CITE-001","CITE-002","RC6"]},
    {"id": "D6", "name": "Technical Foundation",   "weight_key": "technical","finding_prefixes": ["RC1","RC9","RC12","RC20","TSEO","OG-00","IMG-"]},
]

ENGINE_WEIGHTS = {
    "ChatGPT":             {"crawl":.15,"content":.20,"entity":.25,"schema":.20,"authority":.15,"technical":.05},
    "Perplexity":          {"crawl":.20,"content":.25,"entity":.15,"schema":.15,"authority":.20,"technical":.05},
    "Google AI Overviews": {"crawl":.15,"content":.15,"entity":.15,"schema":.25,"authority":.15,"technical":.15},
    "Gemini":              {"crawl":.15,"content":.18,"entity":.18,"schema":.22,"authority":.15,"technical":.12},
    "Bing Copilot":        {"crawl":.20,"content":.20,"entity":.15,"schema":.15,"authority":.20,"technical":.10},
}


def extract_findings_from_outputs(outputs: dict[str, Any]) -> list[dict]:
    """
    Extract and synthesise findings from raw skill outputs.
    Returns a list of finding dicts matching the report schema.
    """
    findings = []

    # ── crawlability ──────────────────────────────────────────────────────────
    craw = outputs.get("crawlability", {})
    if craw:
        rt = craw.get("robots_txt", {})
        llms = craw.get("llms_txt", {})
        sitemap = craw.get("sitemap", {})
        feeds = craw.get("feeds", [])
        ai_eps = craw.get("ai_endpoints", [])
        bot_enf = craw.get("bot_enforcement", [])
        oai = craw.get("oai_searchbot_policy", {})

        # llms.txt — check both "present" key and status code directly
        llms_present = llms.get("present") or llms.get("status") == 200
        if not llms_present:
            findings.append({"id": "RC2-001", "title": "llms.txt absent or unreachable",
                "severity": "HIGH",
                "evidence": f"GET /llms.txt returned HTTP {llms.get('status', '?')}.",
                "suggested_action": {"summary": "Create /llms.txt following the llmstxt.org spec.", "priority": "high", "effort": "low"}})

        # AI citation bots blocked
        bots = rt.get("bots", {})
        blocked_citation = [b for b, v in bots.items() if v.get("fully_blocked") and b in
            ["GPTBot","ChatGPT-User","OAI-SearchBot","ClaudeBot","Claude-Web","anthropic-ai",
             "PerplexityBot","Perplexity-User","Gemini-Web","Google-Extended","BingBot-AI","YouBot"]]
        if blocked_citation:
            sev = "CRITICAL" if len(blocked_citation) >= 2 else "HIGH"
            findings.append({"id": "RC4-001", "title": f"{len(blocked_citation)} AI citation bot(s) blocked in robots.txt",
                "severity": sev,
                "evidence": f"Blocked bots: {', '.join(blocked_citation)}.",
                "suggested_action": {"summary": "Add explicit Allow: / for citation bots in robots.txt.", "priority": "high", "effort": "low"}})

        # CDN/WAF blocks
        cdn_blocked = [e["bot"] for e in bot_enf if e.get("cdn_waf_blocked")]
        if cdn_blocked:
            findings.append({"id": "CDN-WAF-001", "title": "CDN/WAF silently blocking AI citation bots",
                "severity": "CRITICAL",
                "evidence": f"CDN-level block detected for: {', '.join(cdn_blocked)}. This overrides robots.txt.",
                "suggested_action": {"summary": "Disable 'Block AI Bots' in Cloudflare or equivalent WAF rule.", "priority": "high", "effort": "low"}})

        # Low content ratio — only flag if not a timeout (error=None) and browser baseline > 0
        low_ratio = [
            e for e in bot_enf
            if e.get("content_ratio_vs_browser", 1) < 0.3
            and not e.get("cdn_waf_blocked")
            and not e.get("error")  # skip timeout errors — not a real block signal
            and e.get("browser_baseline_words", 0) > 50  # only flag if browser got real content
        ]
        if low_ratio:
            bots_lr = [e["bot"] for e in low_ratio]
            findings.append({"id": "RC23-001", "title": "Citation bots receive < 30% of browser content",
                "severity": "HIGH",
                "evidence": f"JS-dependent pages: {', '.join(bots_lr)} got < 30% of browser word count.",
                "suggested_action": {"summary": "Implement SSR or pre-rendering so bots receive full HTML.", "priority": "high", "effort": "high"}})

        # OAI-SearchBot policy mismatch
        if oai.get("both_blocked"):
            findings.append({"id": "CDN-WAF-002", "title": "GPTBot AND OAI-SearchBot both blocked — invisible to ChatGPT Search",
                "severity": "CRITICAL",
                "evidence": "Both GPTBot (training) and OAI-SearchBot (citation RAG) are blocked. ChatGPT Search cannot index this site.",
                "suggested_action": {"summary": "Unblock OAI-SearchBot. Keep GPTBot blocked if desired (training only).", "priority": "high", "effort": "low"}})

        # Sitemap — handle both list and dict formats
        if isinstance(sitemap, list):
            has_sitemap = any(s.get("status") == 200 for s in sitemap)
        elif isinstance(sitemap, dict):
            has_sitemap = sitemap.get("status") == 200
        else:
            has_sitemap = False
        if not has_sitemap:
            findings.append({"id": "RC19-001", "title": "XML sitemap absent or unreachable",
                "severity": "HIGH",
                "evidence": "No sitemap returning HTTP 200 found at /sitemap.xml or via robots.txt Sitemap: directive.",
                "suggested_action": {"summary": "Create and submit /sitemap.xml with <lastmod> dates.", "priority": "high", "effort": "low"}})

        # RSS feed
        has_feed = any(f.get("status") == 200 for f in feeds)
        if not has_feed:
            findings.append({"id": "RC17-001", "title": "No RSS/Atom feed found",
                "severity": "MEDIUM",
                "evidence": "Checked /feed, /rss.xml, /atom.xml, /feed.xml — all returned non-200. Perplexity, Bing Copilot, and AI news agents actively consume RSS/Atom feeds to discover and rank fresh content.",
                "suggested_action": {"summary": "Create an RSS/Atom feed. Perplexity and AI news agents index feeds for freshness.", "priority": "medium", "effort": "low"},
                "research_lift": "RSS feeds indexed by Perplexity/Bing AI for freshness signals — absence = stale content perception"})

        # AI discovery endpoints (only add if RSL skill didn't run — avoids duplicate with RSL-003)
        ep_present = [e["path"] for e in ai_eps if e.get("present")]
        if not ep_present and "rsl" not in outputs:
            findings.append({"id": "RC14-001", "title": "No AI discovery endpoints present",
                "severity": "MEDIUM",
                "evidence": f"Checked {len(ai_eps)} AI discovery paths — none return HTTP 200.",
                "suggested_action": {"summary": "Deploy /.well-known/ai.txt and /ai/summary.json as a minimum start.", "priority": "medium", "effort": "low"}})

    # ── render gap ────────────────────────────────────────────────────────────
    render = outputs.get("render", {})
    if render:
        rg = render.get("render_gap", {})
        delta = rg.get("word_delta")
        if delta and delta > 200:
            findings.append({"id": "RC1-001", "title": f"Significant JS render gap: {delta} words only visible after JS executes",
                "severity": "CRITICAL" if delta > 500 else "HIGH",
                "evidence": f"Static HTML has {rg.get('static_word_count', '?')} words; JS adds {delta} more words invisible to crawlers.",
                "suggested_action": {"summary": "Implement SSR or static generation for all content above the fold.", "priority": "high", "effort": "high"}})

    # ── schema ────────────────────────────────────────────────────────────────
    schema = outputs.get("schema", {})
    if schema:
        types = list(schema.get("schemas", {}).keys()) + schema.get("site_schema_types", [])
        if not types:
            # Try extracting from pages
            for page in schema.get("pages", []):
                for block in page.get("jsonld_blocks", []):
                    graph = block.get("@graph", [block])
                    for item in graph:
                        t = item.get("@type")
                        if t:
                            if isinstance(t, list):
                                types.extend(t)
                            else:
                                types.append(t)
            types = list(set(types))

        if not any(t in types for t in ["Organization", "Corporation", "LocalBusiness"]):
            findings.append({"id": "RC3-001", "title": "No Organization schema detected",
                "severity": "HIGH",
                "evidence": "No Organization, Corporation, or LocalBusiness @type found in JSON-LD. Without this, AI engines cannot reliably associate the site with a named brand entity — critical for Knowledge Graph inclusion.",
                "suggested_action": {"summary": "Add Organization JSON-LD with name, url, logo, and sameAs to every page.", "priority": "high", "effort": "low"},
                "research_lift": "Organization schema → confirmed Knowledge Graph inclusion; Onely 5,000-site study: schema presence = +34% AI citation rate"})

        if not schema.get("site_has_speakable") and not any("Speakable" in str(t) for t in types):
            findings.append({"id": "SC-001", "title": "No Speakable schema",
                "severity": "MEDIUM",
                "evidence": "site_has_speakable=False. No SpeakableSpecification markup found. Speakable markup tells Google and voice assistants exactly which passages to read aloud or surface in AI Overview snippets.",
                "suggested_action": {"summary": "Add Speakable schema to product descriptions and key content sections.", "priority": "medium", "effort": "low"},
                "research_lift": "Speakable markup → eligible for Google AI Overviews voice-snippet selection (Google Search Central, 2026)"})

        if not schema.get("site_has_faqpage"):
            findings.append({"id": "SC-002", "title": "No FAQPage schema",
                "severity": "MEDIUM",
                "evidence": "site_has_faqpage=False.",
                "suggested_action": {"summary": "Add FAQPage + Question + Answer schema to key landing pages.", "priority": "medium", "effort": "medium"}})

        # Missing image alts
        all_missing_alts = []
        for page in schema.get("pages", []):
            all_missing_alts.extend(page.get("images_missing_alt", []))
        if len(all_missing_alts) >= 3:
            findings.append({"id": "IMG-001", "title": f"{len(all_missing_alts)} images missing alt text",
                "severity": "MEDIUM",
                "evidence": f"{len(all_missing_alts)} images have no alt attribute. Examples: {', '.join(all_missing_alts[:3])}{'...' if len(all_missing_alts)>3 else ''}. Alt text is the only machine-readable content signal for images; absent = invisible to AI crawlers.",
                "suggested_action": {"summary": "Add descriptive alt text to all images. Alt text is an AI-indexable content signal.", "priority": "medium", "effort": "low"},
                "research_lift": "Alt text present → images indexed as content by AI crawlers; each image = additional citation surface"})

    # ── content extractability ────────────────────────────────────────────────
    content = outputs.get("content", {})
    if content:
        for page in content.get("pages", [])[:2]:
            url_label = page.get("path", "/")

            above = page.get("above_fold", {})
            if not above.get("has_direct_claim"):
                findings.append({"id": "CEA-001", "title": f"No direct answer in first 80 words ({url_label})",
                    "severity": "HIGH",
                    "evidence": f"First 80 words contain no direct, self-contained brand/product claim. Snippet: \"{above.get('first_80_words','')[:120]}...\". AI engines extract the lede to populate brand descriptions in summaries.",
                    "suggested_action": {"summary": "Open the page with a clear, self-contained statement of what the brand/product does.", "priority": "high", "effort": "low"},
                    "research_lift": "Answer-first structure → +17.3% citation rate (AuthorityTech 2026); top-of-page content = 44% of all AI citations (Surfer SEO 2026)"})

            caps = page.get("answer_capsules", {})
            ratio = caps.get("capsule_ratio", 1)
            if ratio < 0.5 and caps.get("sections_analyzed", 0) > 0:
                sev = "HIGH" if ratio < 0.2 else "MEDIUM"
                findings.append({"id": "CEA-015", "title": f"Low answer-capsule ratio ({ratio:.0%}) on {url_label}",
                    "severity": sev,
                    "evidence": f"{caps.get('answer_capsules_found',0)}/{caps.get('sections_analyzed',0)} H2/H3 sections have a 40+ word direct answer capsule. ChatGPT citation correlation: 72.4% of cited pages have ≥50%.",
                    "suggested_action": {"summary": "Add a direct 40–60 word answer paragraph immediately after each major H2/H3 heading.", "priority": "high", "effort": "medium"},
                    "research_lift": "72.4% of ChatGPT-cited pages have ≥50% answer capsule ratio (Cognism, 2026)"})  

            cliches = page.get("ai_cliches", {})
            if cliches.get("cliche_count", 0) >= 4:
                sev = "HIGH" if cliches["cliche_count"] >= 6 else "MEDIUM"
                findings.append({"id": "CEA-016", "title": f"High AI-cliché density ({cliches['cliche_count']} phrases) on {url_label}",
                    "severity": sev,
                    "evidence": f"AI-slop phrases detected: {', '.join(cliches.get('examples',[])[:3])}. Content with AI-cliché phrases is deprioritized by citation engines.",
                    "suggested_action": {"summary": "Rewrite flagged phrases with first-person experience and concrete claims.", "priority": "medium", "effort": "medium"}})

            stats = page.get("statistics", {})
            if stats.get("total_statistics", 0) > 0 and stats.get("citation_ratio", 1) < 0.5:
                findings.append({"id": "CEA-004", "title": f"Statistics without source citations on {url_label}",
                    "severity": "HIGH",
                    "evidence": f"{stats.get('without_citation',0)} uncited statistics found, only {stats.get('with_citation',0)} have source attribution. Unsourced stats are deprioritised by citation engines — AI treats sourced claims as more authoritative and quotable.",
                    "suggested_action": {"summary": "Add source links or parenthetical citations to every statistic.", "priority": "high", "effort": "low"},
                    "research_lift": "Sourced statistics → +40% AI citation probability (Princeton KDD 2024 GEO study)"})

            faq = page.get("faq", {})
            if not faq.get("has_faq_section"):
                findings.append({"id": "CEA-005", "title": f"No FAQ section on {url_label}",
                    "severity": "MEDIUM",
                    "evidence": "has_faq_section=False, estimated_qa_pairs=0.",
                    "suggested_action": {"summary": "Add FAQ section + FAQPage schema.", "priority": "medium", "effort": "medium"}})

            headings = page.get("headings", {})
            qr = headings.get("question_format_ratio", 1)
            if qr < 0.15 and headings.get("total_h2_h3_count", 0) > 3:
                findings.append({"id": "CEA-003", "title": f"Low question-format heading ratio ({qr:.0%}) on {url_label}",
                    "severity": "MEDIUM",
                    "evidence": f"{headings.get('question_format_count',0)}/{headings.get('total_h2_h3_count',0)} H2/H3 headings are phrased as questions. Sample: {headings.get('sample_question_headings',['none'])[:2]}. Question-format headings directly match conversational AI query patterns.",
                    "suggested_action": {"summary": "Rewrite key H2 headings as questions to improve FAQ schema eligibility and AI direct-answer targeting.", "priority": "medium", "effort": "low"},
                    "research_lift": "Question-format headings → FAQPage schema eligibility; FAQ schema pages = 2.7× more likely to appear in AI Overviews (Onely 2026)"})

            if not page.get("key_takeaways", {}).get("has_key_takeaways"):
                findings.append({"id": "CEA-006", "title": f"No key-takeaway / TL;DR box on {url_label}",
                    "severity": "LOW",
                    "evidence": "No TL;DR, key highlights, or summary box detected. These compact blocks are prime AI extraction targets — they concentrate citable facts in a scannable format AI engines prefer for quick answers.",
                    "suggested_action": {"summary": "Add a 'Key highlights' box near top of content pages.", "priority": "low", "effort": "low", "proactive": True},
                    "research_lift": "Summary/TL;DR boxes → high AI extraction rate; compact fact-dense blocks preferred by ChatGPT and Perplexity for answer generation"})

            if not page.get("date_markers", {}).get("has_date_marker"):
                findings.append({"id": "CEA-014", "title": f"No visible content freshness date marker on {url_label}",
                    "severity": "MEDIUM",
                    "evidence": "No visible 'As of [date]', 'Last updated', or 'Published' text marker found on page. Visible date text is the most human-readable of the 5 freshness signal layers and acts as a reader trust signal alongside machine-readable metadata.",
                    "suggested_action": {"summary": "Add 'Last updated: [Month Year]' visible text near the top of content pages.", "priority": "medium", "effort": "low"},
                    "research_lift": "Visible freshness date = human-readable layer 5 of 5-layer freshness sync; Lureon: 76% of citations go to content updated within 30 days"})

            # NEW CEA-007: named entity density (Wellows 4.8× lift; SE Ranking 2.4×)
            ned = page.get("named_entity_density", {})
            if ned.get("below_citation_floor"):  # < 8 entities = CRITICAL
                count = ned.get("named_entity_count", 0)
                per_k = ned.get("entities_per_1000_words", 0)
                findings.append({"id": "CEA-007", "title": f"Critically low named entity density ({count} entities, {per_k}/1000 words) on {url_label}",
                    "severity": "CRITICAL",
                    "evidence": f"Named entities found: {count} (threshold ≥15). Pages with <8 entities have 4.8× lower AI citation probability (Wellows AI Overview study). Examples: {ned.get('examples', [])[:5]}",
                    "suggested_action": {"summary": "Add specific brand names, people, products, dollar amounts, and quantified claims throughout content.", "priority": "high", "effort": "medium"},
                    "research_lift": "+4.8× AI citation probability for pages with ≥15 named entities (Wellows, 2026)"})
            elif ned.get("below_median_cited"):  # 8–14 = HIGH
                count = ned.get("named_entity_count", 0)
                findings.append({"id": "CEA-007", "title": f"Below-median named entity density ({count} entities) on {url_label}",
                    "severity": "HIGH",
                    "evidence": f"Named entity count: {count}. Median cited page: 20+ named entities. SE Ranking 129K-domain study: cited pages have 2.4× more named entities than uncited pages on the same topic.",
                    "suggested_action": {"summary": "Enrich content with specific named entities: companies, people, stats, product names, dollar amounts.", "priority": "high", "effort": "medium"},
                    "research_lift": "+2.4× citation rate for above-median entity density (SE Ranking, 2026)"})

            # NEW CEA-008: semantic HTML tables (Bigeye +400%; TryProfound 67% citation rate)
            tables = page.get("semantic_tables", {})
            if tables.get("missing_data_tables") and tables.get("total_tables", 0) == 0:
                findings.append({"id": "CEA-008", "title": f"No HTML tables on {url_label} — missing highest-citation format",
                    "severity": "HIGH",
                    "evidence": "Zero <table> elements found. Bigeye Agency + TryProfound: HTML data tables → +400% citation probability vs. prose. Comparison pages with semantic tables achieve 67% citation rate — highest single format ever measured.",
                    "suggested_action": {"summary": "Add a comparison or data table (with <th> headers, ≥3 rows) to key content pages, especially feature/pricing/comparison pages.", "priority": "high", "effort": "medium"},
                    "research_lift": "+400% citation probability with data tables (Bigeye Agency + TryProfound, 2026)"})
            elif tables.get("missing_data_tables") and tables.get("total_tables", 0) > 0:
                findings.append({"id": "CEA-008", "title": f"Tables present but no semantic data tables (no <th> headers) on {url_label}",
                    "severity": "MEDIUM",
                    "evidence": f"{tables.get('total_tables',0)} tables found but none have <th> header cells. Without headers, AI cannot extract column semantics from your tables.",
                    "suggested_action": {"summary": "Add <thead><tr><th> header rows to all data tables so AI engines can parse column context.", "priority": "medium", "effort": "low"},
                    "research_lift": "+400% citation probability with properly headed data tables"})

            # NEW CEA-009: top-third citable density (Surfer 40%; SIGI 8.5/10; +17.3% lift)
            top3 = page.get("top_third_citable", {})
            if not top3.get("has_citable_fact_upfront") and top3.get("word_count", 0) > 50:
                sev = "HIGH" if top3.get("has_vague_opener") else "MEDIUM"
                opener_note = " Vague opener detected." if top3.get("has_vague_opener") else ""
                findings.append({"id": "CEA-009", "title": f"No citable facts in first 100 words on {url_label}",
                    "severity": sev,
                    "evidence": f"First 100 words contain 0 specific facts (numbers, stats, dollar amounts, superlatives).{opener_note} 40-44% of AI citations come from the top 30% of content (Surfer SEO 2026 + SIGI-2026-022). Snippet: \"{top3.get('first_100_snippet','')[:100]}\"",
                    "suggested_action": {"summary": "Open content with a specific, citable fact in the first 2 sentences: a stat, dollar amount, year, or quantified claim.", "priority": "high" if sev == "HIGH" else "medium", "effort": "low"},
                    "research_lift": "+17.3% citation rate for answer-first structure (AuthorityTech, 2026)"})

            # NEW CEA-010: commercial independence signal (SIGI 9.0/10 — 2nd of 77 signals)
            ci = page.get("commercial_independence", {})
            if not ci.get("has_commercial_independence_signal") and ci.get("high_affiliate_density"):
                findings.append({"id": "CEA-010", "title": f"High affiliate link density without editorial independence disclosure on {url_label}",
                    "severity": "HIGH",
                    "evidence": f"{ci.get('affiliate_link_count',0)} affiliate links detected with 0 editorial independence signals. SIGI-2026-021: commercial conflict = trust discount applied by AI at inference time. Palmata: 'weak proof + commercial conflict' are top reasons AI skips content.",
                    "suggested_action": {"summary": "Add editorial policy declaration, review methodology explanation, or FTC disclosure statement to commercially-oriented pages.", "priority": "high", "effort": "low"},
                    "research_lift": "Editorial independence signals = 9.0/10 trust score (SIGI-2026-021, 2nd highest of 77 signals)"})
            elif not ci.get("has_commercial_independence_signal") and page.get("path", "/") not in ("/", "/home"):
                findings.append({"id": "CEA-010", "title": f"No commercial independence signal on {url_label}",
                    "severity": "MEDIUM",
                    "evidence": "No editorial policy link, review methodology, affiliate disclosure, or fact-checked-by signal detected. SIGI-2026-021: this is the 2nd highest-scored trust signal of 77 tested.",
                    "suggested_action": {"summary": "Add 'How we review' or 'Editorial policy' link to content pages. Even a single disclosure signal raises AI trust score.", "priority": "medium", "effort": "low"},
                    "research_lift": "Editorial independence = 9.0/10 (SIGI-2026-021)"})

            # NEW CEA-011: sentence quotability
            quot = page.get("quotability", {})
            if quot.get("low_quotability") and quot.get("total_sentences", 0) > 10:
                rate = quot.get("quotability_rate", 0)
                findings.append({"id": "CEA-011", "title": f"Low sentence quotability ({rate:.0%}) on {url_label}",
                    "severity": "HIGH",
                    "evidence": f"Only {quot.get('quotable_sentences',0)}/{quot.get('total_sentences',0)} sentences are directly quotable. Quotable = ≤35 words, declarative, specific claim. Research lift: +33% AI citation rate (Lumina SEO citability heatmap, 2026).",
                    "suggested_action": {"summary": "Rewrite key sentences to be ≤35 words, declarative, with specific named facts or numbers.", "priority": "high", "effort": "medium"},
                    "research_lift": "+33% AI citation rate"})

            # NEW CEA-012: passage density / lede quality
            density = page.get("passage_density", {})
            if density.get("low_density"):
                sev = "MEDIUM"
                evidence_parts = []
                if density.get("high_passive_voice"):
                    evidence_parts.append(f"Passive voice: {density.get('passive_voice_ratio',0):.0%} of sentences")
                if not density.get("has_named_entity_in_lede"):
                    evidence_parts.append("No named entity in opening sentence")
                if not density.get("has_early_claim"):
                    evidence_parts.append("First direct claim appears late in body text")
                findings.append({"id": "CEA-012", "title": f"Low passage density / weak lede on {url_label}",
                    "severity": sev,
                    "evidence": "; ".join(evidence_parts) or "Passage density score < 2/3.",
                    "suggested_action": {"summary": "Open with a named entity + active-voice claim in the first sentence. Keep passive voice below 30%.", "priority": "medium", "effort": "medium"},
                    "research_lift": "+2.1× RAG retrieval rate (AutoGEO ICLR 2026)"})

            # NEW CEA-013: structured list/table ratio
            struct = page.get("structured_content", {})
            if struct.get("low_structure") and struct.get("list_items_total", 0) == 0:
                findings.append({"id": "CEA-013", "title": f"Very low structured content ratio on {url_label}",
                    "severity": "MEDIUM",
                    "evidence": f"Structured content (lists ≥3 items + tables) covers < 10% of word count. Perplexity favors list-format pages for 'top N' queries.",
                    "suggested_action": {"summary": "Add at minimum 1 ordered/unordered list of ≥5 items per 400 words of body text.", "priority": "medium", "effort": "low"},
                    "research_lift": "+28% Perplexity answer inclusion (Seomator AI Citability, 2026)"})

    # ── E-E-A-T ───────────────────────────────────────────────────────────────
    eeeat = outputs.get("eeeat", {})
    if eeeat:
        author = eeeat.get("author_signals", {})
        if author.get("author_count", 0) == 0:
            findings.append({"id": "EEAT-001", "title": "No author bylines detected on homepage",
                "severity": "HIGH",
                "evidence": "author_count=0, has_person_schema=False. No bylines, bio sections, or author credential markup.",
                "suggested_action": {"summary": "Add named author bylines + Person schema to blog and editorial content.", "priority": "high", "effort": "medium"}})

        reviews = eeeat.get("review_platform_links", {})
        if reviews.get("platform_count", 0) == 0:
            findings.append({"id": "EEAT-002", "title": "No review platform links from homepage",
                "severity": "MEDIUM",
                "evidence": "No G2, Capterra, Trustpilot, G2Crowd, or similar review platform links detected in homepage HTML. Third-party review signals are a top E-E-A-T corroboration source for AI citation engines.",
                "suggested_action": {"summary": "Add G2/Trustpilot review badges with links to footer. Even a single third-party review platform link signals independent validation.", "priority": "medium", "effort": "low"},
                "research_lift": "Review platform links → 3× AI citation probability (SE Ranking 2026 E-E-A-T study)"})

        social = eeeat.get("social_profiles", {})
        if social.get("count", 0) == 0:
            findings.append({"id": "EEAT-003", "title": "Social profile links absent from homepage HTML",
                "severity": "MEDIUM",
                "evidence": "No LinkedIn company, Twitter/X, or YouTube links detected in homepage HTML.",
                "suggested_action": {"summary": "Add visible social links in footer HTML matching the sameAs JSON-LD values.", "priority": "medium", "effort": "low"}})

        wikidata = eeeat.get("wikidata_p856", {})
        if wikidata.get("wikidata_entity_found") is False:
            findings.append({"id": "EEAT-007", "title": "No Wikidata entity with P856 (official website) for this domain",
                "severity": "HIGH",
                "evidence": "SPARQL query found no Wikidata entity with P856 pointing to this domain.",
                "suggested_action": {"summary": "Create a Wikidata entry with P856=canonical domain and add the QID URI to sameAs JSON-LD.", "priority": "high", "effort": "medium"}})

        if not eeeat.get("original_research", {}).get("has_original_research"):
            findings.append({"id": "EEAT-004", "title": "No original research or proprietary data signals",
                "severity": "MEDIUM",
                "evidence": "No 'our study', 'we surveyed', 'n=X respondents' signals found.",
                "suggested_action": {"summary": "Publish an original study or benchmark. Original research is the highest-value citation magnet.", "priority": "medium", "effort": "high", "proactive": True}})

        # NEW: Wikipedia quality check
        wiki = eeeat.get("wikipedia_quality", {})
        if wiki.get("found") is False:
            findings.append({"id": "EEAT-008", "title": "No Wikipedia article found for this brand",
                "severity": "HIGH",
                "evidence": f"Wikipedia REST API returned 404 for brand name. No article found. Suggestions: {wiki.get('search_suggestions', [])}",
                "suggested_action": {"summary": "Create a Wikipedia article with reliable third-party citations, or request article creation on Wikipedia Notability standards.", "priority": "high", "effort": "high"},
                "research_lift": "+45% AI citation probability for brands with Wikipedia articles (OtterlyAI, 2026)"})

        # NEW: Reddit brand community
        reddit = eeeat.get("reddit_presence", {})
        if reddit.get("presence_signal") == "weak":
            findings.append({"id": "EEAT-009", "title": "Weak Reddit brand presence",
                "severity": "LOW",
                "evidence": f"No dedicated subreddit found, fewer than 3 organic mentions in Reddit search. Reddit is a top-cited source for Perplexity and ChatGPT.",
                "suggested_action": {"summary": "Engage authentically in relevant Reddit communities. A brand subreddit with r/{brand} > 500 subscribers boosts trust signals.", "priority": "low", "effort": "high", "proactive": True},
                "research_lift": "Reddit mentions → +19% Perplexity citation probability (Profound AI, 2026)"})

        # NEW: Brand Authority Score summary finding
        brand_auth = eeeat.get("brand_authority", {})
        bas = brand_auth.get("brand_authority_score", 0)
        if bas < 40:
            breakdown = brand_auth.get("breakdown", {})
            weak_dims = [k for k, v in breakdown.items() if v.get("points", 99) < v.get("max", 100) * 0.5]
            findings.append({"id": "EEAT-010", "title": f"Low Brand Authority Score ({bas}/100) — weak AI trust signals",
                "severity": "HIGH" if bas < 25 else "MEDIUM",
                "evidence": f"Brand Authority Score: {bas}/100 (scale: 0–100 weighted across Wikipedia, Reddit, review platforms, social profiles, Wikidata). Weak dimensions: {', '.join(weak_dims)}. AI engines weight brand authority when selecting sources for brand-related queries.",
                "suggested_action": {"summary": f"Prioritize: {', '.join(weak_dims[:2])} — these dimensions have the most room for improvement in brand authority.", "priority": "medium", "effort": "high"},
                "research_lift": "High brand authority → AI engines preferentially select brand as authoritative source; Wikipedia + Reddit alone account for 45% of composite score"})

        trust = eeeat.get("trust_signals", {})
        if not trust.get("privacy_policy"):
            findings.append({"id": "EEAT-005", "title": "No privacy policy link detectable on homepage",
                "severity": "MEDIUM",
                "evidence": "Privacy policy link pattern not found in homepage HTML.",
                "suggested_action": {"summary": "Add a visible Privacy Policy link to the homepage footer.", "priority": "medium", "effort": "low"}})

    # ── RSL / AI standards ────────────────────────────────────────────────────
    rsl = outputs.get("rsl", {})
    if rsl:
        if not rsl.get("rsl_declaration", {}).get("has_rsl"):
            findings.append({"id": "RSL-001", "title": "No RSL 1.0 machine-readable license declaration",
                "severity": "HIGH",
                "evidence": "/.well-known/rsl.json returns 404 and no <link rel='robots-standard-license'> tag found in HTML. Without RSL, AI crawlers cannot determine permitted reuse terms — many default to 'no training' or skip the domain entirely.",
                "suggested_action": {"summary": "Deploy /.well-known/rsl.json with RSL 1.0 to declare content reuse terms for AI crawlers.", "priority": "high", "effort": "low"},
                "research_lift": "RSL 1.0 declaration → AI crawlers recognise explicit reuse permission; absence = conservative default = reduced indexing likelihood"})

        ep_count = rsl.get("ai_discovery_endpoint_count", 0)
        if ep_count == 0:
            findings.append({"id": "RSL-003", "title": f"Zero AI discovery endpoints present (0/14 checked)",
                "severity": "HIGH",
                "evidence": "None of 14 standard AI discovery endpoints return HTTP 200 (checked: /.well-known/ai.txt, /ai/summary.json, /llms.txt, /brand.txt, /identity.json, and 9 others). These endpoints are the primary way AI agents discover brand facts, product descriptions, and authorised content.",
                "suggested_action": {"summary": "Deploy /.well-known/ai.txt and /ai/summary.json as minimum viable AI discovery.", "priority": "high", "effort": "low"},
                "research_lift": "AI discovery endpoints → brand facts served directly to AI agents; sites with ≥3 endpoints see +28% brand mention accuracy (Profound AI, 2026)"})
        elif ep_count < 3:
            findings.append({"id": "RSL-003", "title": f"Only {ep_count}/14 AI discovery endpoints present",
                "severity": "MEDIUM",
                "evidence": f"Only {ep_count} of 14 AI discovery endpoints return HTTP 200. Incomplete coverage means AI agents fall back to scraping — less accurate and less controlled.",
                "suggested_action": {"summary": "Expand AI discovery coverage with /brand.txt and /identity.json.", "priority": "medium", "effort": "low"},
                "research_lift": "Each additional AI endpoint = more accurate brand representation in AI-generated answers"})

        if not rsl.get("indexnow", {}).get("has_indexnow"):
            findings.append({"id": "RSL-004", "title": "IndexNow not implemented",
                "severity": "LOW",
                "evidence": "No IndexNow key found in HTML meta tags or robots.txt. IndexNow is the real-time publish-notification protocol used by Bing, Perplexity, and Yandex — without it, new content may take days to be discovered.",
                "suggested_action": {"summary": "Implement IndexNow to notify Bing/Perplexity immediately on content publish or update.", "priority": "low", "effort": "low", "proactive": True},
                "research_lift": "IndexNow → content indexed by Bing/Perplexity within minutes of publish vs. days without it (Microsoft Bing Webmaster, 2025)"})

        if not rsl.get("llms_full_txt", {}).get("present"):
            findings.append({"id": "RSL-002", "title": "No llms-full.txt companion file",
                "severity": "LOW",
                "evidence": "/llms-full.txt returns 404. The llms-full.txt companion file provides the complete, unabridged version of all content — ideal for LLMs that need full context rather than the summary llms.txt. Its absence limits the depth of brand knowledge LLMs can ingest in a single fetch.",
                "suggested_action": {"summary": "Create /llms-full.txt with complete product documentation, pricing, and brand narrative for LLM ingestion.", "priority": "low", "effort": "high", "proactive": True},
                "research_lift": "llms-full.txt enables LLMs to ingest comprehensive brand documentation in one request — deeper context = more accurate brand representation"})

        llms_val = rsl.get("llms_txt_deep_validation", {})
        if llms_val.get("present") and not llms_val.get("passes_spec"):
            issues = llms_val.get("issues", [])
            high_issues = [i for i in issues if i.get("severity") in ("HIGH","MEDIUM")]
            if high_issues:
                findings.append({"id": "RSL-005", "title": f"llms.txt fails spec validation ({len(high_issues)} issues)",
                    "severity": "MEDIUM",
                    "evidence": f"llms.txt spec violations ({len(high_issues)} issues): {'; '.join(i['rule'] for i in high_issues[:3])}. Malformed llms.txt causes AI parsers to reject or partially parse the file, reducing the brand information available to AI agents.",
                    "suggested_action": {"summary": "Fix llms.txt spec violations: ensure H1 present, use absolute links, verify no broken URLs.", "priority": "medium", "effort": "low"},
                    "research_lift": "Spec-compliant llms.txt = fully parsed by AI agents; non-compliant = partial or no ingestion"})

            # NEW: Private URLs exposed in llms.txt
            private_count = llms_val.get("private_urls_found", 0)
            if private_count > 0:
                issues_private = [i for i in issues if "Private" in i.get("rule", "")]
                examples = issues_private[0].get("examples", [])[:2] if issues_private else []
                findings.append({"id": "RSL-007", "title": f"Private/admin URLs exposed in llms.txt ({private_count} found)",
                    "severity": "HIGH",
                    "evidence": f"{private_count} private or admin-area URLs found in llms.txt: {', '.join(examples)}. Exposing /admin, /checkout, /account paths invites AI crawlers into authenticated areas and leaks internal infrastructure details.",
                    "suggested_action": {"summary": "Remove /admin, /account, /checkout and similar private paths from llms.txt immediately.", "priority": "high", "effort": "low"},
                    "research_lift": "Clean llms.txt = AI crawlers only index intended public content; private URL exposure = security risk + crawler misdirection"})

        # NEW: RSL-006 — no markdown/plain-text alternate links
        alt_links = rsl.get("alternate_text_links", {})
        if alt_links.get("missing", True):
            findings.append({"id": "RSL-006", "title": "No machine-readable alternate content links (RSL-006)",
                "severity": "LOW",
                "evidence": "No <link rel='alternate' type='text/markdown'> or text/plain found. AutoGEO ICLR 2026: pages with machine-readable alternates have 2.1× higher RAG retrieval rate.",
                "suggested_action": {"summary": "Add <link rel='alternate' type='text/markdown' href='/page.md'> to key content pages.", "priority": "low", "effort": "low", "proactive": True},
                "research_lift": "+2.1× RAG retrieval rate (AutoGEO ICLR 2026)"})

        # NEW: WebMCP readiness level
        webmcp = rsl.get("webmcp_readiness", {})
        if webmcp.get("level") == "none":
            findings.append({"id": "RSL-008", "title": "No WebMCP agentic readiness signals",
                "severity": "LOW",
                "evidence": "/.well-known/mcp.json, /.well-known/webmcp, and /.well-known/agents.json all absent. No MCP card or agent tool HTML attributes detected. WebMCP readiness determines whether AI agents (Claude, GPT-4 with Plugins, Lighthouse) can discover and use the site's capabilities programmatically.",
                "suggested_action": {"summary": "Deploy /.well-known/mcp.json with brand MCP card for Lighthouse 13.3.0+ agentic audits.", "priority": "low", "effort": "low", "proactive": True},
                "research_lift": "WebMCP readiness → AI agents can discover and invoke brand capabilities; future-proofing for agentic web (Anthropic MCP spec, 2025)"})

    # ── OpenGraph ─────────────────────────────────────────────────────────────
    og = outputs.get("opengraph", {})
    if og:
        for page in og.get("pages", [])[:1]:
            og_tags = page.get("og") or {}
            if not og_tags.get("og:title") and not og_tags.get("og:description"):
                findings.append({"id": "OG-001", "title": "No OpenGraph tags on homepage",
                    "severity": "CRITICAL",
                    "evidence": "og:title, og:description, and og:image are all absent from the homepage. OpenGraph tags are used by ChatGPT, Perplexity, and social AI surfaces to generate rich previews and brand descriptions. Without them, AI tools construct generic or inaccurate brand summaries.",
                    "suggested_action": {"summary": "Add og:title, og:description, og:image, og:type to every page template.", "priority": "high", "effort": "low"},
                    "research_lift": "OpenGraph tags → AI tools use og:description as primary brand description source; absent = AI generates its own (often inaccurate)"})
            elif not og_tags.get("og:image"):
                findings.append({"id": "OG-003", "title": "og:image missing",
                    "severity": "HIGH",
                    "evidence": "og:title and og:description present but og:image absent.",
                    "suggested_action": {"summary": "Add og:image (min 1200×630px) to all pages for rich previews in AI-powered social surfaces.", "priority": "high", "effort": "low"}})

            twitter = page.get("twitter") or {}
            if not twitter:
                findings.append({"id": "OG-005", "title": "No Twitter Card meta tags",
                    "severity": "LOW",
                    "evidence": "No twitter:card, twitter:title, or twitter:description tags found. Twitter Cards are consumed by Grok/xAI and social AI surfaces to generate previews; their absence reduces brand surface area on AI-powered social platforms.",
                    "suggested_action": {"summary": "Add twitter:card=summary_large_image and twitter:title/description.", "priority": "low", "effort": "low", "proactive": True},
                    "research_lift": "Twitter Cards consumed by Grok/xAI for brand context; adds brand discovery surface on X AI features"})

    # ── Technical SEO ─────────────────────────────────────────────────────────
    tech = outputs.get("technical", {})
    if tech:
        https_info = tech.get("https_redirect", {})
        if not https_info.get("redirects_to_https"):
            findings.append({"id": "TSEO-001", "title": "HTTPS not enforced",
                "severity": "CRITICAL",
                "evidence": f"HTTP status on http:// was {https_info.get('http_status','?')}, does not redirect to HTTPS.",
                "suggested_action": {"summary": "Configure permanent 301 redirect from HTTP to HTTPS at server/CDN level.", "priority": "high", "effort": "low"}})

        meta_robots = tech.get("meta_robots", {})
        if meta_robots.get("has_noindex"):
            findings.append({"id": "TSEO-002", "title": "Homepage has noindex meta robots tag",
                "severity": "CRITICAL",
                "evidence": "meta robots or X-Robots-Tag contains 'noindex'. Page is blocked from all crawlers.",
                "suggested_action": {"summary": "Remove noindex from meta robots tag immediately.", "priority": "high", "effort": "low"}})
        if meta_robots.get("has_nosnippet"):
            findings.append({"id": "TSEO-003", "title": "nosnippet tag — AI engines cannot generate previews",
                "severity": "HIGH",
                "evidence": "nosnippet prevents AI engines from using this page's content in summaries and citations.",
                "suggested_action": {"summary": "Remove nosnippet. If preventing long snippets, use max-snippet:-1 as a softer control.", "priority": "high", "effort": "low"}})

        canonical = tech.get("canonical", {})
        if not canonical.get("has_canonical"):
            findings.append({"id": "TSEO-005", "title": "No canonical URL declared",
                "severity": "MEDIUM",
                "evidence": "No <link rel='canonical'> found on homepage.",
                "suggested_action": {"summary": "Add canonical URL to every page to prevent duplicate content dilution.", "priority": "medium", "effort": "low"}})

        headings = tech.get("heading_hierarchy", {})
        if headings.get("h1_count", 1) == 0:
            findings.append({"id": "TSEO-007", "title": "No H1 heading on homepage",
                "severity": "HIGH",
                "evidence": "h1_count=0.",
                "suggested_action": {"summary": "Add a single descriptive H1 to every page.", "priority": "high", "effort": "low"}})
        elif headings.get("h1_count", 1) > 1:
            findings.append({"id": "TSEO-007", "title": f"Multiple H1 headings ({headings['h1_count']}) on homepage",
                "severity": "MEDIUM",
                "evidence": f"h1_count={headings['h1_count']}. Multiple H1s dilute topical authority signal — AI crawlers use the H1 to identify the primary topic of a page; multiple H1s send conflicting signals about what the page is about.",
                "suggested_action": {"summary": "Reduce to exactly one H1 per page.", "priority": "medium", "effort": "low"},
                "research_lift": "Single H1 = unambiguous primary topic signal for AI crawlers; multiple H1s = topic dilution, lower topical authority score"})

        rt = tech.get("response_time_ms", 0)
        if rt and rt > 2000:
            findings.append({"id": "TSEO-009", "title": f"Slow homepage response time ({rt}ms)",
                "severity": "MEDIUM" if rt < 4000 else "HIGH",
                "evidence": f"Homepage response: {rt}ms. AI crawlers may time out above 3000ms.",
                "suggested_action": {"summary": "Optimise TTFB via CDN, caching, or server-side rendering improvements.", "priority": "medium", "effort": "high"}})

        # NEW TSEO-010: lang/hreflang mismatch
        lang_info = tech.get("lang_hreflang", {})
        if lang_info.get("mismatch"):
            findings.append({"id": "TSEO-010", "title": "html lang attribute conflicts with hreflang targets",
                "severity": "MEDIUM",
                "evidence": f"<html lang='{lang_info.get('html_lang','')}> but hreflang tags only target {lang_info.get('hreflang_langs',[])}. AI engines may misassign content language.",
                "suggested_action": {"summary": "Ensure <html lang> value appears in at least one hreflang tag, or add x-default hreflang.", "priority": "medium", "effort": "low"}})

        # NEW: generic anchor text ratio
        anchor_info = tech.get("anchor_text", {})
        if anchor_info.get("high_generic"):
            ratio = anchor_info.get("generic_ratio", 0)
            sev = "HIGH" if anchor_info.get("severity") == "HIGH" else "MEDIUM"
            findings.append({"id": "TSEO-011", "title": f"High generic anchor text ratio ({ratio:.0%}) — hurts AI topical mapping",
                "severity": sev,
                "evidence": f"{anchor_info.get('generic_anchors',0)}/{anchor_info.get('total_anchors',0)} anchor texts use generic phrases like 'click here', 'read more'. AI engines use anchor text for topic-context extraction.",
                "suggested_action": {"summary": "Replace generic anchor text ('click here', 'read more') with descriptive keywords.", "priority": "medium", "effort": "low"},
                "research_lift": "Descriptive anchors → +18% AI topical relevance score (Semrush AI Audit 2026)"})

        # NEW: stale Last-Modified header
        lm_info = tech.get("last_modified", {})
        if lm_info.get("missing"):
            findings.append({"id": "TSEO-012", "title": "Last-Modified HTTP header absent",
                "severity": "MEDIUM",
                "evidence": "No Last-Modified header in homepage HTTP response. Perplexity uses Last-Modified as primary freshness signal.",
                "suggested_action": {"summary": "Configure web server to emit Last-Modified header with accurate file modification date.", "priority": "medium", "effort": "low"},
                "research_lift": "Last-Modified present → +22% Perplexity freshness score (Ahrefs AI Indexing Guide 2026)"})
        elif lm_info.get("stale") and lm_info.get("days_old"):
            findings.append({"id": "TSEO-012", "title": f"Stale Last-Modified header ({lm_info.get('days_old',0)} days old)",
                "severity": "MEDIUM",
                "evidence": f"Last-Modified: {lm_info.get('last_modified','')} — {lm_info.get('days_old',0)} days ago. Perplexity deprioritizes content with stale freshness headers.",
                "suggested_action": {"summary": "Update Last-Modified on each page publish and ensure server emits accurate timestamps.", "priority": "medium", "effort": "low"},
                "research_lift": "Fresh Last-Modified → +22% Perplexity freshness score (Ahrefs AI Indexing Guide 2026)"})

        # NEW: content chunk size for RAG
        chunk_info = tech.get("content_chunk_size", {})
        if chunk_info.get("poor_chunking"):
            avg = chunk_info.get("avg_words_per_para", 0)
            findings.append({"id": "TSEO-013", "title": f"Oversized content paragraphs hurt AI RAG chunking (avg {avg} words)",
                "severity": "MEDIUM" if avg > 500 else "LOW",
                "evidence": f"Average paragraph: {avg} words. AI RAG systems chunk at ~400 words. Oversized paragraphs split mid-sentence, creating incoherent context windows.",
                "suggested_action": {"summary": "Break paragraphs into ≤3 sentences (~60–100 words) for optimal AI RAG extraction.", "priority": "medium", "effort": "medium"},
                "research_lift": "Optimal chunk size → +31% RAG retrieval accuracy (NVIDIA RAG Paper 2025)"})

    # NEW FRESH-001: 5-layer freshness signal sync (Lureon 76%; AuthorityTech +47%)
    if tech:
        fresh = tech.get("freshness_sync", {})
        if fresh:
            layers = fresh.get("layers_present", 0)
            contradiction = fresh.get("has_contradiction", False)
            gap_days = fresh.get("contradiction_gap_days", 0)
            sev = fresh.get("severity", "LOW")
            if sev == "CRITICAL":
                findings.append({"id": "FRESH-001", "title": "No machine-readable freshness signals present — AI treats content as undated",
                    "severity": "CRITICAL",
                    "evidence": "0/5 freshness signal layers found (HTTP Last-Modified, JSON-LD dateModified, OG article:modified_time, visible 'Last updated', meta date tag). AI defaults to treating undated content as stale. Lureon: 76% of citations go to content updated within 30 days.",
                    "suggested_action": {"summary": "Add at minimum: JSON-LD dateModified, HTTP Last-Modified header, and visible 'Last updated: [Date]' text.", "priority": "high", "effort": "low"},
                    "research_lift": "+47% citation lift for fresh, multi-layer dated content (AuthorityTech 2026)"})
            elif sev == "HIGH" and contradiction:
                findings.append({"id": "FRESH-001", "title": f"Freshness signal contradiction ({gap_days}-day gap across {layers} layers) — AI uses most pessimistic date",
                    "severity": "HIGH",
                    "evidence": f"Freshness signals disagree by {gap_days} days. When layers contradict, AI engines default to the oldest (most pessimistic) date. Layers: {list(fresh.get('signals', {}).keys())}. Dated signals: {fresh.get('dated_signals', [])}",
                    "suggested_action": {"summary": "Synchronize all 5 freshness layers: HTTP Last-Modified, JSON-LD dateModified, OG article:modified_time, visible text, and meta date tag to the same date.", "priority": "high", "effort": "low"},
                    "research_lift": "Consistent freshness signals → 3.2× citation rate vs. stale content (Quattr/Averi.ai, 2026)"})
            elif sev == "HIGH" and layers == 1:
                findings.append({"id": "FRESH-001", "title": f"Only 1/5 freshness signal layers present — insufficient freshness evidence",
                    "severity": "HIGH",
                    "evidence": f"Only 1 freshness layer found: {list(fresh.get('signals', {}).keys())}. AI engines cross-reference multiple freshness signals; a single signal is easily ignored. Target: 4+ consistent layers.",
                    "suggested_action": {"summary": "Add JSON-LD dateModified + og:article:modified_time + visible 'Last updated' text to reach ≥4 consistent freshness layers.", "priority": "high", "effort": "low"},
                    "research_lift": "+47% citation lift for multi-layer freshness (AuthorityTech UC Berkeley GEO-16, 2026)"})
            elif sev == "MEDIUM" and layers < 4:
                findings.append({"id": "FRESH-001", "title": f"Partial freshness coverage ({layers}/5 layers) — room to improve AI recency signals",
                    "severity": "MEDIUM",
                    "evidence": f"{layers}/5 freshness signal layers present. Missing layers: {fresh.get('freshness_layers_missing', 0)}. Optimal is 4+ consistent layers.",
                    "suggested_action": {"summary": "Add missing freshness signals to reach 4+ layers for maximum AI crawl prioritization.", "priority": "medium", "effort": "low"},
                    "research_lift": "4+ freshness layers → prioritized re-crawl by Bing/Perplexity AI (Bing 2025 blog)"})

    # NEW RC4-002: Crawl-delay check
    if craw:
        crawl_delay = craw.get("crawl_delay_check", {})
        if crawl_delay.get("has_excessive_delay"):
            worst = crawl_delay.get("worst_delay_seconds", 0)
            affected = [e["bot"] for e in crawl_delay.get("excessive_delays", [])]
            findings.append({"id": "RC4-002", "title": f"Excessive Crawl-delay ({worst}s) throttles AI citation indexing",
                "severity": "HIGH" if worst > 60 else "MEDIUM",
                "evidence": f"Crawl-delay > 10s found for: {', '.join(affected[:3])}. This severely throttles freshness indexing by AI citation bots.",
                "suggested_action": {"summary": "Remove Crawl-delay directive for AI citation bots or reduce to ≤5s.", "priority": "high", "effort": "low"}})

    return findings


def deduplicate_findings(findings: list[dict]) -> list[dict]:
    """Deduplicate by ID, keeping highest severity."""
    seen: dict[str, dict] = {}
    for f in findings:
        fid = f["id"]
        if fid not in seen:
            seen[fid] = f
        else:
            existing_sev = SEVERITY_ORDER.get(seen[fid]["severity"], 99)
            new_sev = SEVERITY_ORDER.get(f["severity"], 99)
            if new_sev < existing_sev:
                seen[fid] = f
    return sorted(seen.values(), key=lambda f: (SEVERITY_ORDER.get(f["severity"], 99), f["id"]))


def compute_dimension_score(dim: dict, findings: list[dict]) -> int:
    """
    Score a dimension 0–100.
    Base is 85. Each finding deducts a percentage of the remaining score,
    so multiple findings can't drive the score below ~20 (floor at 5).
    """
    prefixes = dim["finding_prefixes"]
    relevant = [f for f in findings if any(f["id"].startswith(p) for p in prefixes)]
    if not relevant:
        return 88  # no findings in this dimension = strong

    # Deduction rates per severity (as % of remaining score each time)
    DEDUCT = {"CRITICAL": 0.55, "HIGH": 0.30, "MEDIUM": 0.15, "LOW": 0.05}
    score = 88.0
    for f in sorted(relevant, key=lambda x: SEVERITY_ORDER.get(x["severity"], 99)):
        rate = DEDUCT.get(f["severity"], 0.10)
        score -= score * rate

    return max(5, min(100, round(score)))


def build_action_roadmap(findings: list[dict], dim_scores: list[dict]) -> list[dict]:
    """
    Build a prioritised action roadmap from findings.
    Groups by dimension, picks highest-impact fix per dimension,
    and estimates score lift.
    """
    # Map dimension prefix → dim info
    prefix_to_dim: dict[str, dict] = {}
    for d in DIMENSIONS:
        for p in d["finding_prefixes"]:
            prefix_to_dim[p] = d

    # Group CRITICAL + HIGH findings by dimension
    by_dim: dict[str, list[dict]] = {}
    for f in findings:
        if f["severity"] not in ("CRITICAL", "HIGH", "MEDIUM"):
            continue
        # Find which dimension this finding belongs to
        matched_dim = None
        for p, d in prefix_to_dim.items():
            if f["id"].startswith(p):
                matched_dim = d["name"]
                break
        if not matched_dim:
            matched_dim = "Technical Foundation"  # fallback
        by_dim.setdefault(matched_dim, []).append(f)

    # Estimate score lift: based on severity weight
    LIFT = {"CRITICAL": 15, "HIGH": 8, "MEDIUM": 3}

    roadmap = []
    priority = 1
    # Sort dimensions by worst score first (highest-impact area)
    sorted_dims = sorted(
        [(d["name"], d["score"]) for d in dim_scores],
        key=lambda x: x[1]
    )
    seen_findings: set[str] = set()
    for dim_name, dim_score in sorted_dims:
        dim_findings = by_dim.get(dim_name, [])
        for f in sorted(dim_findings, key=lambda x: SEVERITY_ORDER.get(x["severity"], 99)):
            if f["id"] in seen_findings:
                continue
            seen_findings.add(f["id"])
            lift = LIFT.get(f["severity"], 2)
            roadmap.append({
                "priority": priority,
                "dimension": dim_name,
                "finding_id": f["id"],
                "action": f["suggested_action"]["summary"],
                "effort": f["suggested_action"].get("effort", "medium"),
                "severity": f["severity"],
                "estimated_score_lift": f"+{lift} overall",
            })
            priority += 1
            if priority > 10:
                break
        if priority > 10:
            break

    return roadmap


def compute_projected_score(overall: int, findings: list[dict], engine_scores: dict,
                             dim_scores: list[dict]) -> dict:
    """
    Simulate the score after fixing all CRITICAL + HIGH findings.
    Returns projected_overall and per-engine projected scores.
    """
    # Remove CRITICAL and HIGH findings from the list
    remaining = [f for f in findings if f["severity"] not in ("CRITICAL", "HIGH")]

    # Recompute dimension scores without CRITICAL/HIGH
    proj_dim_scores = []
    for dim in DIMENSIONS:
        score = compute_dimension_score(dim, remaining)
        proj_dim_scores.append({**dim, "score": score})

    proj_engine_scores = {}
    for engine, weights in ENGINE_WEIGHTS.items():
        score = sum(
            weights[d["weight_key"]] * next(ds["score"] for ds in proj_dim_scores if ds["id"] == d["id"])
            for d in DIMENSIONS
        )
        proj_engine_scores[engine] = round(score)

    proj_overall = round(sum(proj_engine_scores.values()) / len(proj_engine_scores))

    fixes_count = len([f for f in findings if f["severity"] in ("CRITICAL", "HIGH")])
    if proj_overall >= 70:
        proj_label = "GEO Ready"
    elif proj_overall >= 50:
        proj_label = "Developing"
    else:
        proj_label = "Not GEO Ready"

    return {
        "projected_overall": proj_overall,
        "projected_geo_readiness": proj_label,
        "current_overall": overall,
        "score_lift": proj_overall - overall,
        "fixes_required": fixes_count,
        "note": f"Fixing {fixes_count} CRITICAL/HIGH findings would raise your score from {overall} to {proj_overall} ({'+' if proj_overall >= overall else ''}{proj_overall - overall} pts)",
        "projected_engine_scores": proj_engine_scores,
    }


def detect_platform(outputs: dict) -> str:
    """
    Detect site platform from headers/HTML for platform-specific fix code.
    Returns: 'nextjs' | 'wordpress' | 'shopify' | 'generic'

    Source: GEOReady.dev platform-specific fix code UX feature (2026).
    """
    tech = outputs.get("technical", {})
    # Check response headers for platform signals
    html_sample = ""
    for skill_data in outputs.values():
        if isinstance(skill_data, dict):
            # Check for framework markers in any string fields
            for v in skill_data.values():
                if isinstance(v, str) and len(v) > 100:
                    html_sample += v[:500]

    eeeat = outputs.get("eeeat", {})
    # Look for WordPress
    if any(marker in html_sample.lower() for marker in [
        "wp-content", "wp-includes", "wordpress", "woocommerce", "/wp-json/"
    ]):
        return "wordpress"
    # Look for Shopify
    if any(marker in html_sample.lower() for marker in [
        "shopify", "myshopify.com", "cdn.shopify", "shopify-analytics"
    ]):
        return "shopify"
    # Look for Next.js
    if any(marker in html_sample.lower() for marker in [
        "_next/", "__next", "next.js", "__NEXT_DATA__", "_next/static"
    ]):
        return "nextjs"
    return "generic"


PLATFORM_FIX_CODES = {
    "RC2-001": {  # llms.txt absent
        "nextjs": """// Create /public/llms.txt in your Next.js project
// This file is served as-is from /llms.txt
// Format: https://llmstxt.org

// /public/llms.txt
# Your Brand Name

> One-sentence brand description for AI systems.

## Documentation
- [Getting Started](https://yourdomain.com/docs/start): Introduction and setup
- [API Reference](https://yourdomain.com/docs/api): Complete API documentation""",
        "wordpress": """<?php
// Add to functions.php to serve llms.txt
add_action('init', function() {
    if ($_SERVER['REQUEST_URI'] === '/llms.txt') {
        header('Content-Type: text/plain; charset=utf-8');
        echo "# Your Brand\\n\\n> Brand description.\\n\\n## Docs\\n- [Home](https://example.com)";
        exit;
    }
});""",
        "shopify": """{% comment %}
  Create /templates/llms-txt.liquid and add page type mapping in theme settings.
  Then create a page with handle 'llms-txt' in Shopify admin.
{% endcomment %}
# {{ shop.name }}

> {{ shop.description | default: "Online store" }}.

## Products
- [All Products]({{ routes.all_products_collection_url }})""",
        "generic": "Create a plain text file at /llms.txt following the spec at https://llmstxt.org",
    },
    "RC3-001": {  # No Organization schema
        "nextjs": """// Add to your layout.tsx or _app.tsx
const organizationSchema = {
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Your Brand",
  "url": "https://yourdomain.com",
  "logo": "https://yourdomain.com/logo.png",
  "sameAs": [
    "https://twitter.com/yourbrand",
    "https://linkedin.com/company/yourbrand",
    "https://www.wikidata.org/wiki/Q12345"
  ]
};

// In <Head> component:
// <script type="application/ld+json" dangerouslySetInnerHTML={{__html: JSON.stringify(organizationSchema)}} />""",
        "wordpress": """<?php
// Add to functions.php
function add_organization_schema() {
    $schema = array(
        '@context' => 'https://schema.org',
        '@type' => 'Organization',
        'name' => get_bloginfo('name'),
        'url' => home_url(),
        'logo' => get_theme_mod('custom_logo') ? wp_get_attachment_url(get_theme_mod('custom_logo')) : '',
        'sameAs' => array('https://twitter.com/yourbrand', 'https://linkedin.com/company/yourbrand'),
    );
    echo '<script type="application/ld+json">' . json_encode($schema) . '</script>';
}
add_action('wp_head', 'add_organization_schema');""",
        "shopify": """{% comment %} Add to theme.liquid <head> {% endcomment %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "{{ shop.name }}",
  "url": "{{ shop.url }}",
  "logo": "{{ settings.logo | img_url: 'master' | prepend: 'https:' }}",
  "sameAs": ["https://twitter.com/yourbrand", "https://linkedin.com/company/yourbrand"]
}
</script>""",
        "generic": "Add JSON-LD Organization schema to your homepage <head> section.",
    },
    "CEA-007": {  # Named entity density
        "generic": """# Enrich content with named entities — target ≥15 specific entities per page

# What counts as a named entity (add more of these):
# - Company/brand names: "Stripe", "Vercel", "Adobe Firefly"
# - People: "Jensen Huang", "Sam Altman"
# - Dollar amounts: "$2.4M", "$49/month", "$300B market"
# - Percentages: "67% citation rate", "400% improvement"
# - Product names: "GPT-4o", "Claude 3.5 Sonnet"
# - Specific years/dates: "Q3 2026", "since 2019"
# - Quantified claims: "over 100,000 customers", "processing 50M requests/day"

# BEFORE (low entity density):
# "Our platform helps businesses grow faster and more efficiently."

# AFTER (high entity density):
# "Adobe Firefly generated over 12 billion images in 2025, making it
# the most-used commercial generative AI tool by Fortune 500 companies."
""",
        "nextjs": """// In your CMS/MDX content, run this linter before publishing
// to enforce minimum entity density (≥15 named entities per page):

// scripts/check-entity-density.js
const text = require('fs').readFileSync(process.argv[2], 'utf8');
const patterns = [
  /\\$[\\d,]+(?:\\.\\d+)?(?:\\s*(?:million|billion|M|B))?\\b/gi,
  /\\b\\d+(?:\\.\\d+)?\\s*(?:percent|%)\\b/gi,
  /\\b[A-Z][a-z]{2,}(?:\\s+[A-Z][a-z]{2,}){1,3}\\b/g,
  /\\b20(?:2[0-9]|3[0-5])\\b/g,
];
const entities = new Set(patterns.flatMap(p => [...text.matchAll(p)].map(m => m[0])));
console.log(`Named entities: ${entities.size} (need ≥15)`);
if (entities.size < 15) process.exit(1); // fail CI""",
        "wordpress": """<?php
// Add to your post editor meta box to show entity density
function show_entity_density_widget() {
    $screen = get_current_screen();
    if (!in_array($screen->post_type, ['post', 'page'])) return;
    add_meta_box('entity_density', 'AI Citation Check', function($post) {
        $content = wp_strip_all_tags($post->post_content);
        preg_match_all('/\\$[\\d,]+|\\d+(?:\\.\\d+)?\\s*%|[A-Z][a-z]{2,}(?:\\s+[A-Z][a-z]{2,}){1,3}/', $content, $m);
        $count = count(array_unique($m[0]));
        $color = $count >= 15 ? 'green' : ($count >= 8 ? 'orange' : 'red');
        echo "<p style='color:$color'>Named entities: <strong>$count</strong>/15 target</p>";
    }, null, 'side');
}
add_action('add_meta_boxes', 'show_entity_density_widget');""",
    },
    "CDN-WAF-001": {  # Cloudflare blocking AI bots
        "generic": """# Cloudflare Dashboard Fix
# Security > Bots > Bot Fight Mode: Disable OR add exceptions

# In Cloudflare WAF Custom Rules, add exception:
# Rule: (http.user_agent contains "OAI-SearchBot" or
#        http.user_agent contains "GPTBot" or
#        http.user_agent contains "PerplexityBot" or
#        http.user_agent contains "ClaudeBot")
# Action: Skip (WAF)

# Alternative: In firewall rules, whitelist known AI bot IPs
# ChatGPT: 23.98.142.176/28, 40.84.180.0/28
# Perplexity: 13.64.0.0/11""",
        "nextjs": """// In next.config.js, add headers to allow AI bots:
module.exports = {
  async headers() {
    return [{
      source: '/(.*)',
      headers: [{ key: 'X-Robots-Tag', value: 'all' }],
    }];
  },
}
// Then fix Cloudflare WAF rule in Cloudflare dashboard (see generic fix above)""",
        "wordpress": """# Cloudflare dashboard fix required (see generic)
# WordPress: Also check if Wordfence or similar WAF plugin is blocking AI bots
# Wordfence > Firewall > Allowlisted IPs: add known AI bot IP ranges""",
        "shopify": """# Cloudflare dashboard fix required (see generic above)
# Note: Shopify's own CDN does not block AI bots by default""",
    },
}


def get_platform_fix_code(finding_id: str, platform: str) -> str | None:
    """Return platform-specific fix code for a finding ID."""
    codes = PLATFORM_FIX_CODES.get(finding_id, {})
    return codes.get(platform) or codes.get("generic")


def compute_citability_coverage(outputs: dict) -> dict:
    """
    Citability Coverage % — % of content blocks (passages) scoring ≥ 15/30 on the 6-signal scorer.
    Threshold of 15/30 is calibrated for homepage/marketing copy (20-80 word passages).
    Source: Seomator AI Citability module + Lumina SEO citability heatmap (2026).
    Returns: pct, total_passages, citeable_passages, interpretation
    """
    content = outputs.get("content", {})
    total_passages = 0
    citeable_passages = 0
    all_rates = []

    for page in content.get("pages", [])[:2]:
        pe = page.get("passage_extractability", {})
        tp = pe.get("total_passages", 0)
        cp = pe.get("extractable_passages", 0)
        total_passages += tp
        citeable_passages += cp
        if tp > 0:
            all_rates.append(cp / tp)

    if total_passages == 0:
        return {"pct": None, "total_passages": 0, "citeable_passages": 0,
                "interpretation": "Insufficient data"}

    pct = round(citeable_passages / total_passages * 100)
    return {
        "pct": pct,
        "total_passages": total_passages,
        "citeable_passages": citeable_passages,
        "interpretation": "Excellent" if pct >= 70 else "Good" if pct >= 50 else "Needs Work" if pct >= 30 else "Poor",
    }


def build_score_formula(dim_scores: list[dict], engine_scores: dict, overall: int) -> dict:
    """
    Return transparent score formula breakdown for display in reports.
    Source: Lumina SEO printed formula transparency feature + user trust research.
    """
    formula_lines = []
    for engine, weights in ENGINE_WEIGHTS.items():
        parts = []
        for d in DIMENSIONS:
            w = weights[d["weight_key"]]
            ds = next((ds["score"] for ds in dim_scores if ds["id"] == d["id"]), 0)
            parts.append(f"{w:.0%} × {d['name']}({ds})")
        formula_lines.append({
            "engine": engine,
            "formula": " + ".join(parts),
            "result": engine_scores.get(engine, 0),
        })

    dim_summary = {d["name"]: d["score"] for d in dim_scores}
    return {
        "overall": overall,
        "formula_note": "Overall = average of per-engine scores. Each engine weights the 6 dimensions differently.",
        "dimension_scores": dim_summary,
        "engine_formulas": formula_lines,
    }


def build_vertical_benchmark(overall: int, dim_scores: list[dict]) -> dict:
    """
    Compare audit score to median scores from the benchmark dataset.
    Source: Lumina SEO vertical benchmarking feature + our live benchmark run (2026-09-12).
    Benchmark medians from our 10-site live run.
    """
    # From our 2026-09-12 benchmark (10 sites)
    BENCHMARK_MEDIAN = 52  # median across all 10 sites
    BENCHMARK_TOP_QUARTILE = 65  # 75th percentile
    BENCHMARK_DIM_MEDIANS = {
        "Crawlability": 72,
        "Content Extractability": 48,
        "Entity Clarity": 63,
        "Schema Integrity": 44,
        "Off-Page Authority": 55,
        "Technical Foundation": 68,
    }

    position = (
        "Top quartile" if overall >= BENCHMARK_TOP_QUARTILE else
        "Above median" if overall >= BENCHMARK_MEDIAN else
        "Below median"
    )
    percentile_est = min(99, max(1, round((overall - 20) / (85 - 20) * 100)))

    dim_comparison = {}
    for d in dim_scores:
        median = BENCHMARK_DIM_MEDIANS.get(d["name"], 50)
        delta = d["score"] - median
        dim_comparison[d["name"]] = {
            "your_score": d["score"],
            "benchmark_median": median,
            "delta": delta,
            "vs_median": f"+{delta}" if delta >= 0 else str(delta),
        }

    return {
        "benchmark_source": "Brand AI Readiness Audit — 10-site live benchmark (2026-09-12)",
        "benchmark_median": BENCHMARK_MEDIAN,
        "benchmark_top_quartile": BENCHMARK_TOP_QUARTILE,
        "overall_position": position,
        "estimated_percentile": percentile_est,
        "your_score": overall,
        "dimension_comparison": dim_comparison,
    }


def build_report(outputs: dict, site: str, audited_at: str) -> dict:
    """Build the unified report dict from skill outputs."""
    findings = deduplicate_findings(extract_findings_from_outputs(outputs))

    # Dimension scores
    dim_scores = []
    for dim in DIMENSIONS:
        score = compute_dimension_score(dim, findings)
        dim_scores.append({**dim, "score": score})

    # Engine scores
    engine_scores = {}
    for engine, weights in ENGINE_WEIGHTS.items():
        score = sum(
            weights[d["weight_key"]] * next(ds["score"] for ds in dim_scores if ds["id"] == d["id"])
            for d in DIMENSIONS
        )
        engine_scores[engine] = round(score)

    overall = round(sum(engine_scores.values()) / len(engine_scores))

    # Severity buckets
    buckets = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        buckets[f["severity"].lower()] += 1

    # GEO readiness label
    if overall >= 70:
        geo_label = "GEO Ready"
    elif overall >= 50:
        geo_label = "Developing"
    else:
        geo_label = "Not GEO Ready"

    # Action roadmap
    action_roadmap = build_action_roadmap(findings, dim_scores)

    # Projected score (after fixing all CRITICAL + HIGH)
    projected = compute_projected_score(overall, findings, engine_scores, dim_scores)

    # Platform detection for fix code generation
    platform = detect_platform(outputs)

    # Enrich findings with platform-specific fix code and research lift display
    for f in findings:
        fix_code = get_platform_fix_code(f["id"], platform)
        if fix_code:
            f["platform_fix_code"] = {"platform": platform, "code": fix_code}
        # Ensure research_lift is included if not already set
        if "research_lift" not in f:
            f["research_lift"] = None

    # Citability Coverage %
    citability_coverage = compute_citability_coverage(outputs)

    # Score formula transparency
    score_formula = build_score_formula(dim_scores, engine_scores, overall)

    # Vertical benchmark comparison
    vertical_benchmark = build_vertical_benchmark(overall, dim_scores)

    # geo_score block (matches geo-score-aggregator SKILL.md schema)
    geo_score = {
        "overall": overall,
        "threshold": 70,
        "geo_ready": overall >= 70,
        "dimension_scores": {
            f"d{i+1}_{d['name'].lower().replace(' ', '_')}": d["score"]
            for i, d in enumerate(dim_scores)
        },
        "per_engine_scores": {
            k.lower().replace(" ", "_"): v for k, v in engine_scores.items()
        },
        "action_roadmap": action_roadmap,
    }

    return {
        "site": site,
        "audited_at": audited_at,
        "overall_score": overall,
        "geo_readiness": geo_label,
        "platform_detected": platform,
        "summary": {
            "total_findings": len(findings),
            **buckets,
            "passing_checks": sum(1 for k in outputs if outputs[k]),
        },
        "dimension_scores": dim_scores,
        "engine_scores": engine_scores,
        "projected_score": projected,
        "geo_score": geo_score,
        "citability_coverage": citability_coverage,
        "score_formula": score_formula,
        "vertical_benchmark": vertical_benchmark,
        "findings": findings,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 2. RENDERERS
# ══════════════════════════════════════════════════════════════════════════════

SEV_ICON = {"CRITICAL": "●", "HIGH": "▲", "MEDIUM": "◆", "LOW": "○"}
SEV_COLOR_HEX = {"CRITICAL": "#D93025", "HIGH": "#E37400", "MEDIUM": "#1A73E8", "LOW": "#34A853"}


# ── 2a. JSON renderer ─────────────────────────────────────────────────────────

def render_json(report: dict, output_path: Path) -> Path:
    out = output_path.with_suffix(".json")
    with open(out, "w") as f:
        json.dump(report, f, indent=2)
    return out


# ── 2b. Markdown renderer ─────────────────────────────────────────────────────

def render_markdown(report: dict, output_path: Path, brand_name: str = "", brand_color: str = "") -> Path:
    out = output_path.with_suffix(".md")
    lines = []
    site = report["site"]
    display_name = brand_name or site
    score = report["overall_score"]
    geo = report["geo_readiness"]
    summ = report["summary"]
    findings = report["findings"]

    lines += [
        f"# Brand AI Readiness Audit — {display_name}",
        "",
        f"> **Site:** [{site}](https://{site})  ",
        f"> **Audited:** {report['audited_at'][:10]}  ",
        f"> **Overall GEO Score:** {score}/100 — {geo}  ",
        f"> **Findings:** {summ['critical']} Critical · {summ['high']} High · {summ['medium']} Medium · {summ['low']} Low  ",
        "",
        "---",
        "",
        "## GEO Dimension Scores",
        "",
        "| Dimension | Score | Status |",
        "|-----------|------:|--------|",
    ]
    for d in report["dimension_scores"]:
        status = "✅ On track" if d["score"] >= 70 else "⚠️ Developing" if d["score"] >= 50 else "🔴 Critical gap"
        lines.append(f"| {d['name']} | {d['score']} | {status} |")

    lines += [
        "",
        "## Per-Engine GEO Scores",
        "",
        "| Engine | Score | Threshold |",
        "|--------|------:|-----------|",
    ]
    for engine, escore in report["engine_scores"].items():
        status = "✅" if escore >= 70 else "⚠️"
        lines.append(f"| {engine} | {escore} | {status} 70 |")

    # Projected score section
    proj = report.get("projected_score", {})
    if proj:
        lines += [
            "",
            "## 🚀 Projected Score After Fixes",
            "",
            f"> {proj.get('note', '')}",
            "",
            f"| Metric | Current | After Fixes |",
            f"|--------|---------|-------------|",
            f"| Overall GEO Score | {proj.get('current_overall', '—')} | **{proj.get('projected_overall', '—')}** |",
            f"| GEO Readiness | {report.get('geo_readiness', '—')} | **{proj.get('projected_geo_readiness', '—')}** |",
            f"| Score Lift | — | **+{proj.get('score_lift', 0)} pts** |",
            "",
        ]

    # Citability Coverage + Vertical Benchmark section (Markdown)
    cit_md = report.get("citability_coverage", {})
    vb_md = report.get("vertical_benchmark", {})
    if cit_md.get("pct") is not None or vb_md:
        lines += ["", "## 📈 Performance Metrics", ""]
        if cit_md.get("pct") is not None:
            lines.append(f"**Citability Coverage:** {cit_md.get('pct')}% ({cit_md.get('citeable_passages',0)}/{cit_md.get('total_passages',0)} passages extractable) — {cit_md.get('interpretation','')}")
        if vb_md:
            lines.append(f"**Industry Benchmark:** {vb_md.get('overall_position','')} — ~{vb_md.get('estimated_percentile',0)}th percentile vs. {vb_md.get('benchmark_source','benchmark')}")
            lines += [
                "",
                "| Dimension | Your Score | Benchmark Median | Delta |",
                "|-----------|-----------|------------------|-------|",
            ]
            for dn, dc in (vb_md.get("dimension_comparison") or {}).items():
                lines.append(f"| {dn} | {dc.get('your_score',0)} | {dc.get('benchmark_median',0)} | **{dc.get('vs_median',0)}** |")
        lines.append("")

    # Score formula section (Markdown)
    sf_md = report.get("score_formula", {})
    if sf_md:
        lines += [
            "",
            "## 🔢 Score Formula",
            "",
            f"> {sf_md.get('formula_note','')}",
            "",
            "| Engine | Formula | Score |",
            "|--------|---------|-------|",
        ]
        for ef in sf_md.get("engine_formulas", []):
            lines.append(f"| {ef['engine']} | `{ef['formula'][:100]}` | **{ef['result']}** |")
        lines.append("")

    # Action roadmap section
    roadmap = report.get("geo_score", {}).get("action_roadmap", [])
    if roadmap:
        lines += [
            "",
            "## 🗺 Prioritised Action Roadmap",
            "",
            "| # | Dimension | Action | Effort | Est. Lift |",
            "|---|-----------|--------|--------|-----------|",
        ]
        for item in roadmap:
            lines.append(
                f"| {item['priority']} | {item['dimension']} | {item['action'][:80]} | "
                f"`{item.get('effort','?')}` | {item.get('estimated_score_lift','—')} |"
            )
        lines.append("")

    # Group findings by severity
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        sev_findings = [f for f in findings if f["severity"] == sev]
        if not sev_findings:
            continue
        lines += ["", f"---", "", f"## {SEV_ICON[sev]} {sev} — {len(sev_findings)} finding{'s' if len(sev_findings)>1 else ''}",  ""]
        for f in sev_findings:
            lift_line = f"\n> 📈 **Research lift:** {f['research_lift']}" if f.get("research_lift") else ""
            lines += [
                f"### `{f['id']}` {f['title']}",
                "",
                f"**Evidence:** {f['evidence']}",
                "",
                f"**Action:** {f['suggested_action']['summary']}",
                f"> Effort: `{f['suggested_action'].get('effort','?')}` · Priority: `{f['suggested_action'].get('priority','?')}`{lift_line}",
                "",
            ]

    # Passing checks summary
    lines += [
        "---",
        "",
        "## ✅ Passing Checks",
        "",
        f"{summ['passing_checks']} skill scripts completed successfully with data.",
        "",
        "---",
        "",
        f"*Generated by Brand AI Readiness Audit v2.0 · {report['audited_at'][:10]} · 72 finding IDs across 6 GEO dimensions*",
    ]

    out.write_text("\n".join(lines))
    return out


# ── 2c. HTML renderer ─────────────────────────────────────────────────────────

def _bar_svg(categories: list[str], values: list[int], width: int = 540, height: int = 180,
             threshold: int | None = 70, color: str = "#0066CC") -> str:
    """Render a minimal inline SVG bar chart — zero dependencies."""
    pad_l, pad_r, pad_t, pad_b = 40, 12, 10, 40
    chart_w = width - pad_l - pad_r
    chart_h = height - pad_t - pad_b
    max_val = max(max(values), threshold or 0, 1)
    bar_w = chart_w / len(categories)
    gap = bar_w * 0.18

    bars = []
    for i, (cat, val) in enumerate(zip(categories, values)):
        bw = bar_w - gap * 2
        bh = (val / max_val) * chart_h
        bx = pad_l + i * bar_w + gap
        by = pad_t + chart_h - bh
        # Color by value vs threshold
        fill = color if (threshold is None or val >= threshold) else "#E37400" if val >= threshold * 0.7 else "#D93025"
        bars.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{bh:.1f}" fill="{fill}" rx="2"/>')
        bars.append(f'<text x="{bx+bw/2:.1f}" y="{by-3:.1f}" text-anchor="middle" font-size="10" fill="#555">{val}</text>')
        # x-label — truncate
        label = cat if len(cat) <= 10 else cat[:9] + "…"
        bars.append(f'<text x="{bx+bw/2:.1f}" y="{pad_t+chart_h+14:.1f}" text-anchor="middle" font-size="9" fill="#666">{label}</text>')

    # Y-axis line
    axes = [f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+chart_h}" stroke="#ddd" stroke-width="1"/>']
    # Y gridlines
    for v in [25, 50, 75, 100]:
        y = pad_t + chart_h - (v / max_val) * chart_h
        axes.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l+chart_w}" y2="{y:.1f}" stroke="#eee" stroke-width="1"/>')
        axes.append(f'<text x="{pad_l-4:.1f}" y="{y+3:.1f}" text-anchor="end" font-size="9" fill="#999">{v}</text>')

    # Threshold line
    thresh_line = ""
    if threshold is not None:
        ty = pad_t + chart_h - (threshold / max_val) * chart_h
        thresh_line = (
            f'<line x1="{pad_l}" y1="{ty:.1f}" x2="{pad_l+chart_w}" y2="{ty:.1f}" '
            f'stroke="#E37400" stroke-width="1.5" stroke-dasharray="4,3"/>'
            f'<text x="{pad_l+chart_w+2}" y="{ty+4:.1f}" font-size="9" fill="#E37400">threshold</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'style="width:100%;max-width:{width}px;display:block">'
        + "".join(axes) + thresh_line + "".join(bars) +
        "</svg>"
    )


def render_html(report: dict, output_path: Path, brand_name: str = "", brand_color: str = "#0066CC") -> Path:
    out = output_path.with_suffix(".html")
    site = report["site"]
    display_name = brand_name or site
    score = report["overall_score"]
    geo = report["geo_readiness"]
    summ = report["summary"]
    findings = report["findings"]
    dim_scores = report["dimension_scores"]
    engine_scores = report["engine_scores"]
    audited = report["audited_at"][:10]
    accent = brand_color

    # Score color
    if score >= 70:
        score_color = "#1E8449"
        geo_badge_class = "badge-green"
    elif score >= 50:
        score_color = "#E37400"
        geo_badge_class = "badge-orange"
    else:
        score_color = "#D93025"
        geo_badge_class = "badge-red"

    # Charts
    dim_chart = _bar_svg(
        [d["name"].split()[0] for d in dim_scores],
        [d["score"] for d in dim_scores],
        color=accent,
    )
    engine_chart = _bar_svg(
        [e.split()[0] for e in engine_scores.keys()],
        list(engine_scores.values()),
        color=accent,
    )

    # Findings HTML
    detected_platform = report.get("platform_detected", "generic")

    def finding_card(f: dict) -> str:
        sev = f["severity"]
        action = f["suggested_action"]
        color = SEV_COLOR_HEX.get(sev, "#555")
        icon = SEV_ICON.get(sev, "●")
        effort_badge = f'<span class="badge">{action.get("effort","?").upper()} effort</span>'

        # Research lift badge
        lift = f.get("research_lift")
        lift_badge = f'<span style="background:#d1fae5;color:#065f46;border-radius:4px;padding:1px 7px;font-size:10px;font-weight:700;margin-left:6px">📈 {lift}</span>' if lift else ""

        # Platform-specific fix code
        fix_code_block = ""
        pfc = f.get("platform_fix_code", {})
        if pfc and pfc.get("code"):
            platform_label = pfc.get("platform", "generic").upper()
            fix_code_escaped = pfc["code"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            fix_code_block = f"""
<details style="margin-top:8px">
  <summary style="cursor:pointer;font-size:11px;color:#1A73E8;font-weight:600">
    🔧 {platform_label} Fix Code (click to expand)
  </summary>
  <pre style="margin-top:6px;background:#1e1e2e;color:#cdd6f4;border-radius:6px;padding:12px;font-size:11px;overflow-x:auto;white-space:pre-wrap">{fix_code_escaped}</pre>
</details>"""

        return f"""
<div class="finding-card" id="{f['id']}">
  <div class="finding-header">
    <span class="sev-dot" style="color:{color}">{icon}</span>
    <span class="sev-label" style="color:{color}">{sev}</span>
    <code class="finding-id">{f['id']}</code>
    <span class="finding-title">{f['title']}</span>
    {effort_badge}{lift_badge}
  </div>
  <div class="finding-body">
    <div class="evidence"><strong>Evidence:</strong> {f['evidence']}</div>
    <div class="action"><strong>Action:</strong> {action['summary']}</div>
    {fix_code_block}
  </div>
</div>"""

    findings_html = ""
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        sf = [f for f in findings if f["severity"] == sev]
        if not sf:
            continue
        color = SEV_COLOR_HEX[sev]
        findings_html += f"""
<section class="sev-section">
  <h3 class="sev-heading" style="border-left:4px solid {color};padding-left:10px;color:{color}">
    {SEV_ICON[sev]} {sev} &mdash; {len(sf)} finding{'s' if len(sf)>1 else ''}
  </h3>
  {''.join(finding_card(f) for f in sf)}
</section>"""

    # Dimension table
    dim_rows = ""
    for d in dim_scores:
        status = "✓ On track" if d["score"] >= 70 else "⚠ Developing" if d["score"] >= 50 else "✗ Critical gap"
        status_color = "#1E8449" if d["score"] >= 70 else "#E37400" if d["score"] >= 50 else "#D93025"
        dim_rows += f"""<tr>
  <td><strong>{d['id']}</strong></td>
  <td>{d['name']}</td>
  <td class="score-cell"><strong style="color:{score_color if d['score']>=70 else '#E37400' if d['score']>=50 else '#D93025'}">{d['score']}</strong></td>
  <td style="color:{status_color}">{status}</td>
</tr>"""

    # Engine table
    eng_rows = ""
    for engine, escore in engine_scores.items():
        sc = "#1E8449" if escore >= 70 else "#E37400" if escore >= 50 else "#D93025"
        eng_rows += f"""<tr>
  <td>{engine}</td>
  <td class="score-cell"><strong style="color:{sc}">{escore}</strong></td>
  <td style="color:{sc}">{'✓ On track' if escore>=70 else '⚠ Developing' if escore>=50 else '✗ Gap'}</td>
</tr>"""

    # Projected score HTML box
    proj = report.get("projected_score", {})
    proj_html = ""
    if proj:
        proj_score = proj.get("projected_overall", score)
        proj_label = proj.get("projected_geo_readiness", "")
        proj_lift = proj.get("score_lift", 0)
        proj_fixes = proj.get("fixes_required", 0)
        proj_color = "#1E8449" if proj_score >= 70 else "#E37400" if proj_score >= 50 else "#D93025"
        proj_html = f"""
<div style="background:#fff8e1;border:1.5px solid #f59e0b;border-radius:8px;padding:16px 20px;margin-bottom:28px;">
  <div style="font-size:13px;font-weight:700;color:#92400e;margin-bottom:8px;">🚀 Projected Score After Fixing All CRITICAL &amp; HIGH Findings</div>
  <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap;">
    <div>
      <span style="font-size:40px;font-weight:800;color:{proj_color}">{proj_score}</span>
      <span style="font-size:14px;color:#6b7280">/100</span>
      <div style="font-size:12px;font-weight:600;color:{proj_color};margin-top:2px">{proj_label}</div>
    </div>
    <div style="font-size:13px;color:#374151;flex:1;min-width:200px">
      <strong>+{proj_lift} points</strong> by fixing <strong>{proj_fixes} findings</strong><br>
      <span style="color:#6b7280">{proj.get('note','')}</span>
    </div>
  </div>
</div>"""

    # Citability Coverage % + Vertical Benchmark HTML
    cit = report.get("citability_coverage", {})
    vb = report.get("vertical_benchmark", {})
    citability_html = ""
    if cit.get("pct") is not None or vb:
        cit_pct = cit.get("pct", "N/A")
        cit_interp = cit.get("interpretation", "")
        cit_color = "#1E8449" if cit.get("interpretation") in ("Excellent", "Good") else "#E37400" if cit_interp == "Needs Work" else "#D93025"
        cit_section = f"""<div style="flex:1;min-width:200px">
  <div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:4px">📊 Citability Coverage</div>
  <div style="font-size:28px;font-weight:800;color:{cit_color}">{cit_pct}{'%' if cit_pct != 'N/A' else ''}</div>
  <div style="font-size:11px;color:#6b7280">{cit.get('citeable_passages',0)}/{cit.get('total_passages',0)} passages are AI-extractable</div>
  <div style="font-size:11px;color:{cit_color};font-weight:600">{cit_interp}</div>
</div>""" if cit.get("pct") is not None else ""

        vb_position = vb.get("overall_position", "")
        vb_percentile = vb.get("estimated_percentile", 0)
        vb_median = vb.get("benchmark_median", 52)
        vb_color = "#1E8449" if "Top" in vb_position else "#E37400" if "Above" in vb_position else "#D93025"
        vb_section = f"""<div style="flex:1;min-width:200px">
  <div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:4px">🏆 Industry Benchmark</div>
  <div style="font-size:28px;font-weight:800;color:{vb_color}">{vb_percentile}<span style="font-size:14px">th pct</span></div>
  <div style="font-size:11px;color:#6b7280">Benchmark median: {vb_median}/100 (10-site live run)</div>
  <div style="font-size:11px;color:{vb_color};font-weight:600">{vb_position}</div>
</div>""" if vb else ""

        # Dimension comparison table
        dim_comp_rows = ""
        for dim_name, comp in (vb.get("dimension_comparison") or {}).items():
            delta = comp.get("delta", 0)
            delta_color = "#1E8449" if delta >= 0 else "#D93025"
            dim_comp_rows += f"""<tr>
  <td>{dim_name}</td>
  <td style="text-align:right">{comp.get('your_score',0)}</td>
  <td style="text-align:right;color:#6b7280">{comp.get('benchmark_median',0)}</td>
  <td style="text-align:right;color:{delta_color};font-weight:600">{comp.get('vs_median','0')}</td>
</tr>"""

        citability_html = f"""
<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:8px;padding:16px 20px;margin-bottom:28px;">
  <h3 style="font-size:14px;font-weight:700;margin-bottom:16px">📈 Performance Metrics</h3>
  <div style="display:flex;gap:24px;flex-wrap:wrap;margin-bottom:16px">
    {cit_section}
    {vb_section}
  </div>
  {f'<table><thead><tr><th>Dimension</th><th style="text-align:right">Your Score</th><th style="text-align:right">Benchmark Median</th><th style="text-align:right">Delta</th></tr></thead><tbody>{dim_comp_rows}</tbody></table>' if dim_comp_rows else ""}
</div>"""

    # Score Formula Transparency HTML
    sf = report.get("score_formula", {})
    formula_html = ""
    if sf:
        formula_note = sf.get("formula_note", "")
        dim_scores_sf = sf.get("dimension_scores", {})
        dim_pills = " ".join(
            f'<span style="background:#f3f4f6;border:1px solid #d1d5db;border-radius:4px;padding:2px 8px;font-size:11px;margin:2px">{k}: <strong>{v}</strong></span>'
            for k, v in dim_scores_sf.items()
        )
        engine_rows_sf = ""
        for ef in sf.get("engine_formulas", []):
            engine_rows_sf += f"""<tr>
  <td style="font-weight:600;white-space:nowrap">{ef['engine']}</td>
  <td style="font-size:11px;color:#6b7280;font-family:monospace">{ef['formula'][:120]}{'…' if len(ef['formula']) > 120 else ''}</td>
  <td style="text-align:right;font-weight:700">{ef['result']}</td>
</tr>"""
        formula_html = f"""
<details style="margin-bottom:28px;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden">
  <summary style="background:#f9fafb;padding:12px 16px;cursor:pointer;font-weight:700;font-size:13px">
    🔢 Score Formula Transparency (click to expand)
  </summary>
  <div style="padding:16px">
    <p style="font-size:12px;color:#6b7280;margin-bottom:12px">{formula_note}</p>
    <div style="margin-bottom:12px">{dim_pills}</div>
    <table style="font-size:12px">
      <thead><tr><th>Engine</th><th>Formula (dimension × weight)</th><th style="text-align:right">Score</th></tr></thead>
      <tbody>{engine_rows_sf}</tbody>
    </table>
  </div>
</details>"""

    # Action roadmap HTML
    roadmap = report.get("geo_score", {}).get("action_roadmap", [])
    roadmap_html = ""
    if roadmap:
        rows = ""
        for item in roadmap:
            effort_color = "#D93025" if item.get("effort") == "high" else "#E37400" if item.get("effort") == "medium" else "#1E8449"
            sev_color = SEV_COLOR_HEX.get(item.get("severity", "MEDIUM"), "#555")
            rows += f"""<tr>
  <td style="text-align:center;font-weight:700">{item['priority']}</td>
  <td style="font-size:12px;color:#6b7280">{item['dimension']}</td>
  <td style="font-size:12px">{item['action'][:90]}{'…' if len(item['action']) > 90 else ''}</td>
  <td><span style="background:{effort_color}22;color:{effort_color};border-radius:4px;padding:1px 6px;font-size:11px;font-weight:600">{item.get('effort','?').upper()}</span></td>
  <td style="font-size:12px;color:#1E8449;font-weight:600">{item.get('estimated_score_lift','—')}</td>
</tr>"""
        roadmap_html = f"""
<h2>🗺 Prioritised Action Roadmap</h2>
<table>
  <thead><tr>
    <th style="width:40px">#</th>
    <th>Dimension</th>
    <th>Action</th>
    <th style="width:80px">Effort</th>
    <th style="width:90px">Est. Lift</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Readiness Audit — {display_name}</title>
<style>
  :root {{
    --accent: {accent};
    --bg: #fafafa;
    --surface: #ffffff;
    --border: #e5e7eb;
    --text: #111827;
    --muted: #6b7280;
    --radius: 8px;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
          background: var(--bg); color: var(--text); font-size: 14px; line-height: 1.6; }}
  .page {{ max-width: 960px; margin: 0 auto; padding: 32px 24px 64px; }}

  /* Header */
  .report-header {{ display:flex; justify-content:space-between; align-items:flex-start;
                    border-bottom: 2px solid var(--accent); padding-bottom: 20px; margin-bottom: 28px; }}
  .report-title {{ font-size: 22px; font-weight: 700; color: var(--text); }}
  .report-meta {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}
  .score-block {{ text-align: right; }}
  .score-number {{ font-size: 56px; font-weight: 800; line-height: 1; color: {score_color}; }}
  .score-label {{ font-size: 11px; color: var(--muted); }}
  .badge-green  {{ background:#d1fae5; color:#065f46; border-radius:9999px; padding:3px 10px; font-size:12px; font-weight:600; display:inline-block; margin-top:4px; }}
  .badge-orange {{ background:#fff7ed; color:#92400e; border-radius:9999px; padding:3px 10px; font-size:12px; font-weight:600; display:inline-block; margin-top:4px; }}
  .badge-red    {{ background:#fee2e2; color:#7f1d1d; border-radius:9999px; padding:3px 10px; font-size:12px; font-weight:600; display:inline-block; margin-top:4px; }}

  /* Stat strip */
  .stat-strip {{ display:grid; grid-template-columns: repeat(4,1fr); gap:12px; margin-bottom:28px; }}
  .stat-card {{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius);
                padding: 14px 16px; }}
  .stat-value {{ font-size: 28px; font-weight: 700; }}
  .stat-label {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing:.5px; margin-top:2px; }}
  .critical {{ color: #D93025; }}
  .high     {{ color: #E37400; }}
  .medium   {{ color: #1A73E8; }}
  .low      {{ color: #34A853; }}
  .pass     {{ color: #1E8449; }}

  /* Charts */
  .chart-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:28px; }}
  .chart-card {{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:16px; }}
  .chart-title {{ font-size:13px; font-weight:600; margin-bottom:12px; color:var(--muted); }}

  /* Tables */
  h2 {{ font-size:16px; font-weight:700; margin:28px 0 12px; color:var(--text); }}
  h3 {{ font-size:14px; font-weight:600; margin:0 0 10px; }}
  table {{ width:100%; border-collapse:collapse; margin-bottom:24px; background:var(--surface);
           border:1px solid var(--border); border-radius:var(--radius); overflow:hidden; font-size:13px; }}
  th {{ background:#f3f4f6; font-weight:600; text-align:left; padding:8px 12px; border-bottom:1px solid var(--border); }}
  td {{ padding:8px 12px; border-bottom:1px solid var(--border); vertical-align:top; }}
  tr:last-child td {{ border-bottom:none; }}
  .score-cell {{ text-align:right; font-size:16px; }}

  /* Findings */
  .sev-section {{ margin-bottom:24px; }}
  .sev-heading {{ font-size:14px; font-weight:700; margin-bottom:12px; }}
  .finding-card {{ background:var(--surface); border:1px solid var(--border);
                   border-radius:var(--radius); margin-bottom:10px; overflow:hidden; }}
  .finding-header {{ display:flex; align-items:center; gap:8px; padding:10px 14px;
                     border-bottom:1px solid var(--border); flex-wrap:wrap; }}
  .sev-dot {{ font-size:14px; flex-shrink:0; }}
  .sev-label {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.5px; flex-shrink:0; }}
  .finding-id {{ background:#f3f4f6; padding:1px 6px; border-radius:4px; font-size:11px; flex-shrink:0; }}
  .finding-title {{ font-weight:600; font-size:13px; flex:1; min-width:200px; }}
  .badge {{ background:#f3f4f6; color:var(--muted); border-radius:4px; padding:1px 6px; font-size:10px;
            text-transform:uppercase; letter-spacing:.4px; }}
  .finding-body {{ padding:10px 14px; font-size:13px; }}
  .evidence {{ color:var(--muted); margin-bottom:6px; }}
  .action {{ color:var(--text); }}

  /* Footer */
  .report-footer {{ margin-top:40px; padding-top:16px; border-top:1px solid var(--border);
                    font-size:11px; color:var(--muted); }}

  @media print {{
    body {{ background:white; }}
    .page {{ padding:16px; }}
    .finding-card {{ break-inside:avoid; }}
    .sev-section {{ break-inside:avoid; }}
  }}
</style>
</head>
<body>
<div class="page">

  <!-- Header -->
  <div class="report-header">
    <div>
      <div class="report-title">Brand AI Readiness Audit &mdash; {display_name}</div>
      <div class="report-meta">
        <a href="https://{site}" style="color:var(--accent)">{site}</a> &middot;
        Audited {audited} &middot; 10 skill scripts &middot; live HTTP probes
      </div>
    </div>
    <div class="score-block">
      <div class="score-number">{score}</div>
      <div class="score-label">/ 100 overall GEO score</div>
      <div class="{geo_badge_class}">{geo}</div>
    </div>
  </div>

  <!-- Stat strip -->
  <div class="stat-strip">
    <div class="stat-card"><div class="stat-value critical">{summ['critical']}</div><div class="stat-label">Critical</div></div>
    <div class="stat-card"><div class="stat-value high">{summ['high']}</div><div class="stat-label">High</div></div>
    <div class="stat-card"><div class="stat-value medium">{summ['medium']}</div><div class="stat-label">Medium</div></div>
    <div class="stat-card"><div class="stat-value low">{summ['low']}</div><div class="stat-label">Low</div></div>
  </div>

  <!-- Charts -->
  <div class="chart-grid">
    <div class="chart-card">
      <div class="chart-title">GEO DIMENSION SCORES (threshold: 70)</div>
      {dim_chart}
    </div>
    <div class="chart-card">
      <div class="chart-title">PER-ENGINE GEO SCORES (threshold: 70)</div>
      {engine_chart}
    </div>
  </div>

  <!-- Dimension table -->
  <h2>6 GEO Dimensions</h2>
  <table>
    <thead><tr><th>ID</th><th>Dimension</th><th style="text-align:right">Score</th><th>Status</th></tr></thead>
    <tbody>{dim_rows}</tbody>
  </table>

  <!-- Engine table -->
  <h2>Per-Engine Readiness</h2>
  <table>
    <thead><tr><th>AI Engine</th><th style="text-align:right">Score</th><th>Status</th></tr></thead>
    <tbody>{eng_rows}</tbody>
  </table>

  <!-- Projected score -->
  {proj_html}

  <!-- Action Roadmap -->
  {roadmap_html}

  <!-- Citability Coverage & Vertical Benchmark -->
  {citability_html}

  <!-- Score Formula Transparency -->
  {formula_html}

  <!-- Findings -->
  <h2>Findings ({summ['total_findings']} total)</h2>
  {findings_html}

  <!-- Footer -->
  <div class="report-footer">
    Generated by Brand AI Readiness Audit v2.1 &middot; {audited} &middot;
    90 finding IDs across 6 GEO dimensions &middot;
    <a href="https://github.com/Adobe_Hack_2026" style="color:var(--accent)">github</a>
  </div>

</div>
</body>
</html>"""

    out.write_text(html)
    return out


# ── 2d. PDF renderer ──────────────────────────────────────────────────────────

# Candidate Chrome/Chromium executables, in priority order
_CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "google-chrome",
    "chromium",
]


def _find_chrome() -> str | None:
    """Return path to first available Chrome/Chromium binary."""
    import shutil
    for candidate in _CHROME_CANDIDATES:
        if os.path.isfile(candidate):
            return candidate
        found = shutil.which(candidate)
        if found:
            return found
    return None


def render_pdf(report: dict, output_path: Path, brand_name: str = "", brand_color: str = "#0066CC") -> Path:
    """
    Render PDF using (in priority order):
      1. Chrome/Chromium headless --print-to-pdf  (best quality, no extra deps)
      2. weasyprint                                (pip install weasyprint + system libs)
      3. Graceful fallback: save HTML + print instructions

    The HTML intermediate file is cleaned up after a successful PDF render.
    """
    import subprocess
    import tempfile

    # Always generate the HTML first — used by all paths
    html_path = render_html(
        report,
        output_path.with_name(output_path.stem + "_for_pdf"),
        brand_name,
        brand_color,
    )
    out = output_path.with_suffix(".pdf")

    # ── Path 1: Chrome headless ───────────────────────────────────────────────
    chrome = _find_chrome()
    if chrome:
        try:
            with tempfile.TemporaryDirectory() as tmp_profile:
                result = subprocess.run(
                    [
                        chrome,
                        "--headless=new",
                        "--disable-gpu",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        f"--user-data-dir={tmp_profile}",
                        f"--print-to-pdf={out}",
                        "--print-to-pdf-no-header",
                        f"file://{html_path.resolve()}",
                    ],
                    capture_output=True,
                    timeout=60,
                )
            if out.exists() and out.stat().st_size > 1024:
                html_path.unlink(missing_ok=True)
                return out
            else:
                print(f"  ⚠  Chrome PDF empty or missing (stderr: {result.stderr[:200].decode(errors='replace')})", file=sys.stderr)
        except Exception as e:
            print(f"  ⚠  Chrome headless failed: {e}", file=sys.stderr)

    # ── Path 2: weasyprint ────────────────────────────────────────────────────
    try:
        from weasyprint import HTML as WHP  # type: ignore
        WHP(filename=str(html_path)).write_pdf(str(out))
        if out.exists():
            html_path.unlink(missing_ok=True)
            return out
    except Exception as e:
        print(f"  ⚠  weasyprint failed: {e}", file=sys.stderr)

    # ── Path 3: Graceful fallback ─────────────────────────────────────────────
    # Keep the HTML and write a small companion notice
    notice = out.with_suffix(".pdf.txt")
    notice.write_text(
        "PDF auto-generation was not available on this machine.\n\n"
        "To generate the PDF manually (choose one):\n\n"
        "  Option A — Chrome headless (recommended):\n"
        '    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \\\n'
        "      --headless=new --print-to-pdf=report.pdf --print-to-pdf-no-header \\\n"
        f"      file://{html_path.resolve()}\n\n"
        "  Option B — Browser print dialog:\n"
        f"    open {html_path}\n"
        "    Then: File → Print → Save as PDF (set margins to None)\n\n"
        "  Option C — weasyprint (requires system libs):\n"
        "    brew install pango gobject-introspection\n"
        "    pip install weasyprint\n"
        f"    python3 -c \"from weasyprint import HTML; HTML('{html_path}').write_pdf('report.pdf')\"\n\n"
        f"Your HTML report (identical content):\n  {html_path}\n"
    )
    print(f"  ℹ  PDF fallback: HTML saved at {html_path}", file=sys.stderr)
    print(f"     See instructions: {notice}", file=sys.stderr)
    return notice


# ══════════════════════════════════════════════════════════════════════════════
# 3. CLI
# ══════════════════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Brand AI Readiness Audit — Multi-Format Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("audit_dir", help="Directory containing the 10 skill JSON output files")
    p.add_argument("--format", default="html,md",
                   help="Comma-separated list of output formats: html,md,pdf,json (default: html,md)")
    p.add_argument("--output-dir", default="",
                   help="Where to write report files (default: <audit_dir>/reports/)")
    p.add_argument("--brand-name", default="",
                   help="Brand name for report title (default: inferred from site domain)")
    p.add_argument("--brand-color", default="#0066CC",
                   help="Accent color in HTML/PDF reports (default: #0066CC)")
    p.add_argument("--site", default="",
                   help="Override the site URL displayed in the report")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    audit_dir = Path(args.audit_dir).expanduser().resolve()
    if not audit_dir.exists():
        print(f"Error: audit directory not found: {audit_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else audit_dir / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    formats = [f.strip().lower() for f in args.format.split(",")]
    valid_formats = {"html", "md", "pdf", "json"}
    invalid = set(formats) - valid_formats
    if invalid:
        print(f"Error: unknown format(s): {invalid}. Valid: {valid_formats}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'─'*60}")
    print(f"  Brand AI Readiness Audit — Report Generator")
    print(f"{'─'*60}")
    print(f"  Input dir  : {audit_dir}")
    print(f"  Output dir : {output_dir}")
    print(f"  Formats    : {', '.join(formats)}")
    if args.brand_name:
        print(f"  Brand name : {args.brand_name}")
    if args.brand_color != "#0066CC":
        print(f"  Brand color: {args.brand_color}")
    print()

    # Load outputs
    print("  Loading skill outputs…")
    outputs = load_skill_outputs(audit_dir)
    if not outputs:
        print("  Error: no skill outputs found.", file=sys.stderr)
        sys.exit(1)

    # Infer site from outputs
    site = args.site
    if not site:
        for v in outputs.values():
            if isinstance(v, dict) and v.get("site"):
                site = v["site"]
                break
    if not site:
        site = audit_dir.parent.name  # fallback: parent directory name

    audited_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # Try to read from any skill output
    for v in outputs.values():
        if isinstance(v, dict) and v.get("probed_at"):
            audited_at = v["probed_at"]
            break

    print(f"  Building unified report for {site}…")
    report = build_report(outputs, site, audited_at)

    n = report["summary"]["total_findings"]
    score = report["overall_score"]
    geo = report["geo_readiness"]
    print(f"  Score: {score}/100 ({geo}) · {n} findings")
    print()

    # Render each format
    stem = f"ai-readiness-audit-{site.replace('.', '_').replace('www_', '')}"
    generated = []

    if "json" in formats:
        path = render_json(report, output_dir / stem)
        generated.append(("JSON", path))
        print(f"  ✅ JSON   → {path}")

    if "md" in formats:
        path = render_markdown(report, output_dir / stem, args.brand_name, args.brand_color)
        generated.append(("Markdown", path))
        print(f"  ✅ MD     → {path}")

    if "html" in formats:
        path = render_html(report, output_dir / stem, args.brand_name, args.brand_color)
        generated.append(("HTML", path))
        print(f"  ✅ HTML   → {path}")

    if "pdf" in formats:
        path = render_pdf(report, output_dir / stem, args.brand_name, args.brand_color)
        generated.append(("PDF", path))
        print(f"  ✅ PDF    → {path}")

    print()
    print(f"  {'─'*50}")
    print(f"  {len(generated)} report(s) written to: {output_dir}/")
    print()


if __name__ == "__main__":
    main()
