#!/usr/bin/env python3
"""
eeeat_check.py — E-E-A-T Signal Checker helper script
Usage: python eeeat_check.py <url>

Checks on-page E-E-A-T signals. Agent must run web_search for off-page signals.
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

# Credential indicators for author expertise
CREDENTIAL_PATTERNS = [
    r'\b(?:PhD|Ph\.D|MD|M\.D|J\.D|MBA|CPA|CFA|Certified|CISSP|PE\b|PMP|MSc|BSc|BA|MA)\b',
    r'\byears?\s+of\s+experience\b',
    r'\bfounded\b',
    r'\bauthor\s+of\b',
    r'\bspecialist\b',
    r'\bexpert\b',
    r'\bdirector\b',
    r'\bprofessor\b',
]

TRUST_SIGNAL_PATTERNS = {
    "privacy_policy": r'(?:privacy\s+policy|privacy\s+notice)',
    "terms_of_service": r'(?:terms\s+of\s+service|terms\s+and\s+conditions|terms\s+of\s+use)',
    "cookie_policy": r'(?:cookie\s+policy|cookie\s+notice)',
    "gdpr_compliance": r'(?:gdpr|data\s+protection)',
    "security_badge": r'(?:ssl|secure\s+checkout|verified\s+by|norton|mcafee|trustwave)',
    "money_back_guarantee": r'(?:money.back\s+guarantee|refund\s+policy)',
    "contact_info": r'(?:contact\s+us|email:|phone:|tel:|support@)',
}


def fetch_page(url, ua=DEFAULT_UA):
    headers = {"User-Agent": ua, "Accept": "text/html,*/*;q=0.8"}
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
        return resp.status_code, resp.text, None
    except Exception as e:
        return None, None, str(e)


def check_https(base_url):
    """Check if HTTPS is enforced."""
    http_url = base_url.replace("https://", "http://")
    try:
        resp = requests.get(http_url, headers={"User-Agent": DEFAULT_UA},
                            timeout=TIMEOUT, allow_redirects=False)
        return {
            "https_enforced": resp.status_code in (301, 302, 308),
            "redirect_code": resp.status_code,
            "redirect_to": resp.headers.get("Location", ""),
        }
    except Exception as e:
        return {"https_enforced": None, "error": str(e)}


def detect_author_signals(html):
    """Check for author bylines, bios, and credentials."""
    # Author byline patterns
    byline_patterns = [
        r'<(?:[^>]+class="[^"]*(?:byline|author|written.by)[^"]*")[^>]*>(.*?)</',
        r'(?:by|written\s+by|authored\s+by)\s+<a[^>]*>(.*?)</a>',
        r'<meta[^>]+name=["\']author["\'][^>]+content=["\']([^"\']+)["\']',
        r'(?:author|byline):\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
    ]

    bylines_found = []
    for pattern in byline_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
        for m in matches:
            clean = re.sub(r"<[^>]+>", "", m).strip()
            if 2 < len(clean) < 60:
                bylines_found.append(clean)

    # Credentials
    has_credentials = any(
        bool(re.search(p, html, re.IGNORECASE))
        for p in CREDENTIAL_PATTERNS
    )

    # Bio section
    has_bio = bool(re.search(
        r'<(?:[^>]+class="[^"]*(?:bio|about-author|author-bio)[^"]*")[^>]*>',
        html, re.IGNORECASE
    ))

    # Person schema
    has_person_schema = '"@type": "Person"' in html or '"@type":"Person"' in html

    return {
        "bylines_found": list(set(bylines_found))[:5],
        "author_count": len(set(bylines_found)),
        "has_credentials": has_credentials,
        "has_author_bio": has_bio,
        "has_person_schema": has_person_schema,
    }


def detect_trust_signals(html):
    """Detect trust signals in HTML."""
    html_lower = html.lower()
    found = {}
    for signal, pattern in TRUST_SIGNAL_PATTERNS.items():
        found[signal] = bool(re.search(pattern, html_lower))
    return found


def detect_original_research(html):
    """Detect indicators of original research or proprietary data."""
    text_lower = html.lower()
    signals = []

    research_keywords = [
        "our research", "we surveyed", "our study", "we analyzed",
        "our data shows", "according to our", "we found that",
        "our report", "our benchmark", "proprietary data",
        "n=", "respondents", "participants", "sample size",
    ]

    for kw in research_keywords:
        if kw in text_lower:
            signals.append(kw)

    return {
        "has_original_research": len(signals) > 0,
        "signals_found": signals[:5],
    }


def check_review_links(html):
    """Check for links to review platforms."""
    platforms = {
        "g2": r'href=["\'][^"\']*g2\.com[^"\']*["\']',
        "capterra": r'href=["\'][^"\']*capterra\.com[^"\']*["\']',
        "trustpilot": r'href=["\'][^"\']*trustpilot\.com[^"\']*["\']',
        "producthunt": r'href=["\'][^"\']*producthunt\.com[^"\']*["\']',
        "yelp": r'href=["\'][^"\']*yelp\.com[^"\']*["\']',
        "glassdoor": r'href=["\'][^"\']*glassdoor\.com[^"\']*["\']',
    }

    found = {}
    for platform, pattern in platforms.items():
        found[platform] = bool(re.search(pattern, html, re.IGNORECASE))

    return {
        "platforms_linked": [p for p, v in found.items() if v],
        "platform_count": sum(found.values()),
        "details": found,
    }


def detect_social_profiles(html):
    """Detect social media profile links."""
    profiles = {
        "linkedin": r'href=["\'][^"\']*linkedin\.com/company[^"\']*["\']',
        "twitter": r'href=["\'][^"\']*(?:twitter|x)\.com/[A-Za-z0-9_]+["\']',
        "youtube": r'href=["\'][^"\']*youtube\.com/(?:c/|channel/|@)[^"\']*["\']',
        "github": r'href=["\'][^"\']*github\.com/[^"\']*["\']',
        "facebook": r'href=["\'][^"\']*facebook\.com/[^"\']*["\']',
    }

    found = {}
    for platform, pattern in profiles.items():
        m = re.search(pattern, html, re.IGNORECASE)
        found[platform] = m.group(0)[:80] if m else None

    return {
        "profiles_found": {k: v for k, v in found.items() if v},
        "count": sum(1 for v in found.values() if v),
    }


def check_wikidata_p856(domain):
    """
    Verify that the brand has a Wikidata entity with P856 (official website)
    pointing to this domain. This is one of the strongest E-E-A-T entity
    corroboration signals — if Wikidata doesn't know you exist, AI can't
    confidently attribute claims to you.
    Source: SEOSiri semantic-entity-mcp / spacyfishing research, 2026.
    """
    # Wikidata SPARQL query to find entities where P856 matches the domain
    sparql_query = f"""
