#!/usr/bin/env python3
"""
crawlability_check.py — Crawlability Probe helper script
Usage: python crawlability_check.py <url>

Outputs a single JSON object to stdout with raw probe results.
All HTTP requests are read-only; no site modifications are made.
"""

import sys
import json
import re
import time
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

try:
    import requests
except ImportError:
    print(json.dumps({"error": "requests library not installed. Run: pip install requests"}))
    sys.exit(1)

# AI bot user-agents — 27 bots across 3 tiers (2026 comprehensive list)
CITATION_BOTS = [  # Tier 1: blocking prevents AI citation
    "GPTBot",
    "ChatGPT-User",
    "OAI-SearchBot",
    "ClaudeBot",
    "Claude-Web",
    "anthropic-ai",
    "PerplexityBot",
    "Perplexity-User",
    "Gemini-Web",
    "Google-Extended",
    "BingBot-AI",
    "YouBot",
]
TRAINING_BOTS = [  # Tier 2: acceptable to block
    "CCBot",
    "Applebot-Extended",
    "Amazonbot",
    "DuckAssistBot",
    "FacebookBot",
    "cohere-ai",
    "AI2Bot",
]
EMERGING_BOTS = [  # Tier 3: low impact currently
    "Bytespider",
    "PetalBot",
    "SemrushBot",
    "AhrefsBot",
    "DataForSeoBot",
    "MJ12bot",
    "ia_archiver",
]
ALL_AI_BOTS = CITATION_BOTS + TRAINING_BOTS + EMERGING_BOTS

# Feed paths to probe
FEED_PATHS = ["/feed", "/rss.xml", "/atom.xml", "/feed.xml", "/feeds/posts/default"]

# AI discovery endpoint paths
AI_ENDPOINT_PATHS = ["/.well-known/ai.txt", "/ai/summary.json"]

