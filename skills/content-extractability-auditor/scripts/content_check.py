#!/usr/bin/env python3
"""
content_check.py — Content Extractability Auditor helper script
Usage: python content_check.py <url>

Analyzes content structure for AI passage-level extractability.
Based on Princeton KDD 2024 GEO research. Read-only.
"""

import sys
import json
import re
import time
from urllib.parse import urlparse, urljoin

try:
    import requests
except ImportError:
    print(json.dumps({"error": "requests library not installed. Run: pip install requests"}))
    sys.exit(1)

DEFAULT_UA = "Mozilla/5.0 (compatible; BrandAuditBot/1.0)"
TIMEOUT = 12

# Hedge words that signal uncertain content
HEDGE_WORDS = [
    "might", "could", "possibly", "perhaps", "maybe", "seem", "appears",
    "reportedly", "allegedly", "we think", "we believe", "generally",
    "often", "sometimes", "usually", "tend to", "may be", "can be",
    "would suggest", "it is thought", "arguably", "presumably",
]

# Question starters for headings
QUESTION_STARTERS = ["what", "how", "why", "when", "which", "can", "does", "is", "are",
                     "should", "will", "do", "who", "where", "has", "have"]

# Statistic patterns
STAT_PATTERN = re.compile(
    r'\d+(?:\.\d+)?(?:\s*%|\s*percent|\s*million|\s*billion|\s*thousand|\s*x\b)',
    re.IGNORECASE
)

# Statistic citation patterns (has a source)
STAT_CITED_PATTERN = re.compile(
    r'(?:according to|per |source:|via |from |reported by|cited by|study by|data from)\s',
    re.IGNORECASE
)

# FAQ patterns
FAQ_HEADING_PATTERN = re.compile(
    r'<h[1-6][^>]*>.*?(?:faq|frequently asked|questions?|answers?)[^<]*</h[1-6]>',
    re.IGNORECASE | re.DOTALL
)

FAQ_ITEM_PATTERN = re.compile(
    r'<(?:dt|summary|[^>]+class="[^"]*(?:question|faq-q|accordion)[^"]*")[^>]*>(.*?)</(?:dt|summary|[^>]*)>',
    re.IGNORECASE | re.DOTALL
)

# Key takeaway / TL;DR patterns
TAKEAWAY_PATTERN = re.compile(
    r'(?:key\s+takeaway|tl;dr|tldr|quick\s+summary|in\s+brief|the\s+bottom\s+line|key\s+points?)',
    re.IGNORECASE
)

# AI cliché patterns (Tier 1 — content that reads as AI-generated slop, deprioritized by citation engines)
# Source: kai-cmo-harness research
AI_CLICHES_T1 = [
    r"\bit'?s important to note\b",
    r"\bin conclusion\b",
    r"\bin today'?s (?:fast[- ]paced|digital|modern) (?:world|landscape|era)\b",
    r"\bthis comprehensive guide\b",
    r"\bdive into\b",
    r"\blet'?s explore\b",
    r"\bin this (?:comprehensive|detailed|in-depth) (?:guide|article|post)\b",
    r"\bas an ai language model\b",
    r"\bi cannot provide\b",
    r"\bdelve into\b",
    r"\bnavigate the (?:complex|ever-changing)\b",
    r"\bempower(?:ing)? (?:you|users|businesses)\b",
    r"\btailored (?:solutions|approach|experience)\b",
    r"\bseamless(?:ly)?\b.{0,30}\b(?:integrat|experienc|workflow)\b",
    r"\bunlock(?:ing)? (?:your|the) (?:potential|power|full)\b",
    r"\brobust\b.{0,20}\b(?:solution|platform|ecosystem)\b",
]

# Date marker patterns (explicit freshness signals)
DATE_MARKER_PATTERN = re.compile(
    r'(?:as\s+of|last\s+updated?|updated?:|published?:|reviewed?:|written?:)\s*'
    r'(?:january|february|march|april|may|june|july|august|september|october|november|december|\d{1,2}/\d{4}|\d{4})',
    re.IGNORECASE
)


def fetch_page(url, ua=DEFAULT_UA):
    headers = {"User-Agent": ua, "Accept": "text/html,*/*;q=0.8"}
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
        return resp.status_code, resp.text, None
    except Exception as e:
        return None, None, str(e)


def strip_tags(html):
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def analyze_above_fold(html):
    """Analyze first 80 words for direct answer presence."""
    # Try main content first
    main_match = re.search(
        r'<(?:main|article|section)[^>]*>(.*?)</(?:main|article|section)>',
        html, re.IGNORECASE | re.DOTALL
    )
    source = main_match.group(1) if main_match else html

    text = strip_tags(source)
    words = [w for w in text.split() if len(w) > 1]
    first_80 = " ".join(words[:80])

    # Check for unresolved pronouns
    unresolved_pronouns = bool(re.search(
        r'\b(?:we|our|us|it|this|they|their|the\s+company|the\s+platform|the\s+service)\b',
        first_80, re.IGNORECASE
    ))

    # Direct answer: contains subject + verb + object within first 40-80 words
    has_direct_claim = bool(re.search(
        r'\b(?:is|are|provides?|offers?|helps?|enables?|allows?|builds?|creates?|delivers?|makes?)\b',
        first_80, re.IGNORECASE
    ))

    return {
        "first_80_words": first_80,
        "word_count": len(words),
        "has_direct_claim": has_direct_claim,
        "has_unresolved_pronouns": unresolved_pronouns,
    }