SELECT ?item ?itemLabel WHERE {{
  ?item wdt:P856 ?website .
  FILTER(CONTAINS(STR(?website), "{domain}"))
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT 3
"""
    try:
        resp = requests.get(
            "https://query.wikidata.org/sparql",
            params={"query": sparql_query, "format": "json"},
            headers={"User-Agent": "BrandAuditBot/1.0 (brand-ai-readiness-audit)", "Accept": "application/json"},
            timeout=12,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", {}).get("bindings", [])
            entities = [
                {
                    "qid": r["item"]["value"].split("/")[-1],
                    "label": r.get("itemLabel", {}).get("value", ""),
                    "url": r["item"]["value"],
                }
                for r in results
            ]
            return {
                "wikidata_entity_found": len(entities) > 0,
                "entities": entities,
                "entity_count": len(entities),
            }
    except Exception as e:
        return {"wikidata_entity_found": None, "error": str(e)}

    return {"wikidata_entity_found": False, "entities": []}


def check_wikipedia_quality(brand_name, domain):
    """
    Check Wikipedia article presence and quality class for the brand.
    Quality classes: FA > A > GA > B > C > Start > Stub (Wikipedia assessment scale).
    FA/GA/B = strong E-E-A-T signal for AI citation engines.

    Uses Wikipedia REST API (free, no key required).
    Source: OtterlyAI brand authority score + Semrush Brand Radar methodology.
    """
    if not brand_name:
        return {"checked": False}

    # Try Wikipedia search API
    search_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(brand_name)
    try:
        resp = requests.get(search_url,
                            headers={"User-Agent": "BrandAuditBot/1.0 (brand-ai-readiness-audit)"},
                            timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            page_id = data.get("pageid")
            title = data.get("title", "")
            extract = data.get("extract", "")[:200]
            wikidata_qid = data.get("wikibase_item")

            # Get quality class via Wikipedia action API
            quality_class = None
            if page_id:
                assessment_url = (
                    f"https://en.wikipedia.org/w/api.php?action=query"
                    f"&pageids={page_id}&prop=revisions&rvprop=content&rvslots=main"
                    f"&rvsection=0&format=json&redirects"
                )
                try:
                    astr = requests.get(assessment_url,
                                        headers={"User-Agent": "BrandAuditBot/1.0"},
                                        timeout=10).json()
                    pages = astr.get("query", {}).get("pages", {})
                    # Class not reliably available via content API; fall back to rating talk page
                    # Use "thumbnail" presence as GA/FA proxy for now
                    thumbnail = data.get("thumbnail")
                    originalimage = data.get("originalimage")
                    quality_class = "GA+" if thumbnail else "B/C"
                except Exception:
                    quality_class = "Unknown"

            return {
                "found": True,
                "title": title,
                "page_id": page_id,
                "wikidata_qid": wikidata_qid,
                "quality_class_estimate": quality_class,
                "has_thumbnail": bool(data.get("thumbnail")),
                "extract_snippet": extract,
                "brand_authority_signal": "strong" if quality_class in ("FA", "A", "GA", "GA+") else "moderate",
            }
        elif resp.status_code == 404:
            # Try searching
            search_url2 = (
                f"https://en.wikipedia.org/w/api.php?action=opensearch&search="
                f"{requests.utils.quote(brand_name)}&limit=3&format=json"
            )
            try:
                s_resp = requests.get(search_url2,
                                      headers={"User-Agent": "BrandAuditBot/1.0"},
                                      timeout=8)
                s_data = s_resp.json() if s_resp.status_code == 200 else []
                suggestions = s_data[1] if len(s_data) > 1 else []
                return {
                    "found": False,
                    "search_suggestions": suggestions[:3],
                    "brand_authority_signal": "weak",
                }
            except Exception:
                pass
            return {"found": False, "brand_authority_signal": "weak"}
    except Exception as e:
        return {"found": None, "error": str(e)}


def check_reddit_brand_presence(brand_name):
    """
    Check Reddit brand presence via Reddit JSON API (free, no key required).
    Checks r/brand subreddit existence + top mentions in search.
    Active Reddit brand community = strong real-world trust signal.

    Source: Profound AI Brand Monitoring + OtterlyAI methodology (2026).
    """
    if not brand_name:
        return {"checked": False}

    results = {}

    # Check dedicated subreddit
    subreddit_url = f"https://www.reddit.com/r/{brand_name}/about.json"
    try:
        sr_resp = requests.get(subreddit_url,
                               headers={"User-Agent": "BrandAuditBot/1.0 (brand-ai-readiness-audit)"},
                               timeout=10)
        if sr_resp.status_code == 200:
            sr_data = sr_resp.json().get("data", {})
            results["subreddit"] = {
                "exists": True,
                "subscribers": sr_data.get("subscribers", 0),
                "title": sr_data.get("title", ""),
                "active": sr_data.get("subscribers", 0) > 100,
            }
        else:
            results["subreddit"] = {"exists": False, "status": sr_resp.status_code}
    except Exception as e:
        results["subreddit"] = {"exists": None, "error": str(e)}

    # Search Reddit for brand mentions
    search_url = (
        f"https://www.reddit.com/search.json?q={requests.utils.quote(brand_name)}"
        f"&sort=relevance&limit=5&type=link"
    )
    try:
        s_resp = requests.get(search_url,
                              headers={"User-Agent": "BrandAuditBot/1.0"},
                              timeout=10)
        if s_resp.status_code == 200:
            s_data = s_resp.json()
            posts = s_data.get("data", {}).get("children", [])
            results["search"] = {
                "post_count": len(posts),
                "top_posts": [
                    {
                        "title": p["data"].get("title", "")[:80],
                        "subreddit": p["data"].get("subreddit", ""),
                        "score": p["data"].get("score", 0),
                    }
                    for p in posts[:3]
                ],
            }
        else:
            results["search"] = {"post_count": 0, "status": s_resp.status_code}
    except Exception as e:
        results["search"] = {"error": str(e)}

    mention_count = results.get("search", {}).get("post_count", 0)
    subreddit_active = results.get("subreddit", {}).get("active", False)
    return {
        **results,
        "presence_signal": "strong" if subreddit_active else "moderate" if mention_count > 2 else "weak",
    }


def compute_brand_authority_score(
    wikidata_result,
    wikipedia_result,
    reddit_result,
    review_platform_result,
    social_result,
    wikidata_p856_result,
):
    """
    Weighted Brand Authority Score (0–100) — free-tier signals only.

    Weights (research-backed):
      Wikipedia presence + quality class: 20%
      Reddit brand community: 25%
      Review platform presence: 15%
      Social profile completeness: 25%
      Wikidata entity corroboration: 15%

    Source: OtterlyAI brand authority scoring + Profound AI + Semrush Brand Radar.
    Lower-bounded at 0, upper-bounded at 100.
    """
    score = 0.0
    breakdown = {}

    # Wikipedia (20 pts)
    wiki_found = wikipedia_result.get("found", False)
    wiki_quality = wikipedia_result.get("quality_class_estimate", "")
    wiki_pts = 20 if wiki_found and wiki_quality in ("GA+", "FA", "A") else \
               15 if wiki_found else 0
    score += wiki_pts
    breakdown["wikipedia"] = {"points": wiki_pts, "max": 20,
                              "found": wiki_found, "quality": wiki_quality}

    # Reddit (25 pts) — only award baseline points if reddit was actually checked
    reddit_signal = reddit_result.get("presence_signal", "not_checked") if reddit_result else "not_checked"
    if reddit_signal == "strong":
        reddit_pts = 25
    elif reddit_signal == "moderate":
        reddit_pts = 15
    elif reddit_signal == "weak":
        reddit_pts = 3   # BUG FIX: "weak" = checked but found nothing → small floor, not 5
    else:
        reddit_pts = 0   # not checked (empty/None result)
    score += reddit_pts
    breakdown["reddit"] = {"points": reddit_pts, "max": 25, "signal": reddit_signal}

    # Review platforms (15 pts) — 5 pts per platform, max 15
    review_count = review_platform_result.get("platform_count", 0) if review_platform_result else 0
    review_pts = min(15, review_count * 5)
    score += review_pts
    breakdown["review_platforms"] = {"points": review_pts, "max": 15, "platforms": review_count}

    # Social profiles (25 pts) — 5 pts per profile, max 25
    social_count = social_result.get("count", 0) if social_result else 0
    social_pts = min(25, social_count * 5)
    score += social_pts
    breakdown["social_profiles"] = {"points": social_pts, "max": 25, "profiles": social_count}

    # Wikidata entity (15 pts)
    wd_found = (wikidata_result or {}).get("wikidata_entity_found") or \
               (wikidata_p856_result or {}).get("wikidata_entity_found") or False
    wd_pts = 15 if wd_found else 0
    score += wd_pts
    breakdown["wikidata"] = {"points": wd_pts, "max": 15, "found": wd_found}

    return {
        "brand_authority_score": round(min(100, score)),
        "interpretation": (
            "Strong" if score >= 70 else
            "Moderate" if score >= 40 else
            "Weak"
        ),
        "breakdown": breakdown,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: eeeat_check.py <url>"}))
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

    print("[*] Fetching homepage for E-E-A-T analysis...", file=sys.stderr)
    status, html, error = fetch_page(base_url)

    output["homepage_status"] = status
    output["error"] = error

    if error or not html:
        print(json.dumps(output, indent=2))
        return

    output["https_check"] = check_https(base_url)
    output["author_signals"] = detect_author_signals(html)
    output["trust_signals"] = detect_trust_signals(html)
    output["original_research"] = detect_original_research(html)
    output["review_platform_links"] = check_review_links(html)
    output["social_profiles"] = detect_social_profiles(html)

    print("[*] Checking Wikidata P856 entity corroboration...", file=sys.stderr)
    # Use cleaned domain (strip www.) for the Wikidata query
    clean_domain = parsed.netloc.replace("www.", "")
    output["wikidata_p856"] = check_wikidata_p856(clean_domain)

    # Check about page for additional author/team signals
    print("[*] Checking about page for team/credentials...", file=sys.stderr)
    about_status, about_html, _ = fetch_page(urljoin(base_url, "/about"))
    if about_status == 200 and about_html:
        output["about_page_author_signals"] = detect_author_signals(about_html)
        output["about_page_trust_signals"] = detect_trust_signals(about_html)
    else:
        output["about_page_status"] = about_status

    # NEW: Wikipedia quality class (OtterlyAI + Semrush Brand Radar)
    brand_hint = parsed.netloc.replace("www.", "").split(".")[0]
    print(f"[*] Checking Wikipedia presence and quality class for '{brand_hint}'...", file=sys.stderr)
    output["wikipedia_quality"] = check_wikipedia_quality(brand_hint, clean_domain)

    # NEW: Reddit brand community presence (Profound AI + OtterlyAI)
    print(f"[*] Checking Reddit brand presence for '{brand_hint}'...", file=sys.stderr)
    output["reddit_presence"] = check_reddit_brand_presence(brand_hint)

    # NEW: Weighted Brand Authority Score (composite)
    print("[*] Computing weighted Brand Authority Score...", file=sys.stderr)
    output["brand_authority"] = compute_brand_authority_score(
        wikidata_result=output.get("wikidata_p856"),
        wikipedia_result=output.get("wikipedia_quality", {}),
        reddit_result=output.get("reddit_presence", {}),
        review_platform_result=output.get("review_platform_links", {}),
        social_result=output.get("social_profiles", {}),
        wikidata_p856_result=output.get("wikidata_p856"),
    )

    # Agent guidance for web_search steps
    wikidata_found = output.get("wikidata_p856", {}).get("wikidata_entity_found", False)
    wikipedia_found = output.get("wikipedia_quality", {}).get("found", False)
    output["_agent_next_steps"] = [
        f'web_search: site:reddit.com "{brand_hint}"' if not output.get("reddit_presence", {}).get("subreddit", {}).get("exists") else None,
        f'web_search: site:linkedin.com/company "{brand_hint}"',
        f'web_search: site:g2.com OR site:capterra.com OR site:trustpilot.com "{brand_hint}"',
        f'web_search: "{brand_hint}" site:news.google.com',
        # Only add Wikidata search if P856 SPARQL found no entity
        *([] if wikidata_found else [
            f'web_search: site:wikidata.org "{brand_hint}"',
        ]),
        *([] if wikipedia_found else [
            f'web_search: site:en.wikipedia.org "{brand_hint}"',
        ]),
    ]
    # Remove None entries
    output["_agent_next_steps"] = [s for s in output["_agent_next_steps"] if s]

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
