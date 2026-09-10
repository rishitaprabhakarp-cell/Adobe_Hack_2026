#!/usr/bin/env python3
"""
url_resilience_check.py — URL Resilience Checker helper script
Usage: python url_resilience_check.py <url>

Detects catch-all redirects (RC29), deep redirect chains, dead URLs in
llms.txt and sitemap.xml, and missing AI-referrer landing pages (RC30).
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
FAKE_SLUG = "/this-page-absolutely-does-not-exist-xr7q9z"
MAX_HOPS = 2
WORD_OVERLAP_THRESHOLD = 20
LLMS_SAMPLE = 3
SITEMAP_SAMPLE = 5
AI_LANDING_PATHS = ["/from/ai", "/ai-landing", "/ai"]


def fetch_page(url, ua=DEFAULT_UA, allow_redirects=True):
    headers = {"User-Agent": ua, "Accept": "text/html,text/plain,*/*;q=0.8"}
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT,
                            allow_redirects=allow_redirects)
        return resp.status_code, resp.text, resp.headers.get("Location", ""), None
    except Exception as e:
        return None, None, None, str(e)


def count_hops(start_url, ua=DEFAULT_UA):
    """Follow redirects manually using allow_redirects=False. Returns (hops, final_url)."""
    current = start_url
    seen = set()
    hops = 0
    while hops < 8:
        if current in seen:
            break
        seen.add(current)
        status, _, location, error = fetch_page(current, ua, allow_redirects=False)
        if error or status is None:
            break
        if status in (301, 302, 303, 307, 308) and location:
            if not location.startswith("http"):
                parsed = urlparse(current)
                location = f"{parsed.scheme}://{parsed.netloc}{location}"
            current = location
            hops += 1
        else:
            break
    return hops, current


def word_overlap(html_a, html_b, n=60):
    """Compute shared word count between first n words of each page's text."""
    def words(html):
        text = re.sub(r"<[^>]+>", " ", html or "")
        return set(text.split()[:n])
    return len(words(html_a) & words(html_b))


def parse_llms_urls(text, base_url, limit=LLMS_SAMPLE):
    absolute = re.findall(r"https?://[^\s\)\]\,<>\"']+", text)
    relative = re.findall(r"\]\((/[^\)]+)\)", text)
    for r in relative:
        absolute.append(base_url.rstrip("/") + r)
    seen = []
    for u in absolute:
        if u not in seen:
            seen.append(u)
    return seen[:limit]