HEADERS_DEFAULT = {
    "User-Agent": "Mozilla/5.0 (compatible; BrandAuditBot/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

TIMEOUT = 10


def safe_get(url, headers=None, allow_redirects=True):
    """GET a URL, return (status_code, content_type, body_text, redirect_chain, error)."""
    h = headers or HEADERS_DEFAULT
    try:
        resp = requests.get(url, headers=h, timeout=TIMEOUT, allow_redirects=allow_redirects)
        content_type = resp.headers.get("Content-Type", "")
        redirect_chain = [r.url for r in resp.history] if resp.history else []
        return resp.status_code, content_type, resp.text, redirect_chain, None
    except requests.exceptions.SSLError as e:
        return None, None, None, [], f"SSL error: {e}"
    except requests.exceptions.ConnectionError as e:
        return None, None, None, [], f"Connection error: {e}"
    except requests.exceptions.Timeout:
        return None, None, None, [], "Timeout"
    except Exception as e:
        return None, None, None, [], str(e)


def probe_robots_txt(base_url):
    """Fetch and parse robots.txt. Returns structured info about bot policies."""
    robots_url = urljoin(base_url, "/robots.txt")
    status, content_type, body, redirects, error = safe_get(robots_url)

    result = {
        "url": robots_url,
        "status": status,
        "error": error,
        "sitemap_declared": None,
        "bots": {},
        "raw_snippet": None,
    }

    if error or not body:
        return result

    result["raw_snippet"] = body[:500]

    # Extract Sitemap directives
    sitemaps = re.findall(r"(?i)^Sitemap:\s*(.+)$", body, re.MULTILINE)
    result["sitemap_declared"] = sitemaps if sitemaps else None

    # Parse per-bot rules using RobotFileParser
    rp = RobotFileParser()
    rp.set_url(robots_url)
    rp.parse(body.splitlines())

    for bot in ALL_AI_BOTS:
        can_fetch_root = rp.can_fetch(bot, base_url.rstrip("/") + "/")
        can_fetch_home = rp.can_fetch(bot, base_url.rstrip("/") + "/index.html")

        # Try to extract explicit Disallow rules for this bot
        disallow_rules = []
        current_agent = None
        for line in body.splitlines():
            line = line.strip()
            if line.lower().startswith("user-agent:"):
                ua = line.split(":", 1)[1].strip()
                current_agent = ua
            elif line.lower().startswith("disallow:") and current_agent:
                if current_agent == bot or current_agent == "*":
                    path = line.split(":", 1)[1].strip()
                    if path:
                        disallow_rules.append(path)

        result["bots"][bot] = {
            "can_fetch_root": can_fetch_root,
            "explicit_disallow_rules": disallow_rules,
            "fully_blocked": not can_fetch_root and not can_fetch_home,
        }

    return result


def probe_llms_txt(base_url):
    """Fetch /llms.txt and assess its validity."""
    llms_url = urljoin(base_url, "/llms.txt")
    # First try without following redirects to detect redirect chains
    status_noredir, _, _, _, _ = safe_get(llms_url, allow_redirects=False)
    status, content_type, body, redirects, error = safe_get(llms_url)

    result = {
        "url": llms_url,
        "status": status,
        "content_type": content_type,
        "error": error,
        "redirect_chain": redirects,
        "redirect_count": len(redirects),
        "starts_with_hash": False,
        "word_count": 0,
        "first_100_chars": None,
        "first_200_bytes_has_html": False,
    }

    if error or not body:
        return result

    result["first_100_chars"] = body[:100]
    result["starts_with_hash"] = body.lstrip().startswith("#")
    result["word_count"] = len(body.split())
    result["first_200_bytes_has_html"] = "<html" in body[:200].lower()

    return result


def probe_sitemap(base_url, declared_sitemaps=None):
    """Probe sitemap presence and lastmod freshness."""
    candidates = declared_sitemaps or []
    if not any("/sitemap.xml" in s for s in candidates):
        candidates = [urljoin(base_url, "/sitemap.xml")] + candidates

    results = []
    for sitemap_url in candidates[:3]:  # cap at 3
        status, content_type, body, _, error = safe_get(sitemap_url)
        entry = {
            "url": sitemap_url,
            "status": status,
            "error": error,
            "lastmod_count": 0,
            "lastmod_dates": [],
        }
        if body and status == 200:
            lastmods = re.findall(r"<lastmod>(.*?)</lastmod>", body, re.IGNORECASE)
            entry["lastmod_count"] = len(lastmods)
            entry["lastmod_dates"] = lastmods[:5]  # sample first 5
        results.append(entry)

    return results


def probe_feeds(base_url):
    """Check for RSS/Atom feed endpoints."""
    results = []
    for path in FEED_PATHS:
        feed_url = urljoin(base_url, path)
        status, content_type, body, _, error = safe_get(feed_url)
        results.append({
            "url": feed_url,
            "status": status,
            "content_type": content_type,
            "error": error,
            "looks_like_feed": (
                status == 200 and body is not None and
                any(marker in (body or "")[:500] for marker in ["<rss", "<feed", "<channel", "<?xml"])
            ),
        })
    return results


def probe_ai_endpoints(base_url):
    """Check /.well-known/ai.txt and /ai/summary.json."""
    results = []
    for path in AI_ENDPOINT_PATHS:
        ep_url = urljoin(base_url, path)
        status, content_type, body, _, error = safe_get(ep_url)
        results.append({
            "url": ep_url,
            "status": status,
            "content_type": content_type,
            "error": error,
        })
    return results


def probe_bot_enforcement(base_url, robots_info):
    """
    Test whether a citation bot actually gets blocked at the server/CDN level.
    Checks ALL citation bots (not just those blocked in robots.txt) because
    CDN/WAF rules (e.g. Cloudflare "Block AI Bots") override robots.txt silently.
    This is the most common silent citation killer.
    """
    # Always probe the top 5 citation bots regardless of robots.txt state
    results = []
    # Get browser baseline first
    browser_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    _, _, browser_body, _, _ = safe_get(base_url, headers={"User-Agent": browser_ua, "Accept": "text/html,*/*"})
    browser_word_count = len(browser_body.split()) if browser_body else 0

    for bot in CITATION_BOTS[:6]:  # Top 6 citation bots
        bot_headers = {
            "User-Agent": bot,
            "Accept": "text/html,application/xhtml+xml,*/*",
        }
        status, content_type, body, _, error = safe_get(base_url, headers=bot_headers)
        word_count = len(body.split()) if body else 0

        # CDN/WAF block indicators
        cdn_blocked = status in (403, 429, 503) or (
            body and any(phrase in body.lower() for phrase in
                         ["just a moment", "cf-ray", "cloudflare", "access denied",
                          "bot protection", "ddos protection"])
        )

        # JS-dependency: bot gets significantly less content than browser
        js_dependent = browser_word_count > 0 and word_count < (browser_word_count * 0.3)

        robots_txt_blocked = robots_info["bots"].get(bot, {}).get("fully_blocked", False)

        results.append({
            "bot": bot,
            "robots_txt_blocked": robots_txt_blocked,
            "actual_status": status,
            "actual_word_count": word_count,
            "browser_baseline_words": browser_word_count,
            "cdn_waf_blocked": cdn_blocked,
            "js_dependent": js_dependent,
            "content_ratio_vs_browser": round(word_count / browser_word_count, 2) if browser_word_count > 0 else 0,
            "effective_block": cdn_blocked or status in (403, 404) or (status == 200 and word_count < 20),
            "error": error,
        })

    return results


def check_oai_searchbot_vs_gptbot(robots_info):
    """
    Detect the #1 silent citation killer: blocking GPTBot (training) but not
    OAI-SearchBot (citation). These are separate bots with different purposes.
    GPTBot = training data crawl (acceptable to block)
    OAI-SearchBot = ChatGPT Search RAG index (blocking = invisible to ChatGPT citations)
    ChatGPT-User = user-triggered browsing (blocking = ChatGPT can't browse to your site)
    """
    gptbot = robots_info["bots"].get("GPTBot", {})
    oai_searchbot = robots_info["bots"].get("OAI-SearchBot", {})
    chatgpt_user = robots_info["bots"].get("ChatGPT-User", {})

    gptbot_blocked = gptbot.get("fully_blocked", False)
    oai_blocked = oai_searchbot.get("fully_blocked", False)
    chatgpt_user_blocked = chatgpt_user.get("fully_blocked", False)

    return {
        "gptbot_blocked": gptbot_blocked,
        "oai_searchbot_blocked": oai_blocked,
        "chatgpt_user_blocked": chatgpt_user_blocked,
        "training_blocked_citation_allowed": gptbot_blocked and not oai_blocked,
        "both_blocked": gptbot_blocked and oai_blocked,
        "both_allowed": not gptbot_blocked and not oai_blocked,
        "policy_note": (
            "OPTIMAL: training blocked, citation allowed" if gptbot_blocked and not oai_blocked
            else "CRITICAL: both blocked — invisible to ChatGPT Search" if gptbot_blocked and oai_blocked
            else "OPEN: both allowed (acceptable)" if not gptbot_blocked and not oai_blocked
            else "REVIEW: citation blocked, training allowed (unusual)"
        ),
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: crawlability_check.py <url>"}))
        sys.exit(1)

    url = sys.argv[1].strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Ensure trailing slash for base
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    output = {
        "site": parsed.netloc,
        "base_url": base_url,
        "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Run all probes
    print("[*] Probing robots.txt...", file=sys.stderr)
    robots = probe_robots_txt(base_url)
    output["robots_txt"] = robots

    print("[*] Probing llms.txt...", file=sys.stderr)
    output["llms_txt"] = probe_llms_txt(base_url)

    print("[*] Probing sitemap...", file=sys.stderr)
    declared = robots.get("sitemap_declared") or []
    output["sitemap"] = probe_sitemap(base_url, declared)

    print("[*] Probing feeds...", file=sys.stderr)
    output["feeds"] = probe_feeds(base_url)

    print("[*] Probing AI discovery endpoints...", file=sys.stderr)
    output["ai_endpoints"] = probe_ai_endpoints(base_url)

    print("[*] Testing bot enforcement (CDN/WAF + content ratio check)...", file=sys.stderr)
    output["bot_enforcement"] = probe_bot_enforcement(base_url, robots)

    print("[*] Checking GPTBot vs OAI-SearchBot policy distinction...", file=sys.stderr)
    output["oai_searchbot_policy"] = check_oai_searchbot_vs_gptbot(robots)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
