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
# Cap structural HTML analyzed per page. Modern JS-framework pages (Next.js/Vercel-style)
# ship 500KB+ of markup; several detectors below use lazy DOTALL regexes whose cost on
# unbounded/minified HTML can blow up to minutes. Capping bounds worst-case regex cost
# while still covering far more than the above-fold + first few sections we care about.
MAX_HTML_CHARS = 200_000

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


def strip_script_style(html):
    """Remove script/style/comment blocks but keep other tags intact.
    Run once per page before any structural (heading/paragraph/faq) regex pass —
    inline JS/JSON bundles are the bulk of a modern page's bytes and contribute
    nothing to content analysis, only regex cost."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    return text


def strip_tags(html):
    text = strip_script_style(html)
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


def analyze_statistics(text):
    """Find statistics with and without source attribution. `text` is pre-stripped plain text."""
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

    # Question-like list items: extract <li> blocks with a single lazy scan, then test
    # each one in plain Python. Chaining 3 lazy DOTALL wildcards in one regex (the old
    # approach) re-scans to end-of-document on every near-miss <li> — quadratic on
    # pages with many list items (nav/footer menus etc).
    list_items = re.findall(r'<li[^>]*>(.*?)</li>', html, re.IGNORECASE | re.DOTALL)
    question_word_re = re.compile(r'\b(?:what|how|why|when|is|are|can|does)\b', re.IGNORECASE)
    list_question_count = sum(1 for li in list_items if "?" in li and question_word_re.search(li))
    qa_count = max(qa_count, list_question_count)

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


def measure_hedge_words(text):
    """Measure hedge word ratio in content. `text` is pre-stripped plain text."""
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


def detect_date_markers(text):
    """Detect explicit freshness date markers. `text` is pre-stripped plain text."""
    markers = DATE_MARKER_PATTERN.findall(text)
    return {
        "has_date_marker": len(markers) > 0,
        "markers_found": markers[:5],
    }


def detect_ai_cliches(text):
    """
    Detect AI-generated cliché phrases. Content that reads as AI-generated slop
    is deprioritized by citation engines (kai-cmo-harness research, 2026).
    Pages with many clichés signal low substance density.
    """
    text = text.lower()
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

        # Strip script/style/comments and cap size ONCE — bounds every regex below
        # regardless of how large or JS-heavy the source page is.
        html_struct = strip_script_style(html)[:MAX_HTML_CHARS]
        plain_text = strip_tags(html_struct)

        page_result = {
            "url": page_url,
            "path": path,
            "above_fold": analyze_above_fold(html_struct),
            "headings": analyze_headings(html_struct),
            "statistics": analyze_statistics(plain_text),
            "paragraphs": analyze_paragraphs(html_struct),
            "faq": detect_faq_section(html_struct),
            "key_takeaways": detect_key_takeaways(html_struct),
            "hedge_words": measure_hedge_words(plain_text),
            "date_markers": detect_date_markers(plain_text),
            "ai_cliches": detect_ai_cliches(plain_text),
            "answer_capsules": detect_answer_capsules(html_struct),
        }
        output["pages"].append(page_result)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