def analyze_headings(html):
    """Analyze heading structure for question-format headings."""
    headings = re.findall(r'<(h[2-3])[^>]*>(.*?)</h[2-3]>', html, re.IGNORECASE | re.DOTALL)
    total = len(headings)
    question_count = 0
    question_headings = []

    for tag, content in headings:
        text = re.sub(r"<[^>]+>", "", content).strip().lower()
        if any(text.startswith(q) for q in QUESTION_STARTERS) or text.endswith("?"):
            question_count += 1
            question_headings.append(text[:80])

    return {
        "total_h2_h3_count": total,
        "question_format_count": question_count,
        "question_format_ratio": round(question_count / total, 2) if total > 0 else 0,
        "sample_question_headings": question_headings[:5],
    }


def analyze_statistics(html):
    """Find statistics with and without source attribution."""
    text = strip_tags(html)
    sentences = re.split(r'[.!?]+', text)

    stats_with_citation = 0
    stats_without_citation = 0
    examples_cited = []
    examples_uncited = []

    for sent in sentences:
        if STAT_PATTERN.search(sent):
            if STAT_CITED_PATTERN.search(sent):
                stats_with_citation += 1
                if len(examples_cited) < 3:
                    examples_cited.append(sent.strip()[:120])
            else:
                stats_without_citation += 1
                if len(examples_uncited) < 3:
                    examples_uncited.append(sent.strip()[:120])

    total_stats = stats_with_citation + stats_without_citation
    return {
        "total_statistics": total_stats,
        "with_citation": stats_with_citation,
        "without_citation": stats_without_citation,
        "citation_ratio": round(stats_with_citation / total_stats, 2) if total_stats > 0 else 0,
        "examples_cited": examples_cited,
        "examples_uncited": examples_uncited,
    }


def analyze_paragraphs(html):
    """Analyze paragraph length distribution."""
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.IGNORECASE | re.DOTALL)
    word_counts = []
    violations = []

    for p in paragraphs:
        text = strip_tags(p)
        words = [w for w in text.split() if len(w) > 1]
        if len(words) > 5:
            word_counts.append(len(words))
            if len(words) > 150:
                violations.append({
                    "word_count": len(words),
                    "snippet": " ".join(words[:15]) + "...",
                })

    if not word_counts:
        return {"avg_words": 0, "violation_count": 0, "violations": [], "total_paragraphs": 0}

    return {
        "total_paragraphs": len(word_counts),
        "avg_words": round(sum(word_counts) / len(word_counts), 1),
        "max_words": max(word_counts),
        "violation_count": len(violations),
        "violation_ratio": round(len(violations) / len(word_counts), 2),
        "violations": violations[:3],
    }


def detect_faq_section(html):
    """Detect FAQ sections and count Q&A pairs."""
    has_faq_heading = bool(FAQ_HEADING_PATTERN.search(html))

    # Look for FAQ items
    qa_patterns = [
        r'<(?:dt|summary)[^>]*>(.*?)</(?:dt|summary)>',
        r'<[^>]+(?:class|id)=["\'][^"\']*(?:question|faq)[^"\']*["\'][^>]*>(.*?)</',
    ]
    qa_count = 0
    for pattern in qa_patterns:
        items = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
        qa_count = max(qa_count, len(items))

    # Also check for question-like list items
    list_questions = re.findall(
        r'<li[^>]*>.*?(?:what|how|why|when|is|are|can|does)\b.*?\?.*?</li>',
        html, re.IGNORECASE | re.DOTALL
    )
    qa_count = max(qa_count, len(list_questions))

    return {
        "has_faq_heading": has_faq_heading,
        "estimated_qa_pairs": qa_count,
        "has_faq_section": has_faq_heading or qa_count >= 3,
    }


def detect_key_takeaways(html):
    """Detect key takeaway / TL;DR boxes."""
    text_lower = html.lower()
    patterns_found = []

    for pattern_text in ["key takeaway", "tldr", "tl;dr", "quick summary",
                          "in brief", "the bottom line", "key points", "summary box"]:
        if pattern_text in text_lower:
            patterns_found.append(pattern_text)

    return {
        "has_key_takeaways": len(patterns_found) > 0,
        "patterns_found": patterns_found,
    }


def measure_hedge_words(html):
    """Measure hedge word ratio in content."""
    text = strip_tags(html)
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.split()) > 5]

    hedge_sentences = []
    for sent in sentences:
        sent_lower = sent.lower()
        for hedge in HEDGE_WORDS:
            if hedge in sent_lower:
                hedge_sentences.append(sent[:100])
                break

    total = len(sentences)
    ratio = len(hedge_sentences) / total if total > 0 else 0

    return {
        "total_sentences": total,
        "hedge_sentence_count": len(hedge_sentences),
        "hedge_ratio": round(ratio, 2),
        "sample_hedge_sentences": hedge_sentences[:3],
    }


