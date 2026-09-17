#!/usr/bin/env python3
"""
schema_audit.py — Structured Data Auditor helper script
Usage: python schema_audit.py <url>

Samples homepage + up to 3 inner pages, extracts all JSON-LD blocks,
and reports schema richness, missing types, freshness signals, and alt-text gaps.
Read-only; no site modifications.
"""

import sys
import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin

try:
    import requests
except ImportError:
    print(json.dumps({"error": "requests library not installed. Run: pip install requests"}))
    sys.exit(1)

DEFAULT_UA = "Mozilla/5.0 (compatible; BrandAuditBot/1.0)"
GOOGLEBOT_UA = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

INNER_PAGE_PATHS = ["/product", "/about", "/pricing", "/blog", "/article", "/services", "/features", "/faq", "/docs"]

HIGH_VALUE_SCHEMA_TYPES = {
    "FAQPage", "HowTo", "speakable", "VideoObject", "Article", "BlogPosting",
    "Product", "Organization", "WebSite", "BreadcrumbList", "Review",
    "LocalBusiness", "Person", "Event", "NewsArticle",
}

TIMEOUT = 12


def now_utc():
    return datetime.now(timezone.utc)


def days_old(date_str):
    """Return number of days since a date string, or None if unparseable."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str[:19], fmt[:len(date_str)])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return (now_utc() - dt).days
        except ValueError:
            continue
    return None


def fetch_page(url, ua=DEFAULT_UA):
    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
        return resp.status_code, resp.text, None
    except requests.exceptions.Timeout:
        return None, None, "Timeout"
    except Exception as e:
        return None, None, str(e)


def extract_jsonld_blocks(html):
    """Extract all JSON-LD script blocks from HTML."""
    blocks = []
    pattern = re.compile(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL
    )
    for match in pattern.finditer(html):
        raw = match.group(1).strip()
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                blocks.extend(parsed)
            else:
                blocks.append(parsed)
        except json.JSONDecodeError:
            # Try to recover partial JSON
            blocks.append({"_parse_error": True, "_raw": raw[:200]})
    return blocks


def score_block(block):
    """Count meaningful top-level fields (exclude @context, @type, @id)."""
    if not isinstance(block, dict):
        return 0
    skip = {"@context", "@type", "@id", "_parse_error", "_raw"}
    return sum(1 for k in block if k not in skip)


def extract_schema_types(blocks):
    """Collect all @type values from a list of JSON-LD blocks."""
    types = set()
    for b in blocks:
        if isinstance(b, dict):
            t = b.get("@type")
            if isinstance(t, list):
                types.update(t)
            elif t:
                types.add(t)
    return types


def check_speakable(blocks):
    """Check if any block has a speakable property."""
    for b in blocks:
        if isinstance(b, dict) and "speakable" in b:
            return True
    return False


def extract_freshness(blocks):
    """Extract date fields from JSON-LD blocks."""
    result = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        t = b.get("@type", "")
        dates = {
            "datePublished": b.get("datePublished"),
            "dateModified": b.get("dateModified"),
            "dateReviewed": b.get("dateReviewed"),
        }
        if any(dates.values()):
            result.append({
                "@type": t,
                **dates,
                "datePublished_age_days": days_old(dates["datePublished"]),
                "dateModified_age_days": days_old(dates["dateModified"]),
            })
    return result


def extract_images_missing_alt(html):
    """Find <img> tags with empty or missing alt attributes."""
    missing = []
    # Match img tags
    for m in re.finditer(r'<img([^>]*)>', html, re.IGNORECASE):
        attrs = m.group(1)
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        src_match = re.search(r'src=["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        src = src_match.group(1) if src_match else "(no src)"
        if alt_match is None or alt_match.group(1).strip() == "":
            # Skip tracking pixels (1x1, tiny)
            if "1x1" not in src and "pixel" not in src.lower() and "spacer" not in src.lower():
                missing.append(src[:80])
    return missing


def check_html_lang(html):
    """Extract lang attribute from <html> tag."""
    m = re.search(r'<html[^>]+lang=["\']([^"\']*)["\']', html, re.IGNORECASE)
    return m.group(1) if m else None


def check_hreflang(html):
    """Count hreflang link tags."""
    return len(re.findall(r'hreflang', html, re.IGNORECASE))


def check_paywall_signals(status, html):
    """Detect paywall indicators."""
    if status == 402:
        return True, "HTTP 402 Payment Required"
    if html:
        lh = html.lower()
        for term in ["paywall", "subscribe to read", "members only", "premium content",
                     "subscription required", "log in to read"]:
            if term in lh:
                return True, f'Page body contains "{term}"'
    return False, None


def find_inner_pages(base_url, homepage_html):
    """Find inner pages to sample."""
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    pages = []

    # Try predefined paths
    for path in INNER_PAGE_PATHS:
        pages.append(urljoin(base, path))

    # Extract links from homepage
    if homepage_html:
        links = re.findall(r'href=["\'](/[a-zA-Z0-9\-_/]+)["\']', homepage_html)
        for link in links:
            full = urljoin(base, link)
            if full not in pages and full != base_url and len(link) > 2:
                pages.append(full)
            if len(pages) >= 8:
                break

    return pages[:3]  # cap at 3 inner pages


def analyze_page(url):
    """Fetch and analyze a single page."""
    status, html, error = fetch_page(url)
    result = {
        "url": url,
        "status": status,
        "error": error,
        "jsonld_blocks": [],
        "schema_types": [],
        "schema_richness": [],
        "has_speakable": False,
        "freshness_dates": [],
        "images_missing_alt": [],
        "html_lang": None,
        "hreflang_count": 0,
        "paywall_detected": False,
        "paywall_evidence": None,
        "is_accessible_for_free": None,
        "video_objects": [],
        "faq_howto_headings": [],
    }

    if error or not html or status != 200:
        return result

    # JSON-LD
    blocks = extract_jsonld_blocks(html)
    result["jsonld_blocks"] = blocks
    result["schema_types"] = list(extract_schema_types(blocks))
    result["schema_richness"] = [
        {"@type": b.get("@type", "unknown"), "field_count": score_block(b)}
        for b in blocks if isinstance(b, dict) and not b.get("_parse_error")
    ]
    result["has_speakable"] = check_speakable(blocks)
    result["freshness_dates"] = extract_freshness(blocks)

    # isAccessibleForFree
    for b in blocks:
        if isinstance(b, dict) and "isAccessibleForFree" in b:
            result["is_accessible_for_free"] = b["isAccessibleForFree"]
            break

    # VideoObject
    for b in blocks:
        if isinstance(b, dict) and b.get("@type") == "VideoObject":
            result["video_objects"].append({
                "has_transcript": "transcript" in b,
                "description_length": len(str(b.get("description", ""))),
                "name": b.get("name", "")[:60],
            })

    # Images missing alt
    result["images_missing_alt"] = extract_images_missing_alt(html)[:10]

    # Language
    result["html_lang"] = check_html_lang(html)
    result["hreflang_count"] = check_hreflang(html)

    # Paywall
    result["paywall_detected"], result["paywall_evidence"] = check_paywall_signals(status, html)

    # FAQ/HowTo heading detection
    headings = re.findall(r'<h[1-4][^>]*>(.*?)</h[1-4]>', html, re.IGNORECASE | re.DOTALL)
    faq_keywords = ["faq", "frequently asked", "how to", "how do", "step-by-step", "tutorial"]
    for h in headings:
        clean_h = re.sub(r"<[^>]+>", "", h).strip().lower()
        if any(kw in clean_h for kw in faq_keywords):
            result["faq_howto_headings"].append(clean_h[:80])

    return result


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: schema_audit.py <url>"}))
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
        "site_schema_types": [],
        "site_has_speakable": False,
        "site_has_faqpage": False,
        "site_has_howto": False,
        "site_has_video_object": False,
        "site_inlanguage": None,
    }

    # Fetch homepage
    print("[*] Analyzing homepage...", file=sys.stderr)
    homepage_result = analyze_page(base_url)
    output["pages"].append({"path": "/", **homepage_result})

    # Find and fetch inner pages
    _, homepage_html, _ = fetch_page(base_url)
    inner_pages = find_inner_pages(base_url, homepage_html)

    for inner_url in inner_pages:
        path = urlparse(inner_url).path or "/"
        print(f"[*] Analyzing {path}...", file=sys.stderr)
        page_result = analyze_page(inner_url)
        output["pages"].append({"path": path, **page_result})

    # Aggregate site-level signals
    all_types = set()
    for p in output["pages"]:
        all_types.update(p.get("schema_types", []))
        if p.get("has_speakable"):
            output["site_has_speakable"] = True

    output["site_schema_types"] = sorted(all_types)
    output["site_has_faqpage"] = "FAQPage" in all_types
    output["site_has_howto"] = "HowTo" in all_types
    output["site_has_video_object"] = "VideoObject" in all_types

    # Site-level inLanguage (from Organization/WebSite schema)
    for p in output["pages"]:
        for b in p.get("jsonld_blocks", []):
            if isinstance(b, dict) and b.get("inLanguage"):
                output["site_inlanguage"] = b["inLanguage"]
                break

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
