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
    """Check a sample of internal links for 4xx errors. (legacy)"""
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


def check_generic_anchor_text(html):
    """
    Detect high ratio of generic anchor text — hurts AI topical relevance mapping.
    "click here", "read more", "learn more", "here", "this" etc.
    >20% generic = MEDIUM finding. >35% = HIGH.

    Source: Semrush AI audit guide 2026 + AutoGEO anchor text rule.
    """
    GENERIC_ANCHORS = re.compile(
        r'^(?:click here|read more|learn more|more info|here|this|link|page|see more|'
        r'find out more|discover|view more|get started|continue reading|details)$',
        re.IGNORECASE
    )
    anchors = re.findall(r'<a[^>]*>(.*?)</a>', html or "", re.IGNORECASE | re.DOTALL)
    clean_anchors = [re.sub(r'<[^>]+>', '', a).strip() for a in anchors]
    clean_anchors = [a for a in clean_anchors if len(a) > 0 and len(a) < 100]

    if not clean_anchors:
        return {"total_anchors": 0, "generic_ratio": 0, "high_generic": False}

    generic_count = sum(1 for a in clean_anchors if GENERIC_ANCHORS.match(a))
    ratio = round(generic_count / len(clean_anchors), 2)

    return {
        "total_anchors": len(clean_anchors),
        "generic_anchors": generic_count,
        "generic_ratio": ratio,
        "high_generic": ratio > 0.20,
        "severity": "HIGH" if ratio > 0.35 else "MEDIUM" if ratio > 0.20 else "OK",
        "examples": [a for a in clean_anchors if GENERIC_ANCHORS.match(a)][:5],
    }


def check_lang_hreflang_mismatch(html, hreflang_result):
    """
    TSEO-010: <html lang> vs hreflang consistency check.
    If lang='en' but hreflang only targets 'fr', AI engines may misassign content language.

    Source: Ahrefs AI audit guide 2026 + geo-optimizer-skill TSEO-010 definition.
    """
    # Extract html lang attribute
    lang_match = re.search(r'<html[^>]+lang=["\']([^"\']+)["\']', html or "", re.IGNORECASE)
    html_lang = lang_match.group(1).lower() if lang_match else None

    if not html_lang:
        return {"html_lang": None, "mismatch": False, "note": "No lang attribute found"}

    hreflang_tags = hreflang_result.get("hreflang_tags", []) if hreflang_result else []
    hreflang_langs = [tag.get("lang", "").lower() for tag in hreflang_tags
                      if tag.get("lang") not in (None, "x-default")]

    if not hreflang_langs:
        return {"html_lang": html_lang, "hreflang_langs": [], "mismatch": False,
                "note": "No hreflang tags found (no conflict, but also no multi-region targeting)"}

    base_lang = html_lang.split("-")[0]
    lang_in_hreflang = any(hl.startswith(base_lang) for hl in hreflang_langs)

    return {
        "html_lang": html_lang,
        "hreflang_langs": hreflang_langs[:10],
        "html_lang_in_hreflang": lang_in_hreflang,
        "mismatch": not lang_in_hreflang,
        "severity": "MEDIUM" if not lang_in_hreflang else "OK",
    }


def check_stale_last_modified(resp_headers):
    """
    Detect missing or stale Last-Modified HTTP header (>180 days).
    AI freshness signals use Last-Modified to judge content currency.
    Perplexity deprioritizes content with no Last-Modified or stale headers.

    Source: Ahrefs 2026 AI indexing freshness guide + geo-optimizer-skill freshness rule.
    """
    from email.utils import parsedate_to_datetime
    import datetime

    last_modified = resp_headers.get("Last-Modified") or resp_headers.get("last-modified")

    if not last_modified:
        return {
            "last_modified": None,
            "missing": True,
            "days_old": None,
            "stale": True,
            "severity": "MEDIUM",
        }

    try:
        lm_date = parsedate_to_datetime(last_modified)
        now = datetime.datetime.now(datetime.timezone.utc)
        days_old = (now - lm_date).days
        stale = days_old > 180
        return {
            "last_modified": last_modified,
            "missing": False,
            "days_old": days_old,
            "stale": stale,
            "severity": "MEDIUM" if stale else "OK",
        }
    except Exception:
        return {
            "last_modified": last_modified,
            "missing": False,
            "days_old": None,
            "parse_error": True,
            "stale": False,
            "severity": "LOW",
        }