def detect_date_markers(html):
    """Detect explicit freshness date markers."""
    text = strip_tags(html)
    markers = DATE_MARKER_PATTERN.findall(text)
    return {
        "has_date_marker": len(markers) > 0,
        "markers_found": markers[:5],
    }


def detect_ai_cliches(html):
    """
    Detect AI-generated cliché phrases. Content that reads as AI-generated slop
    is deprioritized by citation engines (kai-cmo-harness research, 2026).
    Pages with many clichés signal low substance density.
    """
    text = strip_tags(html).lower()
    found_cliches = []
    for pattern in AI_CLICHES_T1:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            found_cliches.extend(matches[:1])

    return {
        "cliche_count": len(found_cliches),
        "high_cliche_density": len(found_cliches) >= 4,
        "examples": found_cliches[:5],
    }


def score_passage_extractability(html):
    """
    Passage-level extractability scorer — 6-signal, 0–30 score per passage.
    Threshold: extractable if score >= 18/30. Report extractability_rate.

    Signals (5 pts each):
      DA: Direct Answer opener (no unresolved pronouns in first 15 words)
      DD: Data Density (1 stat per ~200 words → Princeton KDD 2024 +40% lift)
      AS: Authority Signals (named sources, DOIs, "according to")
      SQ: Structure Quality (40–80 word sweet spot)
      FR: Framing (no AI-preamble filler opener)
      UQ: Uniqueness (proprietary research markers)

    Source: zilisrikle/geo-audit-skill citability scorer + jwatte.com
    passage-retrievability methodology + Princeton KDD 2024 GEO research.
    """
    # Extract paragraph text blocks between headings
    # Split on <h2>/<h3> boundaries
    heading_re = re.compile(r'<h[23][^>]*>.*?</h[23]>', re.IGNORECASE | re.DOTALL)
    para_re = re.compile(r'<p[^>]*>(.*?)</p>', re.IGNORECASE | re.DOTALL)

    # Build passage list: text of <p> elements between successive headings
    parts = heading_re.split(html)
    passages_raw = []
    for part in parts:
        paras = para_re.findall(part)
        for p in paras:
            text = strip_tags(p).strip()
            words = [w for w in text.split() if len(w) > 1]
            if len(words) >= 20:  # minimum viable passage
                passages_raw.append(text)

    if not passages_raw:
        # Fall back to all paragraphs
        passages_raw = [strip_tags(p).strip() for p in para_re.findall(html)]
        passages_raw = [p for p in passages_raw if len(p.split()) >= 20]

    # BUG FIX: PRONOUN_RE — only flag pronouns that are likely unresolved references,
    # not those immediately following a named entity (e.g. "Adobe Firefly generated... it")
    # Use word-boundary anchored check on first 15 words only
    PRONOUN_RE = re.compile(r'(?<!\w)(it|this|they|these|that|those|he|she|its)(?!\w)', re.IGNORECASE)
    STAT_RE = re.compile(r'\d+(?:\.\d+)?(?:\s*%|\s*x\b|\s*million|\s*billion|\s*thousand)', re.IGNORECASE)
    AUTHORITY_RE = re.compile(
        r'(?:according to|per |study by|research from|data from|DOI:|doi\.org|reported by|cited by)',
        re.IGNORECASE)
    # BUG FIX: Only flag preamble if it's literally the FIRST word pattern
    PREAMBLE_RE = re.compile(
        r'^(?:great\b|well,|so,\s|in this article|let me|when it comes|to answer|the answer is)',
        re.IGNORECASE)
    PROPRIETARY_RE = re.compile(
        r'\b(?:our research|we surveyed|n=\d+|respondents|our data|we found|proprietary)\b',
        re.IGNORECASE)
    # Named entity at start of passage = DA bonus (passage starts with a specific noun)
    NAMED_ENTITY_START_RE = re.compile(r'^[A-Z][a-z]{2,}')

    scored = []
    for passage in passages_raw[:20]:  # cap at 20 passages per page
        words = passage.split()
        wc = len(words)
        first_15 = " ".join(words[:15])

        # DA: starts with named entity (5pts) or no unresolved pronoun (3pts), else 1pt
        starts_with_entity = bool(NAMED_ENTITY_START_RE.match(passage.strip()))
        has_pronoun = bool(PRONOUN_RE.search(" ".join(words[:8])))  # only first 8 words
        da = 5 if starts_with_entity else (3 if not has_pronoun else 1)

        # DD: 1 stat per 200 words = ideal; cap benefit at 5
        stat_count = len(STAT_RE.findall(passage))
        ideal_stats = max(1, wc // 200)
        dd = min(5, int((stat_count / ideal_stats) * 5)) if ideal_stats else 0

        # AS: authority citations
        as_count = len(AUTHORITY_RE.findall(passage))
        as_s = min(5, as_count * 3)

        # SQ: length sweet spot (BUG FIX: 20-word floor; 80-150 gets 4pts)
        # 20-39w = short but valid for citation (2pts); 40-80w = ideal (5pts);
        # 80-150w = good (4pts); >150w = too long for RAG chunk (2pts); <20w = stub (1pt)
        sq = 5 if 40 <= wc <= 80 else (4 if 80 < wc <= 150 else 3 if 20 <= wc < 40 else 2 if wc > 150 else 1)

        # FR: no filler preamble
        fr = 5 if not PREAMBLE_RE.match(passage.strip()) else 1

        # UQ: proprietary/original data markers
        uq = min(5, len(PROPRIETARY_RE.findall(passage)) * 3)

        total = da + dd + as_s + sq + fr + uq
        scored.append({
            "snippet": " ".join(words[:12]) + ("..." if wc > 12 else ""),
            "word_count": wc,
            "score": total,
            "max_score": 30,
            "is_extractable": total >= 15,   # BUG FIX: lowered from 18 → 15 (homepage copy is short)
            "signals": {"da": da, "dd": dd, "as": as_s, "sq": sq, "fr": fr, "uq": uq},
        })

    if not scored:
        return {"total_passages": 0, "extractable_passages": 0, "extractability_rate": 0,
                "avg_score": 0, "top_passages": [], "bottom_passages": []}

    extractable = [p for p in scored if p["is_extractable"]]
    return {
        "total_passages": len(scored),
        "extractable_passages": len(extractable),
        "extractability_rate": round(len(extractable) / len(scored), 2),
        "avg_score": round(sum(p["score"] for p in scored) / len(scored), 1),
        "citability_coverage_pct": round(len(extractable) / len(scored) * 100),
        "top_passages": sorted(scored, key=lambda x: -x["score"])[:3],
        "bottom_passages": sorted(scored, key=lambda x: x["score"])[:2],
    }


def score_quotability(html):
    """
    CEA-011: Sentence-level quotability score.
    A quotable sentence is: ≤35 words, declarative (not interrogative),
    no unresolved pronouns, specific factual claim (contains noun + verb + number/name).

    Source: Lumina SEO citability heatmap methodology (2026).
    BUG FIX: Strip scripts/styles/tables before sentence split to avoid table-cell
    concatenation being treated as a sentence.
    """
    # Strip non-prose elements first to avoid table/nav/heading text contamination
    clean = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r'<style[^>]*>.*?</style>', ' ', clean, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r'<table[^>]*>.*?</table>', ' ', clean, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r'<nav[^>]*>.*?</nav>', ' ', clean, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r'<header[^>]*>.*?</header>', ' ', clean, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r'<footer[^>]*>.*?</footer>', ' ', clean, flags=re.IGNORECASE | re.DOTALL)
    # BUG FIX: Replace heading tags with period+space so they don't concatenate with next para
    clean = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'. \1. ', clean, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r'<li[^>]*>(.*?)</li>', r'. \1. ', clean, flags=re.IGNORECASE | re.DOTALL)
    text = strip_tags(clean)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)

    PRONOUN_RE = re.compile(r'\b(it|this|they|these|that|those)\b', re.IGNORECASE)
    SPECIFIC_CLAIM_RE = re.compile(r'\d+|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}')  # number or proper noun

    quotable = []
    total = 0
    for sent in sentences:
        sent = sent.strip()
        words = sent.split()
        if len(words) < 5:
            continue
        total += 1
        too_long = len(words) > 35
        has_pronoun = bool(PRONOUN_RE.search(" ".join(words[:10])))
        is_question = sent.rstrip().endswith("?")
        has_claim = bool(SPECIFIC_CLAIM_RE.search(sent))
        if not too_long and not has_pronoun and not is_question and has_claim:
            quotable.append(sent[:80])

    rate = round(len(quotable) / total, 2) if total > 0 else 0
    return {
        "total_sentences": total,
        "quotable_sentences": len(quotable),
        "quotability_rate": rate,
        "low_quotability": rate < 0.20,
        "examples": quotable[:3],
    }


