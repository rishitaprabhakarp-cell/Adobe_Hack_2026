#!/usr/bin/env python3
"""
og_audit.py — OpenGraph & Meta Auditor helper script
Usage: python og_audit.py <url>

Checks OpenGraph tags, Twitter Card, canonical, meta description completeness.
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
TIMEOUT = 12

INNER_PATHS = ["/about", "/product", "/pricing", "/blog", "/services"]


def fetch_page(url, ua=DEFAULT_UA):
    headers = {"User-Agent": ua, "Accept": "text/html,*/*;q=0.8"}
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
        return resp.status_code, resp.text, None
    except Exception as e:
        return None, None, str(e)


def extract_og_tags(html):
    """Extract all OpenGraph meta properties."""
    og = {}
    for m in re.finditer(
        r'<meta[^>]+property=["\']og:([^"\']+)["\'][^>]+content=["\']([^"\']*)["\']',
        html, re.IGNORECASE
    ):
        og[m.group(1)] = m.group(2)
    # Also match reversed attribute order
    for m in re.finditer(
        r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+property=["\']og:([^"\']+)["\']',
        html, re.IGNORECASE
    ):
        og[m.group(2)] = m.group(1)
    return og


def extract_twitter_tags(html):
    """Extract Twitter Card meta tags."""
    tc = {}
    for m in re.finditer(
        r'<meta[^>]+(?:name|property)=["\']twitter:([^"\']+)["\'][^>]+content=["\']([^"\']*)["\']',
        html, re.IGNORECASE
    ):
        tc[m.group(1)] = m.group(2)
    return tc


def extract_meta_description(html):
    m = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']',
        html, re.IGNORECASE
    )
    if not m:
        m = re.search(
            r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']description["\']',
            html, re.IGNORECASE
        )
    return m.group(1).strip() if m else None


def extract_meta_author(html):
    m = re.search(
        r'<meta[^>]+name=["\']author["\'][^>]+content=["\']([^"\']*)["\']',
        html, re.IGNORECASE
    )
    return m.group(1).strip() if m else None


def extract_canonical(html):
    m = re.search(
        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
        html, re.IGNORECASE
    )
    if not m:
        m = re.search(
            r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']canonical["\']',
            html, re.IGNORECASE
        )
    return m.group(1).strip() if m else None


def check_og_image(og_tags, base_url):
    """Validate og:image URL."""
    image_url = og_tags.get("image", "")
    if not image_url:
        return {"present": False}

    is_absolute = image_url.startswith("http")
    if not is_absolute:
        return {
            "present": True,
            "url": image_url,
            "is_absolute": False,
            "http_status": None,
        }

    try:
        resp = requests.head(image_url, headers={"User-Agent": DEFAULT_UA},
                              timeout=8, allow_redirects=True)
        return {
            "present": True,
            "url": image_url[:80],
            "is_absolute": True,
            "http_status": resp.status_code,
            "valid": resp.status_code == 200,
        }
    except Exception as e:
        return {"present": True, "url": image_url[:80], "is_absolute": True, "error": str(e)}


def check_markdown_alternate(html):
    """Check for Markdown alternate link (emerging AI standard)."""
    m = re.search(
        r'<link[^>]+rel=["\']alternate["\'][^>]+type=["\']text/markdown["\'][^>]+href=["\']([^"\']+)["\']',
        html, re.IGNORECASE
    )
    return {
        "has_markdown_alternate": m is not None,
        "markdown_url": m.group(1) if m else None,
    }


def assess_meta_description_quality(desc):
    """Assess meta description quality for AI quotability."""
    if not desc:
        return {"present": False}

    length = len(desc)
    is_generic = any(phrase in desc.lower() for phrase in [
        "welcome to", "home page", "official website", "we are", "we provide",
        "our website", "learn more", "click here",
    ])

    return {
        "present": True,
        "text": desc[:200],
        "length": length,
        "too_short": length < 50,
        "too_long": length > 160,
        "optimal_length": 50 <= length <= 160,
        "is_generic": is_generic,
    }


def analyze_page(url, base_url):
    """Analyze a single page's OG/meta tags."""
    status, html, error = fetch_page(url)
    if error or not html or status != 200:
        return {"url": url, "status": status, "error": error}

    og = extract_og_tags(html)
    twitter = extract_twitter_tags(html)
    meta_desc = extract_meta_description(html)
    meta_author = extract_meta_author(html)
    canonical = extract_canonical(html)

    return {
        "url": url,
        "status": status,
        "og_tags": og,
        "og_title": og.get("title", ""),
        "og_description": og.get("description", ""),
        "og_type": og.get("type", ""),
        "og_site_name": og.get("site_name", ""),
        "og_image": og.get("image", ""),
        "og_image_validation": check_og_image(og, base_url),
        "twitter_card": twitter,
        "meta_description": meta_desc,
        "meta_description_quality": assess_meta_description_quality(meta_desc),
        "meta_author": meta_author,
        "canonical": canonical,
        "markdown_alternate": check_markdown_alternate(html),
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: og_audit.py <url>"}))
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

    # Analyze homepage
    print("[*] Analyzing homepage OG/meta tags...", file=sys.stderr)
    output["pages"].append(analyze_page(base_url, base_url))

    # Analyze up to 2 inner pages
    for path in INNER_PATHS[:2]:
        inner_url = urljoin(base_url, path)
        print(f"[*] Analyzing {path}...", file=sys.stderr)
        result = analyze_page(inner_url, base_url)
        if result.get("status") == 200:
            output["pages"].append(result)

    # Cross-page duplicate detection
    meta_descs = [p.get("meta_description") for p in output["pages"] if p.get("meta_description")]
    output["duplicate_meta_descriptions"] = len(meta_descs) != len(set(meta_descs))

    og_site_names = [p.get("og_site_name") for p in output["pages"] if p.get("og_site_name")]
    output["og_site_name_consistent"] = len(set(og_site_names)) <= 1

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
