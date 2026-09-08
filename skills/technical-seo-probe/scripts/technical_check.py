#!/usr/bin/env python3
"""
technical_check.py — Technical SEO Probe helper script
Usage: python technical_check.py <url>

Checks technical SEO foundations required for AI indexability.
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


def fetch(url, ua=DEFAULT_UA, allow_redirects=True):
    headers = {"User-Agent": ua, "Accept": "text/html,*/*;q=0.8"}
    try:
        t0 = time.time()
        resp = requests.get(url, headers=headers, timeout=TIMEOUT,
                            allow_redirects=allow_redirects)
        elapsed = int((time.time() - t0) * 1000)
        return resp.status_code, resp.text, resp.headers, elapsed, None
    except requests.exceptions.Timeout:
        return None, None, {}, TIMEOUT * 1000, "Timeout"
    except Exception as e:
        return None, None, {}, None, str(e)


def check_https_redirect(base_url):
    """Check if HTTP redirects to HTTPS."""
    http_url = base_url.replace("https://", "http://")
    if http_url == base_url:
        return {"already_http": True}
    status, _, headers, _, error = fetch(http_url, allow_redirects=False)
    return {
        "http_status": status,
        "redirects_to_https": status in (301, 302, 308) and "https://" in headers.get("Location", ""),
        "redirect_type": status,
        "location": headers.get("Location", ""),
        "error": error,
    }


def check_meta_robots(html, response_headers):
    """Check for noindex, nosnippet, max-snippet directives."""
    # Meta robots tag
    meta_robots_match = re.search(
        r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']*)["\']',
        html or "", re.IGNORECASE
    )
    meta_robots = meta_robots_match.group(1) if meta_robots_match else None

    # X-Robots-Tag header
    x_robots = response_headers.get("X-Robots-Tag", "")

    combined = f"{meta_robots or ''} {x_robots}".lower()

    return {
        "meta_robots": meta_robots,
        "x_robots_tag": x_robots,
        "has_noindex": "noindex" in combined,
        "has_nosnippet": "nosnippet" in combined,
        "has_max_snippet_0": "max-snippet:0" in combined or "max-snippet: 0" in combined,
    }


def check_redirect_chain(url):
    """Follow redirect chain and report hops."""
    chain = []
    current = url
    max_hops = 8

    for _ in range(max_hops):
        status, _, headers, _, error = fetch(current, allow_redirects=False)
        chain.append({"url": current, "status": status, "error": error})

        if error or status not in (301, 302, 303, 307, 308):
            break

        location = headers.get("Location", "")
        if not location:
            break
        if location.startswith("/"):
            parsed = urlparse(current)
            location = f"{parsed.scheme}://{parsed.netloc}{location}"
        current = location

    return {
        "hop_count": len(chain),
        "chain": chain,
        "has_loop": len(chain) >= max_hops,
        "has_long_chain": len(chain) > 3,
    }


def check_canonical(html, page_url):
    """Extract and validate canonical tag."""
    canonical_match = re.search(
        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
        html or "", re.IGNORECASE
    )
    if not canonical_match:
        canonical_match = re.search(
            r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']canonical["\']',
            html or "", re.IGNORECASE
        )

    if not canonical_match:
        return {"has_canonical": False}

    canonical_url = canonical_match.group(1).strip()
    parsed_page = urlparse(page_url)
    parsed_canonical = urlparse(canonical_url)

    return {
        "has_canonical": True,
        "canonical_url": canonical_url,
        "is_self_referential": canonical_url == page_url,
        "is_cross_domain": parsed_canonical.netloc != parsed_page.netloc,
    }


def check_heading_hierarchy(html):
    """Validate H1-H6 nesting and detect violations."""
    headings = re.findall(r'<(h[1-6])[^>]*>(.*?)</h[1-6]>', html or "", re.IGNORECASE | re.DOTALL)
    h_levels = []
    for tag, content in headings:
        level = int(tag[1])
        text = re.sub(r"<[^>]+>", "", content).strip()[:60]
        h_levels.append({"level": level, "text": text})

    # Check for multiple H1
    h1_count = sum(1 for h in h_levels if h["level"] == 1)

    # Check for skipped levels
    violations = []
    for i in range(1, len(h_levels)):
        prev = h_levels[i-1]["level"]
        curr = h_levels[i]["level"]
        if curr > prev + 1:
            violations.append(f"H{prev} → H{curr} (skipped)")

    return {
        "total_headings": len(h_levels),
        "h1_count": h1_count,
        "heading_tree": h_levels[:15],
        "multiple_h1": h1_count > 1,
        "level_skip_violations": violations[:5],
        "has_violations": h1_count > 1 or len(violations) > 0,
    }


def check_hreflang(html):
    """Check hreflang tags."""
    hreflang_tags = re.findall(
        r'<link[^>]+hreflang=["\']([^"\']+)["\'][^>]+href=["\']([^"\']+)["\']',
        html or "", re.IGNORECASE
    )
    # Also match reversed attribute order
    hreflang_tags += re.findall(
        r'<link[^>]+href=["\']([^"\']+)["\'][^>]+hreflang=["\']([^"\']+)["\']',
        html or "", re.IGNORECASE
    )

    has_x_default = any(lang == "x-default" for lang, _ in hreflang_tags)

    # Detect multiple languages from html lang attribute
    html_lang = re.search(r'<html[^>]+lang=["\']([^"\']+)["\']', html or "", re.IGNORECASE)
    html_lang_value = html_lang.group(1) if html_lang else None

    return {
        "hreflang_count": len(hreflang_tags),
        "has_x_default": has_x_default,
        "languages_declared": list({lang for lang, _ in hreflang_tags})[:10],
        "html_lang": html_lang_value,
    }


def check_page_size(html):
    """Check HTML payload size."""
    size_bytes = len((html or "").encode("utf-8"))
    return {
        "html_size_bytes": size_bytes,
        "html_size_kb": round(size_bytes / 1024, 1),
    }


def check_broken_links(html, base_url):
    """Check a sample of internal links for 4xx errors."""
    links = re.findall(r'href=["\'](/[a-zA-Z0-9\-_/\.]+)["\']', html or "")
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    broken = []
    checked = 0
    for link in links[:15]:  # sample first 15 internal links
        full_url = urljoin(base, link)
        status, body, _, _, error = fetch(full_url)
        checked += 1
        if error or (status and status >= 400):
            broken.append({"url": full_url, "status": status, "error": error})
        if len(broken) >= 5:
            break

    return {
        "links_checked": checked,
        "broken_links": broken,
        "broken_count": len(broken),
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: technical_check.py <url>"}))
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

    print("[*] Checking HTTPS redirect...", file=sys.stderr)
    output["https_redirect"] = check_https_redirect(base_url)

    print("[*] Fetching homepage with headers...", file=sys.stderr)
    status, html, resp_headers, response_time_ms, error = fetch(base_url)
    output["homepage_status"] = status
    output["response_time_ms"] = response_time_ms
    output["error"] = error

    if html:
        print("[*] Checking meta robots / nosnippet...", file=sys.stderr)
        output["meta_robots"] = check_meta_robots(html, resp_headers)

        print("[*] Checking canonical tag...", file=sys.stderr)
        output["canonical"] = check_canonical(html, base_url)

        print("[*] Checking heading hierarchy...", file=sys.stderr)
        output["heading_hierarchy"] = check_heading_hierarchy(html)

        print("[*] Checking hreflang...", file=sys.stderr)
        output["hreflang"] = check_hreflang(html)

        print("[*] Checking page size...", file=sys.stderr)
        output["page_size"] = check_page_size(html)

        print("[*] Sampling internal links for broken check...", file=sys.stderr)
        output["broken_links"] = check_broken_links(html, base_url)

    print("[*] Checking redirect chain...", file=sys.stderr)
    output["redirect_chain"] = check_redirect_chain(base_url)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
