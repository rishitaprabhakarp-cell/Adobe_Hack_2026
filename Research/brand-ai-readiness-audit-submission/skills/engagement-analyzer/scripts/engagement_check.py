#!/usr/bin/env python3
"""
engagement_check.py — Engagement Analyzer helper script
Usage: python engagement_check.py <url>

Checks above-fold content, CTAs, paragraph lengths, response time,
dynamic state signals, and contact/about reachability. Read-only.
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

# Action verb patterns for CTA detection
CTA_VERBS = [
    "get started", "get free", "start free", "start now", "try free", "try now",
    "sign up", "sign in", "log in", "create account", "open account",
    "book a demo", "book demo", "request demo", "schedule demo",
    "download", "install", "get app", "learn more", "see pricing",
    "contact us", "talk to us", "get in touch",
    "buy now", "shop now", "order now", "add to cart",
    "subscribe", "join free", "join now",
    "watch demo", "see how", "explore",
]

# Dynamic state signals (marketplace, booking, job board)
DYNAMIC_STATE_SIGNALS = [
    "search results", "no results found", "loading", "fetching",
    "available listings", "jobs near", "flights from", "hotels in",
    "results for", "showing", "items found", "properties found",
    "book now", "check availability", "reserve",
]


def fetch_page(url, ua=DEFAULT_UA):
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    }
    try:
        t0 = time.time()
        resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
        elapsed = int((time.time() - t0) * 1000)
        return resp.status_code, resp.text, elapsed, None
    except requests.exceptions.Timeout:
        return None, None, TIMEOUT * 1000, "Timeout"
    except Exception as e:
        return None, None, None, str(e)


def strip_tags(html):
    """Strip HTML tags, script/style blocks, and decode common entities."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_above_fold_text(html, word_limit=200):
    """
    Extract the first ~200 words of static text from the body,
    excluding nav, header boilerplate as best we can.
    """
    # Try to find main content area
    main_match = re.search(
        r'<(?:main|article|section)[^>]*>(.*?)</(?:main|article|section)>',
        html, re.IGNORECASE | re.DOTALL
    )
    if main_match:
        source = main_match.group(1)
    else:
        # Fall back to body
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.IGNORECASE | re.DOTALL)
        source = body_match.group(1) if body_match else html

    text = strip_tags(source)
    words = [w for w in text.split() if len(w) > 1]
    return " ".join(words[:word_limit]), len(words)


def detect_h1(html):
    """Find H1 text in raw HTML."""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()[:120]
    return None


def detect_cta(html):
    """Detect call-to-action links or buttons with action verbs."""
    found_ctas = []
    # Look for links and buttons
    patterns = [
        r'<a[^>]*>(.*?)</a>',
        r'<button[^>]*>(.*?)</button>',
    ]
    for pat in patterns:
        for m in re.finditer(pat, html, re.IGNORECASE | re.DOTALL):
            link_text = re.sub(r"<[^>]+>", "", m.group(1)).strip().lower()
            for cta in CTA_VERBS:
                if cta in link_text:
                    found_ctas.append(link_text[:60])
                    break

    return list(set(found_ctas))[:5]


def measure_paragraphs(html):
    """Calculate average paragraph word count."""
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.IGNORECASE | re.DOTALL)
    word_counts = []
    samples = []
    for p in paragraphs:
        text = strip_tags(p)
        words = [w for w in text.split() if len(w) > 1]
        if len(words) > 5:  # skip tiny paragraphs (labels, captions)
            word_counts.append(len(words))
            if len(words) > 100:
                samples.append(" ".join(words[:20]) + "...")

    if not word_counts:
        return 0, []

    avg = sum(word_counts) / len(word_counts)
    return round(avg, 1), samples[:3]


def detect_dynamic_state(html):
    """Detect marketplace/booking/job-board dynamic content signals."""
    text_lower = html.lower()
    signals_found = []
    for signal in DYNAMIC_STATE_SIGNALS:
        if signal in text_lower:
            signals_found.append(signal)
    return signals_found


