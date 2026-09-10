#!/usr/bin/env python3
"""
content_trust_check.py — Content Trust Auditor helper script
Usage: python content_trust_check.py <url>

Checks content scannability (RC26), search presence (RC27),
social proof, contact info, legal links, author bylines, breadcrumbs.
Read-only.
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
TIMEOUT = 15
MAX_AVG_PARA_WORDS = 80
MIN_HEADING_PER_WORDS = 300
LINK_COMPLEXITY_THRESHOLD = 40

SOCIAL_PROOF_PATTERNS = [
    r"\b\d[\d,]+\s*(customers?|users?|businesses?|companies|teams|clients)\b",
    r"trusted\s+by",
    r"\b(testimonial|review|case\s+study|success\s+stor)",
    r"rated\s+[\d.]+\s*(?:out\s+of|/)\s*[\d.]+",
    r"\b\d+\s*stars?",
]

CONTACT_PATTERNS = [
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    r"\+?[\d][\d\s\-\(\)]{8,20}",
    r"\b(contact\s+us|get\s+in\s+touch|reach\s+us|email\s+us|call\s+us)\b",
]

LEGAL_CHECKS = {
    "privacy policy": re.compile(r"privacy.{0,10}policy", re.IGNORECASE),
    "terms of service": re.compile(r"terms.{0,10}(of.{0,5})?(service|use)", re.IGNORECASE),
}

AUTHOR_PATTERNS = [
    r'(?:class|rel|itemprop)=["\'][^"\']*author[^"\']*["\']',
    r"written\s+by",
    r"by\s+<a\s",
    r'rel=["\']author["\']',
]

BREADCRUMB_PATTERNS = [
    r"BreadcrumbList",
    r'aria-label=["\'][^"\']*breadcrumb',
]


def fetch_page(url, ua=DEFAULT_UA):
    headers = {"User-Agent": ua, "Accept": "text/html,*/*;q=0.8"}
    try:
        t0 = time.time()
        resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
        elapsed = int((time.time() - t0) * 1000)
        return resp.status_code, resp.text, elapsed, None
    except Exception as e:
        return None, None, None, str(e)


def strip_tags(html):
    html = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html).strip()


def clean_html(html):
    return re.sub(r"<(script|style|nav|header|footer|noscript)[^>]*>.*?</\1>", " ",
                  html, flags=re.IGNORECASE | re.DOTALL)


def get_paragraph_word_counts(html):
    cleaned = clean_html(html)
    counts = []
    for m in re.finditer(r"<p[^>]*>(.*?)</p>", cleaned, re.IGNORECASE | re.DOTALL):
        text = strip_tags(m.group(1)).strip()
        words = text.split()
        if len(words) > 10:
            counts.append(len(words))
    return counts


def get_heading_count(html):
    return len(re.findall(r"<h[2-4][^>]*>", clean_html(html), re.IGNORECASE))


def get_word_count(html):
    return len(strip_tags(clean_html(html)).split())


def get_link_count(html):
    return len(re.findall(r"<a\s", html, re.IGNORECASE))


def has_search_input(html):
    return bool(
        re.search(r'<input[^>]+type=["\']search["\']', html, re.IGNORECASE)
        or re.search(r'role=["\']search["\']', html, re.IGNORECASE)
    )


def has_social_proof(html):
    text = strip_tags(html)
    return any(re.search(p, text, re.IGNORECASE) for p in SOCIAL_PROOF_PATTERNS)


def has_contact_info(html):
    text = strip_tags(html)
    return any(re.search(p, text, re.IGNORECASE) for p in CONTACT_PATTERNS)


def missing_legal_links(html):
    footer = re.search(r"<footer[^>]*>(.*?)</footer>", html, re.IGNORECASE | re.DOTALL)
    scope = strip_tags(footer.group(1) if footer else html[-4000:])
    return [name for name, pat in LEGAL_CHECKS.items() if not pat.search(scope)]


def has_author_byline(html):
    return any(re.search(p, html, re.IGNORECASE) for p in AUTHOR_PATTERNS)


def has_breadcrumbs(html):
    return any(re.search(p, html, re.IGNORECASE) for p in BREADCRUMB_PATTERNS)


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: content_trust_check.py <url>"}))
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
    }

    print("[*] Fetching homepage for content trust analysis...", file=sys.stderr)
    status, html, elapsed_ms, error = fetch_page(base_url)
    output["homepage_status"] = status
    output["response_time_ms"] = elapsed_ms
    output["error"] = error

    findings = []
    checks = {}

    if not html or status != 200:
        output["findings"] = findings
        output["checks"] = checks
        print(json.dumps(output, indent=2))
        return

    # ── RC26: Scannability ────────────────────────────────────────────────────
    print("[*] Checking content scannability...", file=sys.stderr)
    para_counts = get_paragraph_word_counts(html)
    total_words = get_word_count(html)
    heading_count = get_heading_count(html)
    avg_para = round(sum(para_counts) / len(para_counts), 1) if para_counts else 0

    checks["avg_paragraph_words"] = avg_para
    checks["paragraph_count"] = len(para_counts)
    checks["heading_count"] = heading_count
    checks["total_words"] = total_words

    if para_counts and avg_para > MAX_AVG_PARA_WORDS:
        findings.append({
            "id": "RC26-001",
            "title": f"Poor scannability: avg paragraph is {avg_para:.0f} words (max: {MAX_AVG_PARA_WORDS})",
            "severity": "MEDIUM",
            "evidence": f"{base_url}: {len(para_counts)} paragraphs, avg {avg_para:.0f} words. Walls of text lose both human readers and AI summarizers.",
            "suggested_action": {
                "summary": "Break paragraphs at 60-80 words max. Use bullet lists for 3+ related items. Shorter passages are quoted more reliably by AI assistants.",
                "priority": "medium",
                "effort": "medium",
            },
        })

    if total_words > 500:
        expected_headings = max(1, total_words // MIN_HEADING_PER_WORDS)
        if heading_count < expected_headings:
            findings.append({
                "id": "RC26-002",
                "title": f"Too few subheadings: {heading_count} H2-H4 for {total_words} words",
                "severity": "LOW",
                "evidence": f"{base_url}: {heading_count} subheadings for ~{total_words} words (recommended: 1 per {MIN_HEADING_PER_WORDS} words).",
                "suggested_action": {
                    "summary": "Add H2/H3 subheadings every 250-300 words. They help users scan and help AI identify distinct topics within the page.",
                    "priority": "low",
                    "effort": "low",
                    "proactive": True,
                },
            })

    # ── RC27: No search on complex sites ─────────────────────────────────────
    print("[*] Checking search and navigation complexity...", file=sys.stderr)
    link_count = get_link_count(html)
    search_present = has_search_input(html)
    checks["link_count"] = link_count
    checks["has_search"] = search_present

    if link_count > LINK_COMPLEXITY_THRESHOLD and not search_present:
        findings.append({
            "id": "RC27-001",
            "title": f"Complex site ({link_count} links) with no search functionality",
            "severity": "MEDIUM",
            "evidence": f"{base_url}: {link_count} links detected, no <input type='search'> or search role found.",
            "suggested_action": {
                "summary": "Add a header search bar. Users on large sites who can't navigate via menus will use search — without it, they leave.",
                "priority": "medium",
                "effort": "medium",
            },
        })

    # ── Trust: Social proof ───────────────────────────────────────────────────
    print("[*] Checking trust signals...", file=sys.stderr)
    sp = has_social_proof(html)
    ci = has_contact_info(html)
    missing_legal = missing_legal_links(html)
    author = has_author_byline(html)
    has_article = bool(re.search(r"<article", html, re.IGNORECASE))

    checks["has_social_proof"] = sp
    checks["has_contact_info"] = ci
    checks["missing_legal_links"] = missing_legal
    checks["has_author_byline"] = author
    checks["has_article_elements"] = has_article

    if not sp:
        findings.append({
            "id": "RC-TRUST-001",
            "title": "No social proof signals in static HTML",
            "severity": "LOW",
            "evidence": f"{base_url}: no customer count, testimonials, ratings, or 'trusted by' found in static HTML.",
            "suggested_action": {
                "summary": "Add server-rendered social proof above the fold: customer count, notable logos, or a short testimonial. Social proof reduces bounce and improves AI citation trust.",
                "priority": "low",
                "effort": "low",
                "proactive": True,
            },
        })

    if not ci:
        findings.append({
            "id": "RC-TRUST-002",
            "title": "No contact information in static HTML",
            "severity": "LOW",
            "evidence": f"{base_url}: no email, phone, or contact link found in static HTML.",
            "suggested_action": {
                "summary": "Include a contact email or /contact link in the footer. AI assistants use contact info to validate the brand as a real, reachable entity.",
                "priority": "low",
                "effort": "low",
                "proactive": True,
            },
        })

    if missing_legal:
        findings.append({
            "id": "RC-TRUST-003",
            "title": f"Missing legal links in footer: {', '.join(missing_legal)}",
            "severity": "LOW",
            "evidence": f"{base_url}: {', '.join(missing_legal)} not found in footer HTML.",
            "suggested_action": {
                "summary": "Add privacy policy and terms of service links to the footer. These are trust signals for users and AI systems evaluating brand legitimacy.",
                "priority": "low",
                "effort": "low",
                "proactive": True,
            },
        })

    if has_article and not author:
        findings.append({
            "id": "RC-TRUST-004",
            "title": "Article content with no author attribution",
            "severity": "LOW",
            "evidence": f"{base_url}: <article> elements found but no author byline or rel='author' detected.",
            "suggested_action": {
                "summary": "Add author bylines to articles using Person JSON-LD (name, jobTitle, url). Author attribution signals expertise and improves AI citation credibility (E-E-A-T).",
                "priority": "low",
                "effort": "low",
                "proactive": True,
            },
        })

    # ── Wayfinding: Breadcrumbs on inner pages ────────────────────────────────
    print("[*] Checking breadcrumbs on /about...", file=sys.stderr)
    about_url = base_url.rstrip("/") + "/about"
    about_status, about_html, _, _ = fetch_page(about_url)
    has_bc = has_breadcrumbs(about_html) if about_html else False
    checks["has_breadcrumbs_on_about"] = has_bc
    checks["about_page_status"] = about_status

    if about_status == 200 and about_html and not has_bc:
        findings.append({
            "id": "RC-NAV-001",
            "title": "No breadcrumb navigation on inner pages",
            "severity": "LOW",
            "evidence": f"{about_url}: no BreadcrumbList JSON-LD or aria-label=breadcrumb navigation found.",
            "suggested_action": {
                "summary": "Add BreadcrumbList JSON-LD to all inner pages. Breadcrumbs tell AI crawlers the page hierarchy and help AI-referred users understand where they landed.",
                "priority": "low",
                "effort": "low",
                "proactive": True,
            },
        })

    output["findings"] = findings
    output["checks"] = checks
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
