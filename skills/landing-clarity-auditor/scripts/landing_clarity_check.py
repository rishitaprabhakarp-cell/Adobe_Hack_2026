#!/usr/bin/env python3
"""
landing_clarity_check.py — Landing Clarity Auditor helper script
Usage: python landing_clarity_check.py <url>

Audits the first-5-second landing experience: H1 quality (RC24),
nav overload (RC25), CTA density (RC28), AI-referrer handling (RC30).
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
MAX_H1_WORDS = 15
MAX_NAV_ITEMS = 7
MAX_ABOVE_FOLD_CTAS = 3

CTA_VERBS = [
    "get started", "get free", "start free", "start now", "try free", "try now",
    "sign up", "sign in", "log in", "create account",
    "book demo", "book a demo", "request demo", "schedule demo",
    "download", "install", "learn more", "see pricing", "view pricing",
    "contact us", "get in touch", "get quote",
    "buy now", "shop now", "order now", "subscribe", "join free", "join now",
]

AI_REFERRER_SIGNALS = [
    r"utm_source",
    r"document\.referrer",
    r"perplexity|chatgpt|claude\.ai|gemini\.google",
    r"/from/ai|/ai-landing|/ai-summary",
    r"data-ai-summary|class=[\"'][^\"']*ai.summary",
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


def get_h1(html):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    return re.sub(r"<[^>]+>", "", m.group(1)).strip()[:200]


def get_meta(html, name):
    for pattern in [
        rf'<meta[^>]+name=["\'{name}["\']\s+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\']\s+name=["\'{name}["\']]',
        rf'<meta[^>]+property=["\'{name}["\']\s+content=["\']([^"\']+)["\']',
    ]:
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def get_nav_item_count(html):
    nav = re.search(r"<nav[^>]*>(.*?)</nav>", html, re.IGNORECASE | re.DOTALL)
    if nav:
        return len(re.findall(r"<li\b", nav.group(1), re.IGNORECASE))
    header = re.search(r"<header[^>]*>(.*?)</header>", html, re.IGNORECASE | re.DOTALL)
    if header:
        return len(re.findall(r"<a\s", header.group(1), re.IGNORECASE))
    return 0


def get_above_fold_cta_count(html):
    body = re.search(r"<body[^>]*>(.*)", html, re.IGNORECASE | re.DOTALL)
    chunk = (body.group(1) if body else html)[:8000]
    text = strip_tags(chunk).lower()
    cta_hits = sum(1 for verb in CTA_VERBS if verb in text)
    buttons = len(re.findall(r"<button[^>]*>", chunk, re.IGNORECASE))
    return cta_hits + buttons


def get_first_para_word_count(html):
    body = re.search(r"<body[^>]*>(.*)", html, re.IGNORECASE | re.DOTALL)
    chunk = (body.group(1) if body else html)[:5000]
    chunk = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", chunk,
                   flags=re.IGNORECASE | re.DOTALL)
    for m in re.finditer(r"<p[^>]*>(.*?)</p>", chunk, re.IGNORECASE | re.DOTALL):
        text = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        words = text.split()
        if len(words) > 5:
            return len(words)
    return 0


def check_ai_referrer_handling(html):
    signals = []
    for pattern in AI_REFERRER_SIGNALS:
        if re.search(pattern, html, re.IGNORECASE):
            signals.append(pattern.split("|")[0].replace("\\.", "."))
    return signals


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: landing_clarity_check.py <url>"}))
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

    print("[*] Fetching homepage for landing clarity analysis...", file=sys.stderr)
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

    # ── H1 analysis ───────────────────────────────────────────────────────────
    print("[*] Checking H1 and above-fold clarity...", file=sys.stderr)
    h1 = get_h1(html)
    h1_word_count = len(h1.split()) if h1 else 0
    meta_desc = get_meta(html, "description")
    og_desc = get_meta(html, "og:description")
    first_para_words = get_first_para_word_count(html)

    checks["h1"] = h1
    checks["h1_word_count"] = h1_word_count
    checks["meta_description"] = meta_desc
    checks["og_description"] = og_desc
    checks["first_para_word_count"] = first_para_words

    if not h1:
        findings.append({
            "id": "RC24-001",
            "title": "H1 missing — no clear headline for users or AI crawlers",
            "severity": "HIGH",
            "evidence": f"{base_url}: no <h1> tag found in page HTML.",
            "suggested_action": {
                "summary": "Add a single H1 naming the product and what it does in under 12 words. H1 is the first signal AI crawlers and users read.",
                "priority": "high",
                "effort": "low",
            },
        })
    elif h1_word_count > MAX_H1_WORDS:
        findings.append({
            "id": "RC24-002",
            "title": f"H1 too long ({h1_word_count} words) — not a clear elevator pitch",
            "severity": "MEDIUM",
            "evidence": f'{base_url}: H1 = "{h1[:120]}"',
            "suggested_action": {
                "summary": f"Shorten H1 to under {MAX_H1_WORDS} words. Users decide in 5 seconds — move detail to a subtitle.",
                "priority": "medium",
                "effort": "low",
            },
        })

    if first_para_words == 0 and not meta_desc and not og_desc:
        findings.append({
            "id": "RC24-003",
            "title": "No above-fold summary — users can't quickly understand the product",
            "severity": "MEDIUM",
            "evidence": f"{base_url}: no readable first paragraph, no meta description, no og:description.",
            "suggested_action": {
                "summary": "Add a 2-3 sentence paragraph below the H1 explaining what the product does, who it's for, and the core benefit.",
                "priority": "medium",
                "effort": "low",
            },
        })
    elif meta_desc and len(meta_desc) < 50:
        findings.append({
            "id": "RC24-004",
            "title": f"Meta description too short ({len(meta_desc)} chars) to serve as AI summary",
            "severity": "LOW",
            "evidence": f'{base_url}: meta description = "{meta_desc}"',
            "suggested_action": {
                "summary": "Expand meta description to 120-160 chars covering product, audience, and key benefit.",
                "priority": "low",
                "effort": "low",
                "proactive": True,
            },
        })

    # ── Navigation overload ───────────────────────────────────────────────────
    print("[*] Checking navigation item count...", file=sys.stderr)
    nav_count = get_nav_item_count(html)
    checks["nav_item_count"] = nav_count

    if nav_count > MAX_NAV_ITEMS:
        findings.append({
            "id": "RC25-001",
            "title": f"Navigation overload: {nav_count} items (Miller's Law max: {MAX_NAV_ITEMS})",
            "severity": "MEDIUM",
            "evidence": f"{base_url}: {nav_count} navigation items in primary nav.",
            "suggested_action": {
                "summary": "Consolidate to 5-7 primary items. Group related pages under dropdowns. Too many choices cause decision paralysis.",
                "priority": "medium",
                "effort": "medium",
            },
        })

    # ── Above-fold CTA density ────────────────────────────────────────────────
    print("[*] Checking above-fold CTA density...", file=sys.stderr)
    cta_count = get_above_fold_cta_count(html)
    checks["above_fold_cta_count"] = cta_count

    if cta_count > MAX_ABOVE_FOLD_CTAS:
        findings.append({
            "id": "RC28-001",
            "title": f"CTA overload: {cta_count} competing actions detected above fold",
            "severity": "MEDIUM",
            "evidence": f"{base_url}: {cta_count} CTA elements (buttons + action links) found in first viewport.",
            "suggested_action": {
                "summary": "Reduce to 1 primary CTA and at most 1 secondary above fold. When everything is a priority, nothing is.",
                "priority": "medium",
                "effort": "low",
            },
        })

    # ── AI-referrer handling ──────────────────────────────────────────────────
    print("[*] Checking AI-referrer handling signals...", file=sys.stderr)
    ai_signals = check_ai_referrer_handling(html)
    checks["has_ai_referrer_handling"] = len(ai_signals) > 0
    checks["ai_referrer_signals_found"] = ai_signals

    if not ai_signals:
        findings.append({
            "id": "RC30-001",
            "title": "No AI-referrer landing experience detected",
            "severity": "LOW",
            "evidence": f"{base_url}: no utm_source handling, referrer detection, or AI summary block found in homepage HTML.",
            "suggested_action": {
                "summary": "Implement a referrer-aware summary card for AI traffic (Perplexity, ChatGPT, Claude). Detect via document.referrer or utm_source=perplexity. Show 60-word summary + one CTA.",
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