def check_content_chunk_size(html):
    """
    Check if average paragraph length is >500 words — hurts RAG chunking quality.
    AI RAG systems chunk at ~512 tokens (~400 words). Oversized paragraphs split
    mid-sentence, creating incoherent context windows.

    Source: NVIDIA RAG paper 2025 + Semrush AI content audit guide 2026.
    """
    paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html or "", re.IGNORECASE | re.DOTALL)
    word_counts = []
    for p in paragraphs:
        text = re.sub(r'<[^>]+>', '', p).strip()
        wc = len(text.split())
        if wc >= 20:  # ignore short decorative paras
            word_counts.append(wc)

    if not word_counts:
        return {"paragraphs_checked": 0, "avg_words": 0, "poor_chunking": False}

    avg = round(sum(word_counts) / len(word_counts))
    oversized = [wc for wc in word_counts if wc > 500]

    return {
        "paragraphs_checked": len(word_counts),
        "avg_words_per_para": avg,
        "oversized_paragraphs": len(oversized),
        "poor_chunking": avg > 500 or len(oversized) > len(word_counts) // 3,
        "severity": "MEDIUM" if avg > 500 else "LOW" if len(oversized) > 2 else "OK",
        "max_para_words": max(word_counts),
        "recommendation": "Break paragraphs >500 words into ≤3 sentences for optimal AI RAG chunking" if avg > 500 else None,
    }


