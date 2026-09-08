#!/usr/bin/env python3
"""
entity_check.py — Entity Corroboration Checker helper script
Usage: python entity_check.py <url>

Extracts brand name from the site and probes Wikidata for entity disambiguation.
Read-only; no site modifications. Agent must run web_search separately for
external corroboration checks (RC6) and collision search (RC5).
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
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
TIMEOUT = 10

# Common dictionary words that have high collision risk when used as brand names
COMMON_WORDS_SAMPLE = {
    "apple", "orange", "spring", "blue", "green", "red", "stripe", "square",
    "amazon", "target", "shell", "bridge", "crown", "echo", "wave", "flow",
    "peak", "base", "core", "edge", "bolt", "beam", "dash", "spark", "arc",
    "hub", "node", "link", "loop", "axis", "nova", "orbit", "pulse", "zoom",
    "slack", "notion", "linear", "plain", "clear", "bright",
}


def fetch_page(url, ua=DEFAULT_UA):
    headers = {"User-Agent": ua, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
    try:
        resp = requests.get(url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
        return resp.status_code, resp.text, None
    except Exception as e:
        return None, None, str(e)


def extract_jsonld_blocks(html):
    blocks = []
    pattern = re.compile(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL
    )
    for match in pattern.finditer(html):
        try:
            parsed = json.loads(match.group(1).strip())
            if isinstance(parsed, list):
                blocks.extend(parsed)
            else:
                blocks.append(parsed)
        except json.JSONDecodeError:
            pass
    return blocks


def extract_brand_name(base_url, homepage_html, jsonld_blocks):
    """
    Extract brand name using multiple signals (priority order):
    1. Organization JSON-LD name field
    2. WebSite JSON-LD name field
    3. og:site_name meta tag
    4. <title> tag (first segment before separator)
    5. Domain name (fallback)
    """
    # 1. Organization JSON-LD
    for b in jsonld_blocks:
        if isinstance(b, dict) and b.get("@type") in ("Organization", "Corporation", "LocalBusiness"):
            name = b.get("name")
            if name and len(name) > 1:
                return name.strip(), "Organization JSON-LD"

    # 2. WebSite JSON-LD
    for b in jsonld_blocks:
        if isinstance(b, dict) and b.get("@type") == "WebSite":
            name = b.get("name")
            if name and len(name) > 1:
                return name.strip(), "WebSite JSON-LD"

    # 3. og:site_name
    og_match = re.search(
        r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)["\']',
        homepage_html or "", re.IGNORECASE
    )
    if og_match:
        return og_match.group(1).strip(), "og:site_name"

    # 4. Title tag — first segment
    title_match = re.search(r"<title[^>]*>(.*?)</title>", homepage_html or "", re.IGNORECASE | re.DOTALL)
    if title_match:
        title = re.sub(r"\s+", " ", title_match.group(1)).strip()
        # Split on common separators: | - — · •
        parts = re.split(r"\s*[|\-—·•]\s*", title)
        if parts:
            candidate = parts[0].strip()
            if 2 < len(candidate) < 60:
                return candidate, "page <title>"

    # 5. Domain fallback
    parsed = urlparse(base_url)
    domain = parsed.netloc.replace("www.", "").split(".")[0]
    return domain.capitalize(), "domain name"


def extract_sameas(jsonld_blocks):
    """Extract sameAs links from Organization/Corporation JSON-LD."""
    for b in jsonld_blocks:
        if isinstance(b, dict) and b.get("@type") in (
            "Organization", "Corporation", "LocalBusiness", "NGO", "GovernmentOrganization"
        ):
            same_as = b.get("sameAs", [])
            if isinstance(same_as, str):
                same_as = [same_as]
            return same_as
    return []


def categorize_sameas(same_as_links):
    """Classify sameAs links by platform."""
    categories = {
        "wikidata": None,
        "wikipedia": None,
        "crunchbase": None,
        "linkedin": None,
        "twitter": None,
        "facebook": None,
        "other": [],
    }
    for link in same_as_links:
        if "wikidata.org" in link:
            categories["wikidata"] = link
        elif "wikipedia.org" in link:
            categories["wikipedia"] = link
        elif "crunchbase.com" in link:
            categories["crunchbase"] = link
        elif "linkedin.com" in link:
            categories["linkedin"] = link
        elif "twitter.com" in link or "x.com" in link:
            categories["twitter"] = link
        elif "facebook.com" in link:
            categories["facebook"] = link
        else:
            categories["other"].append(link)
    return categories


def wikidata_lookup(brand_name):
    """Search Wikidata for the brand entity."""
    result = {
        "query": brand_name,
        "found": False,
        "qid": None,
        "label": None,
        "description": None,
        "candidates": [],
        "error": None,
    }
    try:
        params = {
            "action": "wbsearchentities",
            "search": brand_name,
            "language": "en",
            "type": "item",
            "limit": 5,
            "format": "json",
        }
        headers = {"User-Agent": "BrandAuditBot/1.0 (brand-ai-readiness-audit)"}
        resp = requests.get(WIKIDATA_API, params=params, headers=headers, timeout=TIMEOUT)
        data = resp.json()

        candidates = []
        for item in data.get("search", []):
            candidates.append({
                "qid": item.get("id"),
                "label": item.get("label"),
                "description": item.get("description", ""),
                "url": item.get("url"),
            })

        result["candidates"] = candidates

        if candidates:
            # Check if top candidate label matches brand name (case-insensitive)
            top = candidates[0]
            if top["label"].lower().strip() == brand_name.lower().strip():
                result["found"] = True
                result["qid"] = top["qid"]
                result["label"] = top["label"]
                result["description"] = top["description"]
            else:
                # Partial match — still report candidates
                result["found"] = False
                result["partial_match"] = top["label"]

    except Exception as e:
        result["error"] = str(e)

    return result


def extract_name_variants(base_url, homepage_html):
    """Check name consistency across homepage, about page, and footer."""
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    variants = {}

    # Homepage
    if homepage_html:
        og = re.search(
            r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)["\']',
            homepage_html, re.IGNORECASE
        )
        if og:
            variants["homepage_og_site_name"] = og.group(1).strip()

        title_m = re.search(r"<title[^>]*>(.*?)</title>", homepage_html, re.IGNORECASE | re.DOTALL)
        if title_m:
            variants["homepage_title"] = re.sub(r"\s+", " ", title_m.group(1)).strip()[:80]

    # About page
    about_status, about_html, _ = fetch_page(urljoin(base, "/about"))
    if about_status == 200 and about_html:
        og = re.search(
            r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)["\']',
            about_html, re.IGNORECASE
        )
        if og:
            variants["about_og_site_name"] = og.group(1).strip()

    return variants


def assess_collision_risk(brand_name):
    """Assess entity collision risk based on brand name characteristics."""
    name_lower = brand_name.lower().strip()
    risk_factors = []

    if name_lower in COMMON_WORDS_SAMPLE:
        risk_factors.append(f'"{brand_name}" is a common English word')

    if len(name_lower) <= 4:
        risk_factors.append(f'Brand name is very short ({len(name_lower)} chars) — high collision probability')

    if re.match(r'^[a-z]+$', name_lower) and len(name_lower) <= 6:
        risk_factors.append("Short single lowercase word — high overlap risk")

    return {
        "name": brand_name,
        "risk_factors": risk_factors,
        "high_risk": len(risk_factors) > 0,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: entity_check.py <url>"}))
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

    # Fetch homepage
    print("[*] Fetching homepage...", file=sys.stderr)
    status, homepage_html, error = fetch_page(base_url)
    output["homepage_status"] = status
    output["homepage_error"] = error

    # Extract JSON-LD
    jsonld_blocks = extract_jsonld_blocks(homepage_html or "")

    # Extract brand name
    print("[*] Extracting brand name...", file=sys.stderr)
    brand_name, name_source = extract_brand_name(base_url, homepage_html, jsonld_blocks)
    output["brand_name"] = brand_name
    output["brand_name_source"] = name_source

    # sameAs links
    same_as = extract_sameas(jsonld_blocks)
    output["same_as_links"] = same_as
    output["same_as_categorized"] = categorize_sameas(same_as)

    # Wikidata lookup
    print("[*] Looking up Wikidata entity...", file=sys.stderr)
    output["wikidata"] = wikidata_lookup(brand_name)

    # Collision risk assessment
    output["entity_collision_risk"] = assess_collision_risk(brand_name)

    # Name consistency
    print("[*] Checking name consistency across pages...", file=sys.stderr)
    output["name_variants"] = extract_name_variants(base_url, homepage_html)

    # Determine unique variant count
    all_values = list(output["name_variants"].values())
    unique_values = list({v.split("|")[0].strip().split("-")[0].strip() for v in all_values})
    output["name_is_consistent"] = len(unique_values) <= 1

    # Agent guidance
    output["_agent_next_steps"] = [
        f'web_search: \\"{brand_name}\\" founded',
        f'web_search: \\"{brand_name}\\" company',
        f'web_search: \\"{brand_name}\\" {parsed.netloc.split(".")[0]}',
    ]

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