def check_contact_reachability(base_url, html):
    """Check if contact/about pages are reachable via links in HTML."""
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    contact_urls = ["/contact", "/contact-us", "/contactus", "/reach-us", "/get-in-touch"]
    about_urls = ["/about", "/about-us", "/aboutus", "/company", "/who-we-are"]

    def check_paths(paths, label):
        # Check if any path appears as a link in the HTML
        for path in paths:
            if f'href="{path}"' in html or f"href='{path}'" in html or f'href="{path}/' in html:
                return True, path, "found in HTML links"
        # Try fetching the first candidate
        url = urljoin(base, paths[0])
        try:
            resp = requests.get(url, headers={"User-Agent": DEFAULT_UA}, timeout=8, allow_redirects=True)
            if resp.status_code == 200:
                return True, url, f"HTTP {resp.status_code}"
            return False, url, f"HTTP {resp.status_code}"
        except Exception as e:
            return False, url, str(e)

    contact_ok, contact_url, contact_evidence = check_paths(contact_urls, "contact")
    about_ok, about_url, about_evidence = check_paths(about_urls, "about")

    # Also check for inline contact info
    has_email = bool(re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', html))
    has_phone = bool(re.search(r'[\+\(]?[0-9\s\-\.]{7,20}(?:ext[\s\.]?[0-9]{1,5})?', html))

    return {
        "contact_reachable": contact_ok,
        "contact_url": contact_url,
        "contact_evidence": contact_evidence,
        "about_reachable": about_ok,
        "about_url": about_url,
        "about_evidence": about_evidence,
        "has_email_inline": has_email,
        "has_phone_inline": has_phone,
    }


def check_hero_images_alt(html):
    """Find images in above-fold / hero sections missing alt text."""
    # Focus on images in header, hero, or main sections
    hero_section = re.search(
        r'<(?:header|section|div)[^>]*(?:hero|banner|jumbotron|masthead)[^>]*>(.*?)</(?:header|section|div)>',
        html, re.IGNORECASE | re.DOTALL
    )
    source = hero_section.group(1) if hero_section else html[:3000]

    missing = []
    for m in re.finditer(r'<img([^>]*)>', source, re.IGNORECASE):
        attrs = m.group(1)
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        src_match = re.search(r'src=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        src = src_match.group(1) if src_match else "(no src)"
        if alt_match is None or alt_match.group(1).strip() == "":
            if "1x1" not in src and "pixel" not in src.lower():
                missing.append(src[:80])

    return missing[:5]


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: engagement_check.py <url>"}))
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

    print("[*] Fetching homepage for engagement analysis...", file=sys.stderr)
    status, html, response_time_ms, error = fetch_page(base_url)

    output["homepage_status"] = status
    output["response_time_ms"] = response_time_ms
    output["error"] = error

    if error or not html or status != 200:
        output["above_fold"] = None
        output["cta_found"] = False
        output["ctas"] = []
        output["avg_paragraph_word_count"] = 0
        output["dynamic_state_signals"] = []
        output["contact_info"] = {}
        output["hero_images_missing_alt"] = []
        output["has_meta_viewport"] = False
        print(json.dumps(output, indent=2))
        return

    # Above-fold analysis
    above_fold_text, total_words = extract_above_fold_text(html)
    h1 = detect_h1(html)
    ctas = detect_cta(html)

    # Check if first 200 words contain a description paragraph
    has_description_paragraph = len(above_fold_text.split()) >= 30

    output["above_fold"] = {
        "text_snippet": above_fold_text[:300],
        "word_count": min(total_words, 200),
        "h1": h1,
        "has_h1": h1 is not None,
        "has_description_paragraph": has_description_paragraph,
    }
    output["cta_found"] = len(ctas) > 0
    output["ctas"] = ctas

    # Paragraph length
    avg_para, long_para_samples = measure_paragraphs(html)
    output["avg_paragraph_word_count"] = avg_para
    output["long_paragraph_samples"] = long_para_samples

    # Dynamic state signals
    output["dynamic_state_signals"] = detect_dynamic_state(html)

    # Hero images missing alt
    output["hero_images_missing_alt"] = check_hero_images_alt(html)

    # Mobile viewport
    output["has_meta_viewport"] = bool(re.search(
        r'<meta[^>]+name=["\']viewport["\']', html, re.IGNORECASE
    ))

    # Contact / about reachability
    print("[*] Checking contact/about reachability...", file=sys.stderr)
    output["contact_info"] = check_contact_reachability(base_url, html)

    # Static word count (text only, for dynamic state check)
    clean_text = strip_tags(html)
    static_words = [w for w in clean_text.split() if len(w) > 1]
    output["static_word_count"] = len(static_words)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