def parse_sitemap_urls(xml, limit=SITEMAP_SAMPLE):
    return re.findall(r"<loc>\s*(https?://[^\s<]+)\s*</loc>", xml)[:limit]


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: url_resilience_check.py <url>"}))
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

    findings = []
    checks = {
        "fake_url_status": None,
        "catch_all_detected": False,
        "deep_redirect_pages": [],
        "llms_txt_dead_urls": [],
        "sitemap_dead_urls": [],
        "ai_landing_page_found": False,
        "ai_landing_paths_checked": AI_LANDING_PATHS,
    }

    # ── RC29-001: Catch-all redirect detection ────────────────────────────────
    print("[*] Testing catch-all redirect with fake URL...", file=sys.stderr)
    fake_url = base_url + FAKE_SLUG
    fake_status, fake_html, fake_location, fake_error = fetch_page(fake_url, allow_redirects=False)
    checks["fake_url_status"] = fake_status

    if fake_status == 200 and fake_html:
        home_status, home_html, _, _ = fetch_page(base_url)
        if home_html:
            overlap = word_overlap(home_html, fake_html)
            checks["fake_url_homepage_word_overlap"] = overlap
            if overlap > WORD_OVERLAP_THRESHOLD:
                checks["catch_all_detected"] = True
                findings.append({
                    "id": "RC29-001",
                    "title": "Catch-all redirect: non-existent URLs silently serve homepage content",
                    "severity": "HIGH",
                    "evidence": (
                        f"{fake_url} returned HTTP 200 with content matching the homepage "
                        f"({overlap} shared words). AI-cited URLs that expire silently show "
                        "the homepage — users arrive with no context."
                    ),
                    "suggested_action": {
                        "summary": "Return HTTP 404 for non-existent pages. Build a custom 404 with site search and popular links. Never silently redirect dead URLs to the homepage.",
                        "priority": "high",
                        "effort": "medium",
                    },
                })

    elif fake_status in (301, 302, 307, 308) and fake_location:
        parsed_location = urlparse(fake_location)
        if parsed_location.path in ("/", "") or fake_location.rstrip("/") == base_url.rstrip("/"):
            checks["catch_all_detected"] = True
            findings.append({
                "id": "RC29-001",
                "title": "Catch-all redirect: non-existent URLs redirect to homepage",
                "severity": "HIGH",
                "evidence": (
                    f"{fake_url} → HTTP {fake_status} → {fake_location}. "
                    "AI-cited URLs that no longer exist drop users at the homepage with zero context."
                ),
                "suggested_action": {
                    "summary": "Return HTTP 404 for missing pages. A custom 404 with search and navigation is far better than a silent homepage redirect.",
                    "priority": "high",
                    "effort": "medium",
                },
            })

    # ── RC29-002: Deep redirect chains ───────────────────────────────────────
    print("[*] Checking redirect chain depth on key pages...", file=sys.stderr)
    for page_path in ["", "/about", "/pricing"]:
        page_url = base_url + page_path if page_path else base_url
        hops, final = count_hops(page_url)
        if hops > MAX_HOPS:
            checks["deep_redirect_pages"].append({
                "url": page_url,
                "hops": hops,
                "final_url": final,
            })
            findings.append({
                "id": "RC29-002",
                "title": f"Deep redirect chain ({hops} hops): {page_url}",
                "severity": "MEDIUM",
                "evidence": (
                    f"{page_url} → {hops} redirect hops → {final}. "
                    "Each hop adds latency and some AI crawlers drop chains longer than 2."
                ),
                "suggested_action": {
                    "summary": f"Collapse to 1 hop. Update all internal links and sitemaps to point directly to {final}.",
                    "priority": "medium",
                    "effort": "low",
                },
            })
        time.sleep(0.2)

    # ── RC29-003: Dead URLs in llms.txt ──────────────────────────────────────
    print("[*] Sampling llms.txt URLs for dead links...", file=sys.stderr)
    llms_status, llms_body, _, _ = fetch_page(base_url + "/llms.txt")
    if llms_status == 200 and llms_body:
        llms_urls = parse_llms_urls(llms_body, base_url)
        dead = []
        for lurl in llms_urls:
            s, _, _, _ = fetch_page(lurl)
            if s not in (200, 301, 302, 303):
                dead.append(f"{lurl} → HTTP {s}")
            time.sleep(0.3)
        checks["llms_txt_dead_urls"] = dead
        if dead:
            findings.append({
                "id": "RC29-003",
                "title": f"Dead URLs in llms.txt ({len(dead)} of {len(llms_urls)} sampled)",
                "severity": "HIGH",
                "evidence": f"llms.txt URLs not resolving: {'; '.join(dead[:3])}",
                "suggested_action": {
                    "summary": "Audit llms.txt and replace or remove dead URLs. AI assistants treat llms.txt as the authoritative index — dead links reduce trust in the entire listing.",
                    "priority": "high",
                    "effort": "low",
                },
            })

    # ── RC29-004: Dead URLs in sitemap.xml ────────────────────────────────────
    print("[*] Sampling sitemap.xml URLs for dead links...", file=sys.stderr)
    sm_status, sm_body, _, _ = fetch_page(base_url + "/sitemap.xml")
    if sm_status == 200 and sm_body:
        sitemap_urls = parse_sitemap_urls(sm_body)
        dead_sm = []
        for surl in sitemap_urls:
            s, _, _, _ = fetch_page(surl)
            if s not in (200, 301, 302, 303):
                dead_sm.append(f"{surl} → HTTP {s}")
            time.sleep(0.3)
        checks["sitemap_dead_urls"] = dead_sm
        if dead_sm:
            findings.append({
                "id": "RC29-004",
                "title": f"Dead URLs in sitemap.xml ({len(dead_sm)} of {len(sitemap_urls)} sampled)",
                "severity": "MEDIUM",
                "evidence": f"sitemap.xml contains URLs returning errors: {'; '.join(dead_sm[:3])}",
                "suggested_action": {
                    "summary": "Regenerate sitemap.xml excluding 404/error pages. A stale sitemap signals poor maintenance to AI crawlers.",
                    "priority": "medium",
                    "effort": "low",
                },
            })

    # ── RC30-002: No dedicated AI landing page ────────────────────────────────
    print("[*] Checking for dedicated AI-referrer landing page...", file=sys.stderr)
    for ai_path in AI_LANDING_PATHS:
        s, _, _, _ = fetch_page(base_url + ai_path)
        if s == 200:
            checks["ai_landing_page_found"] = True
            checks["ai_landing_path"] = ai_path
            break

    if not checks["ai_landing_page_found"]:
        findings.append({
            "id": "RC30-002",
            "title": "No dedicated AI-referrer landing page",
            "severity": "LOW",
            "evidence": (
                f"Checked {', '.join(base_url + p for p in AI_LANDING_PATHS)} — "
                "none return HTTP 200."
            ),
            "suggested_action": {
                "summary": "Create /from/ai optimised for AI-referred visitors: concise 60-word summary, one CTA, one trust signal. Reference it in llms.txt so AI assistants can send users directly to it.",
                "priority": "low",
                "effort": "medium",
                "proactive": True,
            },
        })

    output["findings"] = findings
    output["checks"] = checks
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