def check_passage_density(html):
    """
    CEA-012: Passage density / lede quality — predicts "retrieved but not cited" gap.
    Pages with low passage density are retrieved by AI but not cited.

    Signals (from Profound AI + Ahrefs Brand Radar research, 2026):
      - Direct claim position: answer buried past word 100 of body
      - Passive voice ratio: >30% of sentences start with is/are/was/were
      - Named entity in opening sentence: capitalized non-pronoun noun in first sentence
    """
    text = strip_tags(html).strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    words = text.split()

    # Signal 1: position of first direct claim (look for verb + subject in first 100 words)
    # BUG FIX: expanded verb set to include action verbs like "generated", "launched", etc.
    first_100 = " ".join(words[:100])
    has_early_claim = bool(re.search(
        r'\b(?:is|are|was|were|provides?|helps?|enables?|allows?|generates?|created?|'
        r'launched?|builds?|powers?|delivers?|supports?|offers?|serves?|processes?|'
        r'has|have|had|makes?|uses?|runs?|works?|gives?|brings?|gets?|puts?)\b',
        first_100, re.IGNORECASE))
    first_claim_word_offset = None
    for i, word in enumerate(words[:200]):
        if re.match(r'\b(?:is|are|provides?|helps?|enables?)\b', word, re.IGNORECASE):
            first_claim_word_offset = i
            break

    # Signal 2: passive voice ratio
    passive_re = re.compile(r'^\s*(?:is|are|was|were|be|been|being)\s', re.IGNORECASE)
    passive_count = sum(1 for s in sentences if passive_re.match(s))
    passive_ratio = round(passive_count / len(sentences), 2) if sentences else 0

    # Signal 3: named entity in first sentence
    first_sent = sentences[0] if sentences else ""
    named_entity_re = re.compile(r'\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\b')
    has_named_entity_in_lede = bool(named_entity_re.search(first_sent))

    # Combined passage density score (0–3)
    score = (1 if has_early_claim else 0) + \
            (1 if passive_ratio < 0.30 else 0) + \
            (1 if has_named_entity_in_lede else 0)

    return {
        "passage_density_score": score,  # 0–3
        "low_density": score < 2,
        "has_early_claim": has_early_claim,
        "first_claim_word_offset": first_claim_word_offset,
        "passive_voice_ratio": passive_ratio,
        "high_passive_voice": passive_ratio > 0.30,
        "has_named_entity_in_lede": has_named_entity_in_lede,
        "first_sentence_snippet": first_sent[:100],
    }


