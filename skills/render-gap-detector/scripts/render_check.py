#!/usr/bin/env python3
"""
render_check.py — Render Gap Detector helper script
Usage: python render_check.py <url>

Fetches multiple pages using a Googlebot user-agent and analyzes raw HTML
for JS-render gaps. Read-only; no site modifications.
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

try:
    from html.parser import HTMLParser
except ImportError:
    HTMLParser = None

# Googlebot user-agent (simulates what AI crawlers often use)
GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

# SPA shell fingerprints
SPA_SHELLS = [
    '<div id="root">',
    '<div id="root"/>',
    '<div id="__next">',
    '<div id="app">',
    '<div id="app"/>',
    '<div ng-app',
    '<app-root>',
    '<div id="nuxt">',
]

# JS framework signals
JS_FRAMEWORK_SIGNALS = {
    "__NEXT_DATA__": "Next.js",
    "ng-version": "Angular",
    "_nuxt/": "Nuxt.js",
    "react-root": "React",
    "__vue__": "Vue.js",
    "data-reactroot": "React (SSR hint present but check content)",
    "window.__INITIAL_STATE__": "Generic SPA with initial state injection",
    "window.__PRELOADED_STATE__": "Generic SPA with preloaded state",
}

# Inner pages to sample for selective SSR detection
INNER_PAGE_PATHS = ["/about", "/pricing", "/product", "/services", "/features", "/blog"]

TIMEOUT = 12


def fetch_page(url):
    """Fetch a URL with Googlebot UA. Returns analysis dict."""
    headers = {
        "User-Agent": GOOGLEBOT_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    result = {
        "url": url,
        "status": None,
        "error": None,
        "word_count": 0,
        "raw_text_snippet": None,
        "page_title": None,
        "meta_description": None,
        "has_h1": False,
        "h1_text": None,
        "spa_shell_detected": False,
        "spa_shell_markers": [],
        "js_framework_signals": [],
        "has_meta_viewport": False,
        "noscript_content": False,
        "response_time_ms": None,
        "classification": None,
    }

    try:
        t0 = time.time()
        resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
        result["response_time_ms"] = int((time.time() - t0) * 1000)
        result["status"] = resp.status_code

        if resp.status_code != 200:
            result["classification"] = "fully_blocked"
            return result

        html = resp.text
        result["raw_html_length"] = len(html)

        # ---- Title ----
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if title_match:
            result["page_title"] = re.sub(r"\s+", " ", title_match.group(1)).strip()

        # ---- Meta description ----
        meta_match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']',
            html, re.IGNORECASE
        ) or re.search(
            r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']description["\']',
            html, re.IGNORECASE
        )
        if meta_match:
            result["meta_description"] = meta_match.group(1).strip()

        # ---- H1 ----
        h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
        if h1_match:
            result["has_h1"] = True
            result["h1_text"] = re.sub(r"<[^>]+>", "", h1_match.group(1)).strip()[:100]

        # ---- Meta viewport ----
        result["has_meta_viewport"] = bool(re.search(
            r'<meta[^>]+name=["\']viewport["\']', html, re.IGNORECASE
        ))

        # ---- SPA shell detection ----
        for marker in SPA_SHELLS:
            if marker.lower() in html.lower():
                result["spa_shell_detected"] = True
                result["spa_shell_markers"].append(marker)

        # ---- JS framework signals ----
        for signal, framework in JS_FRAMEWORK_SIGNALS.items():
            if signal in html:
                result["js_framework_signals"].append({"signal": signal, "framework": framework})

        # ---- Noscript fallback ----
        noscript_match = re.search(r"<noscript[^>]*>(.*?)</noscript>", html, re.IGNORECASE | re.DOTALL)
        if noscript_match:
            ns_content = re.sub(r"<[^>]+>", "", noscript_match.group(1)).strip()
            result["noscript_content"] = len(ns_content) > 30

        # ---- Word count (text only, strip HTML tags) ----
        # Remove script and style blocks first
        clean = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        clean = re.sub(r"<style[^>]*>.*?</style>", " ", clean, flags=re.IGNORECASE | re.DOTALL)
        clean = re.sub(r"<!--.*?-->", " ", clean, flags=re.DOTALL)
        clean = re.sub(r"<[^>]+>", " ", clean)  # strip remaining tags
        clean = re.sub(r"&[a-zA-Z]+;", " ", clean)  # decode common entities
        words = [w for w in clean.split() if len(w) > 1 and not w.startswith("{") and not w.startswith("[")]
        result["word_count"] = len(words)
        result["raw_text_snippet"] = " ".join(words[:30])

        # ---- Classify ----
        has_meta_desc = bool(result["meta_description"])
        if result["word_count"] < 10:
            result["classification"] = "fully_blocked"
        elif result["spa_shell_detected"] and result["word_count"] < 100:
            result["classification"] = "browser_only"
        elif result["word_count"] >= 100 and result["has_h1"] and has_meta_desc:
            result["classification"] = "raw_html_works"
        else:
            result["classification"] = "poor_semantics"

    except requests.exceptions.Timeout:
        result["error"] = "Timeout"
        result["classification"] = "fully_blocked"
    except Exception as e:
        result["error"] = str(e)
        result["classification"] = "fully_blocked"

    return result


def find_inner_pages(base_url, html=None):
    """
    Try to find inner page URLs to sample.
    Uses predefined paths; falls back to link extraction from homepage HTML.
    """
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    pages = []
    for path in INNER_PAGE_PATHS:
        pages.append(urljoin(base, path))

    # Also try to extract a few real links from homepage HTML
    if html:
        links = re.findall(r'href=["\'](/[a-zA-Z0-9\-_/]+)["\']', html)
        for link in links:
            full = urljoin(base, link)
            if full not in pages and full != base_url and len(link) > 1:
                pages.append(full)
            if len(pages) >= 6:
                break

    return pages[:4]  # cap at 4 inner pages


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: render_check.py <url>"}))
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

    # Always fetch homepage
    print("[*] Fetching homepage with Googlebot UA...", file=sys.stderr)
    homepage = fetch_page(base_url)
    output["pages"].append({"path": "/", **homepage})

    # Fetch inner pages
    homepage_html = None
    try:
        resp = requests.get(base_url, headers={"User-Agent": GOOGLEBOT_UA}, timeout=TIMEOUT)
        homepage_html = resp.text if resp.status_code == 200 else None
    except Exception:
        pass

    inner_pages = find_inner_pages(base_url, homepage_html)
    for inner_url in inner_pages:
        path = urlparse(inner_url).path or "/"
        print(f"[*] Fetching {path}...", file=sys.stderr)
        page_result = fetch_page(inner_url)
        output["pages"].append({"path": path, **page_result})

    # Summary
    classifications = [p.get("classification") for p in output["pages"]]
    output["summary"] = {
        "total_pages_sampled": len(output["pages"]),
        "raw_html_works": classifications.count("raw_html_works"),
        "browser_only": classifications.count("browser_only"),
        "poor_semantics": classifications.count("poor_semantics"),
        "fully_blocked": classifications.count("fully_blocked"),
    }

    # Collect all unique JS framework signals
    frameworks_seen = set()
    for p in output["pages"]:
        for sig in p.get("js_framework_signals", []):
            frameworks_seen.add(sig["framework"])
    output["js_frameworks_detected"] = list(frameworks_seen)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
