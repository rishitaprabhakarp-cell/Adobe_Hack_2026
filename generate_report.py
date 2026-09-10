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
    "crawlability":   "crawlability.json",
    "render":         "render.json",
    "schema":         "schema.json",
    "entity":         "entity.json",
    "content":        "content.json",
    "eeeat":          "eeeat.json",
    "engagement":     "engagement.json",
    "rsl":            "rsl.json",
    "opengraph":      "opengraph.json",
    "technical":      "technical.json",
    "landing_clarity": "landing_clarity.json",
    "content_trust":  "content_trust.json",
    "url_resilience": "url_resilience.json",
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
    {"id": "D1", "name": "Crawlability",           "weight_key": "crawl",   "finding_prefixes": ["RC2","RC4","RC7","RC14","RC17","RC19","RC23","RC29","CDN-WAF","RSL"]},
    {"id": "D2", "name": "Content Extractability", "weight_key": "content", "finding_prefixes": ["CEA","RC8","RC11","RC24","RC26"]},
    {"id": "D3", "name": "Entity Clarity",         "weight_key": "entity",  "finding_prefixes": ["RC5","RC6","EEAT-007","CITE-003","CITE-004"]},
    {"id": "D4", "name": "Schema Integrity",       "weight_key": "schema",  "finding_prefixes": ["RC3","RC10","RC11","RC13","RC15","RC18","RC21","OG-007","SC-"]},
    {"id": "D5", "name": "Off-Page Authority",     "weight_key": "authority","finding_prefixes": ["EEAT","CITE-001","CITE-002","RC6"]},
    {"id": "D6", "name": "Technical Foundation",   "weight_key": "technical","finding_prefixes": ["RC1","RC9","RC12","RC20","TSEO","OG-00","IMG-","RC25","RC27","RC28","RC30","RC-NAV","RC-TRUST"]},
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
                "evidence": "Checked /feed, /rss.xml, /atom.xml, /feed.xml — all returned non-200.",
                "suggested_action": {"summary": "Create an RSS/Atom feed. Perplexity and AI news agents index feeds for freshness.", "priority": "medium", "effort": "low"}})

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
                "evidence": "No Organization, Corporation, or LocalBusiness @type found in JSON-LD.",
                "suggested_action": {"summary": "Add Organization JSON-LD with name, url, logo, and sameAs to every page.", "priority": "high", "effort": "low"}})

        if not schema.get("site_has_speakable") and not any("Speakable" in str(t) for t in types):
            findings.append({"id": "SC-001", "title": "No Speakable schema",
                "severity": "MEDIUM",
                "evidence": "site_has_speakable=False. No SpeakableSpecification markup found.",
                "suggested_action": {"summary": "Add Speakable schema to product descriptions and key content sections.", "priority": "medium", "effort": "low"}})

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
                "evidence": f"Images without alt attributes: {', '.join(all_missing_alts[:3])}{'...' if len(all_missing_alts)>3 else ''}",
                "suggested_action": {"summary": "Add descriptive alt text to all images. Alt text is an AI-indexable content signal.", "priority": "medium", "effort": "low"}})

    # ── content extractability ────────────────────────────────────────────────
    content = outputs.get("content", {})
    if content:
        for page in content.get("pages", [])[:2]:
            url_label = page.get("path", "/")

            above = page.get("above_fold", {})
            if not above.get("has_direct_claim"):
                findings.append({"id": "CEA-001", "title": f"No direct answer in first 80 words ({url_label})",
                    "severity": "HIGH",
                    "evidence": f"First 80 words: \"{above.get('first_80_words','')[:120]}...\"",
                    "suggested_action": {"summary": "Open the page with a clear, self-contained statement of what the brand/product does.", "priority": "high", "effort": "low"}})

            caps = page.get("answer_capsules", {})
            ratio = caps.get("capsule_ratio", 1)
            if ratio < 0.5 and caps.get("sections_analyzed", 0) > 0:
                sev = "HIGH" if ratio < 0.2 else "MEDIUM"
                findings.append({"id": "CEA-009", "title": f"Low answer-capsule ratio ({ratio:.0%}) on {url_label}",
                    "severity": sev,
                    "evidence": f"{caps.get('answer_capsules_found',0)}/{caps.get('sections_analyzed',0)} H2/H3 sections have a 40+ word direct answer capsule. ChatGPT citation correlation: 72.4% of cited pages have ≥50%.",
                    "suggested_action": {"summary": "Add a direct 40–60 word answer paragraph immediately after each major H2/H3 heading.", "priority": "high", "effort": "medium"}})

            cliches = page.get("ai_cliches", {})
            if cliches.get("cliche_count", 0) >= 4:
                sev = "HIGH" if cliches["cliche_count"] >= 6 else "MEDIUM"
                findings.append({"id": "CEA-010", "title": f"High AI-cliché density ({cliches['cliche_count']} phrases) on {url_label}",
                    "severity": sev,
                    "evidence": f"AI-slop phrases: {', '.join(cliches.get('examples',[])[:3])}",
                    "suggested_action": {"summary": "Rewrite flagged phrases with first-person experience and concrete claims.", "priority": "medium", "effort": "medium"}})

            stats = page.get("statistics", {})
            if stats.get("total_statistics", 0) > 0 and stats.get("citation_ratio", 1) < 0.5:
                findings.append({"id": "CEA-004", "title": f"Statistics without source citations on {url_label}",
                    "severity": "HIGH",
                    "evidence": f"{stats.get('without_citation',0)} uncited stats, {stats.get('with_citation',0)} cited. Princeton KDD 2024: sourced stats → +40% AI citation.",
                    "suggested_action": {"summary": "Add source links or parenthetical citations to every statistic.", "priority": "high", "effort": "low"}})

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
                    "evidence": f"{headings.get('question_format_count',0)}/{headings.get('total_h2_h3_count',0)} H2/H3s are questions. Sample: {headings.get('sample_question_headings',['none'])[:2]}",
                    "suggested_action": {"summary": "Rewrite key H2 headings as questions to improve FAQ schema eligibility and AI direct-answer targeting.", "priority": "medium", "effort": "low"}})

            if not page.get("key_takeaways", {}).get("has_key_takeaways"):
                findings.append({"id": "CEA-006", "title": f"No key-takeaway / TL;DR box on {url_label}",
                    "severity": "LOW",
                    "evidence": "No TL;DR, summary, or key-highlight block detected.",
                    "suggested_action": {"summary": "Add a 'Key highlights' box near top of content pages.", "priority": "low", "effort": "low", "proactive": True}})

            if not page.get("date_markers", {}).get("has_date_marker"):
                findings.append({"id": "CEA-008", "title": f"No content freshness date marker on {url_label}",
                    "severity": "MEDIUM",
                    "evidence": "No visible 'As of [date]' or 'Last updated' text marker found.",
                    "suggested_action": {"summary": "Add 'Last updated: [Month Year]' visible text. Freshness is top Perplexity ranking signal.", "priority": "medium", "effort": "low"}})

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
                "evidence": "No G2, Capterra, Trustpilot, or other review platform links detected.",
                "suggested_action": {"summary": "Add G2/Trustpilot badges. SE Ranking 2026: review links → 3× citation probability.", "priority": "medium", "effort": "low"}})

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
                "evidence": "/.well-known/rsl.json returns 404 and no <link rel='robots-standard-license'> in HTML.",
                "suggested_action": {"summary": "Deploy /.well-known/rsl.json with RSL 1.0 to declare content reuse terms for AI crawlers.", "priority": "high", "effort": "low"}})

        ep_count = rsl.get("ai_discovery_endpoint_count", 0)
        if ep_count == 0:
            findings.append({"id": "RSL-003", "title": f"Zero AI discovery endpoints present (0/14 checked)",
                "severity": "HIGH",
                "evidence": "None of 14 AI discovery endpoints return HTTP 200.",
                "suggested_action": {"summary": "Deploy /.well-known/ai.txt and /ai/summary.json as minimum viable AI discovery.", "priority": "high", "effort": "low"}})
        elif ep_count < 3:
            findings.append({"id": "RSL-003", "title": f"Only {ep_count}/14 AI discovery endpoints present",
                "severity": "MEDIUM",
                "evidence": f"{ep_count} of 14 AI discovery endpoints return HTTP 200.",
                "suggested_action": {"summary": "Expand AI discovery coverage with /brand.txt and /identity.json.", "priority": "medium", "effort": "low"}})

        if not rsl.get("indexnow", {}).get("has_indexnow"):
            findings.append({"id": "RSL-004", "title": "IndexNow not implemented",
                "severity": "LOW",
                "evidence": "No IndexNow key found in HTML or robots.txt.",
                "suggested_action": {"summary": "Implement IndexNow to notify Bing/Perplexity on publish.", "priority": "low", "effort": "low", "proactive": True}})

        if not rsl.get("llms_full_txt", {}).get("present"):
            findings.append({"id": "RSL-002", "title": "No llms-full.txt companion file",
                "severity": "LOW",
                "evidence": "/llms-full.txt returns 404.",
                "suggested_action": {"summary": "Create /llms-full.txt with complete product documentation for LLM ingestion.", "priority": "low", "effort": "high", "proactive": True}})

        llms_val = rsl.get("llms_txt_deep_validation", {})
        if llms_val.get("present") and not llms_val.get("passes_spec"):
            issues = llms_val.get("issues", [])
            high_issues = [i for i in issues if i.get("severity") in ("HIGH","MEDIUM")]
            if high_issues:
                findings.append({"id": "RSL-005", "title": f"llms.txt fails spec validation ({len(high_issues)} issues)",
                    "severity": "MEDIUM",
                    "evidence": "; ".join(i["rule"] for i in high_issues[:3]),
                    "suggested_action": {"summary": "Fix llms.txt spec violations: ensure H1 present, use absolute links, verify no broken URLs.", "priority": "medium", "effort": "low"}})

    # ── OpenGraph ─────────────────────────────────────────────────────────────
    og = outputs.get("opengraph", {})
    if og:
        for page in og.get("pages", [])[:1]:
            og_tags = page.get("og") or {}
            if not og_tags.get("og:title") and not og_tags.get("og:description"):
                findings.append({"id": "OG-001", "title": "No OpenGraph tags on homepage",
                    "severity": "CRITICAL",
                    "evidence": "og:title, og:description, og:image all absent from homepage.",
                    "suggested_action": {"summary": "Add og:title, og:description, og:image, og:type to every page template.", "priority": "high", "effort": "low"}})
            elif not og_tags.get("og:image"):
                findings.append({"id": "OG-003", "title": "og:image missing",
                    "severity": "HIGH",
                    "evidence": "og:title and og:description present but og:image absent.",
                    "suggested_action": {"summary": "Add og:image (min 1200×630px) to all pages for rich previews in AI-powered social surfaces.", "priority": "high", "effort": "low"}})

            twitter = page.get("twitter") or {}
            if not twitter:
                findings.append({"id": "OG-005", "title": "No Twitter Card meta tags",
                    "severity": "LOW",
                    "evidence": "No twitter:card, twitter:title, or twitter:description found.",
                    "suggested_action": {"summary": "Add twitter:card=summary_large_image and twitter:title/description.", "priority": "low", "effort": "low", "proactive": True}})

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
                "evidence": f"h1_count={headings['h1_count']}. Multiple H1s dilute topical authority signal.",
                "suggested_action": {"summary": "Reduce to exactly one H1 per page.", "priority": "medium", "effort": "low"}})

        rt = tech.get("response_time_ms", 0)
        if rt and rt > 2000:
            findings.append({"id": "TSEO-009", "title": f"Slow homepage response time ({rt}ms)",
                "severity": "MEDIUM" if rt < 4000 else "HIGH",
                "evidence": f"Homepage response: {rt}ms. AI crawlers may time out above 3000ms.",
                "suggested_action": {"summary": "Optimise TTFB via CDN, caching, or server-side rendering improvements.", "priority": "medium", "effort": "high"}})

    # ── Landing Clarity (RC24, RC25, RC28, RC30) ─────────────────────────────
    landing = outputs.get("landing_clarity", {})
    if landing:
        for f in landing.get("findings", []):
            findings.append(f)

    # ── Content Trust (RC26, RC27, RC-TRUST, RC-NAV) ──────────────────────────
    content_trust = outputs.get("content_trust", {})
    if content_trust:
        for f in content_trust.get("findings", []):
            findings.append(f)

    # ── URL Resilience (RC29, RC30) ────────────────────────────────────────────
    url_resilience = outputs.get("url_resilience", {})
    if url_resilience:
        for f in url_resilience.get("findings", []):
            findings.append(f)

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

    return {
        "site": site,
        "audited_at": audited_at,
        "overall_score": overall,
        "geo_readiness": geo_label,
        "summary": {
            "total_findings": len(findings),
            **buckets,
            "passing_checks": sum(1 for k in outputs if outputs[k]),
        },
        "dimension_scores": dim_scores,
        "engine_scores": engine_scores,
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

    # Group findings by severity
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        sev_findings = [f for f in findings if f["severity"] == sev]
        if not sev_findings:
            continue
        lines += ["", f"---", "", f"## {SEV_ICON[sev]} {sev} — {len(sev_findings)} finding{'s' if len(sev_findings)>1 else ''}",  ""]
        for f in sev_findings:
            lines += [
                f"### `{f['id']}` {f['title']}",
                "",
                f"**Evidence:** {f['evidence']}",
                "",
                f"**Action:** {f['suggested_action']['summary']}",
                f"> Effort: `{f['suggested_action'].get('effort','?')}` · Priority: `{f['suggested_action'].get('priority','?')}`",
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


def _score_ring(score: int, size: int = 200, sw: int = 18) -> str:
    """SVG donut ring showing score/100."""
    r = (size - sw) / 2
    cx = cy = size / 2
    circ = 2 * math.pi * r
    filled = circ * score / 100
    gap = circ - filled
    sc = "#1E8449" if score >= 70 else "#E37400" if score >= 50 else "#D93025"
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">'
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="none" stroke="#334155" stroke-width="{sw}"/>'
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="none" stroke="{sc}" stroke-width="{sw}" '
        f'stroke-dasharray="{filled:.2f} {gap:.2f}" stroke-linecap="round" '
        f'transform="rotate(-90 {cx:.1f} {cy:.1f})"/>'
        f'<text x="{cx:.1f}" y="{cy - 8:.1f}" text-anchor="middle" font-size="{int(size * 0.28)}" font-weight="800" fill="{sc}">{score}</text>'
        f'<text x="{cx:.1f}" y="{cy + size * 0.18:.1f}" text-anchor="middle" font-size="{int(size * 0.1)}" fill="#94a3b8">/100</text>'
        f'</svg>'
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

    score_color = "#1E8449" if score >= 70 else "#E37400" if score >= 50 else "#D93025"
    geo_bg   = "#d1fae5" if geo == "GEO Ready" else "#fff7ed" if geo == "Developing" else "#fee2e2"
    geo_text = "#065f46" if geo == "GEO Ready" else "#92400e" if geo == "Developing" else "#7f1d1d"

    dim_chart    = _bar_svg([d["name"].split()[0] for d in dim_scores], [d["score"] for d in dim_scores], color=accent)
    engine_chart = _bar_svg([e.split()[0] for e in engine_scores.keys()], list(engine_scores.values()), color=accent)

    # ── Build slides ──────────────────────────────────────────────────────────
    slides = []

    # Slide 0: Cover
    ring = _score_ring(score)
    pill_row = (
        f'<span class="pill pill-crit">{summ["critical"]} Critical</span>'
        f'<span class="pill pill-high">{summ["high"]} High</span>'
        f'<span class="pill pill-med">{summ["medium"]} Medium</span>'
        f'<span class="pill pill-low">{summ["low"]} Low</span>'
    )
    slides.append(f"""<div class="slide active" data-label="Overview">
  <div class="cover-layout">
    <div class="cover-left">
      <div class="eyebrow">Brand AI Readiness Audit</div>
      <h1 class="cover-h1">{display_name}</h1>
      <p class="cover-sub"><a href="https://{site}">{site}</a> &middot; Audited {audited}</p>
      <div class="pill-row">{pill_row}</div>
      <p class="cover-note">{summ["total_findings"]} findings &middot; 6 GEO dimensions &middot; 5 AI engines</p>
    </div>
    <div class="cover-right">
      {ring}
      <div class="geo-badge" style="background:{geo_bg};color:{geo_text}">{geo}</div>
    </div>
  </div>
</div>""")

    # Slide 1: GEO Dimension Scores
    dim_rows = ""
    for d in dim_scores:
        sc = "#1E8449" if d["score"] >= 70 else "#E37400" if d["score"] >= 50 else "#D93025"
        mark = "✓" if d["score"] >= 70 else "⚠" if d["score"] >= 50 else "✗"
        dim_rows += (
            f'<tr><td><strong>{d["id"]}</strong></td><td>{d["name"]}</td>'
            f'<td style="text-align:right;color:{sc};font-weight:700">{d["score"]}</td>'
            f'<td style="color:{sc}">{mark}</td></tr>'
        )
    slides.append(f"""<div class="slide" data-label="GEO Dimensions">
  <div class="slide-head">
    <div class="eyebrow">6 GEO Dimensions &mdash; Directive Consulting 2026</div>
    <h2 class="slide-h2">Dimension Scores</h2>
  </div>
  <div class="two-col">
    <div class="chart-card">{dim_chart}</div>
    <div class="table-card"><table><thead><tr><th>ID</th><th>Dimension</th><th>Score</th><th></th></tr></thead><tbody>{dim_rows}</tbody></table></div>
  </div>
</div>""")

    # Slide 2: Per-Engine Scores
    eng_rows = ""
    for engine, escore in engine_scores.items():
        sc = "#1E8449" if escore >= 70 else "#E37400" if escore >= 50 else "#D93025"
        mark = "✓ Ready" if escore >= 70 else "⚠ Developing" if escore >= 50 else "✗ Gap"
        eng_rows += (
            f'<tr><td>{engine}</td>'
            f'<td style="text-align:right;color:{sc};font-weight:700">{escore}</td>'
            f'<td style="color:{sc}">{mark}</td></tr>'
        )
    slides.append(f"""<div class="slide" data-label="Per-Engine">
  <div class="slide-head">
    <div class="eyebrow">Threshold &ge;70 = GEO Ready (Directive Consulting 2026)</div>
    <h2 class="slide-h2">Per-Engine GEO Readiness</h2>
  </div>
  <div class="two-col">
    <div class="chart-card">{engine_chart}</div>
    <div class="table-card"><table><thead><tr><th>Engine</th><th>Score</th><th>Status</th></tr></thead><tbody>{eng_rows}</tbody></table></div>
  </div>
</div>""")

    # Individual slides for CRITICAL and HIGH
    for sev in ["CRITICAL", "HIGH"]:
        sev_color = SEV_COLOR_HEX[sev]
        sev_icon  = SEV_ICON[sev]
        for f in [x for x in findings if x["severity"] == sev]:
            action = f["suggested_action"]
            slides.append(f"""<div class="slide" data-label="{sev}">
  <div class="slide-head">
    <div class="eyebrow" style="color:{sev_color}">{sev_icon} {sev} &mdash; <code>{f['id']}</code></div>
    <h2 class="slide-h2">{f['title']}</h2>
  </div>
  <div class="two-col">
    <div class="finding-panel">
      <div class="panel-label">Evidence</div>
      <p>{f['evidence']}</p>
    </div>
    <div class="finding-panel action-panel">
      <div class="panel-label">Recommended Action</div>
      <p class="action-text">{action['summary']}</p>
      <span class="effort-tag">Effort: {action.get('effort', '?').upper()} &middot; Priority: {action.get('priority', '?').upper()}</span>
    </div>
  </div>
</div>""")

    # Batch slides for MEDIUM and LOW
    for sev in ["MEDIUM", "LOW"]:
        sev_color    = SEV_COLOR_HEX[sev]
        sev_icon     = SEV_ICON[sev]
        sev_findings = [x for x in findings if x["severity"] == sev]
        if not sev_findings:
            continue
        rows = "".join(
            f'<tr><td><code class="fid-sm">{f["id"]}</code></td>'
            f'<td>{f["title"]}</td>'
            f'<td style="color:var(--muted);font-size:12px">{f["suggested_action"]["summary"][:72]}…</td>'
            f'<td><span class="effort-sm">{f["suggested_action"].get("effort", "?").upper()}</span></td></tr>'
            for f in sev_findings
        )
        slides.append(f"""<div class="slide" data-label="{sev}">
  <div class="slide-head">
    <div class="eyebrow" style="color:{sev_color}">{sev_icon} {sev}</div>
    <h2 class="slide-h2">{sev.title()} Findings ({len(sev_findings)})</h2>
  </div>
  <div class="table-card"><table>
    <thead><tr><th>ID</th><th>Finding</th><th>Action</th><th>Effort</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>
</div>""")

    total       = len(slides)
    slides_html = "\n".join(slides)
    dots        = "\n".join(
        f'<button class="dot{" active" if i == 0 else ""}" onclick="goTo({i})"></button>'
        for i in range(total)
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Readiness &mdash; {display_name}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
  :root{{--accent:{accent};--bg:#fafafa;--surface:#fff;--border:#e5e7eb;--text:#111827;--muted:#6b7280;--rad:10px}}
  html.dark{{--bg:#0f172a;--surface:#1e293b;--border:#334155;--text:#f1f5f9;--muted:#94a3b8}}
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  html,body{{height:100%;overflow:hidden}}
  body{{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);font-size:14px;line-height:1.6}}
  a{{color:var(--accent);text-decoration:none}}a:hover{{text-decoration:underline}}
  .deck{{position:fixed;inset:0;background:var(--bg)}}
  .slide{{position:absolute;inset:0;overflow-y:auto;overflow-x:hidden;padding:52px 72px 88px;transform:translateX(100%);transition:transform .38s cubic-bezier(.4,0,.2,1);background:var(--bg)}}
  .slide.active{{transform:none}}
  .slide.gone{{transform:translateX(-100%)}}
  .cover-layout{{display:flex;align-items:center;justify-content:space-between;min-height:calc(100vh - 140px);gap:48px}}
  .cover-left{{flex:1;max-width:580px}}
  .cover-right{{text-align:center;flex-shrink:0}}
  .cover-h1{{font-size:52px;font-weight:900;line-height:1.05;margin:8px 0 16px;color:var(--text)}}
  .cover-sub{{font-size:15px;color:var(--muted);margin-bottom:24px}}
  .cover-note{{font-size:13px;color:var(--muted);margin-top:16px}}
  .geo-badge{{display:inline-block;margin-top:14px;padding:6px 20px;border-radius:9999px;font-size:14px;font-weight:700}}
  .slide-head{{margin-bottom:28px}}
  .eyebrow{{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:6px}}
  .slide-h2{{font-size:34px;font-weight:800;color:var(--text);line-height:1.15}}
  .two-col{{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:start}}
  .chart-card,.table-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--rad);padding:20px;overflow:hidden}}
  .table-card{{padding:0}}
  .finding-panel{{background:var(--surface);border:1px solid var(--border);border-radius:var(--rad);padding:28px;font-size:15px;line-height:1.75}}
  .action-panel{{border-left:4px solid var(--accent)}}
  .panel-label{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--muted);margin-bottom:12px}}
  .action-text{{font-size:16px;font-weight:600;line-height:1.5}}
  .pill-row{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px}}
  .pill{{padding:5px 14px;border-radius:9999px;font-size:13px;font-weight:700}}
  .pill-crit{{background:#fee2e2;color:#7f1d1d}}
  .pill-high{{background:#fff7ed;color:#92400e}}
  .pill-med{{background:#eff6ff;color:#1e40af}}
  .pill-low{{background:#f0fdf4;color:#166534}}
  .effort-tag{{display:inline-block;margin-top:18px;padding:4px 10px;background:var(--border);border-radius:5px;font-size:11px;color:var(--muted);font-weight:600}}
  .fid-sm{{background:var(--border);padding:1px 6px;border-radius:4px;font-size:11px;font-family:monospace;color:var(--muted)}}
  .effort-sm{{padding:2px 6px;background:var(--border);border-radius:4px;font-size:11px;color:var(--muted)}}
  code{{background:var(--border);padding:1px 5px;border-radius:4px;font-size:11px;font-family:monospace;color:var(--muted)}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th,td{{padding:9px 14px;text-align:left;border-bottom:1px solid var(--border)}}
  th{{font-weight:600;color:var(--muted);text-transform:uppercase;font-size:10px;letter-spacing:.5px;background:var(--bg)}}
  tr:last-child td{{border-bottom:none}}
  html.dark .chart-card svg text{{fill:#94a3b8}}
  html.dark .chart-card svg line{{stroke:#334155}}
  .nav-btn{{position:fixed;top:50%;transform:translateY(-50%);background:var(--surface);border:1px solid var(--border);border-radius:50%;width:44px;height:44px;font-size:18px;cursor:pointer;z-index:200;display:flex;align-items:center;justify-content:center;color:var(--text);transition:background .2s,opacity .2s;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
  .nav-btn:hover{{background:var(--border)}}
  .nav-btn:disabled{{opacity:.2;cursor:default}}
  #prevBtn{{left:14px}}#nextBtn{{right:14px}}
  .dots{{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);display:flex;gap:8px;z-index:200}}
  .dot{{width:8px;height:8px;border-radius:50%;background:var(--border);border:none;cursor:pointer;transition:background .2s,transform .2s;padding:0}}
  .dot.active{{background:var(--accent);transform:scale(1.3)}}
  .dark-btn{{position:fixed;top:18px;right:18px;z-index:200;background:var(--surface);border:1px solid var(--border);border-radius:9999px;padding:6px 14px;font-size:13px;cursor:pointer;color:var(--text);transition:background .2s;font-family:inherit}}
  .dark-btn:hover{{background:var(--border)}}
  .counter{{position:fixed;top:18px;left:18px;z-index:200;font-size:12px;color:var(--muted);background:var(--surface);border:1px solid var(--border);border-radius:9999px;padding:4px 12px}}
</style>
</head>
<body>
<div class="deck">
{slides_html}
</div>
<button class="nav-btn" id="prevBtn" onclick="go(-1)" disabled>&#8592;</button>
<button class="nav-btn" id="nextBtn" onclick="go(1)">&#8594;</button>
<div class="dots" id="dotsEl">{dots}</div>
<button class="dark-btn" id="darkBtn" onclick="toggleDark()">&#127769; Dark</button>
<div class="counter"><span id="cur">1</span> / {total}</div>
<script>
const slides=document.querySelectorAll('.slide');
const dotEls=document.querySelectorAll('.dot');
let cur=0;
function goTo(n){{
  if(n===cur||n<0||n>=slides.length)return;
  slides[cur].classList.remove('active');
  slides[cur].classList.add('gone');
  cur=n;
  slides.forEach((s,i)=>{{s.classList.remove('active','gone');if(i<cur)s.classList.add('gone');}});
  slides[cur].classList.add('active');
  dotEls.forEach((d,i)=>d.classList.toggle('active',i===cur));
  document.getElementById('cur').textContent=cur+1;
  document.getElementById('prevBtn').disabled=cur===0;
  document.getElementById('nextBtn').disabled=cur===slides.length-1;
}}
function go(d){{goTo(cur+d);}}
document.addEventListener('keydown',e=>{{
  if(e.key==='ArrowRight'||e.key==='ArrowDown')go(1);
  if(e.key==='ArrowLeft'||e.key==='ArrowUp')go(-1);
}});
function toggleDark(){{
  const dark=document.documentElement.classList.toggle('dark');
  document.getElementById('darkBtn').textContent=dark?'☀ Light':'🌙 Dark';
}}
if(window.matchMedia('(prefers-color-scheme: dark)').matches)toggleDark();
</script>
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


def render_ppt(report: dict, output_path: Path, brand_name: str = "", brand_color: str = "#0066CC") -> Path:
    try:
        from pptx import Presentation            # type: ignore
        from pptx.util import Inches, Pt         # type: ignore
        from pptx.dml.color import RGBColor      # type: ignore
        from pptx.enum.text import PP_ALIGN      # type: ignore
    except ImportError:
        print("  ⚠  python-pptx not installed. Run: pip install python-pptx", file=sys.stderr)
        fallback = output_path.with_suffix(".pptx.txt")
        fallback.write_text("Install python-pptx: pip install python-pptx\n")
        return fallback

    site          = report["site"]
    display_name  = brand_name or site
    score         = report["overall_score"]
    geo           = report["geo_readiness"]
    summ          = report["summary"]
    findings      = report["findings"]
    dim_scores    = report["dimension_scores"]
    engine_scores = report["engine_scores"]
    audited       = report["audited_at"][:10]

    hx        = brand_color.lstrip("#")
    accent    = RGBColor(int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))
    dark_bg   = RGBColor(15, 23, 42)
    white     = RGBColor(255, 255, 255)
    muted_clr = RGBColor(100, 116, 139)
    score_clr = RGBColor(30, 132, 73) if score >= 70 else RGBColor(227, 116, 0) if score >= 50 else RGBColor(217, 48, 37)

    prs = Presentation()
    prs.slide_width  = Inches(13.33)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    def add_bg(slide, color=dark_bg):
        fill = slide.background.fill
        fill.solid()
        fill.fore_color.rgb = color

    def txb(slide, text, l, t, w, h, size=14, bold=False, color=white, align=PP_ALIGN.LEFT, wrap=True):
        tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = wrap
        p  = tf.paragraphs[0]
        p.alignment = align
        r  = p.add_run()
        r.text = text
        r.font.size      = Pt(size)
        r.font.bold      = bold
        r.font.color.rgb = color
        return tb

    def bar_rect(slide, l, t, w, h, color=accent):
        s = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Inches(h))
        s.fill.solid()
        s.fill.fore_color.rgb = color
        s.line.fill.background()
        return s

    def accent_bar(slide):
        bar_rect(slide, 0, 0, 0.08, 7.5, accent)

    # Cover slide
    s = prs.slides.add_slide(blank); add_bg(s); accent_bar(s)
    txb(s, "BRAND AI READINESS AUDIT", 0.3, 0.55, 9, 0.35, size=11, color=muted_clr)
    txb(s, display_name, 0.3, 0.95, 9, 1.4, size=44, bold=True)
    txb(s, f"{site}  ·  Audited {audited}", 0.3, 2.45, 9, 0.4, size=13, color=muted_clr)
    txb(s, str(score), 9.8, 1.6, 3.1, 1.7, size=90, bold=True, color=score_clr, align=PP_ALIGN.CENTER)
    txb(s, "/ 100 GEO Score", 9.8, 3.3, 3.1, 0.4, size=12, color=muted_clr, align=PP_ALIGN.CENTER)
    txb(s, geo.upper(), 9.8, 3.8, 3.1, 0.5, size=15, bold=True, color=score_clr, align=PP_ALIGN.CENTER)
    sev_data = [
        ("CRITICAL", "critical", RGBColor(217, 48, 37)),
        ("HIGH",     "high",     RGBColor(227, 116, 0)),
        ("MEDIUM",   "medium",   RGBColor(26, 115, 232)),
        ("LOW",      "low",      RGBColor(52, 168, 83)),
    ]
    for i, (lbl, key, clr) in enumerate(sev_data):
        txb(s, f"{summ[key]}  {lbl}", 0.3, 3.3 + i * 0.52, 5, 0.45, size=14,
            bold=(key in ("critical", "high")), color=clr)

    # Dimension scores slide
    s = prs.slides.add_slide(blank); add_bg(s); accent_bar(s)
    txb(s, "6 GEO DIMENSIONS", 0.3, 0.4, 12, 0.3, size=11, color=muted_clr)
    txb(s, "Dimension Scores", 0.3, 0.7, 12, 0.8, size=34, bold=True)
    for i, d in enumerate(dim_scores):
        sc_clr = RGBColor(30, 132, 73) if d["score"] >= 70 else RGBColor(227, 116, 0) if d["score"] >= 50 else RGBColor(217, 48, 37)
        y = 1.75 + i * 0.65
        txb(s, f'{d["id"]}  {d["name"]}', 0.3, y, 7.5, 0.45, size=13)
        bar_rect(s, 8.1, y + 0.08, (d["score"] / 100) * 4.8, 0.28, sc_clr)
        txb(s, str(d["score"]), 13.1, y, 0.7, 0.45, size=13, bold=True, color=sc_clr, align=PP_ALIGN.RIGHT)

    # Per-engine scores slide
    s = prs.slides.add_slide(blank); add_bg(s); accent_bar(s)
    txb(s, "DIRECTIVE CONSULTING 2026  ·  ≥70 = GEO READY", 0.3, 0.4, 12, 0.3, size=11, color=muted_clr)
    txb(s, "Per-Engine GEO Readiness", 0.3, 0.7, 12, 0.8, size=34, bold=True)
    for i, (engine, escore) in enumerate(engine_scores.items()):
        sc_clr = RGBColor(30, 132, 73) if escore >= 70 else RGBColor(227, 116, 0) if escore >= 50 else RGBColor(217, 48, 37)
        y = 1.75 + i * 0.72
        txb(s, engine, 0.3, y, 5, 0.45, size=13)
        bar_rect(s, 5.6, y + 0.08, (escore / 100) * 5.0, 0.28, sc_clr)
        txb(s, str(escore), 10.8, y, 0.6, 0.45, size=13, bold=True, color=sc_clr)
        status = "✓ Ready" if escore >= 70 else "⚠ Developing" if escore >= 50 else "✗ Gap"
        txb(s, status, 11.5, y, 1.7, 0.45, size=12, color=sc_clr)

    # CRITICAL + HIGH: one slide per finding
    for sev in ["CRITICAL", "HIGH"]:
        sc_clr = {"CRITICAL": RGBColor(217, 48, 37), "HIGH": RGBColor(227, 116, 0)}[sev]
        for f in [x for x in findings if x["severity"] == sev]:
            s = prs.slides.add_slide(blank); add_bg(s)
            bar_rect(s, 0, 0, 0.08, 7.5, sc_clr)
            txb(s, f'{SEV_ICON[sev]} {sev}  ·  {f["id"]}', 0.3, 0.4, 12, 0.35, size=12, color=sc_clr)
            txb(s, f["title"], 0.3, 0.75, 12.7, 1.1, size=24, bold=True)
            bar_rect(s, 0.3, 2.1, 6.0, 4.6, RGBColor(30, 41, 59))
            txb(s, "EVIDENCE", 0.5, 2.2, 5.5, 0.3, size=9, color=muted_clr)
            txb(s, f["evidence"], 0.5, 2.6, 5.6, 3.7, size=12, color=RGBColor(203, 213, 225), wrap=True)
            bar_rect(s, 6.7, 2.1, 6.3, 4.6, RGBColor(30, 41, 59))
            txb(s, "ACTION", 6.9, 2.2, 5.9, 0.3, size=9, color=muted_clr)
            txb(s, f["suggested_action"]["summary"], 6.9, 2.6, 5.9, 2.8, size=14, bold=True, wrap=True)
            effort = f["suggested_action"].get("effort", "?").upper()
            prio   = f["suggested_action"].get("priority", "?").upper()
            txb(s, f"Effort: {effort}  ·  Priority: {prio}", 6.9, 5.7, 5.5, 0.5, size=11, color=muted_clr)

    # MEDIUM + LOW: one batch slide each
    for sev in ["MEDIUM", "LOW"]:
        sc_clr = {"MEDIUM": RGBColor(26, 115, 232), "LOW": RGBColor(52, 168, 83)}[sev]
        batch = [x for x in findings if x["severity"] == sev]
        if not batch:
            continue
        s = prs.slides.add_slide(blank); add_bg(s)
        bar_rect(s, 0, 0, 0.08, 7.5, sc_clr)
        txb(s, f'{SEV_ICON[sev]} {sev}  ·  {len(batch)} findings', 0.3, 0.4, 12, 0.35, size=12, color=sc_clr)
        txb(s, f'{sev.title()} Priority Findings', 0.3, 0.75, 12, 0.8, size=30, bold=True)
        for j, f in enumerate(batch[:10]):
            y = 1.8 + j * 0.47
            txb(s, f'{f["id"]}  {f["title"]}', 0.3, y, 10, 0.42, size=12)
            effort = f["suggested_action"].get("effort", "?").upper()
            txb(s, effort, 10.4, y, 1.0, 0.42, size=11, color=muted_clr)
        if len(batch) > 10:
            txb(s, f'+ {len(batch) - 10} more…', 0.3, 1.8 + 10 * 0.47, 4, 0.4, size=12, color=muted_clr)

    out = output_path.with_suffix(".pptx")
    prs.save(str(out))
    return out


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
                   help="Comma-separated list of output formats: html,md,pdf,json,pptx (default: html,md)")
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
    valid_formats = {"html", "md", "pdf", "json", "pptx"}
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

    if "pptx" in formats:
        path = render_ppt(report, output_dir / stem, args.brand_name, args.brand_color)
        generated.append(("PPT", path))
        print(f"  ✅ PPTX   → {path}")

    print()
    print(f"  {'─'*50}")
    print(f"  {len(generated)} report(s) written to: {output_dir}/")
    print()


if __name__ == "__main__":
    main()