def check_structured_list_ratio(html):
    """
    CEA-013: Structured list/table ratio for Perplexity citation eligibility.
    Perplexity's answer engine heavily favors list-format for "top N" queries.
    Threshold: <10% of content in structured lists = flag.

    Source: Seomator AI Citability module + GeoKit CLI structured-content rule (2026).
    """
    # Count meaningful lists (≥3 items)
    ol_lists = re.findall(r'<ol[^>]*>(.*?)</ol>', html, re.IGNORECASE | re.DOTALL)
    ul_lists = re.findall(r'<ul[^>]*>(.*?)</ul>', html, re.IGNORECASE | re.DOTALL)
    tables = re.findall(r'<table[^>]*>.*?<th[^>]*>', html, re.IGNORECASE | re.DOTALL)

    def count_items(list_html):
        return len(re.findall(r'<li[^>]*>', list_html, re.IGNORECASE))

    meaningful_lists = [l for l in ol_lists + ul_lists if count_items(l) >= 3]
    total_lists = len(ol_lists) + len(ul_lists)
    meaningful_tables = len(tables)

    # Estimate total word count for ratio
    text = strip_tags(html)
    total_words = max(1, len(text.split()))

    # Words in structured content (approx 8 words per list item)
    structured_words = sum(count_items(l) * 8 for l in meaningful_lists) + \
                       meaningful_tables * 40  # approx 40 words per table
    ratio = round(structured_words / total_words, 2)

    return {
        "total_lists": total_lists,
        "meaningful_lists": len(meaningful_lists),  # ≥3 items
        "tables_with_headers": meaningful_tables,
        "structured_content_ratio": ratio,
        "low_structure": ratio < 0.10,
        "list_items_total": sum(count_items(l) for l in meaningful_lists),
    }