def check_freshness_multi_layer(html, resp_headers):
    """
    FRESH-001: 5-layer freshness signal sync check.
    When layers disagree by >90 days, AI uses the most pessimistic date.

    Layers checked:
      1. HTTP Last-Modified header
      2. JSON-LD dateModified
      3. OpenGraph article:modified_time
      4. Visible "Last updated" text in page (first 8000 chars)
      5. <meta name="date"> / <meta name="revised">

    Research basis:
      - Lureon AI: 76% of AI citations go to content updated within last 30 days
      - Geodocs.dev: AI engines weight freshness through 5 signal categories; must be consistent
      - AuthorityTech 2026: freshness = +47% lift (highest single signal in UC Berkeley GEO-16)
      - Content <90 days cited at 3.2× rate of stale content (Quattr/Averi.ai on Perplexity)
      - Bing: accurate lastmod explicitly critical for AI search re-crawl prioritization
    """
    import datetime

    signals: dict = {}

    # Layer 1: HTTP Last-Modified
    lm_header = resp_headers.get("Last-Modified") or resp_headers.get("last-modified")
    if lm_header:
        signals["http_last_modified"] = lm_header

    # Layer 2: JSON-LD dateModified
    jsonld_blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html or "", re.IGNORECASE | re.DOTALL
    )
    for block in jsonld_blocks:
        try:
            data = json.loads(block)
            if isinstance(data, dict) and data.get("dateModified"):
                signals["jsonld_date_modified"] = data["dateModified"]
                break
            # Handle @graph
            for item in data.get("@graph", []):
                if isinstance(item, dict) and item.get("dateModified"):
                    signals["jsonld_date_modified"] = item["dateModified"]
                    break
        except Exception:
            pass

    # Layer 3: OG article:modified_time
    og_mod = re.search(
        r'<meta[^>]+(?:property|name)=["\']article:modified_time["\'][^>]+content=["\']([^"\']+)["\']',
        html or "", re.IGNORECASE
    )
    if og_mod:
        signals["og_modified_time"] = og_mod.group(1)

    # Layer 4: visible "Last updated" text (first 8000 chars of rendered text)
    text_sample = re.sub(r'<[^>]+>', ' ', (html or "")[:8000])
    vis_date = re.search(
        r'(?:last\s+updated?|updated?:|reviewed?:|as\s+of|published:?)\s*:?\s*'
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+\d{1,2},?\s+20\d\d'
        r'|\d{1,2}/\d{1,2}/20\d\d|20\d\d-\d\d-\d\d)',
        text_sample, re.IGNORECASE
    )
    if vis_date:
        signals["visible_last_updated"] = vis_date.group(1)

    # Layer 5: <meta name="date"> or <meta name="revised">
    meta_date = re.search(
        r'<meta[^>]+name=["\'](?:date|last-modified|revised)["\'][^>]+content=["\']([^"\']+)["\']',
        html or "", re.IGNORECASE
    )
    if meta_date:
        signals["meta_date_tag"] = meta_date.group(1)

    # Parse all found dates and compute age in days
    # BUG FIX: Support HTTP date format "01 Jan 2026", ISO "2026-09-01", slash "09/2026"
    MONTH_MAP = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    today = datetime.date.today()
    dated_signals = []

    def parse_date_from_str(val):
        s = str(val)
        # ISO format: 2026-09-01 or 2026/09
        m = re.search(r'(20\d\d)[-/](0[1-9]|1[0-2])', s)
        if m:
            return int(m.group(1)), int(m.group(2))
        # HTTP date: "01 Jan 2026" or "Sun, 01 Jan 2026"
        m = re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(20\d\d)', s, re.IGNORECASE)
        if m:
            return int(m.group(3)), MONTH_MAP[m.group(2).lower()[:3]]
        # "Jan 2026" or "January 2026"
        m = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\.?\s+(20\d\d)', s, re.IGNORECASE)
        if m:
            return int(m.group(2)), MONTH_MAP[m.group(1).lower()[:3]]
        # Slash: 09/2026
        m = re.search(r'(\d{1,2})[/](20\d\d)', s)
        if m:
            return int(m.group(2)), int(m.group(1))
        return None, None

    for key, val in signals.items():
        year, month = parse_date_from_str(val)
        if year and month:
            try:
                age = (today - datetime.date(year, month, 1)).days
                dated_signals.append({"layer": key, "value": str(val)[:40], "age_days": age})
            except Exception:
                pass

    # Contradiction check
    has_contradiction = False
    contradiction_gap = 0
    if len(dated_signals) >= 2:
        ages = [d["age_days"] for d in dated_signals]
        contradiction_gap = max(ages) - min(ages)
        has_contradiction = contradiction_gap > 90

    # Freshness from best (most recent) signal
    most_recent_age = min((d["age_days"] for d in dated_signals), default=None)
    stale = most_recent_age is not None and most_recent_age > 180

    return {
        "layers_present": len(signals),
        "layers_with_dates": len(dated_signals),
        "signals": signals,
        "dated_signals": dated_signals,
        "has_contradiction": has_contradiction,
        "contradiction_gap_days": contradiction_gap,
        "has_any_freshness_signal": len(signals) > 0,
        "most_recent_age_days": most_recent_age,
        "content_stale": stale,
        "freshness_layers_missing": 5 - len(signals),
        "severity": (
            "CRITICAL" if len(signals) == 0
            else "HIGH" if has_contradiction or len(signals) == 1
            else "MEDIUM" if len(signals) < 4
            else "OK"
        ),
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

        # NEW: generic anchor text ratio (Semrush AI audit guide 2026)
        print("[*] Checking generic anchor text ratio...", file=sys.stderr)
        output["anchor_text"] = check_generic_anchor_text(html)

        # NEW: lang vs hreflang mismatch (TSEO-010)
        print("[*] Checking lang/hreflang mismatch (TSEO-010)...", file=sys.stderr)
        output["lang_hreflang"] = check_lang_hreflang_mismatch(html, output.get("hreflang"))

        # NEW: content chunk size for RAG (NVIDIA RAG 2025 + Semrush 2026)
        print("[*] Checking content chunk size for AI RAG...", file=sys.stderr)
        output["content_chunk_size"] = check_content_chunk_size(html)

    # NEW: stale Last-Modified header freshness check (Ahrefs 2026)
    print("[*] Checking Last-Modified header freshness...", file=sys.stderr)
    headers_for_check = resp_headers if html else {}
    output["last_modified"] = check_stale_last_modified(headers_for_check)

    # NEW: 5-layer freshness signal sync (FRESH-001 — Lureon 76%, AuthorityTech +47%)
    print("[*] Checking 5-layer freshness signal consistency (FRESH-001)...", file=sys.stderr)
    output["freshness_sync"] = check_freshness_multi_layer(html or "", headers_for_check)

    print("[*] Checking redirect chain...", file=sys.stderr)
    output["redirect_chain"] = check_redirect_chain(base_url)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