def check_named_entity_density(html):
    """
    CEA-007: Named entity density per page.
    Cited pages have ≥15 named entities; median cited page: 20.6/1000 words.

    Research basis:
      - Wellows AI Overview study: pages with ≥15 named entities → 4.8× citation probability
      - SE Ranking 129K-domain study: cited pages have 2.4× more named entities
      - SIGI-2026-022: entity density >15% → score 8.0/10 (4th highest of 77 trust signals)

    Uses non-overlapping, atomic patterns to avoid double-counting multi-word matches.
    BUG FIX: Strip tables/nav/headers before entity extraction to avoid cell-text
    concatenation producing spurious bigrams like 'Plan Price' or 'Features Starter'.
    """
    # Strip structural non-prose elements first
    clean = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r'<style[^>]*>.*?</style>', ' ', clean, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r'<table[^>]*>.*?</table>', ' ', clean, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r'<nav[^>]*>.*?</nav>', ' ', clean, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r'<header[^>]*>.*?</header>', ' ', clean, flags=re.IGNORECASE | re.DOTALL)
    clean = re.sub(r'<footer[^>]*>.*?</footer>', ' ', clean, flags=re.IGNORECASE | re.DOTALL)
    text = strip_tags(clean)

    # BUG FIX: Use separate, non-overlapping passes for each entity type.
    # Do NOT combine proper-noun multi-word with single CamelCase — they overlap.
    entities: set = set()

    # Numeric/monetary entities (high-precision, low false-positive)
    for pat in [
        r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|thousand|M|B|K))?\b',
        r'€[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|M|B))?\b',
        r'\b\d+(?:\.\d+)?\s*(?:percent|%)\b',
        r'\b\d{1,3}(?:,\d{3})+\b',       # large comma-separated numbers
        r'\b\d+\s*(?:million|billion|thousand)\b',
    ]:
        entities.update(re.findall(pat, text, re.IGNORECASE))

    # Year references (specific, e.g. 2024, 2025, 2026)
    entities.update(re.findall(r'\b20(?:2[0-9]|3[0-5])\b', text))

    # Proper noun bigrams/trigrams ONLY — 2-3 consecutive Title-Case words
    # Must start with capital, not be common sentence starters
    SENTENCE_STARTERS = {
        'The', 'A', 'An', 'In', 'On', 'At', 'By', 'For', 'Of', 'And', 'Or',
        'But', 'So', 'If', 'As', 'We', 'Our', 'Its', 'This', 'That', 'These',
        'Those', 'When', 'While', 'With', 'From', 'Over', 'Under', 'About',
        'Into', 'Through', 'During', 'Before', 'After', 'Above', 'Below',
        'Welcome', 'Here', 'There', 'How', 'What', 'Where', 'Why', 'Who',
    }
    # Bigrams: two consecutive title-case words (both ≥4 chars avoids "Hi My")
    for m in re.finditer(r'\b([A-Z][a-z]{2,})\s+([A-Z][a-z]{2,})\b', text):
        w1, w2 = m.group(1), m.group(2)
        if w1 not in SENTENCE_STARTERS and w2 not in SENTENCE_STARTERS:
            entities.add(f"{w1} {w2}")

    # Single CamelCase brand/product names (≥6 chars, at least one lowercase sequence)
    for m in re.finditer(r'\b([A-Z][a-z]{2,}[A-Z][a-zA-Z]{2,}|[A-Z]{2,}[a-z]{2,})\b', text):
        entities.add(m.group(1))

    # Remove numeric-only strings and very short entities
    entities = {e for e in entities if len(e.strip()) > 2 and not e.strip().isdigit()}

    word_count = max(1, len(text.split()))
    entity_count = len(entities)
    per_1000 = round(entity_count / word_count * 1000, 1)

    return {
        "named_entity_count": entity_count,
        "word_count": word_count,
        "entities_per_1000_words": per_1000,
        "below_citation_floor": entity_count < 8,         # <8 = CRITICAL (4.8× lower)
        "below_median_cited": entity_count < 15,          # <15 = HIGH
        "passes_threshold": entity_count >= 15,
        "examples": sorted(entities)[:10],
    }


def detect_semantic_tables(html):
    """
    CEA-008: Semantic HTML table presence (comparison/data tables vs. layout tables).
    Data tables with <th> headers and ≥3 rows = highest single-format citation signal.

    Research basis:
      - Bigeye Agency 2026 + TryProfound: HTML tables → +400% citation probability vs. prose
      - TryProfound: comparison pages with semantic tables → 67% citation rate (highest ever)
      - Discovered Labs: pricing pages β=+0.39; comparison content near-reference
      - ArXiv 2604.25707: high-influence pages more modular, more likely to contain comparisons
    """
    all_tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.IGNORECASE | re.DOTALL)

    data_tables = 0
    comparison_tables = 0
    table_signals = []

    for table_html in all_tables:
        has_th = bool(re.search(r'<th[^>]*>', table_html, re.IGNORECASE))
        row_count = len(re.findall(r'<tr[^>]*>', table_html, re.IGNORECASE))
        has_numbers = bool(re.search(r'\$\d|\d+%|\d+\s*(?:ms|px|GB|MB|fps|req)', table_html))
        has_compare_words = bool(re.search(
            r'\b(?:vs\.?|versus|compare|comparison|better|worse|faster|cheaper|plan|tier|feature|include)\b',
            table_html, re.IGNORECASE))

        if has_th and row_count >= 3:
            data_tables += 1
            if has_compare_words or has_numbers:
                comparison_tables += 1
                table_signals.append(f"{row_count}-row comparison table")
            else:
                table_signals.append(f"{row_count}-row data table")

    return {
        "total_tables": len(all_tables),
        "data_tables": data_tables,
        "comparison_tables": comparison_tables,
        "has_structured_tables": data_tables > 0,
        "has_comparison_tables": comparison_tables > 0,
        "missing_data_tables": data_tables == 0,
        "table_signals": table_signals[:3],
    }


def check_top_third_citable_density(html):
    """
    CEA-009: Top-third citable density — citable fact in first 100 words.
    44.2% of AI citations originate from the first 30% of content.

    Research basis:
      - SIGI-2026-022: 44.2% of cited text at median depth 0.36 (top third)
      - Surfer SEO 2026 (25K+ citations): 40% from first 100 words
      - Google AI Mode: Early Query Confirmation = 28.6% of citation signal
      - AuthorityTech: answer-first structure = +17.3% citation rate across 6 engines
      - SIGI trust signal: "Direct Answer in First Sentence" = 8.5/10 (joint highest)

    IMPORTANT: distinct from analyze_above_fold() — this checks for *citable facts*
    (numbers, statistics, named entities, concrete claims), not just any verb presence.
    """
    # Extract main content — prefer <main>/<article>/<section>
    content_html = html
    for tag in ['main', 'article', 'section']:
        match = re.search(f'<{tag}[^>]*>(.*?)</{tag}>', html, re.IGNORECASE | re.DOTALL)
        if match:
            content_html = match.group(1)
            break

    # Strip scripts/styles/headings (h1 is navigation context, not citable content body)
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', content_html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.IGNORECASE | re.DOTALL)
    # BUG FIX: remove H1 from content (it's the title, not a body sentence)
    text = re.sub(r'<h1[^>]*>.*?</h1>', ' ', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    words = text.split()
    first_100 = ' '.join(words[:100])
    first_30_pct = ' '.join(words[:max(1, len(words) // 3)])

    CITABLE_PATTERNS = [
        r'\b\d+(?:\.\d+)?\s*(?:percent|%)\b',
        r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|M|B))?\b',
        r'\b(?:first|only|largest|fastest|most|best|top\s+\d)\b.{0,30}\b(?:in|of|for)\b',
        r'\b(?:founded|launched|acquired|raised)\s+in\s+\d{4}\b',
        r'\b\d+\s+(?:companies|customers|users|clients|people|employees|brands|sites)\b',
        r'\b\d{1,3}(?:,\d{3})+\b',                   # large numbers with commas
        r'\b\d+\s*(?:million|billion|thousand)\b',
    ]

    VAGUE_OPENERS = [
        r"^(?:in today'?s|in the modern|in this day|welcome to|are you looking|have you ever)",
        r"^(?:in recent years|over the past|with the rise of|as the world|the world of)",
        r"^(?:whether you'?re|if you'?re looking|when it comes to|for many businesses)",
    ]

    facts_first_100 = 0
    fact_examples = []
    for p in CITABLE_PATTERNS:
        m = re.findall(p, first_100, re.IGNORECASE)
        facts_first_100 += len(m)
        if m and len(fact_examples) < 3:
            fact_examples.append(m[0])

    facts_first_30_pct = sum(len(re.findall(p, first_30_pct, re.IGNORECASE)) for p in CITABLE_PATTERNS)

    first_20_words = ' '.join(words[:20]).lower()
    has_vague_opener = any(re.match(p, first_20_words, re.IGNORECASE) for p in VAGUE_OPENERS)

    return {
        "word_count": len(words),
        "citable_facts_first_100_words": facts_first_100,
        "citable_facts_first_30_pct": facts_first_30_pct,
        "has_citable_fact_upfront": facts_first_100 >= 1,
        "has_vague_opener": has_vague_opener,
        "fact_examples": fact_examples,
        "first_100_snippet": first_100[:200],
    }


def check_commercial_independence(html, base_url=""):
    """
    CEA-010: Commercial independence signal — 2nd highest scored trust signal
    in the SIGI-2026-021 taxonomy (9.0/10 out of 77 signals).

    Research basis:
      - SIGI-2026-021: "No-paid-placement declaration" = 9.0/10 (only behind proprietary data at 9.5)
      - Palmata: "weak proof" + "commercial conflict" are top reasons AI skips content
      - Peec AI: editorial sources earn higher citation rates than pure corporate pages
      - 9 of 10 top SIGI signals operate at inference time (detectable from HTML)
    """
    text_lower = html.lower()

    signals_found = []

    # Signal 1: Editorial methodology / review policy declared in text
    if re.search(
        r'(?:editorial\s+(?:policy|guidelines?|independence)|review\s+methodology|'
        r'how\s+we\s+(?:test|review|rate|score)|our\s+(?:methodology|testing\s+process|'
        r'evaluation\s+criteria|scoring\s+system|selection\s+criteria))',
        text_lower
    ):
        signals_found.append('editorial_policy_declared')

    # Signal 2: Link to editorial/disclosure/about page
    if re.search(
        r'href=["\'][^"\']*(?:editorial.policy|review.methodology|disclosur|about.us|'
        r'transparency|our.approach)[^"\']*["\']',
        html, re.IGNORECASE
    ):
        signals_found.append('disclosure_page_linked')

    # Signal 3: Affiliate/sponsored content disclosure (shows adherence to guidelines)
    if re.search(
        r'(?:affiliate\s+disclosure|sponsored\s+content|we\s+(?:may|might)\s+earn|'
        r'commission(?:s)?\s+(?:from|when|if)|this\s+post\s+(?:contains|may\s+contain)\s+affiliate)',
        text_lower
    ):
        signals_found.append('affiliate_disclosure_present')

    # Signal 4: Fact-checked / reviewed by (two-author credibility signal)
    if re.search(
        r'(?:fact.check(?:ed)?|reviewed|medically\s+reviewed|clinically\s+reviewed|'
        r'verified|approved)\s+by',
        text_lower
    ):
        signals_found.append('fact_checked_or_reviewed_by')

    # Signal 5: "Updated by" / "last reviewed by" editor
    if re.search(r'(?:updated|reviewed|edited)\s+by\s+[A-Z]', html):
        signals_found.append('editor_updated_signal')

    # Signal 6 (negative): High affiliate link density without any disclosure = red flag
    affiliate_params = re.findall(
        r'href=["\'][^"\']*[?&](?:ref=|aff=|affid=|affiliate=|partner=|utm_source=affiliate)[^"\']*["\']',
        html, re.IGNORECASE
    )
    affiliate_count = len(affiliate_params)

    return {
        "independence_signals_count": len(signals_found),
        "signals_found": signals_found,
        "has_commercial_independence_signal": len(signals_found) > 0,
        "affiliate_link_count": affiliate_count,
        "high_affiliate_density": affiliate_count > 5,
        "no_signals_and_high_affiliate": len(signals_found) == 0 and affiliate_count > 5,
    }


def detect_answer_capsules(html):
    """
    Detect 'answer capsules' — 40–60 word direct answers immediately after H2/H3 headings.
    72.4% of ChatGPT-cited pages have them (Cognism, 2026).
    An answer capsule: ≥40 words before next heading, no preamble ('great question', 'let's explore').
    """
    PREAMBLE_PATTERNS = [
        r"^(?:great question|let'?s explore|in this (?:guide|article|section)|let me explain)",
        r"^(?:when it comes to|the answer is|to answer this)",
    ]

    sections = re.split(r'<h[23][^>]*>', html, flags=re.IGNORECASE)
    capsules_found = 0
    capsule_examples = []
    sections_analyzed = 0

    for section in sections[1:6]:  # analyze up to 5 sections after H2/H3
        # Get text up to the next heading
        next_heading = re.search(r'<h[1-6]', section, re.IGNORECASE)
        if next_heading:
            section_html = section[:next_heading.start()]
        else:
            section_html = section

        text = strip_tags(section_html)
        words = [w for w in text.split() if len(w) > 1]
        sections_analyzed += 1

        if len(words) < 40:
            continue  # Too short

        first_sentence = " ".join(words[:15]).lower()
        has_preamble = any(re.match(p, first_sentence) for p in PREAMBLE_PATTERNS)

        if not has_preamble and 40 <= len(words):
            capsules_found += 1
            if len(capsule_examples) < 3:
                capsule_examples.append(" ".join(words[:12]) + "...")

    return {
        "sections_analyzed": sections_analyzed,
        "answer_capsules_found": capsules_found,
        "capsule_ratio": round(capsules_found / sections_analyzed, 2) if sections_analyzed > 0 else 0,
        "meets_threshold": capsules_found >= max(1, sections_analyzed // 2),
        "examples": capsule_examples,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: content_check.py <url>"}))
        sys.exit(1)

    url = sys.argv[1].strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    output = {
        "site": parsed.netloc,
        "base_url": base_url,
        "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pages": [],
    }

    pages_to_check = [base_url]
    # Add a blog/article page if we can find one
    try:
        _, home_html, _ = fetch_page(base_url)
        if home_html:
            blog_links = re.findall(r'href=["\'](/(?:blog|article|post|news)[^\s"\']*)["\']',
                                     home_html, re.IGNORECASE)
            if blog_links:
                pages_to_check.append(urljoin(base_url, blog_links[0]))
    except Exception:
        pass

    for page_url in pages_to_check[:2]:
        path = urlparse(page_url).path or "/"
        print(f"[*] Analyzing content extractability for {path}...", file=sys.stderr)
        status, html, error = fetch_page(page_url)

        if error or not html or status != 200:
            output["pages"].append({"url": page_url, "path": path, "error": error or f"HTTP {status}"})
            continue

        page_result = {
            "url": page_url,
            "path": path,
            "above_fold": analyze_above_fold(html),
            "headings": analyze_headings(html),
            "statistics": analyze_statistics(html),
            "paragraphs": analyze_paragraphs(html),
            "faq": detect_faq_section(html),
            "key_takeaways": detect_key_takeaways(html),
            "hedge_words": measure_hedge_words(html),
            "date_markers": detect_date_markers(html),
            "ai_cliches": detect_ai_cliches(html),
            "answer_capsules": detect_answer_capsules(html),
            # NEW: passage-level scoring (Princeton KDD 2024 + zilisrikle/geo-audit-skill)
            "passage_extractability": score_passage_extractability(html),
            # NEW: sentence quotability (Lumina SEO citability heatmap methodology)
            "quotability": score_quotability(html),
            # NEW: passage density / lede quality (Profound AI + Ahrefs Brand Radar)
            "passage_density": check_passage_density(html),
            # NEW: structured list/table ratio (Seomator AI Citability + GeoKit)
            "structured_content": check_structured_list_ratio(html),
            # NEW: named entity density (Wellows 4.8× lift; SE Ranking 2.4×; SIGI 8.0/10)
            "named_entity_density": check_named_entity_density(html),
            # NEW: semantic HTML table detection (Bigeye +400%; TryProfound 67% citation rate)
            "semantic_tables": detect_semantic_tables(html),
            # NEW: top-third citable density (Surfer 40%; SIGI 8.5/10; +17.3% lift)
            "top_third_citable": check_top_third_citable_density(html),
            # NEW: commercial independence signal (SIGI 9.0/10 — 2nd highest of 77 signals)
            "commercial_independence": check_commercial_independence(html, base_url),
        }
        output["pages"].append(page_result)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
